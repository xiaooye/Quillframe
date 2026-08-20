import { decode, encode, open, randomToken, seal } from "./crypto.js";
import { requireTransactionalStorage, systemClock, type Clock, type SecretLeaseInput, type SecretLeaseReceipt, type StateLike, type StorageLike, type TransactionStorageLike } from "./platform.js";

const IDLE_MS = 30 * 60 * 1000;
const ABSOLUTE_MS = 8 * 60 * 60 * 1000;
const MAX_INDEX = 2048;
const MAX_ID = 128;
const MAX_CIPHERTEXT = 256 * 1024;

type LeaseRecord = {
  schema: "quillframe_encrypted_secret_lease_v1";
  lease_id: string;
  workspace_id: string;
  session_id: string;
  purpose: SecretLeaseInput["purpose"];
  iv: string;
  ciphertext: string;
  created_at: number;
  last_accessed_at: number;
  absolute_expires_at: number;
  epoch: number;
};

type VaultTombstone = {
  schema: "quillframe_cloud_vault_tombstone_v1";
  workspace_id: string;
  session_id: string;
  destroyed_at: number;
  epoch: number;
  authority: false;
};

type VaultSessionBinding = {
  schema: "quillframe_cloud_vault_session_binding_v1";
  workspace_id: string;
  session_id: string;
  bound_at: number;
  authority: false;
};

type VaultFailure = { error: SessionVaultError };

export class SessionVaultError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

function failure(code: string, message: string): VaultFailure {
  return { error: new SessionVaultError(code, message) };
}

function boundedIdentity(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_ID && /^[A-Za-z0-9._:-]+$/.test(value);
}

function exactKeys(value: object, required: readonly string[]): boolean {
  const keys = Object.keys(value).sort();
  const expected = [...required].sort();
  return keys.length === expected.length && keys.every((key, index) => key === expected[index]);
}

function assertIdentity(workspaceId: unknown, sessionId: unknown): asserts workspaceId is string {
  if (!boundedIdentity(workspaceId) || !boundedIdentity(sessionId)) throw new SessionVaultError("invalid_secret_lease", "workspace and session identity are required");
}

function validPurpose(value: unknown): value is SecretLeaseInput["purpose"] {
  return value === "workos_access" || value === "workos_refresh" || value === "model_endpoint";
}

function readIds(value: unknown): string[] {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > MAX_INDEX || value.some((item) => !boundedIdentity(item))) throw new SessionVaultError("vault_record_invalid", "secret lease index is invalid");
  return [...new Set(value)];
}

function assertLease(record: LeaseRecord, leaseId: string): void {
  if (!record || !exactKeys(record, ["schema", "lease_id", "workspace_id", "session_id", "purpose", "iv", "ciphertext", "created_at", "last_accessed_at", "absolute_expires_at", "epoch"]) || record.schema !== "quillframe_encrypted_secret_lease_v1" || record.lease_id !== leaseId || !boundedIdentity(record.workspace_id) || !boundedIdentity(record.session_id) || !validPurpose(record.purpose) || typeof record.iv !== "string" || record.iv.length > 256 || typeof record.ciphertext !== "string" || record.ciphertext.length > MAX_CIPHERTEXT || !Number.isSafeInteger(record.created_at) || !Number.isSafeInteger(record.last_accessed_at) || !Number.isSafeInteger(record.absolute_expires_at) || !Number.isSafeInteger(record.epoch) || record.epoch < 0) throw new SessionVaultError("vault_record_invalid", "secret lease record is invalid");
}

function assertTombstone(tombstone: VaultTombstone, sessionId: string): void {
  if (!tombstone || !exactKeys(tombstone, ["schema", "workspace_id", "session_id", "destroyed_at", "epoch", "authority"]) || tombstone.schema !== "quillframe_cloud_vault_tombstone_v1" || tombstone.session_id !== sessionId || !boundedIdentity(tombstone.workspace_id) || !Number.isSafeInteger(tombstone.destroyed_at) || !Number.isSafeInteger(tombstone.epoch) || tombstone.epoch < 1 || tombstone.authority !== false) throw new SessionVaultError("vault_record_invalid", "secret session tombstone is invalid");
}

function assertVaultBinding(binding: VaultSessionBinding, workspaceId: string, sessionId: string): void {
  if (!binding || !exactKeys(binding, ["schema", "workspace_id", "session_id", "bound_at", "authority"]) || binding.schema !== "quillframe_cloud_vault_session_binding_v1" || binding.workspace_id !== workspaceId || binding.session_id !== sessionId || !boundedIdentity(binding.workspace_id) || !boundedIdentity(binding.session_id) || !Number.isSafeInteger(binding.bound_at) || binding.bound_at < 0 || binding.authority !== false) throw new SessionVaultError("vault_binding_invalid", "secret session workspace binding is invalid");
}

async function ensureVaultBindingTx(tx: TransactionStorageLike, workspaceId: string, sessionId: string, now: number): Promise<void> {
  const current = await tx.get<VaultSessionBinding>(`vault-session-binding:${sessionId}`);
  if (current !== undefined) {
    assertVaultBinding(current, workspaceId, sessionId);
    return;
  }
  await tx.put(`vault-session-binding:${sessionId}`, {
    schema: "quillframe_cloud_vault_session_binding_v1",
    workspace_id: workspaceId,
    session_id: sessionId,
    bound_at: now,
    authority: false,
  } satisfies VaultSessionBinding);
}

function requireVaultBinding(binding: VaultSessionBinding | undefined, workspaceId: string, sessionId: string): VaultSessionBinding {
  if (!binding) throw new SessionVaultError("vault_binding_missing", "secret session workspace binding is missing");
  assertVaultBinding(binding, workspaceId, sessionId);
  return binding;
}

export class SessionVault {
  private readonly clock: Clock;
  private readonly storage: StorageLike;

  constructor(
    state: StateLike,
    private readonly env: { SESSION_VAULT_KEY_B64: string },
    options: { now?: () => number } = {},
  ) {
    this.storage = requireTransactionalStorage(state.storage);
    this.clock = options.now ? { now: options.now } : systemClock;
  }

  async leaseSecret(input: SecretLeaseInput): Promise<SecretLeaseReceipt> {
    assertIdentity(input.workspace_id, input.session_id);
    if (!input.secret || typeof input.secret !== "string" || input.secret.length > 128 * 1024) throw new SessionVaultError("invalid_secret_lease", "workspace, session, and secret are required");
    if (!validPurpose(input.purpose)) throw new SessionVaultError("invalid_secret_lease", "unsupported secret purpose");
    const now = this.clock.now();
    const leaseId = `lease_${randomToken(18)}`;
    const aad = `${input.workspace_id}\n${input.session_id}\n${leaseId}\n${input.purpose}`;
    // Encryption is deliberately outside the transaction callback.
    const encrypted = await seal(encode(input.secret), this.env.SESSION_VAULT_KEY_B64, aad);
    const record: LeaseRecord = {
      schema: "quillframe_encrypted_secret_lease_v1",
      lease_id: leaseId,
      workspace_id: input.workspace_id,
      session_id: input.session_id,
      purpose: input.purpose,
      iv: encrypted.iv,
      ciphertext: encrypted.ciphertext,
      created_at: now,
      last_accessed_at: now,
      absolute_expires_at: now + ABSOLUTE_MS,
      epoch: 0,
    };
    const outcome = await this.storage.transaction(async (tx): Promise<SecretLeaseReceipt | VaultFailure> => {
      const tombstone = await tx.get<VaultTombstone>(`vault-tombstone:${input.session_id}`);
      if (tombstone !== undefined) {
        requireVaultBinding(await tx.get<VaultSessionBinding>(`vault-session-binding:${input.session_id}`), input.workspace_id, input.session_id);
        assertTombstone(tombstone, input.session_id);
        if (tombstone.workspace_id !== input.workspace_id) return failure("secret_lease_forbidden", "secret session identity does not match");
        return failure("secret_session_destroyed", "secret session was destroyed");
      }
      await ensureVaultBindingTx(tx, input.workspace_id, input.session_id, now);
      const sessionKey = `session:${input.session_id}`;
      const sessionIndex = readIds(await tx.get<string[]>(sessionKey));
      const leaseIndex = readIds(await tx.get<string[]>("lease-index"));
      await tx.put(`lease:${leaseId}`, record);
      await tx.put(sessionKey, sessionIndex.includes(leaseId) ? sessionIndex : [...sessionIndex, leaseId]);
      await tx.put("lease-index", leaseIndex.includes(leaseId) ? leaseIndex : [...leaseIndex, leaseId]);
      await scheduleNextAlarmTx(tx, now);
      return this.receipt(record);
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async readSecret(leaseId: string, identity: { workspace_id: string; session_id: string }): Promise<string> {
    if (!boundedIdentity(leaseId)) throw new SessionVaultError("secret_lease_not_found", "secret lease does not exist");
    assertIdentity(identity.workspace_id, identity.session_id);
    const now = this.clock.now();
    const probe = await this.storage.transaction(async (tx): Promise<{ record: LeaseRecord; epoch: number } | VaultFailure> => {
      const binding = await tx.get<VaultSessionBinding>(`vault-session-binding:${identity.session_id}`);
      if (!binding) return failure("vault_binding_missing", "secret session workspace binding is missing");
      requireVaultBinding(binding, identity.workspace_id, identity.session_id);
      const tombstone = await tx.get<VaultTombstone>(`vault-tombstone:${identity.session_id}`);
      if (tombstone !== undefined) {
        assertTombstone(tombstone, identity.session_id);
        if (tombstone.workspace_id !== identity.workspace_id) return failure("secret_lease_forbidden", "secret lease identity does not match");
        return failure("secret_session_destroyed", "secret session was destroyed");
      }
      const record = await tx.get<LeaseRecord>(`lease:${leaseId}`);
      if (!record) return failure("secret_lease_not_found", "secret lease does not exist");
      assertLease(record, leaseId);
      if (record.workspace_id !== identity.workspace_id || record.session_id !== identity.session_id) return failure("secret_lease_forbidden", "secret lease identity does not match");
      if (now - record.last_accessed_at > IDLE_MS || now >= record.absolute_expires_at) {
        await removeLeaseTx(tx, record);
        await scheduleNextAlarmTx(tx, now);
        return failure("secret_lease_expired", "secret lease expired");
      }
      return { record, epoch: record.epoch };
    });
    if ("error" in probe) {
      throw probe.error;
    }
    const aad = `${probe.record.workspace_id}\n${probe.record.session_id}\n${probe.record.lease_id}\n${probe.record.purpose}`;
    let plaintext: string;
    try {
      plaintext = decode(await open(probe.record, this.env.SESSION_VAULT_KEY_B64, aad));
    } catch {
      throw new SessionVaultError("secret_lease_integrity_failed", "secret lease integrity failed");
    }
    const updated = await this.storage.transaction(async (tx): Promise<boolean | VaultFailure> => {
      const binding = await tx.get<VaultSessionBinding>(`vault-session-binding:${identity.session_id}`);
      if (!binding) return failure("vault_binding_missing", "secret session workspace binding is missing");
      requireVaultBinding(binding, identity.workspace_id, identity.session_id);
      const tombstone = await tx.get<VaultTombstone>(`vault-tombstone:${identity.session_id}`);
      if (tombstone !== undefined) {
        assertTombstone(tombstone, identity.session_id);
        return failure("secret_session_destroyed", "secret session was destroyed");
      }
      const current = await tx.get<LeaseRecord>(`lease:${leaseId}`);
      if (!current) return failure("secret_lease_not_found", "secret lease does not exist");
      assertLease(current, leaseId);
      if (current.workspace_id !== identity.workspace_id || current.session_id !== identity.session_id || current.epoch !== probe.epoch || current.last_accessed_at !== probe.record.last_accessed_at || current.ciphertext !== probe.record.ciphertext) return failure("secret_lease_conflict", "secret lease changed during read");
      await tx.put(`lease:${leaseId}`, { ...current, last_accessed_at: now });
      await scheduleNextAlarmTx(tx, now);
      return true;
    });
    if (typeof updated !== "boolean") throw updated.error;
    return plaintext;
  }

  async destroySession(input: { workspace_id: string; session_id: string }): Promise<{ destroyed: number; authority: false }> {
    if (!input || typeof input !== "object") throw new SessionVaultError("secret_session_identity_required", "workspace and session identity are required");
    assertIdentity(input.workspace_id, input.session_id);
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<{ destroyed: number; authority: false } | VaultFailure> => {
      const tombstoneKey = `vault-tombstone:${input.session_id}`;
      const previous = await tx.get<VaultTombstone>(tombstoneKey);
      if (previous !== undefined) {
        requireVaultBinding(await tx.get<VaultSessionBinding>(`vault-session-binding:${input.session_id}`), input.workspace_id, input.session_id);
        assertTombstone(previous, input.session_id);
        if (previous.workspace_id !== input.workspace_id) return failure("secret_lease_forbidden", "secret session identity does not match");
        return { destroyed: 0, authority: false };
      }
      await ensureVaultBindingTx(tx, input.workspace_id, input.session_id, now);
      const sessionKey = `session:${input.session_id}`;
      const sessionIds = readIds(await tx.get<string[]>(sessionKey));
      const globalIds = readIds(await tx.get<string[]>("lease-index"));
      const candidateIds = [...new Set([...sessionIds, ...globalIds])];
      const owned: LeaseRecord[] = [];
      for (const leaseId of candidateIds) {
        const record = await tx.get<LeaseRecord>(`lease:${leaseId}`);
        if (!record) continue;
        assertLease(record, leaseId);
        if (record.workspace_id === input.workspace_id && record.session_id === input.session_id) owned.push(record);
        else if (sessionIds.includes(leaseId)) return failure("vault_record_invalid", "secret lease session binding is invalid");
      }
      const epoch = 1;
      const tombstone: VaultTombstone = {
        schema: "quillframe_cloud_vault_tombstone_v1",
        workspace_id: input.workspace_id,
        session_id: input.session_id,
        destroyed_at: now,
        epoch,
        authority: false,
      };
      for (const record of owned) await removeLeaseTx(tx, record);
      await tx.put(tombstoneKey, tombstone);
      await tx.delete(sessionKey);
      await scheduleNextAlarmTx(tx, now);
      return { destroyed: owned.length, authority: false };
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async alarm(): Promise<void> {
    const now = this.clock.now();
    await this.storage.transaction(async (tx): Promise<void> => {
      const leaseIds = readIds(await tx.get<string[]>("lease-index"));
      for (const leaseId of leaseIds) {
        const record = await tx.get<LeaseRecord>(`lease:${leaseId}`);
        if (!record) continue;
        assertLease(record, leaseId);
        const binding = await tx.get<VaultSessionBinding>(`vault-session-binding:${record.session_id}`);
        requireVaultBinding(binding, record.workspace_id, record.session_id);
        const tombstone = await tx.get<VaultTombstone>(`vault-tombstone:${record.session_id}`);
        if (tombstone !== undefined) {
          assertTombstone(tombstone, record.session_id);
          if (tombstone.workspace_id !== record.workspace_id) throw new SessionVaultError("vault_record_invalid", "secret session tombstone identity is invalid");
          await removeLeaseTx(tx, record);
          continue;
        }
        const expires = Math.min(record.last_accessed_at + IDLE_MS, record.absolute_expires_at);
        if (now >= expires) await removeLeaseTx(tx, record);
      }
      await scheduleNextAlarmTx(tx, now);
    });
  }

  async destroyAll(): Promise<void> {
    await this.storage.transaction(async (tx) => {
      if (!tx.list) throw new SessionVaultError("storage_list_required", "storage list is required for destruction");
      const all = await tx.list();
      for (const key of all.keys()) await tx.delete(key);
      await tx.deleteAlarm();
    });
  }

  private receipt(record: LeaseRecord): SecretLeaseReceipt {
    return {
      schema: "quillframe_secret_lease_receipt_v1",
      lease_id: record.lease_id,
      workspace_id: record.workspace_id,
      session_id: record.session_id,
      purpose: record.purpose,
      idle_expires_at: record.last_accessed_at + IDLE_MS,
      absolute_expires_at: record.absolute_expires_at,
      encrypted: true,
      authority: false,
    };
  }

}

async function removeLeaseTx(tx: TransactionStorageLike, record: LeaseRecord): Promise<void> {
  await tx.delete(`lease:${record.lease_id}`);
  const sessionKey = `session:${record.session_id}`;
  const sessionIds = readIds(await tx.get<string[]>(sessionKey)).filter((id) => id !== record.lease_id);
  if (sessionIds.length) await tx.put(sessionKey, sessionIds);
  else await tx.delete(sessionKey);
  const leaseIds = readIds(await tx.get<string[]>("lease-index")).filter((id) => id !== record.lease_id);
  if (leaseIds.length) await tx.put("lease-index", leaseIds);
  else await tx.delete("lease-index");
}

async function scheduleNextAlarmTx(tx: TransactionStorageLike, now: number): Promise<number | undefined> {
  const leaseIds = readIds(await tx.get<string[]>("lease-index"));
  let next: number | undefined;
  for (const leaseId of leaseIds) {
    const record = await tx.get<LeaseRecord>(`lease:${leaseId}`);
    if (!record) continue;
    assertLease(record, leaseId);
    requireVaultBinding(await tx.get<VaultSessionBinding>(`vault-session-binding:${record.session_id}`), record.workspace_id, record.session_id);
    const tombstone = await tx.get<VaultTombstone>(`vault-tombstone:${record.session_id}`);
    if (tombstone !== undefined) {
      assertTombstone(tombstone, record.session_id);
      if (tombstone.workspace_id !== record.workspace_id) throw new SessionVaultError("vault_record_invalid", "secret session tombstone identity is invalid");
      await removeLeaseTx(tx, record);
      continue;
    }
    const expires = Math.min(record.last_accessed_at + IDLE_MS, record.absolute_expires_at);
    if (now >= expires) {
      await removeLeaseTx(tx, record);
      continue;
    }
    next = next === undefined ? expires : Math.min(next, expires);
  }
  if (next === undefined) await tx.deleteAlarm();
  else await tx.setAlarm(next);
  return next;
}

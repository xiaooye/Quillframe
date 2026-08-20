import { randomToken, sha256, sha256Hex } from "./crypto.js";
import {
  requireTransactionalStorage,
  systemClock,
  type AuthTransaction,
  type Clock,
  type ProjectPointer,
  type ProjectPointerCasInput,
  type ProjectTombstoneInput,
  type ProjectVersionPreparationInput,
  type ProjectVersionPreparationReceipt,
  type ProjectVersionGcFinishInput,
  type ProjectVersionGcInput,
  type ProjectVersionGcReceipt,
  type SessionCreation,
  type SessionProjection,
  type StateLike,
  type StorageLike,
} from "./platform.js";

const IDLE_MS = 30 * 60 * 1000;
const ABSOLUTE_MS = 8 * 60 * 60 * 1000;
const AUTH_MS = 10 * 60 * 1000;
const CORE_NONCE_REPLAY_SKEW_MS = 5 * 1000;
const CORE_NONCE_INDEX_MAX = 256;
const MAX_ID = 128;
const MAX_REASON = 256;
const MAX_POINTER_REF = 512;
const MAX_OPERATION_ID = 128;
const MAX_VERSION_BYTES = 128 * 1024 * 1024;
const RETURN_TO_FALLBACK = "/studio";
const RETURN_TO_BASE = new URL("https://quillframe.invalid");

function normalizeReturnTo(value: unknown): string {
  if (typeof value !== "string" || value.length > 2048 || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u001f\u007f-\u009f]/.test(value)) return RETURN_TO_FALLBACK;
  const path = value.split(/[?#]/, 1)[0];
  if (/%(?:2f|5c)/i.test(path)) return RETURN_TO_FALLBACK;
  try {
    if (new URL(value, RETURN_TO_BASE).origin !== RETURN_TO_BASE.origin) return RETURN_TO_FALLBACK;
  } catch {
    return RETURN_TO_FALLBACK;
  }
  return value;
}

function boundedId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_ID && /^[A-Za-z0-9._:-]+$/.test(value);
}

function boundedProjectId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 64 && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value);
}

function validAuthTransactionId(value: unknown): value is string {
  return typeof value === "string" && /^auth_[A-Za-z0-9_-]{1,96}$/.test(value);
}

function validAuthState(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}

function boundedReason(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_REASON && !/[\u0000-\u001f\u007f-\u009f]/.test(value);
}

function boundedPointerRef(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_POINTER_REF && !/[\u0000-\u001f\u007f-\u009f]/.test(value);
}

function stableJson(value: Record<string, unknown>): string {
  return JSON.stringify(Object.keys(value).sort().reduce<Record<string, unknown>>((result, key) => {
    result[key] = value[key];
    return result;
  }, {}));
}

function exactKeys(value: object, required: readonly string[], optional: readonly string[] = []): boolean {
  const keys = Object.keys(value).sort();
  const requiredSet = new Set(required);
  const allowedSet = new Set([...required, ...optional]);
  return required.every((key) => keys.includes(key)) && keys.every((key) => allowedSet.has(key)) && keys.length >= requiredSet.size;
}

type AuthRecord = AuthTransaction & { state_hash: string };
type AuthConsumed = {
  schema: "quillframe_cloud_auth_consumed_v1";
  transaction_id: string;
  state_hash: string;
  consumed_at: number;
  authority: false;
};
type CoreNonceRecord = {
  schema: "quillframe_cloud_core_nonce_v1";
  session_id: string;
  project_id: string | null;
  nonce_hash: string;
  proof_digest: string;
  issued_at: number;
  expires_at: number;
  replay_expires_at: number;
  consumed_at: number;
  authority: false;
};
type CoreNonceIndexEntry = { schema: "quillframe_cloud_core_nonce_index_entry_v1"; nonce_hash: string; session_id: string; project_id: string | null; issued_at: number; expires_at: number; replay_expires_at: number; consumed_at: number };
type CoreNonceIndex = { schema: "quillframe_cloud_core_nonce_index_v1"; entries: CoreNonceIndexEntry[]; authority: false };

type WorkspaceBinding = {
  schema: "quillframe_cloud_workspace_binding_v1";
  workspace_id: string;
  bound_at: number;
  authority: false;
};

type SessionRecord = {
  schema: "quillframe_cloud_session_record_v1";
  workspace_id: string;
  workspace_handle: string;
  session_id: string;
  cookie_hash: string;
  csrf_hash: string;
  workos_session_id?: string;
  created_at: number;
  last_seen_at: number;
  absolute_expires_at: number;
  epoch: number;
};

type SessionTombstone = {
  schema: "quillframe_cloud_session_tombstone_v1";
  cookie_hash: string;
  workspace_id: string;
  session_id: string;
  destroyed_at: number;
  reason: "logout" | "expired" | "replaced";
  epoch: number;
  authority: false;
};

type ProjectTombstoneOperation = {
  schema: "quillframe_cloud_project_tombstone_operation_v1";
  operation_id: string;
  input_fingerprint: string;
  receipt_snapshot: ProjectPointer;
  reason: string;
  created_at: number;
  authority: false;
};

type ProjectVersionRecord = Omit<ProjectVersionPreparationReceipt, "schema" | "status"> & {
  schema: "quillframe_cloud_project_version_record_v1";
  status: "prepared" | "active" | "orphan" | "gc_pending";
  created_at: number;
  pointer_version: number;
};

type ProjectVersionOperation = {
  schema: "quillframe_cloud_project_version_operation_v1";
  operation_id: string;
  input_fingerprint: string;
  receipt_snapshot: ProjectVersionPreparationReceipt;
  created_at: number;
  authority: false;
};

type ProjectVersionGcOperation = {
  schema: "quillframe_cloud_project_version_gc_operation_v1";
  operation_id: string;
  project_id: string;
  version_id: string;
  retention_before: number;
  receipt_snapshot: ProjectVersionGcReceipt;
  created_at: number;
  authority: false;
};

type TransactionFailure = { error: WorkspaceCoordinatorError };

export class WorkspaceCoordinatorError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

function failure(code: string, message: string): TransactionFailure {
  return { error: new WorkspaceCoordinatorError(code, message) };
}

function versionRecordFromReceipt(
  receipt: ProjectVersionPreparationReceipt,
  status: ProjectVersionRecord["status"],
  createdAt: number,
  pointerVersion: number,
): ProjectVersionRecord {
  return {
    schema: "quillframe_cloud_project_version_record_v1",
    operation_id: receipt.operation_id,
    input_fingerprint: receipt.input_fingerprint,
    workspace_id: receipt.workspace_id,
    project_id: receipt.project_id,
    expected_pointer_version: receipt.expected_pointer_version,
    version_id: receipt.version_id,
    object_key: receipt.object_key,
    plaintext_fingerprint: receipt.plaintext_fingerprint,
    byte_size: receipt.byte_size,
    status,
    authority: false,
    created_at: createdAt,
    pointer_version: pointerVersion,
  };
}

function publicAuth(record: AuthRecord): AuthTransaction {
  return {
    schema: "quillframe_auth_transaction_v1",
    transaction_id: record.transaction_id,
    state: record.state,
    code_verifier: record.code_verifier,
    code_challenge: record.code_challenge,
    return_to: record.return_to,
    expires_at: record.expires_at,
    authority: false,
  };
}

function assertAuthConsumed(record: AuthConsumed, transactionId: string): void {
  if (!record || !exactKeys(record, ["schema", "transaction_id", "state_hash", "consumed_at", "authority"]) || record.schema !== "quillframe_cloud_auth_consumed_v1" || record.transaction_id !== transactionId || typeof record.state_hash !== "string" || record.state_hash.length > 128 || !Number.isSafeInteger(record.consumed_at) || record.consumed_at < 0 || record.authority !== false) throw new WorkspaceCoordinatorError("auth_record_invalid", "authorization transaction record is invalid");
}

function assertPendingAuth(record: AuthRecord, transactionId: string): void {
  if (!record || !exactKeys(record, ["schema", "transaction_id", "state", "state_hash", "code_verifier", "code_challenge", "return_to", "expires_at", "authority"]) || record.schema !== "quillframe_auth_transaction_v1" || !validAuthTransactionId(record.transaction_id) || record.transaction_id !== transactionId || !validAuthState(record.state) || !/^[A-Za-z0-9_-]{43}$/.test(record.state_hash) || typeof record.code_verifier !== "string" || record.code_verifier.length < 1 || record.code_verifier.length > 128 || !/^[A-Za-z0-9_-]+$/.test(record.code_verifier) || typeof record.code_challenge !== "string" || record.code_challenge.length < 1 || record.code_challenge.length > 128 || !/^[A-Za-z0-9_-]+$/.test(record.code_challenge) || normalizeReturnTo(record.return_to) !== record.return_to || !Number.isSafeInteger(record.expires_at) || record.expires_at < 0 || record.expires_at > 100_000_000_000_000 || record.authority !== false) throw new WorkspaceCoordinatorError("auth_record_invalid", "authorization transaction record is invalid");
}

function assertWorkspaceBinding(record: WorkspaceBinding, expectedWorkspaceId?: string): void {
  if (!record || !exactKeys(record, ["schema", "workspace_id", "bound_at", "authority"]) || record.schema !== "quillframe_cloud_workspace_binding_v1" || !boundedId(record.workspace_id) || !Number.isSafeInteger(record.bound_at) || record.bound_at < 0 || record.authority !== false) throw new WorkspaceCoordinatorError("workspace_binding_invalid", "workspace binding is invalid");
  if (expectedWorkspaceId !== undefined && record.workspace_id !== expectedWorkspaceId) throw new WorkspaceCoordinatorError("workspace_binding_conflict", "workspace binding does not match");
}

async function ensureWorkspaceBindingTx(tx: import("./platform.js").TransactionStorageLike, workspaceId: string, now: number): Promise<void> {
  const current = await tx.get<WorkspaceBinding>("workspace-binding");
  if (current !== undefined) {
    requireWorkspaceBinding(current, workspaceId);
    return;
  }
  await tx.put("workspace-binding", {
    schema: "quillframe_cloud_workspace_binding_v1",
    workspace_id: workspaceId,
    bound_at: now,
    authority: false,
  } satisfies WorkspaceBinding);
}

function requireWorkspaceBinding(record: WorkspaceBinding | undefined, expectedWorkspaceId?: string): WorkspaceBinding {
  if (!record) throw new WorkspaceCoordinatorError("workspace_binding_missing", "workspace binding is missing");
  assertWorkspaceBinding(record, expectedWorkspaceId);
  return record;
}

function assertSessionRecord(record: SessionRecord, cookieHash: string): void {
  if (!record || !exactKeys(record, ["schema", "workspace_id", "workspace_handle", "session_id", "cookie_hash", "csrf_hash", "created_at", "last_seen_at", "absolute_expires_at", "epoch"], ["workos_session_id"]) || record.schema !== "quillframe_cloud_session_record_v1" || record.cookie_hash !== cookieHash || !boundedId(record.workspace_id) || !boundedId(record.workspace_handle) || !boundedId(record.session_id) || typeof record.csrf_hash !== "string" || record.csrf_hash.length > 128 || record.workos_session_id !== undefined && !boundedId(record.workos_session_id) || !Number.isSafeInteger(record.created_at) || !Number.isSafeInteger(record.last_seen_at) || !Number.isSafeInteger(record.absolute_expires_at) || !Number.isSafeInteger(record.epoch) || record.epoch < 1) throw new WorkspaceCoordinatorError("session_record_invalid", "session record is invalid");
}

function assertSessionTombstone(record: SessionTombstone, cookieHash: string): void {
  if (!record || !exactKeys(record, ["schema", "cookie_hash", "workspace_id", "session_id", "destroyed_at", "reason", "epoch", "authority"]) || record.schema !== "quillframe_cloud_session_tombstone_v1" || record.cookie_hash !== cookieHash || !boundedId(record.workspace_id) || !boundedId(record.session_id) || record.reason !== "logout" && record.reason !== "expired" && record.reason !== "replaced" || !Number.isSafeInteger(record.destroyed_at) || record.destroyed_at < 0 || !Number.isSafeInteger(record.epoch) || record.epoch < 1 || record.authority !== false) throw new WorkspaceCoordinatorError("session_record_invalid", "session tombstone is invalid");
}

function assertProjectTombstoneOperation(
  record: ProjectTombstoneOperation,
  projectId: string,
  operationId: string,
): void {
  if (
    !record ||
    !exactKeys(record, [
      "schema",
      "operation_id",
      "input_fingerprint",
      "receipt_snapshot",
      "reason",
      "created_at",
      "authority",
    ]) ||
    record.schema !== "quillframe_cloud_project_tombstone_operation_v1" ||
    record.operation_id !== operationId ||
    !boundedId(record.operation_id) ||
    !/^[A-Za-z0-9_-]{43}$/.test(record.input_fingerprint) ||
    !boundedReason(record.reason) ||
    !Number.isSafeInteger(record.created_at) ||
    record.created_at < 0 ||
    record.authority !== false
  ) {
    throw new WorkspaceCoordinatorError(
      "project_tombstone_operation_invalid",
      "stored project tombstone operation is invalid",
    );
  }
  assertPointer(record.receipt_snapshot, projectId);
}

function assertVersionFingerprint(value: unknown): value is string {
  return typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);
}

function assertProjectVersionInput(input: ProjectVersionPreparationInput): void {
  if (!input || !boundedId(input.operation_id) || input.operation_id.length > MAX_OPERATION_ID || !assertVersionFingerprint(input.input_fingerprint) || !boundedId(input.workspace_id) || !boundedProjectId(input.project_id) || !Number.isSafeInteger(input.expected_pointer_version) || input.expected_pointer_version < 0 || !assertVersionFingerprint(input.version_id) || !boundedPointerRef(input.object_key) || !assertVersionFingerprint(input.plaintext_fingerprint) || !Number.isSafeInteger(input.byte_size) || input.byte_size <= 0 || input.byte_size > MAX_VERSION_BYTES) throw new WorkspaceCoordinatorError("project_version_invalid", "project version input is invalid");
}

function assertProjectVersionReceipt(record: ProjectVersionPreparationReceipt, expectedOperationId?: string): void {
  if (!record || !exactKeys(record, ["schema", "operation_id", "input_fingerprint", "workspace_id", "project_id", "expected_pointer_version", "version_id", "object_key", "plaintext_fingerprint", "byte_size", "status", "authority"]) || record.schema !== "quillframe_cloud_project_version_preparation_v1" || expectedOperationId !== undefined && record.operation_id !== expectedOperationId || !boundedId(record.operation_id) || !assertVersionFingerprint(record.input_fingerprint) || !boundedId(record.workspace_id) || !boundedProjectId(record.project_id) || !Number.isSafeInteger(record.expected_pointer_version) || record.expected_pointer_version < 0 || !assertVersionFingerprint(record.version_id) || !boundedPointerRef(record.object_key) || !assertVersionFingerprint(record.plaintext_fingerprint) || !Number.isSafeInteger(record.byte_size) || record.byte_size <= 0 || record.byte_size > MAX_VERSION_BYTES || record.status !== "prepared" && record.status !== "replayed" || record.authority !== false) throw new WorkspaceCoordinatorError("project_version_record_invalid", "project version receipt is invalid");
}

function assertProjectVersionRecord(record: ProjectVersionRecord, projectId: string, versionId: string): void {
  if (!record || !exactKeys(record, ["schema", "operation_id", "input_fingerprint", "workspace_id", "project_id", "expected_pointer_version", "version_id", "object_key", "plaintext_fingerprint", "byte_size", "status", "authority", "created_at", "pointer_version"]) || record.schema !== "quillframe_cloud_project_version_record_v1" || record.project_id !== projectId || record.version_id !== versionId || record.status !== "prepared" && record.status !== "active" && record.status !== "orphan" && record.status !== "gc_pending" || !Number.isSafeInteger(record.created_at) || record.created_at < 0 || !Number.isSafeInteger(record.pointer_version) || record.pointer_version < 0 || record.authority !== false) throw new WorkspaceCoordinatorError("project_version_record_invalid", "project version index record is invalid");
  assertProjectVersionReceipt({ schema: "quillframe_cloud_project_version_preparation_v1", operation_id: record.operation_id, input_fingerprint: record.input_fingerprint, workspace_id: record.workspace_id, project_id: record.project_id, expected_pointer_version: record.expected_pointer_version, version_id: record.version_id, object_key: record.object_key, plaintext_fingerprint: record.plaintext_fingerprint, byte_size: record.byte_size, status: "prepared", authority: false }, record.operation_id);
}

function assertProjectVersionGcReceipt(record: ProjectVersionGcReceipt, projectId: string, versionId: string, operationId?: string): void {
  if (!record || !exactKeys(record, ["schema", "operation_id", "project_id", "version_id", "workspace_id", "object_key", "plaintext_fingerprint", "byte_size", "pointer_version", "status", "authority"]) || record.schema !== "quillframe_cloud_project_version_gc_v1" || record.operation_id !== (operationId ?? record.operation_id) || !boundedProjectId(record.project_id) || record.project_id !== projectId || !assertVersionFingerprint(record.version_id) || record.version_id !== versionId || !boundedId(record.operation_id) || !boundedId(record.workspace_id) || !boundedPointerRef(record.object_key) || !assertVersionFingerprint(record.plaintext_fingerprint) || !Number.isSafeInteger(record.byte_size) || record.byte_size <= 0 || record.byte_size > MAX_VERSION_BYTES || !Number.isSafeInteger(record.pointer_version) || record.pointer_version < 0 || record.status !== "pending" && record.status !== "completed" || record.authority !== false) throw new WorkspaceCoordinatorError("project_gc_record_invalid", "project garbage-collection record is invalid");
}

function assertProjectVersionGcOperation(record: ProjectVersionGcOperation, projectId: string, operationId: string): void {
  if (!record || !exactKeys(record, ["schema", "operation_id", "project_id", "version_id", "retention_before", "receipt_snapshot", "created_at", "authority"]) || record.schema !== "quillframe_cloud_project_version_gc_operation_v1" || record.operation_id !== operationId || !boundedProjectId(record.project_id) || record.project_id !== projectId || !assertVersionFingerprint(record.version_id) || !Number.isSafeInteger(record.retention_before) || record.retention_before < 0 || !Number.isSafeInteger(record.created_at) || record.created_at < 0 || record.authority !== false) throw new WorkspaceCoordinatorError("project_gc_record_invalid", "project garbage-collection operation is invalid");
  assertProjectVersionGcReceipt(record.receipt_snapshot, projectId, record.version_id, operationId);
}

function assertProjectVersionOperation(record: ProjectVersionOperation, projectId: string, operationId: string): void {
  if (!record || !exactKeys(record, ["schema", "operation_id", "input_fingerprint", "receipt_snapshot", "created_at", "authority"]) || record.schema !== "quillframe_cloud_project_version_operation_v1" || record.operation_id !== operationId || !Number.isSafeInteger(record.created_at) || record.created_at < 0 || record.authority !== false) throw new WorkspaceCoordinatorError("project_version_record_invalid", "project version operation record is invalid");
  assertProjectVersionReceipt(record.receipt_snapshot, operationId);
  if (record.receipt_snapshot.project_id !== projectId || record.input_fingerprint !== record.receipt_snapshot.input_fingerprint) throw new WorkspaceCoordinatorError("project_version_record_invalid", "project version operation binding is invalid");
}

export async function workspaceHandleForIdentity(identityId: string): Promise<string> {
  if (!identityId) throw new WorkspaceCoordinatorError("identity_required", "identity_id is required");
  return (await sha256Hex(`quillframe-personal-workspace:${identityId}`)).slice(0, 24);
}

export class WorkspaceCoordinator {
  private readonly storage: StorageLike;
  private readonly clock: Clock;

  constructor(state: StateLike, _env: unknown, options: { now?: () => number } = {}) {
    this.storage = requireTransactionalStorage(state.storage);
    this.clock = options.now ? { now: options.now } : systemClock;
  }

  async beginAuth(returnTo = "/studio"): Promise<AuthTransaction> {
    const transactionId = `auth_${randomToken(18)}`;
    const state = randomToken(24);
    const codeVerifier = randomToken(32);
    const transaction: AuthRecord = {
      schema: "quillframe_auth_transaction_v1",
      transaction_id: transactionId,
      state,
      state_hash: await sha256(state),
      code_verifier: codeVerifier,
      code_challenge: await sha256(codeVerifier),
      return_to: normalizeReturnTo(returnTo),
      expires_at: this.clock.now() + AUTH_MS,
      authority: false,
    };
    await this.storage.transaction(async (tx) => {
      await tx.put(`auth:${transactionId}`, transaction);
    });
    return publicAuth(transaction);
  }

  async consumeAuth(transactionId: string, state: string): Promise<AuthTransaction> {
    if (!validAuthTransactionId(transactionId) || !validAuthState(state)) throw new WorkspaceCoordinatorError("auth_state_invalid", "authorization transaction state does not match");
    const stateHash = await sha256(state);
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<AuthRecord | TransactionFailure> => {
      const consumed = await tx.get<AuthConsumed>(`auth-consumed:${transactionId}`);
      if (consumed) {
        assertAuthConsumed(consumed, transactionId);
        return failure("auth_already_consumed", "authorization transaction was already consumed");
      }
      const pending = await tx.get<AuthRecord>(`auth:${transactionId}`);
      if (pending !== undefined) assertPendingAuth(pending, transactionId);
      const valid = pending && pending.schema === "quillframe_auth_transaction_v1" &&
        pending.transaction_id === transactionId && pending.state_hash === stateHash &&
        pending.state === state && pending.authority === false && now < pending.expires_at;
      const consumedRecord: AuthConsumed = {
        schema: "quillframe_cloud_auth_consumed_v1",
        transaction_id: transactionId,
        state_hash: stateHash,
        consumed_at: now,
        authority: false,
      };
      if (!valid) {
        await tx.put(`auth-consumed:${transactionId}`, consumedRecord);
        if (pending) await tx.delete(`auth:${transactionId}`);
        return failure(pending && now >= pending.expires_at ? "auth_transaction_expired" : "auth_state_invalid", pending && now >= pending.expires_at ? "authorization transaction expired" : "authorization transaction state does not match");
      }
      await tx.put(`auth-consumed:${transactionId}`, consumedRecord);
      await tx.delete(`auth:${transactionId}`);
      return pending;
    });
    if ("error" in outcome) throw outcome.error;
    return publicAuth(outcome);
  }

  async consumeCoreNonce(input: { session_id: string; project_id: string | null; nonce: string; proof_digest: string; issued_at: number; expires_at: number }): Promise<{ schema: "quillframe_core_nonce_receipt_v1"; consumed: true; authority: false }> {
    if (!boundedId(input?.session_id) || !/^[A-Za-z0-9_-]{1,128}$/.test(input?.nonce ?? "") || !/^sha256:[0-9a-f]{64}$/.test(input?.proof_digest ?? "")) throw new WorkspaceCoordinatorError("core_nonce_invalid", "core proof nonce is invalid");
    if (!(input.project_id === null || boundedId(input.project_id)) || !Number.isSafeInteger(input.issued_at) || !Number.isSafeInteger(input.expires_at) || input.expires_at <= input.issued_at || input.expires_at - input.issued_at > 30000) throw new WorkspaceCoordinatorError("core_nonce_invalid", "core proof nonce timing is invalid");
    const nonceHash = await sha256Hex(input.nonce);
    const now = this.clock.now();
    const replayExpiresAt = input.expires_at + CORE_NONCE_REPLAY_SKEW_MS;
    if (!Number.isSafeInteger(replayExpiresAt) || now < input.issued_at - CORE_NONCE_REPLAY_SKEW_MS || now > replayExpiresAt) throw new WorkspaceCoordinatorError("core_nonce_invalid", "core proof nonce timing is invalid");
    const outcome = await this.storage.transaction(async (tx): Promise<true | TransactionFailure> => {
      if (!tx.list) return failure("storage_list_required", "core proof nonce index requires bounded listing");
      const key = `core-nonce:${nonceHash}`;
      const indexKey = "core-nonce-index";
      const storedIndex = await tx.get<CoreNonceIndex>(indexKey);
      let index: CoreNonceIndexEntry[];
      if (storedIndex === undefined) {
        const records = await tx.list({ prefix: "core-nonce:" });
        if (records.size !== 0) return failure("core_nonce_record_invalid", "core proof nonce index is missing");
        index = [];
      } else {
        if (!storedIndex || !exactKeys(storedIndex, ["schema", "entries", "authority"]) || storedIndex.schema !== "quillframe_cloud_core_nonce_index_v1" || !Array.isArray(storedIndex.entries) || storedIndex.authority !== false) return failure("core_nonce_record_invalid", "core proof nonce index is invalid");
        index = storedIndex.entries;
      }
      const liveIndex: CoreNonceIndexEntry[] = [];
      const seen = new Set<string>();
      for (const entry of index) {
        if (!entry || !exactKeys(entry, ["schema", "nonce_hash", "session_id", "project_id", "issued_at", "expires_at", "replay_expires_at", "consumed_at"]) || entry.schema !== "quillframe_cloud_core_nonce_index_entry_v1" || !/^[0-9a-f]{64}$/.test(entry.nonce_hash) || seen.has(entry.nonce_hash) || !boundedId(entry.session_id) || !(entry.project_id === null || boundedId(entry.project_id)) || !Number.isSafeInteger(entry.issued_at) || !Number.isSafeInteger(entry.expires_at) || !Number.isSafeInteger(entry.replay_expires_at) || !Number.isSafeInteger(entry.consumed_at) || entry.expires_at <= entry.issued_at || entry.replay_expires_at !== entry.expires_at + CORE_NONCE_REPLAY_SKEW_MS || entry.consumed_at < 0) return failure("core_nonce_record_invalid", "core proof nonce index is invalid");
        seen.add(entry.nonce_hash);
        if (entry.replay_expires_at <= now) {
          await tx.delete(`core-nonce:${entry.nonce_hash}`);
          continue;
        }
        const record = await tx.get<CoreNonceRecord>(`core-nonce:${entry.nonce_hash}`);
        if (!record || !exactKeys(record, ["schema", "session_id", "project_id", "nonce_hash", "proof_digest", "issued_at", "expires_at", "replay_expires_at", "consumed_at", "authority"]) || record.schema !== "quillframe_cloud_core_nonce_v1" || record.session_id !== entry.session_id || record.project_id !== entry.project_id || record.nonce_hash !== entry.nonce_hash || !/^sha256:[0-9a-f]{64}$/.test(record.proof_digest) || record.issued_at !== entry.issued_at || record.expires_at !== entry.expires_at || record.replay_expires_at !== entry.replay_expires_at || record.consumed_at !== entry.consumed_at || record.authority !== false) return failure("core_nonce_record_invalid", "core proof nonce record is invalid");
        liveIndex.push(entry);
      }
      if (liveIndex.length >= CORE_NONCE_INDEX_MAX && !liveIndex.some((entry) => entry.nonce_hash === nonceHash)) return failure("core_nonce_capacity", "core proof nonce capacity is exhausted");
      const previous = await tx.get<CoreNonceRecord>(key);
      if (previous !== undefined) {
        if (!exactKeys(previous, ["schema", "session_id", "project_id", "nonce_hash", "proof_digest", "issued_at", "expires_at", "replay_expires_at", "consumed_at", "authority"]) || previous.schema !== "quillframe_cloud_core_nonce_v1" || previous.nonce_hash !== nonceHash || !/^sha256:[0-9a-f]{64}$/.test(previous.proof_digest) || !Number.isSafeInteger(previous.issued_at) || !Number.isSafeInteger(previous.expires_at) || !Number.isSafeInteger(previous.replay_expires_at) || !Number.isSafeInteger(previous.consumed_at) || previous.replay_expires_at !== previous.expires_at + CORE_NONCE_REPLAY_SKEW_MS || previous.authority !== false) return failure("core_nonce_record_invalid", "core proof nonce record is invalid");
        if (previous.replay_expires_at > now) return previous.session_id === input.session_id && previous.project_id === input.project_id && previous.proof_digest === input.proof_digest ? failure("core_nonce_replayed", "core proof nonce was already consumed") : failure("core_nonce_digest_conflict", "core proof nonce digest conflicts");
      }
      const record: CoreNonceRecord = { schema: "quillframe_cloud_core_nonce_v1", session_id: input.session_id, project_id: input.project_id, nonce_hash: nonceHash, proof_digest: input.proof_digest, issued_at: input.issued_at, expires_at: input.expires_at, replay_expires_at: replayExpiresAt, consumed_at: now, authority: false };
      const nextEntry: CoreNonceIndexEntry = { schema: "quillframe_cloud_core_nonce_index_entry_v1", nonce_hash: nonceHash, session_id: input.session_id, project_id: input.project_id, issued_at: input.issued_at, expires_at: input.expires_at, replay_expires_at: replayExpiresAt, consumed_at: now };
      await tx.put(key, record);
      await tx.put(indexKey, { schema: "quillframe_cloud_core_nonce_index_v1", entries: [...liveIndex.filter((entry) => entry.nonce_hash !== nonceHash), nextEntry], authority: false } satisfies CoreNonceIndex);
      return true;
    });
    if (outcome !== true) throw outcome.error;
    return { schema: "quillframe_core_nonce_receipt_v1", consumed: true, authority: false };
  }

  async assertWorkspaceBinding(workspaceId: string): Promise<void> {
    if (!boundedId(workspaceId)) throw new WorkspaceCoordinatorError("workspace_binding_invalid", "workspace binding is invalid");
    await this.storage.transaction(async (tx) => { requireWorkspaceBinding(await tx.get<WorkspaceBinding>("workspace-binding"), workspaceId); });
  }

  async prepareProjectVersion(input: ProjectVersionPreparationInput): Promise<ProjectVersionPreparationReceipt> {
    assertProjectVersionInput(input);
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<ProjectVersionPreparationReceipt | TransactionFailure> => {
      const operationKey = `project-version-operation:${input.project_id}:${input.operation_id}`;
      const prior = await tx.get<ProjectVersionOperation>(operationKey);
      if (prior !== undefined) {
        assertProjectVersionOperation(prior, input.project_id, input.operation_id);
        if (prior.input_fingerprint !== input.input_fingerprint || prior.receipt_snapshot.workspace_id !== input.workspace_id || prior.receipt_snapshot.project_id !== input.project_id || prior.receipt_snapshot.expected_pointer_version !== input.expected_pointer_version || prior.receipt_snapshot.version_id !== input.version_id || prior.receipt_snapshot.object_key !== input.object_key || prior.receipt_snapshot.plaintext_fingerprint !== input.plaintext_fingerprint || prior.receipt_snapshot.byte_size !== input.byte_size) return failure("project_version_operation_conflict", "project version operation input conflicts");
        return prior.receipt_snapshot;
      }
      const binding = await tx.get<WorkspaceBinding>("workspace-binding");
      requireWorkspaceBinding(binding, input.workspace_id);
      const pointerKey = `project:${input.project_id}`;
      const pointer = await tx.get<ProjectPointer>(pointerKey);
      if (pointer !== undefined) {
        assertPointer(pointer, input.project_id);
        if (pointer.workspace_id !== input.workspace_id) return failure("workspace_binding_conflict", "project workspace binding does not match");
      } else if (input.expected_pointer_version !== 0) return failure("project_pointer_conflict", "absent project pointer requires version zero");
      if (!tx.list) return failure("storage_list_required", "project version index requires bounded listing");
      const versionKey = `project-version:${input.project_id}:${input.version_id}`;
      const existing = await tx.get<ProjectVersionRecord>(versionKey);
      if (existing !== undefined) {
        assertProjectVersionRecord(existing, input.project_id, input.version_id);
        if (existing.status === "gc_pending") return failure("project_version_gc_pending", "project version is pending garbage collection");
        if (existing.workspace_id !== input.workspace_id || existing.project_id !== input.project_id || existing.expected_pointer_version !== input.expected_pointer_version || existing.version_id !== input.version_id || existing.object_key !== input.object_key || existing.plaintext_fingerprint !== input.plaintext_fingerprint || existing.byte_size !== input.byte_size) return failure("project_version_conflict", "project version identity conflicts");
        if (!tx.list) return failure("storage_list_required", "project version index requires bounded listing");
        const operationEntries = await tx.list({ prefix: `project-version-operation:${input.project_id}:` });
        for (const [entryKey, entryValue] of operationEntries) {
          const operationId = entryKey.slice(`project-version-operation:${input.project_id}:`.length);
          if (!operationId || entryKey !== `project-version-operation:${input.project_id}:${operationId}`) return failure("project_version_record_invalid", "project version operation key is invalid");
          assertProjectVersionOperation(entryValue as ProjectVersionOperation, input.project_id, operationId);
        }
        if (operationEntries.size >= 256) return failure("project_version_capacity", "project version history is bounded");
        const replay = existing.status === "active" || pointer?.version_id === input.version_id ? "replayed" : "prepared";
        const receipt: ProjectVersionPreparationReceipt = { schema: "quillframe_cloud_project_version_preparation_v1", operation_id: input.operation_id, input_fingerprint: input.input_fingerprint, workspace_id: input.workspace_id, project_id: input.project_id, expected_pointer_version: input.expected_pointer_version, version_id: input.version_id, object_key: input.object_key, plaintext_fingerprint: input.plaintext_fingerprint, byte_size: input.byte_size, status: replay, authority: false };
        await tx.put(operationKey, { schema: "quillframe_cloud_project_version_operation_v1", operation_id: input.operation_id, input_fingerprint: input.input_fingerprint, receipt_snapshot: receipt, created_at: now, authority: false } satisfies ProjectVersionOperation);
        return receipt;
      }
      const versionEntries = await tx.list({ prefix: `project-version:${input.project_id}:` });
      const operationEntries = await tx.list({ prefix: `project-version-operation:${input.project_id}:` });
      for (const [entryKey, entryValue] of versionEntries) {
        const versionId = entryKey.slice(`project-version:${input.project_id}:`.length);
        if (!versionId || entryKey !== `project-version:${input.project_id}:${versionId}`) return failure("project_version_record_invalid", "project version index key is invalid");
        assertProjectVersionRecord(entryValue as ProjectVersionRecord, input.project_id, versionId);
      }
      for (const [entryKey, entryValue] of operationEntries) {
        const operationId = entryKey.slice(`project-version-operation:${input.project_id}:`.length);
        if (!operationId || entryKey !== `project-version-operation:${input.project_id}:${operationId}`) return failure("project_version_record_invalid", "project version operation key is invalid");
        assertProjectVersionOperation(entryValue as ProjectVersionOperation, input.project_id, operationId);
      }
      if (versionEntries.size >= 256 || operationEntries.size >= 256) return failure("project_version_capacity", "project version history is bounded");
      if (pointer && pointer.pointer_version !== input.expected_pointer_version) {
        const orphanReceipt: ProjectVersionPreparationReceipt = { schema: "quillframe_cloud_project_version_preparation_v1", operation_id: input.operation_id, input_fingerprint: input.input_fingerprint, workspace_id: input.workspace_id, project_id: input.project_id, expected_pointer_version: input.expected_pointer_version, version_id: input.version_id, object_key: input.object_key, plaintext_fingerprint: input.plaintext_fingerprint, byte_size: input.byte_size, status: "prepared", authority: false };
        await tx.put(versionKey, versionRecordFromReceipt(orphanReceipt, "orphan", now, pointer.pointer_version));
        await tx.put(operationKey, { schema: "quillframe_cloud_project_version_operation_v1", operation_id: input.operation_id, input_fingerprint: input.input_fingerprint, receipt_snapshot: orphanReceipt, created_at: now, authority: false } satisfies ProjectVersionOperation);
        return failure("project_pointer_conflict", "project pointer version is stale");
      }
      const receipt: ProjectVersionPreparationReceipt = { schema: "quillframe_cloud_project_version_preparation_v1", operation_id: input.operation_id, input_fingerprint: input.input_fingerprint, workspace_id: input.workspace_id, project_id: input.project_id, expected_pointer_version: input.expected_pointer_version, version_id: input.version_id, object_key: input.object_key, plaintext_fingerprint: input.plaintext_fingerprint, byte_size: input.byte_size, status: "prepared", authority: false };
      const record = versionRecordFromReceipt(receipt, "prepared", now, input.expected_pointer_version);
      await tx.put(versionKey, record);
      await tx.put(operationKey, { schema: "quillframe_cloud_project_version_operation_v1", operation_id: input.operation_id, input_fingerprint: input.input_fingerprint, receipt_snapshot: receipt, created_at: now, authority: false } satisfies ProjectVersionOperation);
      return receipt;
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async beginProjectVersionGc(input: ProjectVersionGcInput): Promise<ProjectVersionGcReceipt> {
    if (!boundedProjectId(input?.project_id) || !assertVersionFingerprint(input?.version_id) || !boundedId(input?.operation_id) || input.operation_id.length > MAX_OPERATION_ID || !Number.isSafeInteger(input?.retention_before) || input.retention_before < 0) throw new WorkspaceCoordinatorError("project_gc_invalid", "project garbage-collection input is invalid");
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<ProjectVersionGcReceipt | TransactionFailure> => {
      if (!tx.list) return failure("storage_list_required", "project garbage-collection index requires bounded listing");
      const operationKey = `project-version-gc-operation:${input.project_id}:${input.operation_id}`;
      const prior = await tx.get<ProjectVersionGcOperation>(operationKey);
      if (prior !== undefined) {
        assertProjectVersionGcOperation(prior, input.project_id, input.operation_id);
        if (prior.version_id !== input.version_id || prior.retention_before !== input.retention_before) return failure("project_gc_operation_conflict", "project garbage-collection operation input conflicts");
        return prior.receipt_snapshot;
      }
      const binding = requireWorkspaceBinding(await tx.get<WorkspaceBinding>("workspace-binding"));
      const versionKey = `project-version:${input.project_id}:${input.version_id}`;
      const version = await tx.get<ProjectVersionRecord>(versionKey);
      if (!version) return failure("project_gc_not_found", "project version was not found");
      assertProjectVersionRecord(version, input.project_id, input.version_id);
      if (version.workspace_id !== binding.workspace_id) return failure("workspace_binding_conflict", "project workspace binding does not match");
      if (version.status !== "orphan") return failure("project_gc_not_eligible", "project version is not an orphan");
      if (version.created_at > input.retention_before) return failure("project_gc_retention", "project version is younger than the retention boundary");
      const pointer = await tx.get<ProjectPointer>(`project:${input.project_id}`);
      if (pointer !== undefined) {
        assertPointer(pointer, input.project_id);
        requireWorkspaceBinding(binding, pointer.workspace_id);
        if (pointer.version_id === input.version_id) return failure("project_gc_not_eligible", "project version is still referenced");
      }
      const operations = await tx.list({ prefix: `project-version-gc-operation:${input.project_id}:` });
      for (const [key, value] of operations) {
        const operationId = key.slice(`project-version-gc-operation:${input.project_id}:`.length);
        if (!operationId || key !== `project-version-gc-operation:${input.project_id}:${operationId}`) return failure("project_gc_record_invalid", "project garbage-collection key is invalid");
        assertProjectVersionGcOperation(value as ProjectVersionGcOperation, input.project_id, operationId);
      }
      if (operations.size >= 256) {
        const prunable = [...operations.entries()]
          .filter(([, value]) => (value as ProjectVersionGcOperation).receipt_snapshot.status === "completed")
          .sort(([leftKey, leftValue], [rightKey, rightValue]) => (leftValue as ProjectVersionGcOperation).created_at - (rightValue as ProjectVersionGcOperation).created_at || leftKey.localeCompare(rightKey));
        const needed = operations.size - 255;
        if (prunable.length < needed) return failure("project_gc_capacity", "project garbage-collection history is bounded");
        for (const [key] of prunable.slice(0, needed)) await tx.delete(key);
      }
      const receipt: ProjectVersionGcReceipt = {
        schema: "quillframe_cloud_project_version_gc_v1",
        operation_id: input.operation_id,
        project_id: input.project_id,
        version_id: input.version_id,
        workspace_id: version.workspace_id,
        object_key: version.object_key,
        plaintext_fingerprint: version.plaintext_fingerprint,
        byte_size: version.byte_size,
        pointer_version: version.pointer_version,
        status: "pending",
        authority: false,
      };
      await tx.put(versionKey, { ...version, status: "gc_pending" });
      await tx.put(operationKey, { schema: "quillframe_cloud_project_version_gc_operation_v1", operation_id: input.operation_id, project_id: input.project_id, version_id: input.version_id, retention_before: input.retention_before, receipt_snapshot: receipt, created_at: now, authority: false } satisfies ProjectVersionGcOperation);
      return receipt;
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async finishProjectVersionGc(input: ProjectVersionGcFinishInput): Promise<ProjectVersionGcReceipt> {
    if (!boundedProjectId(input?.project_id) || !assertVersionFingerprint(input?.version_id) || !boundedId(input?.operation_id) || input.operation_id.length > MAX_OPERATION_ID || typeof input.deleted !== "boolean") throw new WorkspaceCoordinatorError("project_gc_invalid", "project garbage-collection input is invalid");
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<ProjectVersionGcReceipt | TransactionFailure> => {
      const operationKey = `project-version-gc-operation:${input.project_id}:${input.operation_id}`;
      const operation = await tx.get<ProjectVersionGcOperation>(operationKey);
      if (!operation) return failure("project_gc_operation_missing", "project garbage-collection operation was not found");
      assertProjectVersionGcOperation(operation, input.project_id, input.operation_id);
      if (operation.version_id !== input.version_id) return failure("project_gc_operation_conflict", "project garbage-collection operation input conflicts");
      const versionKey = `project-version:${input.project_id}:${input.version_id}`;
      const version = await tx.get<ProjectVersionRecord>(versionKey);
      if (!input.deleted) return operation.receipt_snapshot;
      if (version !== undefined) {
        assertProjectVersionRecord(version, input.project_id, input.version_id);
        if (version.status !== "gc_pending") return failure("project_gc_reference_conflict", "project version is no longer pending garbage collection");
        const pointer = await tx.get<ProjectPointer>(`project:${input.project_id}`);
        if (pointer !== undefined) {
          assertPointer(pointer, input.project_id);
          if (pointer.version_id === input.version_id) return failure("project_gc_reference_conflict", "project version became referenced");
        }
        const preparationKey = `project-version-operation:${input.project_id}:${version.operation_id}`;
        const preparation = await tx.get<ProjectVersionOperation>(preparationKey);
        if (preparation !== undefined) {
          assertProjectVersionOperation(preparation, input.project_id, version.operation_id);
          await tx.delete(preparationKey);
        }
        await tx.delete(versionKey);
      }
      const completed = { ...operation.receipt_snapshot, status: "completed" as const, authority: false as const };
      assertProjectVersionGcReceipt(completed, input.project_id, input.version_id, input.operation_id);
      await tx.put(operationKey, { ...operation, receipt_snapshot: completed, created_at: operation.created_at || now, authority: false });
      return completed;
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async readProjectVersionGcOperation(input: { project_id: string; operation_id: string }): Promise<{ receipt: ProjectVersionGcReceipt; retention_before: number } | undefined> {
    if (!boundedProjectId(input?.project_id) || !boundedId(input?.operation_id) || input.operation_id.length > MAX_OPERATION_ID) throw new WorkspaceCoordinatorError("project_gc_invalid", "project garbage-collection operation is invalid");
    return this.storage.transaction(async (tx) => {
      const record = await tx.get<ProjectVersionGcOperation>(`project-version-gc-operation:${input.project_id}:${input.operation_id}`);
      if (record === undefined) return undefined;
      assertProjectVersionGcOperation(record, input.project_id, input.operation_id);
      return { receipt: record.receipt_snapshot, retention_before: record.retention_before };
    });
  }

  async createSession(input: { identity_id: string; workos_session_id?: string }): Promise<SessionCreation> {
    if (!boundedId(input.identity_id)) throw new WorkspaceCoordinatorError("identity_required", "identity_id is required");
    if (input.workos_session_id !== undefined && !boundedId(input.workos_session_id)) throw new WorkspaceCoordinatorError("session_identity_invalid", "workos session identity is invalid");
    const now = this.clock.now();
    const workspaceHandle = await workspaceHandleForIdentity(input.identity_id);
    const workspaceId = `workspace_${workspaceHandle}`;
    const sessionId = `session_${randomToken(18)}`;
    const cookieToken = `${workspaceHandle}.${randomToken(32)}`;
    const csrfToken = randomToken(24);
    const record: SessionRecord = {
      schema: "quillframe_cloud_session_record_v1",
      workspace_id: workspaceId,
      workspace_handle: workspaceHandle,
      session_id: sessionId,
      cookie_hash: await sha256(cookieToken),
      csrf_hash: await sha256(csrfToken),
      workos_session_id: input.workos_session_id,
      created_at: now,
      last_seen_at: now,
      absolute_expires_at: now + ABSOLUTE_MS,
      epoch: 1,
    };
    await this.storage.transaction(async (tx) => {
      await ensureWorkspaceBindingTx(tx, workspaceId, now);
      await tx.put(`session:${record.cookie_hash}`, record);
    });
    return {
      schema: "quillframe_cloud_session_creation_v1",
      workspace_id: workspaceId,
      workspace_handle: workspaceHandle,
      session_id: sessionId,
      cookie_token: cookieToken,
      csrf_token: csrfToken,
      created_at: now,
      idle_expires_at: now + IDLE_MS,
      absolute_expires_at: record.absolute_expires_at,
      authority: false,
    };
  }

  async validateSession(cookieToken: string, csrfToken?: string): Promise<SessionProjection> {
    const cookieHash = await sha256(cookieToken);
    const csrfHash = csrfToken === undefined ? undefined : await sha256(csrfToken);
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<SessionProjection | TransactionFailure> => {
      const key = `session:${cookieHash}`;
      const record = await tx.get<SessionRecord>(key);
      const tombstone = await tx.get<SessionTombstone>(`session-tombstone:${cookieHash}`);
      if (!record || record.schema !== "quillframe_cloud_session_record_v1" || record.cookie_hash !== cookieHash) return failure("session_invalid", "session is invalid");
      assertSessionRecord(record, cookieHash);
      if (tombstone) {
        assertSessionTombstone(tombstone, cookieHash);
        if (tombstone.epoch >= record.epoch) return failure("session_destroyed", "session was destroyed");
      }
      if (csrfHash !== undefined && csrfHash !== record.csrf_hash) return failure("csrf_invalid", "CSRF token is invalid");
      if (now - record.last_seen_at > IDLE_MS || now >= record.absolute_expires_at) {
        const expired: SessionTombstone = {
          schema: "quillframe_cloud_session_tombstone_v1",
          cookie_hash: cookieHash,
          workspace_id: record.workspace_id,
          session_id: record.session_id,
          destroyed_at: now,
          reason: "expired",
          epoch: record.epoch,
          authority: false,
        };
        await tx.put(`session-tombstone:${cookieHash}`, expired);
        await tx.delete(key);
        return failure("session_expired", "session expired");
      }
      const lastSeenRecord = { ...record, last_seen_at: now };
      await tx.put(key, lastSeenRecord);
      return {
        schema: "quillframe_cloud_session_projection_v1",
        workspace_id: record.workspace_id,
        workspace_handle: record.workspace_handle,
        session_id: record.session_id,
        workos_session_id: record.workos_session_id,
        idle_expires_at: now + IDLE_MS,
        absolute_expires_at: record.absolute_expires_at,
        authority: false,
      };
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async destroySession(cookieToken: string): Promise<{ destroyed: true; session_id: string; authority: false }> {
    const cookieHash = await sha256(cookieToken);
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<{ destroyed: true; session_id: string; authority: false } | TransactionFailure> => {
      const key = `session:${cookieHash}`;
      const record = await tx.get<SessionRecord>(key);
      const tombstone = await tx.get<SessionTombstone>(`session-tombstone:${cookieHash}`);
      if (tombstone) assertSessionTombstone(tombstone, cookieHash);
      if (!record || tombstone) return failure("session_invalid", "session is invalid");
      assertSessionRecord(record, cookieHash);
      const destroyed: SessionTombstone = {
        schema: "quillframe_cloud_session_tombstone_v1",
        cookie_hash: cookieHash,
        workspace_id: record.workspace_id,
        session_id: record.session_id,
        destroyed_at: now,
        reason: "logout",
        epoch: record.epoch,
        authority: false,
      };
      await tx.put(`session-tombstone:${cookieHash}`, destroyed);
      await tx.delete(key);
      return { destroyed: true, session_id: record.session_id, authority: false };
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async readProjectPointer(projectId: string): Promise<ProjectPointer | undefined> {
    assertProjectId(projectId);
    return this.storage.transaction(async (tx) => {
      const pointer = await tx.get<ProjectPointer>(`project:${projectId}`);
      const binding = await tx.get<WorkspaceBinding>("workspace-binding");
      if (pointer !== undefined) {
        assertPointer(pointer, projectId);
        requireWorkspaceBinding(binding, pointer.workspace_id);
      } else if (binding !== undefined) {
        assertWorkspaceBinding(binding);
      }
      return pointer;
    });
  }

  async casProjectPointer(input: ProjectPointerCasInput): Promise<ProjectPointer> {
    assertProjectId(input.project_id);
    assertExpectedVersion(input.expected_pointer_version);
    assertNextPointer(input.next, input.project_id);
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<ProjectPointer | TransactionFailure> => {
      const key = `project:${input.project_id}`;
      const current = await tx.get<ProjectPointer>(key);
      if (current !== undefined) assertPointer(current, input.project_id);
      const versionKey = `project-version:${input.project_id}:${input.next.version_id}`;
      const version = await tx.get<ProjectVersionRecord>(versionKey);
      if (version === undefined) return failure("project_version_required", "project version must be prepared before pointer CAS");
      assertProjectVersionRecord(version, input.project_id, input.next.version_id);
      if (version.status === "gc_pending") return failure("project_version_gc_pending", "project version is pending garbage collection");
      if (version.workspace_id !== input.next.workspace_id || version.expected_pointer_version !== input.expected_pointer_version || version.version_id !== input.next.version_id || version.object_key !== input.next.object_key || version.plaintext_fingerprint !== input.next.plaintext_fingerprint || version.byte_size <= 0) return failure("project_version_conflict", "project version pointer identity conflicts");
      const currentVersion = current?.pointer_version ?? 0;
      if (current && current.state === "active" && (current.pointer_version === input.expected_pointer_version || current.pointer_version === input.expected_pointer_version + 1) && current.version_id === input.next.version_id && current.object_key === input.next.object_key && current.plaintext_fingerprint === input.next.plaintext_fingerprint && current.workspace_id === input.next.workspace_id) return current;
      if (currentVersion !== input.expected_pointer_version) {
        if (version.workspace_id === input.next.workspace_id && version.object_key === input.next.object_key && version.plaintext_fingerprint === input.next.plaintext_fingerprint) await tx.put(versionKey, { ...version, status: "orphan" });
        return failure("project_pointer_conflict", "project pointer version is stale");
      }
      const binding = await tx.get<WorkspaceBinding>("workspace-binding");
      if (current === undefined) {
        if (binding !== undefined) assertWorkspaceBinding(binding, input.next.workspace_id);
        else await ensureWorkspaceBindingTx(tx, input.next.workspace_id, now);
      } else {
        const owner = requireWorkspaceBinding(binding, current.workspace_id);
        if (input.next.workspace_id !== owner.workspace_id) return failure("workspace_binding_conflict", "project workspace binding does not match");
      }
      const next: ProjectPointer = {
        schema: "quillframe_cloud_project_pointer_v1",
        workspace_id: input.next.workspace_id,
        project_id: input.project_id,
        pointer_version: currentVersion + 1,
        state: input.next.state,
        version_id: input.next.version_id,
        object_key: input.next.object_key,
        plaintext_fingerprint: input.next.plaintext_fingerprint,
        updated_at: now,
        authority: false,
      };
      assertPointer(next, input.project_id);
      if (current?.version_id && current.version_id !== next.version_id) {
        const previousVersionKey = `project-version:${input.project_id}:${current.version_id}`;
        const previousVersion = await tx.get<ProjectVersionRecord>(previousVersionKey);
        if (previousVersion === undefined) return failure("project_version_record_invalid", "current project version record is missing");
        assertProjectVersionRecord(previousVersion, input.project_id, current.version_id);
        if (previousVersion.workspace_id !== current.workspace_id || previousVersion.object_key !== current.object_key || previousVersion.plaintext_fingerprint !== current.plaintext_fingerprint) return failure("project_version_record_invalid", "current project version identity conflicts");
        if (previousVersion.status === "gc_pending") return failure("project_version_gc_pending", "current project version is pending garbage collection");
        await tx.put(previousVersionKey, { ...previousVersion, status: "orphan" });
      }
      await tx.put(key, next);
      await tx.put(versionKey, { ...version, status: "active", pointer_version: next.pointer_version });
      return next;
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async casProjectTombstone(input: ProjectTombstoneInput): Promise<ProjectPointer> {
    assertProjectId(input.project_id);
    assertExpectedVersion(input.expected_pointer_version);
    if (!boundedReason(input.reason) || !boundedId(input.operation_id)) throw new WorkspaceCoordinatorError("project_tombstone_invalid", "project tombstone input is invalid");
    const inputFingerprint = await sha256(stableJson({
      expected_pointer_version: input.expected_pointer_version,
      operation_id: input.operation_id,
      project_id: input.project_id,
      reason: input.reason,
    }));
    const now = this.clock.now();
    const outcome = await this.storage.transaction(async (tx): Promise<ProjectPointer | TransactionFailure> => {
      const operationKey = `project-tombstone-operation:${input.project_id}:${input.operation_id}`;
      const previous = await tx.get<ProjectTombstoneOperation>(operationKey);
      if (previous !== undefined) {
        assertProjectTombstoneOperation(previous, input.project_id, input.operation_id);
        if (
          previous.input_fingerprint !== inputFingerprint ||
          previous.reason !== input.reason ||
          previous.receipt_snapshot.pointer_version !== input.expected_pointer_version + 1 ||
          previous.created_at !== previous.receipt_snapshot.updated_at
        ) return failure("project_tombstone_operation_conflict", "project tombstone operation input conflicts");
        requireWorkspaceBinding(await tx.get<WorkspaceBinding>("workspace-binding"), previous.receipt_snapshot.workspace_id);
        return previous.receipt_snapshot;
      }
      const key = `project:${input.project_id}`;
      const current = await tx.get<ProjectPointer>(key);
      if (current === undefined) return failure("project_pointer_conflict", "project pointer version is stale");
      assertPointer(current, input.project_id);
      requireWorkspaceBinding(await tx.get<WorkspaceBinding>("workspace-binding"), current.workspace_id);
      if (current.pointer_version !== input.expected_pointer_version || current.state !== "active") return failure("project_pointer_conflict", "project pointer version is stale");
      const next: ProjectPointer = { ...current, state: "deleted", pointer_version: current.pointer_version + 1, updated_at: now, authority: false };
      const operation: ProjectTombstoneOperation = {
        schema: "quillframe_cloud_project_tombstone_operation_v1",
        operation_id: input.operation_id,
        input_fingerprint: inputFingerprint,
        receipt_snapshot: next,
        reason: input.reason,
        created_at: now,
        authority: false,
      };
      await tx.put(key, next);
      if (current.version_id) {
        const versionKey = `project-version:${input.project_id}:${current.version_id}`;
        const version = await tx.get<ProjectVersionRecord>(versionKey);
        if (version !== undefined) {
          assertProjectVersionRecord(version, input.project_id, current.version_id);
          await tx.put(versionKey, { ...version, status: "orphan" });
        }
      }
      await tx.put(operationKey, operation);
      return next;
    });
    if ("error" in outcome) throw outcome.error;
    return outcome;
  }

  async readProjectTombstoneOperation(input: { project_id: string; operation_id: string }): Promise<ProjectPointer | undefined> {
    assertProjectId(input.project_id);
    if (!boundedId(input.operation_id)) throw new WorkspaceCoordinatorError("project_tombstone_invalid", "project tombstone operation is invalid");
    return this.storage.transaction(async (tx) => {
      const record = await tx.get<ProjectTombstoneOperation>(`project-tombstone-operation:${input.project_id}:${input.operation_id}`);
      if (record === undefined) return undefined;
      assertProjectTombstoneOperation(record, input.project_id, input.operation_id);
      requireWorkspaceBinding(await tx.get<WorkspaceBinding>("workspace-binding"), record.receipt_snapshot.workspace_id);
      return record.receipt_snapshot;
    });
  }

  async destroyAll(): Promise<void> {
    const result = await this.storage.transaction(async (tx) => {
      if (!tx.list) throw new WorkspaceCoordinatorError("storage_list_required", "storage list is required for destruction");
      const all = await tx.list();
      for (const key of all.keys()) await tx.delete(key);
      await tx.deleteAlarm();
    });
    void result;
  }
}

function assertProjectId(projectId: unknown): asserts projectId is string {
  if (!boundedProjectId(projectId)) throw new WorkspaceCoordinatorError("project_identity_invalid", "project identity is invalid");
}

function assertExpectedVersion(version: unknown): asserts version is number {
  if (!Number.isSafeInteger(version) || (version as number) < 0 || (version as number) > 2 ** 31) throw new WorkspaceCoordinatorError("project_pointer_invalid", "project pointer version is invalid");
}

function assertNextPointer(next: ProjectPointerCasInput["next"], projectId: string): void {
  if (!next || next.state !== "active" || next.authority !== undefined && next.authority !== false || next.schema !== undefined && next.schema !== "quillframe_cloud_project_pointer_v1" || !boundedId(next.workspace_id) || next.project_id !== undefined && next.project_id !== projectId || !boundedPointerRef(next.version_id) || !boundedPointerRef(next.object_key) || !boundedPointerRef(next.plaintext_fingerprint)) throw new WorkspaceCoordinatorError("project_pointer_invalid", "project pointer input is invalid");
}

function assertPointer(pointer: ProjectPointer, projectId: string): void {
  if (!pointer || !exactKeys(pointer, ["schema", "workspace_id", "project_id", "pointer_version", "state", "updated_at", "authority"], ["version_id", "object_key", "plaintext_fingerprint"]) || pointer.schema !== "quillframe_cloud_project_pointer_v1" || !boundedId(pointer.workspace_id) || pointer.project_id !== projectId || !Number.isSafeInteger(pointer.pointer_version) || pointer.pointer_version < 1 || pointer.state !== "active" && pointer.state !== "deleted" || pointer.authority !== false || !Number.isSafeInteger(pointer.updated_at) || pointer.updated_at < 0) throw new WorkspaceCoordinatorError("project_pointer_invalid", "stored project pointer is invalid");
  for (const value of [pointer.version_id, pointer.object_key, pointer.plaintext_fingerprint]) if (value !== undefined && !boundedPointerRef(value)) throw new WorkspaceCoordinatorError("project_pointer_invalid", "stored project pointer reference is invalid");
  if (pointer.state === "active" && (!pointer.version_id || !pointer.object_key || !pointer.plaintext_fingerprint)) throw new WorkspaceCoordinatorError("project_pointer_invalid", "stored active project pointer is incomplete");
}

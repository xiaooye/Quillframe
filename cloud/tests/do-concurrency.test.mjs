import assert from "node:assert/strict";
import test from "node:test";

import { SessionVault, SessionVaultError } from "../dist/session-vault.js";
import { WorkspaceCoordinator, WorkspaceCoordinatorError } from "../dist/workspace-coordinator.js";
import { sha256, sha256Hex } from "../dist/crypto.js";
import { MemoryState, SerialTransactionStorage, keyBase64 } from "./helpers.mjs";

test("serialized transaction storage is copy-on-write, barriered, and reusable after commit failure", async () => {
  const storage = new SerialTransactionStorage();
  await storage.put("value", { count: 1 });
  const barrier = storage.installCommitBarrier();
  const first = storage.transaction(async (tx) => {
    const value = await tx.get("value");
    await tx.put("value", { count: value.count + 1 });
    return "committed";
  });
  await barrier.entered;
  assert.equal(storage.maxActive, 1);
  assert.deepEqual(await storage.get("value"), { count: 1 });
  barrier.release();
  assert.equal(await first, "committed");
  assert.deepEqual(await storage.get("value"), { count: 2 });

  storage.failNextCommit(new Error("commit sentinel"));
  await assert.rejects(() => storage.transaction(async (tx) => {
    await tx.put("value", { count: 3 });
  }), /commit sentinel/);
  assert.deepEqual(await storage.get("value"), { count: 2 });
  await storage.transaction(async (tx) => tx.put("value", { count: 4 }));
  assert.deepEqual(await storage.get("value"), { count: 4 });
  assert.equal(storage.maxActive, 1);
});

test("transaction rollback rejects later operations and leaves the serial queue usable", async () => {
  const storage = new SerialTransactionStorage();
  await storage.put("value", "before");
  await assert.rejects(() => storage.transaction(async (tx) => {
    await tx.put("value", "uncommitted");
    tx.rollback();
    await tx.get("value");
  }), (error) => error.code === "transaction_rolled_back");
  assert.equal(await storage.get("value"), "before");
  await storage.transaction(async (tx) => tx.put("value", "after"));
  assert.equal(await storage.get("value"), "after");
});

test("coordinator and vault fail closed when the storage transaction seam is absent", () => {
  const state = { storage: { get: async () => undefined, put: async () => {}, delete: async () => false, deleteAll: async () => {} } };
  assert.throws(() => new WorkspaceCoordinator(state, {}), (error) => error.code === "storage_transaction_required");
  assert.throws(() => new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64() }), (error) => error.code === "storage_transaction_required");
});

test("auth consumption is one-time and never returns a consumed verifier", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  const pending = await coordinator.beginAuth("/studio");
  assert.deepEqual(Object.keys(pending).sort(), ["authority", "code_challenge", "code_verifier", "expires_at", "return_to", "schema", "state", "transaction_id"]);
  const barrier = state.storage.installCommitBarrier();
  const outcomesPromise = Promise.allSettled([
    coordinator.consumeAuth(pending.transaction_id, pending.state),
    coordinator.consumeAuth(pending.transaction_id, pending.state),
  ]);
  await barrier.entered;
  barrier.release();
  const outcomes = await outcomesPromise;
  assert.ok([1, 2].includes(outcomes.filter((item) => item.status === "fulfilled").length));
  const fulfilled = outcomes.find((item) => item.status === "fulfilled");
  assert.deepEqual(Object.keys(fulfilled.value).sort(), ["authority", "code_challenge", "code_verifier", "expires_at", "return_to", "schema", "state", "transaction_id"]);
  const rejected = outcomes.find((item) => item.status === "rejected");
  assert.ok(rejected);
  assert.ok(["auth_already_consumed", "auth_state_invalid"].includes(rejected.reason.code));
  assert.equal(JSON.stringify(await state.storage.get(`auth-consumed:${pending.transaction_id}`)).includes("code_verifier"), false);
  await assert.rejects(() => coordinator.consumeAuth(pending.transaction_id, pending.state), (error) => error instanceof WorkspaceCoordinatorError && error.code === "auth_already_consumed");
});

test("session validation and destruction are transaction-bound and leave an epoch tombstone", async () => {
  let now = 1_800_000_000_000;
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => now });
  const created = await coordinator.createSession({ identity_id: "user_session" });
  const barrier = state.storage.installCommitBarrier();
  const outcomesPromise = Promise.allSettled([
    coordinator.validateSession(created.cookie_token, created.csrf_token),
    coordinator.destroySession(created.cookie_token),
  ]);
  await barrier.entered;
  barrier.release();
  const outcomes = await outcomesPromise;
  assert.equal(outcomes.filter((item) => item.status === "fulfilled").length, 1);
  assert.equal(state.storage.values.has(`session:${await sha256(created.cookie_token)}`), false);
  const tombstones = [...state.storage.values].filter(([key]) => key.startsWith("session-tombstone:"));
  assert.equal(tombstones.length, 1);
  await assert.rejects(() => coordinator.validateSession(created.cookie_token, created.csrf_token), (error) => error.code === "session_invalid" || error.code === "session_destroyed");
  now += 1;
  assert.equal(tombstones[0][1].authority, false);
});

test("lease versus destroy cannot resurrect a lease or index", async () => {
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(13) }, { now: () => 1_800_000_000_000 });
  const barrier = state.storage.installCommitBarrier();
  const outcomesPromise = Promise.allSettled([
    vault.leaseSecret({ workspace_id: "ws_race", session_id: "s_race", purpose: "model_endpoint", secret: "race-secret" }),
    vault.destroySession({ workspace_id: "ws_race", session_id: "s_race" }),
  ]);
  await barrier.entered;
  barrier.release();
  const outcomes = await outcomesPromise;
  const destroy = outcomes.find((item) => item.status === "fulfilled" && item.value && "destroyed" in item.value);
  assert.ok(destroy);
  assert.equal((await state.storage.get("lease-index") ?? []).length, 0);
  assert.equal(await state.storage.get("session:s_race"), undefined);
  assert.equal((await state.storage.get("vault-tombstone:s_race")).authority, false);
  const leaseOutcome = outcomes.find((item) => item.status === "fulfilled" && item.value && "lease_id" in item.value) ?? outcomes.find((item) => item.status === "rejected");
  assert.ok(leaseOutcome);
  if (leaseOutcome.status === "fulfilled") assert.equal((await state.storage.get(`lease:${leaseOutcome.value.lease_id}`)), undefined);
  else assert.ok(["secret_session_destroyed", "vault_alarm_failed"].includes(leaseOutcome.reason.code));
});

test("alarm versus lease retains only the new live lease", async () => {
  let now = 1_800_000_000_000;
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(14) }, { now: () => now });
  const old = await vault.leaseSecret({ workspace_id: "ws_alarm", session_id: "s_alarm", purpose: "model_endpoint", secret: "old" });
  now += 31 * 60 * 1000;
  const barrier = state.storage.installCommitBarrier();
  const outcomesPromise = Promise.allSettled([
    vault.alarm(),
    vault.leaseSecret({ workspace_id: "ws_alarm", session_id: "s_alarm", purpose: "model_endpoint", secret: "new" }),
  ]);
  await barrier.entered;
  barrier.release();
  const outcomes = await outcomesPromise;
  assert.equal(outcomes.filter((item) => item.status === "fulfilled").length, 2);
  const newReceipt = outcomes.find((item) => item.status === "fulfilled" && item.value && "lease_id" in item.value)?.value;
  assert.ok(newReceipt);
  const ids = await state.storage.get("session:s_alarm");
  assert.deepEqual(ids, [newReceipt.lease_id]);
  assert.equal(await state.storage.get(`lease:${old.lease_id}`), undefined);
  assert.deepEqual(await state.storage.get("lease-index"), [newReceipt.lease_id]);
});

test("real coordinator and vault commit failures produce no success receipt and leave retryable state", async () => {
  const coordinatorState = new MemoryState();
  const coordinator = new WorkspaceCoordinator(coordinatorState, {});
  coordinatorState.storage.failNextCommit(new Error("coordinator commit sentinel"));
  await assert.rejects(() => coordinator.beginAuth(), /coordinator commit sentinel/);
  assert.equal((await coordinatorState.storage.list({ prefix: "auth:" })).size, 0);
  const retryAuth = await coordinator.beginAuth();
  assert.equal(retryAuth.authority, false);

  const vaultState = new MemoryState();
  const vault = new SessionVault(vaultState, { SESSION_VAULT_KEY_B64: keyBase64(15) });
  vaultState.storage.failNextCommit(new Error("vault commit sentinel"));
  await assert.rejects(() => vault.leaseSecret({ workspace_id: "ws_failure", session_id: "s_failure", purpose: "model_endpoint", secret: "secret" }), /vault commit sentinel/);
  assert.equal((await vaultState.storage.list()).size, 0);
  const retryLease = await vault.leaseSecret({ workspace_id: "ws_failure", session_id: "s_failure", purpose: "model_endpoint", secret: "secret" });
  assert.equal(retryLease.authority, false);
});

test("alarm failure is atomic for lease creation and retryable without a leaked lease", async () => {
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(17) });
  state.storage.failNextAlarm(new Error("alarm commit sentinel"));
  await assert.rejects(() => vault.leaseSecret({ workspace_id: "ws_alarm_failure", session_id: "s_alarm_failure", purpose: "model_endpoint", secret: "alarm-secret" }), /alarm commit sentinel/);
  assert.equal((await state.storage.list()).size, 0);
  assert.equal(state.storage.alarm, undefined);
  const receipt = await vault.leaseSecret({ workspace_id: "ws_alarm_failure", session_id: "s_alarm_failure", purpose: "model_endpoint", secret: "alarm-secret" });
  assert.equal(receipt.authority, false);
  assert.equal((await state.storage.get("lease-index")).length, 1);
  assert.notEqual(state.storage.alarm, undefined);
});

test("alarm failure rolls back destroy and expiry cleanup, then retry completes", async () => {
  let now = 1_800_000_000_000;
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(18) }, { now: () => now });
  const lease = await vault.leaseSecret({ workspace_id: "ws_alarm_destroy", session_id: "s_alarm_destroy", purpose: "model_endpoint", secret: "destroy-secret" });
  state.storage.failNextAlarm(new Error("destroy alarm sentinel"));
  await assert.rejects(() => vault.destroySession({ workspace_id: "ws_alarm_destroy", session_id: "s_alarm_destroy" }), /destroy alarm sentinel/);
  assert.ok(await state.storage.get(`lease:${lease.lease_id}`));
  assert.equal(await state.storage.get("vault-tombstone:s_alarm_destroy"), undefined);
  await vault.destroySession({ workspace_id: "ws_alarm_destroy", session_id: "s_alarm_destroy" });
  assert.equal(await state.storage.get(`lease:${lease.lease_id}`), undefined);

  const expired = await vault.leaseSecret({ workspace_id: "ws_alarm_expiry", session_id: "s_alarm_expiry", purpose: "model_endpoint", secret: "expiry-secret" });
  now += 31 * 60 * 1000;
  state.storage.failNextAlarm(new Error("expiry alarm sentinel"));
  await assert.rejects(() => vault.alarm(), /expiry alarm sentinel/);
  assert.ok(await state.storage.get(`lease:${expired.lease_id}`));
  await vault.alarm();
  assert.equal(await state.storage.get(`lease:${expired.lease_id}`), undefined);
});

test("workspace binding prevents cross-owner pointer and session writes", async () => {
  const pointerState = new MemoryState();
  const coordinator = new WorkspaceCoordinator(pointerState, {}, { now: () => 1_800_000_000_000 });
  const firstNext = { ...pointer("bound"), project_id: "bound_project", workspace_id: "workspace_A" };
  await bindWorkspace(pointerState.storage, "workspace_A");
  await preparePointer(coordinator, firstNext, "op_bound_create", 0);
  const first = await coordinator.casProjectPointer({ project_id: "bound_project", expected_pointer_version: 0, next: firstNext });
  assert.equal(first.workspace_id, "workspace_A");
  await assert.rejects(() => coordinator.casProjectPointer({ project_id: "bound_project", expected_pointer_version: 1, next: { ...pointer("cross"), project_id: "bound_project", workspace_id: "workspace_B" } }), (error) => error.code === "workspace_binding_conflict" || error.code === "project_version_required");
  assert.equal((await coordinator.readProjectPointer("bound_project")).workspace_id, "workspace_A");
  const deleted = await coordinator.casProjectTombstone({ project_id: "bound_project", expected_pointer_version: 1, reason: "remove", operation_id: "op_bound" });
  assert.equal(deleted.workspace_id, "workspace_A");

  const sessionState = new MemoryState();
  const sessionCoordinator = new WorkspaceCoordinator(sessionState, {}, { now: () => 1_800_000_000_000 });
  const session = await sessionCoordinator.createSession({ identity_id: "binding_owner" });
  await assert.rejects(() => sessionCoordinator.casProjectPointer({ project_id: "session_project", expected_pointer_version: 0, next: { ...pointer("session"), project_id: "session_project", workspace_id: "workspace_other" } }), (error) => error.code === "workspace_binding_conflict" || error.code === "project_pointer_invalid" || error.code === "project_version_required");
  assert.equal((await sessionState.storage.get("workspace-binding")).workspace_id, session.workspace_id);
});

test("vault session binding prevents cross-workspace lease, read, destroy, and tombstone reuse", async () => {
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(19) });
  const lease = await vault.leaseSecret({ workspace_id: "workspace_A", session_id: "shared_session", purpose: "model_endpoint", secret: "a" });
  await assert.rejects(() => vault.leaseSecret({ workspace_id: "workspace_B", session_id: "shared_session", purpose: "model_endpoint", secret: "b" }), (error) => error.code === "vault_binding_invalid");
  await assert.rejects(() => vault.readSecret(lease.lease_id, { workspace_id: "workspace_B", session_id: "shared_session" }), (error) => error.code === "vault_binding_invalid" || error.code === "secret_lease_forbidden");
  await assert.rejects(() => vault.destroySession({ workspace_id: "workspace_B", session_id: "shared_session" }), (error) => error.code === "vault_binding_invalid" || error.code === "secret_lease_forbidden");
  await vault.destroySession({ workspace_id: "workspace_A", session_id: "shared_session" });
  await assert.rejects(() => vault.leaseSecret({ workspace_id: "workspace_B", session_id: "shared_session", purpose: "model_endpoint", secret: "b" }), (error) => error.code === "vault_binding_invalid");
});

test("concurrent lease creation preserves both indexes and destroy blocks resurrection", async () => {
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(12) }, { now: () => 1_800_000_000_000 });
  const barrier = state.storage.installCommitBarrier();
  const receiptsPromise = Promise.all([
    vault.leaseSecret({ workspace_id: "ws", session_id: "s", purpose: "workos_access", secret: "a" }),
    vault.leaseSecret({ workspace_id: "ws", session_id: "s", purpose: "workos_refresh", secret: "b" }),
  ]);
  await barrier.entered;
  barrier.release();
  const receipts = await receiptsPromise;
  assert.equal(new Set(receipts.map((item) => item.lease_id)).size, 2);
  assert.equal((await state.storage.get("session:s")).length, 2);
  assert.equal((await state.storage.get("lease-index")).length, 2);
  const destroyed = await vault.destroySession({ workspace_id: "ws", session_id: "s" });
  assert.equal(destroyed.authority, false);
  assert.equal(destroyed.destroyed, 2);
  await assert.rejects(() => vault.leaseSecret({ workspace_id: "ws", session_id: "s", purpose: "model_endpoint", secret: "c" }), (error) => error instanceof SessionVaultError && error.code === "secret_session_destroyed");
  assert.equal((await state.storage.get("vault-tombstone:s")).authority, false);
  assert.equal((await state.storage.get("lease-index") ?? []).length, 0);
});

function pointer(suffix = "one") {
  const digest = Array.from(new TextEncoder().encode(suffix), (value) => value.toString(16).padStart(2, "0")).join("").padEnd(64, "0").slice(0, 64);
  return {
    workspace_id: "workspace_test",
    project_id: "project_test",
    state: "active",
    version_id: `sha256:${digest}`,
    object_key: `v2/project_test/${suffix}.qfbundle`,
    plaintext_fingerprint: `sha256:${digest}`,
    authority: false,
  };
}

async function preparePointer(coordinator, next, operationId, expectedPointerVersion) {
  return coordinator.prepareProjectVersion({
    operation_id: operationId,
    input_fingerprint: `sha256:${"e".repeat(64)}`,
    workspace_id: next.workspace_id,
    project_id: next.project_id,
    expected_pointer_version: expectedPointerVersion,
    version_id: next.version_id,
    object_key: next.object_key,
    plaintext_fingerprint: next.plaintext_fingerprint,
    byte_size: 1,
  });
}

async function bindWorkspace(storage, workspaceId) {
  await storage.put("workspace-binding", { schema: "quillframe_cloud_workspace_binding_v1", workspace_id: workspaceId, bound_at: 1_800_000_000_000, authority: false });
}

test("project pointer CAS is serialized and stale writers conflict", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  const firstNext = pointer();
  await bindWorkspace(state.storage, "workspace_test");
  await preparePointer(coordinator, firstNext, "op_one", 0);
  const first = await coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 0, next: firstNext });
  assert.equal(first.pointer_version, 1);
  const secondNext = pointer("two");
  const thirdNext = pointer("three");
  await preparePointer(coordinator, secondNext, "op_two", 1);
  await preparePointer(coordinator, thirdNext, "op_three", 1);
  const barrier = state.storage.installCommitBarrier();
  const outcomesPromise = Promise.allSettled([
    coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 1, next: secondNext }),
    coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 1, next: thirdNext }),
  ]);
  await barrier.entered;
  barrier.release();
  const outcomes = await outcomesPromise;
  assert.equal(outcomes.filter((item) => item.status === "fulfilled").length, 1);
  const conflict = outcomes.find((item) => item.status === "rejected");
  assert.ok(conflict);
  assert.equal(conflict.reason.code, "project_pointer_conflict");
  assert.equal((await coordinator.readProjectPointer("project_test")).pointer_version, 2);
});

test("orphan GC is bounded, tombstones the version before delete, and blocks re-reference", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  await bindWorkspace(state.storage, "workspace_test");
  const first = { ...pointer("gc-base") };
  await preparePointer(coordinator, first, "gc_base", 0);
  await coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 0, next: first });
  const loser = { ...pointer("gc-loser") };
  await preparePointer(coordinator, loser, "gc_loser", 1);
  const winner = { ...pointer("gc-winner") };
  await preparePointer(coordinator, winner, "gc_winner", 1);
  await coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 1, next: winner });
  await assert.rejects(() => coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 1, next: loser }), (error) => error.code === "project_pointer_conflict");

  const pending = await coordinator.beginProjectVersionGc({ project_id: "project_test", version_id: loser.version_id, operation_id: "gc_run", retention_before: 1_800_000_000_001 });
  assert.equal(pending.status, "pending");
  await assert.rejects(() => coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 2, next: loser }), (error) => error.code === "project_version_gc_pending");
  const failedDelete = await coordinator.finishProjectVersionGc({ project_id: "project_test", version_id: loser.version_id, operation_id: "gc_run", deleted: false });
  assert.equal(failedDelete.status, "pending");
  const complete = await coordinator.finishProjectVersionGc({ project_id: "project_test", version_id: loser.version_id, operation_id: "gc_run", deleted: true });
  assert.equal(complete.status, "completed");
  assert.equal(await state.storage.get(`project-version:project_test:${loser.version_id}`), undefined);
  assert.equal(await state.storage.get("project-version-operation:project_test:gc_loser"), undefined);
  assert.deepEqual(await coordinator.beginProjectVersionGc({ project_id: "project_test", version_id: loser.version_id, operation_id: "gc_run", retention_before: 1_800_000_000_001 }), complete);
  await assert.rejects(() => coordinator.beginProjectVersionGc({ project_id: "project_test", version_id: winner.version_id, operation_id: "gc_active", retention_before: 1_800_000_000_001 }), (error) => error.code === "project_gc_not_eligible");

  for (let index = 0; index < 255; index += 1) {
    const versionId = `sha256:${index.toString(16).padStart(64, "0")}`;
    const receipt = { schema: "quillframe_cloud_project_version_gc_v1", operation_id: `gc_old_${index}`, project_id: "project_test", version_id: versionId, workspace_id: "workspace_test", object_key: `v2/workspace_test/project_test/versions/${versionId}.qfbundle`, plaintext_fingerprint: versionId, byte_size: 1, pointer_version: 0, status: "completed", authority: false };
    await state.storage.put(`project-version-gc-operation:project_test:gc_old_${index}`, { schema: "quillframe_cloud_project_version_gc_operation_v1", operation_id: `gc_old_${index}`, project_id: "project_test", version_id: versionId, retention_before: 1, receipt_snapshot: receipt, created_at: index + 1, authority: false });
  }
  const pruneVersion = `sha256:${"d".repeat(64)}`;
  await state.storage.put(`project-version:project_test:${pruneVersion}`, { schema: "quillframe_cloud_project_version_record_v1", operation_id: "gc_prune_prepare", input_fingerprint: `sha256:${"a".repeat(64)}`, workspace_id: "workspace_test", project_id: "project_test", expected_pointer_version: 2, version_id: pruneVersion, object_key: `v2/workspace_test/project_test/versions/${pruneVersion}.qfbundle`, plaintext_fingerprint: pruneVersion, byte_size: 1, status: "orphan", authority: false, created_at: 0, pointer_version: 2 });
  const pruned = await coordinator.beginProjectVersionGc({ project_id: "project_test", version_id: pruneVersion, operation_id: "gc_prune_new", retention_before: 1_800_000_000_001 });
  assert.equal(pruned.status, "pending");
  assert.equal(await state.storage.get("project-version-gc-operation:project_test:gc_old_0"), undefined);
});

test("project tombstone operation is immutable, exact-replayable, and cannot remove a later active pointer", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  const initial = pointer();
  await bindWorkspace(state.storage, "workspace_test");
  await preparePointer(coordinator, initial, "op_delete_create", 0);
  await coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 0, next: initial });
  const deleted = await coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "author_delete", operation_id: "op_delete_1" });
  assert.equal(deleted.state, "deleted");
  assert.equal(typeof deleted.version_id, "string");
  assert.equal(typeof deleted.object_key, "string");
  assert.equal(typeof deleted.plaintext_fingerprint, "string");
  const replay = await coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "author_delete", operation_id: "op_delete_1" });
  assert.deepEqual(replay, deleted);
  await assert.rejects(() => coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "different", operation_id: "op_delete_1" }), (error) => error.code === "project_tombstone_operation_conflict");
  const restoredNext = pointer("restored");
  await preparePointer(coordinator, restoredNext, "op_restore", 2);
  const restored = await coordinator.casProjectPointer({ project_id: "project_test", expected_pointer_version: 2, next: restoredNext });
  assert.equal(restored.state, "active");
  assert.deepEqual(await coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "author_delete", operation_id: "op_delete_1" }), deleted);
  assert.equal((await coordinator.readProjectPointer("project_test")).pointer_version, restored.pointer_version);

  const operationKey = "project-tombstone-operation:project_test:op_delete_1";
  const operation = await state.storage.get(operationKey);
  await state.storage.put(operationKey, { ...operation, unexpected: true });
  await assert.rejects(
    () => coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "author_delete", operation_id: "op_delete_1" }),
    (error) => error.code === "project_tombstone_operation_invalid",
  );
  const { created_at: _createdAt, ...missingCreatedAt } = operation;
  await state.storage.put(operationKey, missingCreatedAt);
  await assert.rejects(
    () => coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "author_delete", operation_id: "op_delete_1" }),
    (error) => error.code === "project_tombstone_operation_invalid",
  );
  await state.storage.put(operationKey, { ...operation, reason: "corrupt_reason" });
  await assert.rejects(
    () => coordinator.casProjectTombstone({ project_id: "project_test", expected_pointer_version: 1, reason: "author_delete", operation_id: "op_delete_1" }),
    (error) => error.code === "project_tombstone_operation_conflict",
  );
});

test("corrupt records and oversized indexes fail closed with exact validation", async () => {
  const authState = new MemoryState();
  const authCoordinator = new WorkspaceCoordinator(authState, {});
  const auth = await authCoordinator.beginAuth();
  await authState.storage.put(`auth-consumed:${auth.transaction_id}`, {
    schema: "quillframe_cloud_auth_consumed_v1",
    transaction_id: auth.transaction_id,
    state_hash: "x",
    consumed_at: 1,
    authority: false,
    unexpected: true,
  });
  await assert.rejects(() => authCoordinator.consumeAuth(auth.transaction_id, auth.state), (error) => error.code === "auth_record_invalid");
  await assert.rejects(() => authCoordinator.consumeAuth(`auth_${"x".repeat(97)}`, auth.state), (error) => error.code === "auth_state_invalid");

  const pendingState = new MemoryState();
  const pendingCoordinator = new WorkspaceCoordinator(pendingState, {});
  const pendingAuth = await pendingCoordinator.beginAuth();
  const pendingRecord = await pendingState.storage.get(`auth:${pendingAuth.transaction_id}`);
  const { code_verifier: _missingVerifier, ...missingVerifierRecord } = pendingRecord;
  await pendingState.storage.put(`auth:${pendingAuth.transaction_id}`, missingVerifierRecord);
  await assert.rejects(() => pendingCoordinator.consumeAuth(pendingAuth.transaction_id, pendingAuth.state), (error) => error.code === "auth_record_invalid");

  const wrongTypeState = new MemoryState();
  const wrongTypeCoordinator = new WorkspaceCoordinator(wrongTypeState, {});
  const wrongTypeAuth = await wrongTypeCoordinator.beginAuth();
  const wrongTypeRecord = await wrongTypeState.storage.get(`auth:${wrongTypeAuth.transaction_id}`);
  await wrongTypeState.storage.put(`auth:${wrongTypeAuth.transaction_id}`, { ...wrongTypeRecord, code_challenge: 42 });
  await assert.rejects(() => wrongTypeCoordinator.consumeAuth(wrongTypeAuth.transaction_id, wrongTypeAuth.state), (error) => error.code === "auth_record_invalid");

  const sessionState = new MemoryState();
  const sessionCoordinator = new WorkspaceCoordinator(sessionState, {});
  const session = await sessionCoordinator.createSession({ identity_id: "corrupt_session" });
  const sessionKey = `session:${await sha256(session.cookie_token)}`;
  const sessionRecord = await sessionState.storage.get(sessionKey);
  await sessionState.storage.put(sessionKey, { ...sessionRecord, unexpected: true });
  await assert.rejects(() => sessionCoordinator.validateSession(session.cookie_token, session.csrf_token), (error) => error.code === "session_record_invalid");

  const pointerState = new MemoryState();
  const pointerCoordinator = new WorkspaceCoordinator(pointerState, {});
  await pointerState.storage.put("project:corrupt", {
    schema: "quillframe_cloud_project_pointer_v1",
    workspace_id: "workspace_corrupt",
    project_id: "corrupt",
    pointer_version: 1,
    state: "active",
    version_id: "version_corrupt",
    object_key: "v1/corrupt.qfbundle",
    plaintext_fingerprint: "fp_corrupt",
    updated_at: 1,
    authority: false,
    unexpected: true,
  });
  await assert.rejects(() => pointerCoordinator.readProjectPointer("corrupt"), (error) => error.code === "project_pointer_invalid");

  const vaultState = new MemoryState();
  const vault = new SessionVault(vaultState, { SESSION_VAULT_KEY_B64: keyBase64(16) });
  await vaultState.storage.put("lease-index", Array.from({ length: 2049 }, (_, index) => `lease_${index}`));
  await assert.rejects(() => vault.alarm(), (error) => error.code === "vault_record_invalid");
});

test("transaction mock exposes an external-I/O sentinel without allowing production callbacks to use it", async () => {
  const storage = new SerialTransactionStorage();
  await storage.transaction(async () => storage.markExternalIo());
  assert.equal(storage.externalIoDuringTransaction, 1);
});

test("project version preparation is transactional, exact-replayable, and content-deduplicates new operations", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  await bindWorkspace(state.storage, "workspace_version");
  const version = {
    workspace_id: "workspace_version",
    project_id: "project_version",
    version_id: `sha256:${"1".repeat(64)}`,
    object_key: "v2/project_version/one.qfbundle",
    plaintext_fingerprint: `sha256:${"1".repeat(64)}`,
    byte_size: 12,
  };
  const firstInput = { ...version, operation_id: "version_op_one", input_fingerprint: `sha256:${"2".repeat(64)}`, expected_pointer_version: 0 };
  const first = await coordinator.prepareProjectVersion(firstInput);
  assert.equal(first.status, "prepared");
  assert.deepEqual(await coordinator.prepareProjectVersion(firstInput), first);
  const dedup = await coordinator.prepareProjectVersion({ ...firstInput, operation_id: "version_op_two", input_fingerprint: `sha256:${"3".repeat(64)}` });
  assert.equal(dedup.operation_id, "version_op_two");
  assert.equal(dedup.version_id, first.version_id);
  await assert.rejects(() => coordinator.prepareProjectVersion({ ...firstInput, operation_id: "version_op_three", plaintext_fingerprint: `sha256:${"4".repeat(64)}` }), (error) => error.code === "project_version_conflict");
  await assert.rejects(() => coordinator.prepareProjectVersion({ ...firstInput, operation_id: "version_op_four", expected_pointer_version: 1 }), (error) => error.code === "project_version_conflict" || error.code === "project_pointer_conflict");
  state.storage.failNextCommit(new Error("version commit sentinel"));
  await assert.rejects(() => coordinator.prepareProjectVersion({ ...version, operation_id: "version_op_retry", input_fingerprint: `sha256:${"5".repeat(64)}`, expected_pointer_version: 0 }), /version commit sentinel/);
  assert.equal(await state.storage.get("project-version-operation:project_version:version_op_retry"), undefined);
  const retry = await coordinator.prepareProjectVersion({ ...version, operation_id: "version_op_retry", input_fingerprint: `sha256:${"5".repeat(64)}`, expected_pointer_version: 0 });
  assert.equal(retry.operation_id, "version_op_retry");
});

test("pointer CAS rejects an unprepared version instead of authorizing arbitrary active state", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  await bindWorkspace(state.storage, "workspace_unprepared");
  const next = { ...pointer("unprepared"), workspace_id: "workspace_unprepared", project_id: "project_unprepared" };
  await assert.rejects(() => coordinator.casProjectPointer({ project_id: "project_unprepared", expected_pointer_version: 0, next }), (error) => error.code === "project_version_required");
  assert.equal(await coordinator.readProjectPointer("project_unprepared"), undefined);
});

test("core proof nonce is single-use, digest-bound, and transactionally serialized", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  const input = { session_id: "session_nonce", project_id: "project_nonce", nonce: "nonce_1", proof_digest: "sha256:" + "a".repeat(64), issued_at: 1_800_000_000_000, expires_at: 1_800_000_025_000 };
  const outcomes = await Promise.allSettled([
    coordinator.consumeCoreNonce(input),
    coordinator.consumeCoreNonce(input),
  ]);
  assert.equal(outcomes.filter((item) => item.status === "fulfilled").length, 1);
  assert.equal(outcomes.filter((item) => item.status === "rejected" && item.reason.code === "core_nonce_replayed").length, 1);
  await assert.rejects(() => coordinator.consumeCoreNonce({ ...input, proof_digest: "sha256:" + "b".repeat(64) }), (error) => error.code === "core_nonce_digest_conflict");
  const nonceRecords = [...state.storage.values].filter(([key]) => key.startsWith("core-nonce:"));
  assert.equal(nonceRecords.length, 1);
  assert.equal(JSON.stringify(nonceRecords[0][1]).includes("nonce_1"), false);
});

test("core nonce binds the global nonce hash to session, project, and proof digest", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  const input = { session_id: "session_a", project_id: "project_a", nonce: "nonce_cross", proof_digest: "sha256:" + "a".repeat(64), issued_at: 1_800_000_000_000, expires_at: 1_800_000_025_000 };
  await coordinator.consumeCoreNonce(input);
  await assert.rejects(() => coordinator.consumeCoreNonce({ ...input, session_id: "session_b" }), (error) => error.code === "core_nonce_digest_conflict");
  await assert.rejects(() => coordinator.consumeCoreNonce({ ...input, project_id: "project_b" }), (error) => error.code === "core_nonce_digest_conflict");
  await assert.rejects(() => coordinator.consumeCoreNonce({ ...input, proof_digest: "sha256:" + "b".repeat(64) }), (error) => error.code === "core_nonce_digest_conflict");
});

test("core nonce index is an exact envelope and missing or corrupt state fails closed", async () => {
  const missing = new MemoryState();
  const missingCoordinator = new WorkspaceCoordinator(missing, {}, { now: () => 1_800_000_000_000 });
  await missing.storage.put(`core-nonce:${await sha256Hex("orphan")}`, { schema: "unexpected" });
  await assert.rejects(() => missingCoordinator.consumeCoreNonce({ session_id: "session_a", project_id: null, nonce: "fresh", proof_digest: "sha256:" + "a".repeat(64), issued_at: 1_800_000_000_000, expires_at: 1_800_000_025_000 }), (error) => error.code === "core_nonce_record_invalid");

  const corrupt = new MemoryState();
  const corruptCoordinator = new WorkspaceCoordinator(corrupt, {}, { now: () => 1_800_000_000_000 });
  const input = { session_id: "session_a", project_id: null, nonce: "nonce_corrupt", proof_digest: "sha256:" + "a".repeat(64), issued_at: 1_800_000_000_000, expires_at: 1_800_000_025_000 };
  await corruptCoordinator.consumeCoreNonce(input);
  await corrupt.storage.put("core-nonce-index", []);
  await assert.rejects(() => corruptCoordinator.consumeCoreNonce({ ...input, nonce: "nonce_other", proof_digest: "sha256:" + "b".repeat(64) }), (error) => error.code === "core_nonce_record_invalid");
  assert.equal(Array.isArray(await corrupt.storage.get("core-nonce-index")), true);
});

test("core nonce replay retention covers verifier skew, then expires and permits a fresh nonce epoch", async () => {
  let now = 1_800_000_000_000;
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => now });
  const first = { session_id: "session_a", project_id: null, nonce: "nonce_skew", proof_digest: "sha256:" + "a".repeat(64), issued_at: now, expires_at: now + 1_000 };
  await coordinator.consumeCoreNonce(first);
  now = first.expires_at + 1;
  await assert.rejects(() => coordinator.consumeCoreNonce(first), (error) => error.code === "core_nonce_replayed");
  now = first.expires_at + 5_001;
  await coordinator.consumeCoreNonce({ ...first, issued_at: now, expires_at: now + 1_000, proof_digest: "sha256:" + "b".repeat(64) });
  const index = await state.storage.get("core-nonce-index");
  assert.equal(index.entries.length, 1);
  assert.equal(index.entries[0].replay_expires_at, now + 6_000);
});

test("core nonce capacity rejects without truncating the exact 256-entry index", async () => {
  const now = 1_800_000_000_000;
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => now });
  for (let index = 0; index < 256; index += 1) {
    await coordinator.consumeCoreNonce({ session_id: "session_capacity", project_id: null, nonce: `nonce_capacity_${index}`, proof_digest: "sha256:" + index.toString(16).padStart(2, "0").repeat(32), issued_at: now, expires_at: now + 25_000 });
  }
  const before = await state.storage.get("core-nonce-index");
  assert.equal(before.entries.length, 256);
  await assert.rejects(() => coordinator.consumeCoreNonce({ session_id: "session_capacity", project_id: null, nonce: "nonce_capacity_overflow", proof_digest: "sha256:" + "f".repeat(64), issued_at: now, expires_at: now + 25_000 }), (error) => error.code === "core_nonce_capacity");
  const after = await state.storage.get("core-nonce-index");
  assert.deepEqual(after, before);
  assert.equal([...state.storage.values].filter(([key]) => key.startsWith("core-nonce:")).length, 256);
});

test("core nonce commit failure rolls back record and index, then retry succeeds", async () => {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => 1_800_000_000_000 });
  const input = { session_id: "session_retry", project_id: null, nonce: "nonce_retry", proof_digest: "sha256:" + "a".repeat(64), issued_at: 1_800_000_000_000, expires_at: 1_800_000_025_000 };
  state.storage.failNextCommit(new Error("nonce commit sentinel"));
  await assert.rejects(() => coordinator.consumeCoreNonce(input), /nonce commit sentinel/);
  assert.equal(await state.storage.get("core-nonce-index"), undefined);
  assert.equal([...state.storage.values].filter(([key]) => key.startsWith("core-nonce:")).length, 0);
  await coordinator.consumeCoreNonce(input);
});

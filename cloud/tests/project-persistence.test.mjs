import assert from "node:assert/strict";
import test from "node:test";

import { createWorker } from "../dist/index.js";
import { canonicalJsonBytes } from "../dist/core-provenance.js";
import { sha256Hex } from "../dist/crypto.js";
import { WorkspaceCoordinator } from "../dist/workspace-coordinator.js";
import { MemoryBucket, MemoryState, keyBase64 } from "./helpers.mjs";

function namespace(value) {
  return { getByName: () => value };
}

async function fixture({ alignUploadPointerReads = false } = {}) {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {});
  const session = await coordinator.createSession({ identity_id: "project_upload_owner" });
  const bucket = new MemoryBucket();
  const observed = [];
  let rejectNextCore = false;
  const core = {
    fetch: async (request) => {
      if (rejectNextCore) {
        rejectNextCore = false;
        return new Response(canonicalJsonBytes({ authority: false, code: "native_backup_invalid", schema: "quillframe_cloud_core_error_v1" }), { status: 400, headers: { "content-type": "application/json" } });
      }
      observed.push(request);
      const source = new URL(request.url);
      assert.equal(source.pathname, "/native/project-backup/verify");
      const operation = source.searchParams.get("operation");
      if (operation === "project.read") {
        assert.deepEqual([...source.searchParams.keys()].sort(), ["object_key_sha256", "operation", "pointer_version", "project_id", "version_id"]);
      } else {
        assert.equal(operation, "project.upload");
        assert.deepEqual([...source.searchParams.keys()].sort(), ["operation", "project_id"]);
        assert.equal(source.search, "?operation=project.upload&project_id=project_h3");
      }
      assert.equal(request.headers.get("content-type"), "application/zip");
      const body = new Uint8Array(await request.arrayBuffer());
      const fingerprint = `sha256:${await sha256Hex(body)}`;
      const receipt = {
        authority: false,
        blob_count: 0,
        body_fingerprint: fingerprint,
        bundle_fingerprint: fingerprint,
        bundle_schema: "quillframe_backup_bundle_v1",
        byte_size: body.byteLength,
        chapter_scope: "CH001",
        database_bytes: 1,
        database_fingerprint: `sha256:${"a".repeat(64)}`,
        project_id: "project_h3",
        schema: "quillframe_native_backup_verification_v1",
        verified: true,
      };
      return new Response(canonicalJsonBytes(receipt), { status: 200, headers: { "content-type": "application/json" } });
    },
  };
  let releasePointerReadBarrier = () => {};
  if (alignUploadPointerReads) {
    let pointerReadCount = 0;
    let resolvePointerReadBarrier;
    const pointerReadBarrier = new Promise((resolve) => { resolvePointerReadBarrier = resolve; });
    releasePointerReadBarrier = resolvePointerReadBarrier;
    const readProjectPointer = coordinator.readProjectPointer.bind(coordinator);
    coordinator.readProjectPointer = async (projectId) => {
      const pointer = await readProjectPointer(projectId);
      pointerReadCount += 1;
      if (pointerReadCount === 2) resolvePointerReadBarrier();
      await pointerReadBarrier;
      return pointer;
    };
  }
  const key = Buffer.alloc(32, 8).toString("base64url");
  const env = {
    PUBLIC_ORIGIN: "https://studio.example",
    WORKOS_CLIENT_ID: "client",
    WORKOS_API_KEY: "key",
    WORKOS_REDIRECT_URI: "https://studio.example/api/auth/callback",
    SESSION_VAULT_KEY_B64: keyBase64(3),
    PROJECT_BUNDLE_KEY_B64: keyBase64(4),
    PROJECT_BUNDLE_KEY_ID: "current",
    WORKSPACE_COORDINATOR: namespace(coordinator),
    SESSION_VAULT: namespace({ destroySession: async () => ({ destroyed: 0, authority: false }) }),
    PROJECT_BUNDLES: bucket,
    CORE_CONTAINER: namespace(core),
    CORE_PROOF_KEY_B64: key,
    CORE_PROOF_KEY_ID: "current",
    ENDPOINT_EGRESS: { fetch: async () => new Response(null, { status: 204 }) },
  };
  const cookies = `__Host-qf_session=${session.cookie_token}; __Host-qf_csrf=${session.csrf_token}`;
  return { env, worker: createWorker(), session, cookies, bucket, observed, state, rejectNextCore: () => { rejectNextCore = true; }, releasePointerReadBarrier };
}

function requestFor(cookies, method, path, body, headers = {}) {
  const bytes = body === undefined ? undefined : new TextEncoder().encode(body);
  return new Request(`https://studio.example${path}`, {
    method,
    headers: {
      Origin: "https://studio.example",
      Cookie: cookies,
      "x-qf-csrf": cookies.split("__Host-qf_csrf=")[1],
      "content-type": "application/zip",
      ...(bytes ? { "content-length": String(bytes.byteLength) } : {}),
      ...headers,
    },
    body: bytes,
  });
}

test("hosted upload verifies raw native receipt before immutable R2 and pointer CAS, then exact-replays", async () => {
  const { env, worker, cookies, bucket, observed } = await fixture();
  const headers = { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_h3_1" };
  const first = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "native-bundle", headers), env);
  assert.equal(first.status, 201);
  const receipt = await first.json();
  assert.equal(receipt.schema, "quillframe_cloud_project_upload_receipt_v2");
  assert.equal(receipt.authority, false);
  assert.equal(observed.length, 1);
  assert.equal(bucket.values.size, 1);
  const pointer = await env.WORKSPACE_COORDINATOR.getByName("unused").readProjectPointer("project_h3");
  assert.equal(pointer.state, "active");
  assert.equal(pointer.object_key, receipt.object_key);
  assert.equal(pointer.pointer_version, 1);

  const replay = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "native-bundle", headers), env);
  assert.equal(replay.status, 201);
  assert.deepEqual(await replay.json(), receipt);
  assert.equal(bucket.values.size, 1);
  assert.equal(observed.length, 2);
  const replayedPointer = await env.WORKSPACE_COORDINATOR.getByName("unused").readProjectPointer("project_h3");
  assert.equal(replayedPointer.pointer_version, receipt.pointer_version);
});

test("two hosted uploads aligned on the same pointer produce one CAS winner and one indexed orphan", async () => {
  const { env, worker, cookies, bucket, state } = await fixture({ alignUploadPointerReads: true });
  const firstRequest = worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "concurrent-first", { "x-qf-explicit-action": "project.upload", "idempotency-key": "concurrent_first" }), env);
  const secondRequest = worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "concurrent-second", { "x-qf-explicit-action": "project.upload", "idempotency-key": "concurrent_second" }), env);
  const responses = await Promise.all([firstRequest, secondRequest]);
  assert.deepEqual(responses.map((response) => response.status).sort((left, right) => left - right), [201, 400]);
  const winnerResponse = responses.find((response) => response.status === 201);
  const loserResponse = responses.find((response) => response.status === 400);
  const winner = await winnerResponse.json();
  assert.equal((await loserResponse.json()).code, "project_pointer_conflict");
  const pointer = await env.WORKSPACE_COORDINATOR.getByName("unused").readProjectPointer("project_h3");
  assert.equal(pointer.pointer_version, 1);
  assert.equal(pointer.version_id, winner.version_id);
  assert.equal(bucket.values.size, 2);
  const versionRecords = [...state.storage.values.entries()]
    .filter(([key]) => key.startsWith("project-version:project_h3:"))
    .map(([, value]) => value);
  assert.equal(versionRecords.length, 2);
  assert.deepEqual(versionRecords.map((record) => record.status).sort(), ["active", "orphan"]);
  assert.equal(versionRecords.filter((record) => record.status === "active")[0].version_id, winner.version_id);
});

test("hosted project delete tombstones before R2, keeps the session, and retries GC without touching a later identity", async () => {
  const { env, worker, cookies, bucket } = await fixture();
  const upload = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "delete-me", { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_for_delete" }), env);
  assert.equal(upload.status, 201);

  const originalDelete = bucket.delete.bind(bucket);
  bucket.delete = async () => { throw new Error("r2 delete sentinel"); };
  const pending = await worker.fetch(requestFor(cookies, "DELETE", "/api/projects/project_h3", undefined, { "x-qf-explicit-action": "project.delete", "idempotency-key": "delete_h3_1" }), env);
  assert.equal(pending.status, 202);
  assert.equal((await pending.json()).gc, "pending");
  const deletedPointer = await env.WORKSPACE_COORDINATOR.getByName("unused").readProjectPointer("project_h3");
  assert.equal(deletedPointer.state, "deleted");
  bucket.delete = originalDelete;
  const complete = await worker.fetch(requestFor(cookies, "DELETE", "/api/projects/project_h3", undefined, { "x-qf-explicit-action": "project.delete", "idempotency-key": "delete_h3_1" }), env);
  assert.equal(complete.status, 200);
  assert.equal((await complete.json()).gc, "complete");
  assert.equal(bucket.values.size, 0);
  const session = await env.WORKSPACE_COORDINATOR.getByName("unused").validateSession(cookies.split(";")[0].split("=")[1], cookies.split("__Host-qf_csrf=")[1]);
  assert.equal(session.authority, false);
});

test("hosted project mutations reject legacy proof/identity aliases and caller-only upload headers", async () => {
  const { env, worker, cookies } = await fixture();
  const cases = [
    { "x-qf-explicit-upload": "true", "idempotency-key": "legacy_upload" },
    { "x-qf-explicit-action": "project.upload", "idempotency-key": "alias_upload", "x-qf-project-id": "sentinel" },
    { "x-qf-explicit-action": "project.delete", "idempotency-key": "alias_delete", authorization: "Bearer sentinel" },
  ];
  for (const headers of cases) {
    const method = headers["x-qf-explicit-action"] === "project.delete" ? "DELETE" : "POST";
    const response = await worker.fetch(requestFor(cookies, method, "/api/projects/project_h3" + (method === "POST" ? "/upload" : ""), method === "POST" ? "body" : undefined, headers), env);
    assert.equal(response.status, 403);
    assert.doesNotMatch(await response.text(), /sentinel|Bearer/);
  }
});

test("hosted GET reads only the active pointer, revalidates through signed native read proof, and returns bounded ZIP bytes", async () => {
  const { env, worker, cookies } = await fixture();
  const upload = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "readable-bundle", { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_for_read" }), env);
  assert.equal(upload.status, 201);
  const response = await worker.fetch(requestFor(cookies, "GET", "/api/projects/project_h3"), env);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("content-type"), "application/zip");
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("x-qf-authority"), "false");
  assert.equal(response.headers.get("x-qf-pointer-version"), "1");
  assert.equal(await response.text(), "readable-bundle");
});

test("hosted GET rejects caller proof/identity aliases without returning bytes", async () => {
  const { env, worker, cookies } = await fixture();
  const upload = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "read-alias", { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_alias_read" }), env);
  assert.equal(upload.status, 201);
  for (const [name, value] of [["x-qf-project-id", "sentinel"], ["x-qf-core-proof", "proof-sentinel"], ["authorization", "Bearer sentinel"]]) {
    const response = await worker.fetch(requestFor(cookies, "GET", "/api/projects/project_h3", undefined, { [name]: value }), env);
    assert.equal(response.status, 403);
    assert.doesNotMatch(await response.text(), /sentinel|read-alias/);
  }
});

test("hosted GET fails closed on Core revalidation and never returns stored bytes", async () => {
  const { env, worker, cookies, rejectNextCore } = await fixture();
  const upload = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "read-core-failure", { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_core_failure" }), env);
  assert.equal(upload.status, 201);
  rejectNextCore();
  const response = await worker.fetch(requestFor(cookies, "GET", "/api/projects/project_h3"), env);
  assert.equal(response.status, 400);
  assert.doesNotMatch(await response.text(), /read-core-failure|native_backup_invalid/);
});

test("hosted project GC is authenticated, exact-project bounded, retryable, and never scans the bucket", async () => {
  const { env, worker, cookies, bucket, session, state } = await fixture();
  const upload = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "gc-base", { "x-qf-explicit-action": "project.upload", "idempotency-key": "gc_base_upload" }), env);
  assert.equal(upload.status, 201);
  const coordinator = env.WORKSPACE_COORDINATOR.getByName("unused");
  const loserVersion = `sha256:${"f".repeat(64)}`;
  const winnerVersion = `sha256:${"e".repeat(64)}`;
  const loserKey = `v2/${await sha256Hex(session.workspace_id)}/project_h3/versions/${loserVersion}.qfbundle`;
  const winnerKey = `v2/${await sha256Hex(session.workspace_id)}/project_h3/versions/${winnerVersion}.qfbundle`;
  const baseInput = { workspace_id: session.workspace_id, project_id: "project_h3", expected_pointer_version: 1, byte_size: 1 };
  await coordinator.prepareProjectVersion({ ...baseInput, operation_id: "gc_loser_prepare", input_fingerprint: `sha256:${"1".repeat(64)}`, version_id: loserVersion, object_key: loserKey, plaintext_fingerprint: loserVersion });
  await coordinator.prepareProjectVersion({ ...baseInput, operation_id: "gc_winner_prepare", input_fingerprint: `sha256:${"2".repeat(64)}`, version_id: winnerVersion, object_key: winnerKey, plaintext_fingerprint: winnerVersion });
  await coordinator.casProjectPointer({ project_id: "project_h3", expected_pointer_version: 1, next: { ...baseInput, state: "active", version_id: winnerVersion, object_key: winnerKey, plaintext_fingerprint: winnerVersion, authority: false } });
  await assert.rejects(() => coordinator.casProjectPointer({ project_id: "project_h3", expected_pointer_version: 1, next: { ...baseInput, state: "active", version_id: loserVersion, object_key: loserKey, plaintext_fingerprint: loserVersion, authority: false } }), (error) => error.code === "project_pointer_conflict");
  const loserStorageKey = `project-version:project_h3:${loserVersion}`;
  // The public coordinator owns the record; age it through the test storage
  // only to make the conservative retention boundary deterministic.
  const record = await state.storage.get(loserStorageKey);
  await state.storage.put(loserStorageKey, { ...record, created_at: 0 });
  const originalDelete = bucket.delete.bind(bucket);
  bucket.delete = async () => { throw new Error("gc pending sentinel"); };
  const pending = await worker.fetch(requestFor(cookies, "POST", `/api/projects/project_h3/gc?version_id=${loserVersion}`, undefined, { "x-qf-explicit-action": "project.gc", "idempotency-key": "gc_operation" }), env);
  assert.equal(pending.status, 202);
  bucket.delete = originalDelete;
  const complete = await worker.fetch(requestFor(cookies, "POST", `/api/projects/project_h3/gc?version_id=${loserVersion}`, undefined, { "x-qf-explicit-action": "project.gc", "idempotency-key": "gc_operation" }), env);
  assert.equal(complete.status, 200);
  assert.equal((await complete.json()).status, "completed");
});

test("a delete operation cannot remove a later reactivated pointer after response loss", async () => {
  const { env, worker, cookies, bucket } = await fixture();
  const initial = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "first-version", { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_first" }), env);
  assert.equal(initial.status, 201);
  const pendingDelete = bucket.delete;
  bucket.delete = async () => { throw new Error("delete response lost"); };
  const pending = await worker.fetch(requestFor(cookies, "DELETE", "/api/projects/project_h3", undefined, { "x-qf-explicit-action": "project.delete", "idempotency-key": "delete_old" }), env);
  assert.equal(pending.status, 202);
  bucket.delete = pendingDelete;
  const reactivated = await worker.fetch(requestFor(cookies, "POST", "/api/projects/project_h3/upload", "second-version", { "x-qf-explicit-action": "project.upload", "idempotency-key": "upload_second" }), env);
  assert.equal(reactivated.status, 201);
  const second = await reactivated.json();
  const staleRetry = await worker.fetch(requestFor(cookies, "DELETE", "/api/projects/project_h3", undefined, { "x-qf-explicit-action": "project.delete", "idempotency-key": "delete_old" }), env);
  assert.equal(staleRetry.status, 400);
  assert.doesNotMatch(await staleRetry.text(), /second-version/);
  assert.equal(bucket.values.has(second.object_key), true);
});

import assert from "node:assert/strict";
import test from "node:test";

import {
  EncryptedProjectStore,
  PROJECT_BUNDLE_TRANSPORT_LIMIT,
  ProjectStoreError,
  assertProjectBundleTransportSize,
} from "../dist/project-store.js";
import { canonicalJsonBytes } from "../dist/core-provenance.js";
import { sha256Hex } from "../dist/crypto.js";
import { MemoryBucket, keyBase64 } from "./helpers.mjs";

function verification(projectId, bundle, database = "a") {
  return {
    schema: "quillframe_native_backup_verification_v1",
    bundle_schema: "quillframe_backup_bundle_v1",
    body_fingerprint: `sha256:${bundle.fingerprint}`,
    bundle_fingerprint: `sha256:${bundle.fingerprint}`,
    project_id: projectId,
    chapter_scope: "CH001",
    database_fingerprint: `sha256:${database.repeat(64)}`,
    database_bytes: 1,
    blob_count: 0,
    byte_size: bundle.bytes.byteLength,
    verified: true,
    authority: false,
  };
}

async function bundle(value) {
  const bytes = new TextEncoder().encode(value);
  return { bytes, fingerprint: await sha256Hex(bytes) };
}

function pointer(receipt) {
  return {
    schema: "quillframe_cloud_project_pointer_v1",
    workspace_id: receipt.workspace_id,
    project_id: receipt.project_id,
    pointer_version: 1,
    state: "active",
    version_id: receipt.version_id,
    object_key: receipt.object_key,
    plaintext_fingerprint: receipt.plaintext_fingerprint,
    updated_at: 1,
    authority: false,
  };
}

test("project bundle transport validator accepts exact 128 MiB and rejects +1 without encryption", () => {
  assert.doesNotThrow(() => assertProjectBundleTransportSize(PROJECT_BUNDLE_TRANSPORT_LIMIT));
  assert.throws(() => assertProjectBundleTransportSize(PROJECT_BUNDLE_TRANSPORT_LIMIT + 1), (error) => error.code === "project_bundle_transport_limit");
  assert.throws(() => assertProjectBundleTransportSize(0), (error) => error.code === "project_bundle_transport_limit");
});

test("project store key ring rejects every incomplete, duplicate, malformed, and wrong-length configuration", () => {
  const bucket = new MemoryBucket();
  assert.throws(() => new EncryptedProjectStore(bucket, undefined), (error) => error.code === "project_key_config_invalid");
  const cases = [
    { current_key_id: "bad/id" },
    { current_key_id: "current", previous_key_id: "previous" },
    { current_key_id: "current", previous_key_base64: keyBase64(2) },
    { current_key_id: "current", previous_key_id: "current", previous_key_base64: keyBase64(2) },
    { current_key_id: "current", previous_key_id: "previous", previous_key_base64: "not-base64" },
    { current_key_id: "current", previous_key_id: "previous", previous_key_base64: Buffer.alloc(31).toString("base64") },
  ];
  for (const ring of cases) assert.throws(() => new EncryptedProjectStore(bucket, keyBase64(1), ring), (error) => error.code === "project_key_config_invalid");
  assert.throws(() => new EncryptedProjectStore(bucket, "not-base64"), (error) => error.code === "project_key_config_invalid");
  assert.throws(() => new EncryptedProjectStore(bucket, Buffer.alloc(31).toString("base64")), (error) => error.code === "project_key_config_invalid");
});

test("project store uses immutable plaintext project keys, exact conditional semantics, and typed delete failure", async () => {
  const value = await bundle("native bundle bytes");
  const bucket = new MemoryBucket();
  const store = new EncryptedProjectStore(bucket, keyBase64(9));
  const receipt = await store.uploadVerified({ workspace_id: "workspace_p", project_id: "project_p", bundle: value.bytes, verification: verification("project_p", value) });
  assert.match(receipt.object_key, /^v2\/[0-9a-f]{64}\/project_p\/versions\/sha256:[0-9a-f]{64}\.qfbundle$/);
  assert.deepEqual(await store.readVerified("workspace_p", "project_p", pointer(receipt)), value.bytes);
  assert.deepEqual(await store.uploadVerified({ workspace_id: "workspace_p", project_id: "project_p", bundle: value.bytes.slice(), verification: verification("project_p", value) }), receipt);
  assert.equal(bucket.values.size, 1);

  const unsupported = new MemoryBucket();
  unsupported.supportsConditional = false;
  await assert.rejects(() => new EncryptedProjectStore(unsupported, keyBase64(10)).uploadVerified({ workspace_id: "workspace_q", project_id: "project_q", bundle: value.bytes, verification: verification("project_q", value) }), (error) => error.code === "project_conditional_put_unsupported");
  const throwing = new MemoryBucket();
  throwing.put = async () => { throw new Error("conditional sentinel"); };
  await assert.rejects(() => new EncryptedProjectStore(throwing, keyBase64(11)).uploadVerified({ workspace_id: "workspace_q", project_id: "project_q", bundle: value.bytes, verification: verification("project_q", value) }), (error) => error.code === "project_store_write_failed");

  bucket.delete = async () => { throw new Error("delete sentinel"); };
  await assert.rejects(() => store.deleteVerified("workspace_p", "project_p", { ...pointer(receipt), state: "deleted" }), (error) => error instanceof ProjectStoreError && error.code === "project_gc_pending");
});

test("project store rejects malformed truthy, key-mismatched, and size-mismatched conditional put results", async () => {
  const value = await bundle("malformed conditional result");
  const outcomes = [
    () => ({ unexpected: "truthy" }),
    (_key, bytes) => ({ key: "wrong-key", size: bytes.byteLength }),
    (key, bytes) => ({ key, size: bytes.byteLength + 1 }),
  ];
  for (const outcome of outcomes) {
    const bucket = {
      async put(key, bytes) { return outcome(key, bytes); },
      async get() { throw new Error("unreadable object must not be treated as success"); },
      async delete() {},
    };
    const store = new EncryptedProjectStore(bucket, keyBase64(13));
    await assert.rejects(
      () => store.uploadVerified({ workspace_id: "workspace_malformed", project_id: "project_malformed", bundle: value.bytes, verification: verification("project_malformed", value) }),
      (error) => error instanceof ProjectStoreError && error.code === "project_conditional_put_invalid",
    );
  }
});

test("project store rejects conditional null existing mismatch and pointer/envelope hostile identities", async () => {
  const value = await bundle("hostile envelope bundle");
  const bucket = new MemoryBucket();
  const store = new EncryptedProjectStore(bucket, keyBase64(12));
  const projectId = "project_hostile";
  const workspaceId = "workspace_hostile";
  const receipt = await store.uploadVerified({ workspace_id: workspaceId, project_id: projectId, bundle: value.bytes, verification: verification(projectId, value, "d") });
  const projectPointer = pointer(receipt);
  const original = bucket.values.get(receipt.object_key).bytes.slice();
  const envelope = JSON.parse(new TextDecoder().decode(original));
  const hostile = [
    { ...envelope, unexpected: true },
    { ...envelope, cipher: "AES-128-GCM" },
    { ...envelope, key_version: "unknown" },
    { ...envelope, iv: envelope.iv.slice(0, -1) + (envelope.iv.endsWith("A") ? "B" : "A") },
    { ...envelope, plaintext_byte_size: 2 },
    { ...envelope, workspace_id: "workspace_other" },
    { ...envelope, project_id: "project_other" },
    { ...envelope, version_id: `sha256:${"e".repeat(64)}` },
    { ...envelope, object_key: envelope.object_key + "-tampered" },
    { ...envelope, plaintext_fingerprint: `sha256:${"e".repeat(64)}` },
    { ...envelope, ciphertext: `${envelope.ciphertext.slice(0, -1)}${envelope.ciphertext.endsWith("A") ? "B" : "A"}` },
    { ...envelope, ciphertext_fingerprint: `sha256:${"e".repeat(64)}` },
  ];
  for (const candidate of hostile) {
    bucket.values.get(receipt.object_key).bytes = canonicalJsonBytes(candidate);
    await assert.rejects(() => store.readVerified(workspaceId, projectId, projectPointer), (error) => ["project_envelope_invalid", "project_envelope_integrity_failed", "project_bundle_integrity_failed"].includes(error.code));
  }
  bucket.values.get(receipt.object_key).bytes = new TextEncoder().encode(`{"authority":false,"authority":false}`);
  await assert.rejects(() => store.readVerified(workspaceId, projectId, projectPointer), (error) => error.code === "project_envelope_invalid");
  bucket.values.get(receipt.object_key).bytes = original;
  await assert.rejects(() => store.readVerified(workspaceId, projectId, { ...projectPointer, plaintext_fingerprint: `sha256:${"e".repeat(64)}` }), (error) => error.code === "project_bundle_integrity_failed");
  await assert.rejects(() => store.readVerified(workspaceId, projectId, { ...projectPointer, object_key: `${projectPointer.object_key}-other` }), (error) => error.code === "project_pointer_invalid");

  const mismatchBucket = new MemoryBucket();
  const mismatchStore = new EncryptedProjectStore(mismatchBucket, keyBase64(13));
  const fingerprint = `sha256:${value.fingerprint}`;
  const expectedKey = `v2/${await sha256Hex(workspaceId)}/${projectId}/versions/${fingerprint}.qfbundle`;
  mismatchBucket.values.set(expectedKey, { bytes: new TextEncoder().encode("not-an-envelope"), options: {} });
  await assert.rejects(() => mismatchStore.uploadVerified({ workspace_id: workspaceId, project_id: projectId, bundle: value.bytes, verification: verification(projectId, value, "d") }), (error) => error.code === "project_envelope_invalid");
});

test("project store fails closed on unknown, oversized, and previous-key envelopes", async () => {
  const value = await bundle("size envelope bundle");
  const bucket = new MemoryBucket();
  const oldKey = keyBase64(21);
  const oldStore = new EncryptedProjectStore(bucket, oldKey, { current_key_id: "old" });
  const receipt = await oldStore.uploadVerified({ workspace_id: "workspace_rotation", project_id: "project_rotation", bundle: value.bytes, verification: verification("project_rotation", value, "c") });
  const projectPointer = pointer(receipt);
  const rotated = new EncryptedProjectStore(bucket, keyBase64(22), { current_key_id: "new", previous_key_id: "old", previous_key_base64: oldKey });
  assert.deepEqual(await rotated.readVerified("workspace_rotation", "project_rotation", projectPointer), value.bytes);
  const unknown = new EncryptedProjectStore(bucket, keyBase64(22));
  await assert.rejects(() => unknown.readVerified("workspace_rotation", "project_rotation", projectPointer), (error) => ["project_key_version_unknown", "project_envelope_invalid"].includes(error.code));

  const unknownSize = { get: async () => ({ arrayBuffer: async () => new ArrayBuffer(1) }), put: async () => ({}) , delete: async () => {} };
  await assert.rejects(() => new EncryptedProjectStore(unknownSize, keyBase64(23)).readVerified("workspace_rotation", "project_rotation", projectPointer), (error) => error.code === "project_envelope_size_unknown");
  const oversized = { get: async () => ({ size: 192 * 1024 * 1024 + 1, arrayBuffer: async () => new ArrayBuffer(1) }), put: async () => ({}) , delete: async () => {} };
  await assert.rejects(() => new EncryptedProjectStore(oversized, keyBase64(23)).readVerified("workspace_rotation", "project_rotation", projectPointer), (error) => error.code === "project_envelope_limit");
});

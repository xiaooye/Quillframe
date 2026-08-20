import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_CORE_BODY,
  MAX_NATIVE_BACKUP_BODY,
  coreForwardUrl,
  readCoreBody,
  safeCoreForwardHeaders,
  validateCoreContainerRequest,
} from "../dist/core-container.js";
import { buildCoreProof, canonicalJsonBytes } from "../dist/core-provenance.js";
import { sha256Hex } from "../dist/crypto.js";

function requestWith(body, headers = {}) {
  return new Request("https://core.internal/bridge?b=2&a=1", {
    method: "POST",
    headers: { "content-length": String(body.byteLength), ...headers },
    body,
  });
}

test("readCoreBody requires exact bounded framing and strict transfer headers", async () => {
  const body = new TextEncoder().encode("{}{}\n");
  assert.deepEqual(await readCoreBody(requestWith(body)), body);
  await assert.rejects(() => readCoreBody(new Request("https://core.internal/bridge", { method: "POST", body: "{}" })), (error) => error.code === "core_body_length_invalid");
  await assert.rejects(() => readCoreBody(requestWith(body, { "content-length": "0" })), (error) => error.code === "core_body_length_invalid");
  await assert.rejects(() => readCoreBody(requestWith(body, { "content-length": "4" })), (error) => error.code === "core_body_overrun");
  await assert.rejects(() => readCoreBody(requestWith(body, { "transfer-encoding": "chunked" })), (error) => error.code === "core_transfer_encoding_forbidden");
  await assert.rejects(() => readCoreBody(new Request("https://core.internal/bridge", { method: "POST", headers: { "content-length": String(body.byteLength) }, body: body.slice(0, 2) })), (error) => error.code === "core_body_short");
  const oversized = new Uint8Array(MAX_CORE_BODY + 1);
  await assert.rejects(() => readCoreBody(requestWith(oversized)), (error) => error.code === "core_body_size_invalid");
});

test("native backup framing uses the 128 MiB transport cap while Bridge remains 4 MiB", async () => {
  const nativeBody = new Uint8Array(MAX_CORE_BODY + 1);
  const nativeRequest = new Request("https://core.internal/native/project-backup/verify?operation=project.upload&project_id=P1", {
    method: "POST",
    headers: { "content-type": "application/zip", "content-length": String(nativeBody.byteLength) },
    body: nativeBody,
  });
  assert.equal((await readCoreBody(nativeRequest, MAX_NATIVE_BACKUP_BODY)).byteLength, MAX_CORE_BODY + 1);
  const exactBody = new Uint8Array(MAX_NATIVE_BACKUP_BODY);
  const exactRequest = new Request("https://core.internal/native/project-backup/verify?operation=project.upload&project_id=P1", {
    method: "POST",
    headers: { "content-type": "application/zip", "content-length": String(exactBody.byteLength) },
    body: exactBody,
  });
  assert.equal((await readCoreBody(exactRequest, MAX_NATIVE_BACKUP_BODY)).byteLength, MAX_NATIVE_BACKUP_BODY);
  const overLimit = new Request("https://core.internal/native/project-backup/verify?operation=project.upload&project_id=P1", {
    method: "POST",
    headers: { "content-type": "application/zip", "content-length": String(MAX_NATIVE_BACKUP_BODY + 1) },
    body: new Uint8Array([1]),
  });
  await assert.rejects(() => readCoreBody(overLimit, MAX_NATIVE_BACKUP_BODY), (error) => error.code === "core_body_size_invalid");
});

test("Container forward headers are an explicit proof/content allowlist", () => {
  const request = new Request("https://core.internal/bridge", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
      "idempotency-key": "request-1",
      "x-qf-core-proof": "proof",
      authorization: "sentinel",
      "x-qf-workspace-id": "sentinel",
    },
  });
  const headers = safeCoreForwardHeaders(request, "proof");
  assert.deepEqual([...headers.keys()].sort(), ["accept", "content-type", "idempotency-key", "x-qf-core-proof"]);
  assert.equal(headers.get("x-qf-core-proof"), "proof");
  assert.equal(headers.get("authorization"), null);
  assert.equal(headers.get("x-qf-workspace-id"), null);
});

test("Container boundary binds proof workspace, query, operation, project, and rejects aliases", async () => {
  const key = new Uint8Array(32).fill(7);
  const now = 1_800_000_000_000;
  const bodyValue = {
    args: { project_id: "project_a" }, authority: false, bridge_version: "11", operation: "project.open",
    request_id: "request_a", schema: "quillframe_host_bridge_request_v11", surface: "hosted_web",
  };
  const body = canonicalJsonBytes(bodyValue);
  const proof = await buildCoreProof({ key_id: "current", key, method: "POST", path: "/bridge?b=2&a=1", body, workspace_id: "workspace_a", session_id: "session_a", project_id: "project_a", chapter_scope: "CH001", issued_at: now, expires_at: now + 30_000, nonce: "nonce_a" });
  const request = () => new Request("https://core.internal/bridge?b=2&a=1", { method: "POST", headers: { "content-length": String(body.byteLength), "x-qf-core-proof": proof.header }, body });
  const keys = new Map([["current", key]]);
  assert.equal((await validateCoreContainerRequest(request(), keys, "workspace_a", now)).body.byteLength, body.byteLength);
  await assert.rejects(() => validateCoreContainerRequest(request(), keys, "workspace_b", now), (error) => error.code === "container_boundary_invalid" && !String(error.message).includes("workspace_a"));
  await assert.rejects(() => validateCoreContainerRequest(new Request("https://core.internal/bridge?a=1&b=2", { method: "POST", headers: { "content-length": String(body.byteLength), "x-qf-core-proof": proof.header }, body }), keys, "workspace_a", now), (error) => error.code === "container_boundary_invalid");
  const projectChanged = canonicalJsonBytes({ ...bodyValue, args: { project_id: "project_b" } });
  await assert.rejects(() => validateCoreContainerRequest(new Request("https://core.internal/bridge?b=2&a=1", { method: "POST", headers: { "content-length": String(projectChanged.byteLength), "x-qf-core-proof": proof.header }, body: projectChanged }), keys, "workspace_a", now), (error) => error.code === "container_boundary_invalid");
  await assert.rejects(() => validateCoreContainerRequest(new Request("https://core.internal/bridge?b=2&a=1", { method: "POST", headers: { "content-length": String(body.byteLength), "x-qf-core-proof": proof.header, "x-qf-workspace-id": "sentinel" }, body }), keys, "workspace_a", now), (error) => error.code === "container_boundary_forbidden" && !String(error.message).includes("sentinel"));
});

test("Container native query is hard-cut upload/read and read body binds version", async () => {
  const key = new Uint8Array(32).fill(9);
  const now = 1_800_000_000_000;
  const body = new TextEncoder().encode("native-read-body");
  const versionId = `sha256:${await sha256Hex(body)}`;
  const path = `/native/project-backup/verify?operation=project.read&project_id=project_a&version_id=${versionId}&object_key_sha256=sha256:${"b".repeat(64)}&pointer_version=4`;
  const proof = await buildCoreProof({ key_id: "current", key, method: "POST", path, body, workspace_id: "workspace_a", session_id: "session_a", project_id: "project_a", chapter_scope: "CH001", issued_at: now, expires_at: now + 30_000, nonce: "native_read_nonce" });
  const request = new Request(`https://core.internal${path}`, { method: "POST", headers: { "content-type": "application/zip", "content-length": String(body.byteLength), "x-qf-core-proof": proof.header }, body });
  assert.equal((await validateCoreContainerRequest(request, new Map([["current", key]]), "workspace_a", now)).body.byteLength, body.byteLength);
  const legacy = new Request("https://core.internal/native/project-backup/verify?project_id=project_a", { method: "POST", headers: { "content-type": "application/zip", "content-length": String(body.byteLength), "x-qf-core-proof": proof.header }, body });
  await assert.rejects(() => validateCoreContainerRequest(legacy, new Map([["current", key]]), "workspace_a", now), (error) => error.code === "container_boundary_invalid");
  const changed = new Request(`https://core.internal${path.replace(versionId, `sha256:${"c".repeat(64)}`)}`, { method: "POST", headers: { "content-type": "application/zip", "content-length": String(body.byteLength), "x-qf-core-proof": proof.header }, body });
  await assert.rejects(() => validateCoreContainerRequest(changed, new Map([["current", key]]), "workspace_a", now), (error) => error.code === "container_boundary_invalid");
});

test("Container forwarding preserves raw query and maps only the core path", () => {
  assert.equal(coreForwardUrl("https://studio.example/api/core/bridge?b=2&a=1"), "http://core.internal/bridge?b=2&a=1");
});

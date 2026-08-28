import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

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

test("Cloud deployment resolves its Core image and owns hosted Studio assets with pinned Wrangler", () => {
  const cloudRoot = fileURLToPath(new URL("../", import.meta.url));
  const repositoryRoot = path.resolve(cloudRoot, "..");
  const config = JSON.parse(fs.readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8"));
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe cloud config "));
  try {
    const isolatedConfig = {
      ...config,
      main: path.resolve(cloudRoot, config.main),
      ...(config.assets ? { assets: { ...config.assets, directory: path.resolve(cloudRoot, config.assets.directory) } } : {}),
      containers: config.containers.map((container) => ({
        ...container,
        image: path.resolve(cloudRoot, container.image),
        ...(container.image_build_context ? { image_build_context: path.resolve(cloudRoot, container.image_build_context) } : {}),
      })),
    };
    const configPath = path.join(tempRoot, "wrangler.jsonc");
    const outputPath = path.join(tempRoot, "cloud-env.d.ts");
    const envPath = path.join(tempRoot, ".env");
    fs.writeFileSync(configPath, JSON.stringify(isolatedConfig));
    fs.writeFileSync(envPath, "");
    fs.writeFileSync(path.join(tempRoot, ".dev.vars"), "");
    const env = {
      CI: "1",
      WRANGLER_SEND_METRICS: "false",
      WRANGLER_HIDE_BANNER: "true",
      WRANGLER_LOG_PATH: path.join(tempRoot, "logs"),
      CLOUDFLARE_LOAD_DEV_VARS_FROM_DOT_ENV: "false",
    };
    for (const key of ["PATH", "Path", "SystemRoot", "WINDIR", "TEMP", "TMP"]) {
      if (process.env[key] !== undefined) env[key] = process.env[key];
    }
    const run = spawnSync(process.execPath, [
      path.join(cloudRoot, "node_modules", "wrangler", "bin", "wrangler.js"),
      "types", outputPath, "--config", configPath, "--env-file", envPath,
      "--include-runtime=false", "--strict-vars=false",
    ], { cwd: tempRoot, env, encoding: "utf8", timeout: 30_000 });
    assert.equal(run.status, 0, run.error?.message ?? `${run.stdout}\n${run.stderr}`);
    const bindings = fs.readFileSync(outputPath, "utf8");
    assert.match(bindings, /CORE_CONTAINER/);
    assert.match(bindings, /ASSETS/);
    for (const container of isolatedConfig.containers) {
      assert.equal(container.image, path.join(repositoryRoot, "Dockerfile"));
      assert.equal(container.image_build_context ?? path.dirname(container.image), repositoryRoot);
    }
    const studioRoot = path.join(repositoryRoot, "studio", "app");
    const preview = JSON.parse(fs.readFileSync(path.join(studioRoot, "wrangler.jsonc"), "utf8"));
    assert.equal(isolatedConfig.assets.directory, path.resolve(studioRoot, preview.assets.directory));
    assert.equal(config.assets.binding, "ASSETS");
    assert.equal(config.assets.run_worker_first, true, "HTML and API requests must pass through the BFF");
    assert.equal(config.assets.html_handling, "none", "the BFF owns trusted index selection");
    assert.equal(config.assets.not_found_handling, "none", "the asset binding must not mask missing API or script paths");
    const publicOrigin = new URL(config.vars.PUBLIC_ORIGIN);
    assert.equal(publicOrigin.origin, config.vars.PUBLIC_ORIGIN);
    assert.equal(publicOrigin.protocol, "https:");
    assert.deepEqual(config.routes, [{ pattern: publicOrigin.hostname, custom_domain: true }]);
    assert.deepEqual(preview.routes ?? [], [], "the static preview must not claim the hosted domain");
    assert.equal(preview.workers_dev, true);
    assert.equal(preview.preview_urls, true);
  } finally {
    assert.equal(path.dirname(tempRoot), path.resolve(os.tmpdir()));
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});

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
  const proof = await buildCoreProof({ key_id: "current", key, method: "POST", path: "/bridge?b=2&a=1", body, workspace_id: "workspace_a", session_id: "session_a", project_id: "project_a", scope: "novel", issued_at: now, expires_at: now + 30_000, nonce: "nonce_a" });
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
  const proof = await buildCoreProof({ key_id: "current", key, method: "POST", path, body, workspace_id: "workspace_a", session_id: "session_a", project_id: "project_a", scope: "novel", issued_at: now, expires_at: now + 30_000, nonce: "native_read_nonce" });
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

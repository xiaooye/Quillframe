import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

async function loadBridge() {
  const source = fs.readFileSync(new URL("../src/bridge.ts", import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

const bridge = await loadBridge();
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonical(child)]));
  return value;
}

function digest(value) {
  return `sha256:${crypto.createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex")}`;
}

function redactRequest(request) {
  const secretKeys = new Set(["access_token", "api_key", "apikey", "password", "secret", "token"]);
  const wire = JSON.parse(JSON.stringify(request));
  const secrets = [];
  const collect = (value) => {
    if (Array.isArray(value)) return value.forEach(collect);
    if (!value || typeof value !== "object") return;
    for (const [key, child] of Object.entries(value)) {
      if (secretKeys.has(key.toLowerCase().replaceAll("-", "_"))) { if (typeof child === "string" && child) secrets.push(child); }
      else collect(child);
    }
  };
  collect(wire);
  const scrub = (value) => {
    if (Array.isArray(value)) return value.map(scrub);
    if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, secretKeys.has(key.toLowerCase().replaceAll("-", "_")) ? "<redacted>" : scrub(child)]));
    if (typeof value === "string") return [...secrets].sort((a, b) => b.length - a.length).reduce((current, secret) => current.replaceAll(secret, "<redacted>"), value);
    return value;
  };
  return scrub(wire);
}

async function resultFor(request, overrides = {}) {
  const requestedResultFingerprint = overrides.result_fingerprint;
  const candidate = {
    schema: "quillframe_host_bridge_result_v11",
    bridge_version: "11",
    request_id: request.request_id,
    operation: request.operation,
    surface: request.surface,
    status: "ok",
    request_fingerprint: digest(redactRequest(request)),
    data: { project_id: "novel" },
    error: null,
    secret_values_persisted: false,
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    ...overrides,
  };
  delete candidate.result_fingerprint;
  candidate.result_fingerprint = digest(candidate);
  if (requestedResultFingerprint !== undefined) candidate.result_fingerprint = requestedResultFingerprint;
  return candidate;
}

test("normalizes one exact Host Bridge v11 operation set", () => {
  const normalized = bridge.normalizeBridgeDescription({
    schema: "quillframe_host_bridge_description_v11",
    framework_version: "1.0.0-dev.0",
    contract_version: "11",
    surface: "local_app",
    operations: ["author.run.start", "project.inspect"],
    operation_contracts: {
      "project.inspect": { kind: "query", required_args: ["project_id"] },
      "author.run.start": { kind: "command", required_args: ["project_id", "task_mode", "payload"] },
    },
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  });
  assert.deepEqual(normalized.operations, ["author.run.start", "project.inspect"]);
  assert.deepEqual(Object.keys(normalized.operationContracts).sort(), ["author.run.start", "project.inspect"]);
  assert.equal(normalized.frameworkVersion, "1.0.0-dev.0");
  assert.equal(normalized.authority, false);
});

test("bridge description rejects operation drift and direct Core store authority", () => {
  const base = {
    schema: "quillframe_host_bridge_description_v11",
    framework_version: "1.0.0-dev.0",
    contract_version: "11",
    surface: "local_app",
    operations: ["project.inspect"],
    operation_contracts: { "project.inspect": { kind: "query", required_args: ["project_id"] } },
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  };
  assert.throws(() => bridge.normalizeBridgeDescription({ ...base, operations: ["project.inspect", "retired.flat.list"] }), /operation set/);
  assert.throws(() => bridge.normalizeBridgeDescription({ ...base, direct_core_store_access: true }), /authority invariant/);
});

test("BridgeClient forwards one authority=false request envelope through its transport", async () => {
  let observed;
  const transport = {
    name: "hosted-http",
    requestSurface: "hosted_web",
    available: () => true,
    invoke: async (request) => {
      observed = request;
      return resultFor(request);
    },
  };
  const client = new bridge.BridgeClient(transport);
  const result = await client.invoke("project.inspect", { project_id: "novel" });
  assert.equal(result.status, "ok");
  assert.equal(observed.schema, "quillframe_host_bridge_request_v11");
  assert.equal(observed.bridge_version, "11");
  assert.equal(observed.operation, "project.inspect");
  assert.equal(observed.surface, "hosted_web");
  assert.equal(observed.authority, false);
  assert.deepEqual(observed.args, { project_id: "novel" });
});

test("bridge description with elevated authority fails closed", () => {
  assert.throws(() => bridge.normalizeBridgeDescription({
    schema: "quillframe_host_bridge_description_v11",
    operations: [],
    authority: true,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  }), /authority invariant/);
});

test("bridge description rejects every non-v11 contract", () => {
  assert.throws(() => bridge.normalizeBridgeDescription({
    schema: "quillframe_host_bridge_description_v11",
    contract_version: "10",
    operations: [],
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  }), /exactly 11/);
});

test("bridge description rejects the retired description schema", () => {
  assert.throws(() => bridge.normalizeBridgeDescription({
    schema: "quillframe_host_bridge_description_v1",
    contract_version: "11",
    operations: [],
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  }), /description schema/);
});

test("bridge description requires complete operation contract metadata", () => {
  const base = {
    schema: "quillframe_host_bridge_description_v11",
    contract_version: "11",
    operations: ["project.inspect"],
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  };
  assert.throws(() => bridge.normalizeBridgeDescription(base), /operation_contracts/);
  assert.throws(() => bridge.normalizeBridgeDescription({
    ...base,
    operation_contracts: { "project.inspect": { kind: "query", required_args: [1] } },
  }), /required_args/);
  assert.throws(() => bridge.normalizeBridgeDescription({
    ...base,
    operation_contracts: { "project.inspect": { kind: "query", required_args: [], allowed_surfaces: "local_app" } },
  }), /allowed_surfaces/);
});

test("subscribeAuthorRun uses the cursor event operation", async () => {
  let observed;
  const transport = {
    name: "local-http",
    requestSurface: "local_app",
    available: () => true,
    invoke: async (request) => {
      observed = request;
      return resultFor(request, { data: { events: [], next_cursor: 7 } });
    },
  };
  const client = new bridge.BridgeClient(transport);
  await client.subscribeAuthorRun("RUN-1", 7);
  assert.equal(observed.operation, "author.run.events");
  assert.deepEqual(observed.args, { run_id: "RUN-1", cursor: 7 });
});

test("Host Bridge result envelope is exact, fingerprint-bound, and request-bound", async () => {
  const request = {
    schema: "quillframe_host_bridge_request_v11",
    bridge_version: "11",
    request_id: "REQ-BOUND",
    operation: "project.inspect",
    surface: "local_app",
    args: { project_id: "novel" },
    authority: false,
  };
  const valid = await resultFor(request);
  await assert.doesNotReject(() => bridge.assertEnvelope(valid, request.surface, request));
  for (const mutation of [
    { secret_values_persisted: undefined },
    { request_id: "OTHER" },
    { operation: "project.open" },
    { request_fingerprint: `sha256:${"a".repeat(64)}` },
    { result_fingerprint: "sha256:result" },
    { authority: true },
    { status: "ok", error: { code: "hidden" } },
    { status: "failed", data: { leaked: true }, error: { code: "failed" } },
    { status: "failed", data: null, error: { code: "failed", mutation_performed: false, message: "HTTP_SECRET /var/private/sentinel" } },
    { status: "failed", data: null, error: "HTTP_SECRET /var/private/sentinel" },
    { extra: "forbidden" },
  ]) {
    const candidate = await resultFor(request, mutation);
    if (mutation.secret_values_persisted === undefined) delete candidate.secret_values_persisted;
    await assert.rejects(() => bridge.assertEnvelope(candidate, request.surface, request));
  }
  const tampered = { ...valid, data: { project_id: "tampered" } };
  await assert.rejects(() => bridge.assertEnvelope(tampered, request.surface, request), /result fingerprint/);

  const failed = await resultFor(request, { status: "failed", data: null, error: { code: "bridge_internal_error", mutation_performed: false } });
  await assert.doesNotReject(() => bridge.assertEnvelope(failed, request.surface, request));
  assert.equal(bridge.operationError(failed), "bridge_internal_error");
});

test("Bridge fingerprint verification redacts credentials but binds every other request field", async () => {
  const request = {
    schema: "quillframe_host_bridge_request_v11",
    bridge_version: "11",
    request_id: "REQ-SECRET",
    operation: "model.service.add",
    surface: "local_app",
    args: { endpoint: "https://example.invalid/v1", access_token: "SECRET-A" },
    authority: false,
  };
  const result = await resultFor(request);
  await assert.doesNotReject(() => bridge.assertEnvelope(result, request.surface, request));
  await assert.doesNotReject(() => bridge.assertEnvelope(result, request.surface, { ...request, args: { ...request.args, access_token: "SECRET-B" } }));
  await assert.rejects(() => bridge.assertEnvelope(result, request.surface, { ...request, args: { ...request.args, endpoint: "https://other.invalid/v1" } }), /request fingerprint/);
});

test("frontend verification accepts the SQLite-independent Python Bridge envelope contract", async () => {
  const request = {
    schema: "quillframe_host_bridge_request_v11",
    bridge_version: "11",
    request_id: "REQ-CROSS-LANGUAGE",
    operation: "model.service.add",
    surface: "local_app",
    args: { endpoint: "https://例子.invalid/v1", access_token: "CROSS-LANGUAGE-SECRET" },
    authority: false,
  };
  const repoRoot = new URL("../../../", import.meta.url);
  const output = execFileSync("python", ["-c", `
import builtins
import json
import sys

real_import = builtins.__import__
def without_sqlite(name, *args, **kwargs):
    if name == "_sqlite3":
        raise ModuleNotFoundError("Cloudflare Python does not provide _sqlite3")
    return real_import(name, *args, **kwargs)
builtins.__import__ = without_sqlite

from studio.host_bridge_protocol import result
request = json.load(sys.stdin)
print(json.dumps(result(request, "ok", data={"project_id": "novel"}), ensure_ascii=False))
`], {
    cwd: repoRoot,
    input: JSON.stringify(request),
    encoding: "utf8",
  });
  const result = JSON.parse(output);
  await assert.doesNotReject(() => bridge.assertEnvelope(result, request.surface, request));
  assert.equal(JSON.stringify(result).includes("CROSS-LANGUAGE-SECRET"), false);
});

test("HTTP transport never exposes an untrusted response message", async () => {
  const request = {
    schema: "quillframe_host_bridge_request_v11",
    bridge_version: "11",
    request_id: "REQ-HTTP",
    operation: "project.inspect",
    surface: "local_app",
    args: { project_id: "novel" },
    authority: false,
  };
  const sentinel = "HTTP_SECRET /var/private/sentinel";
  await assert.rejects(
    () => bridge.parseHttpResult(new Response(JSON.stringify({ message: sentinel }), { status: 500 }), request.surface, request),
    (error) => error instanceof Error && error.message === "Host Bridge transport failed (HTTP 500)" && !error.message.includes(sentinel),
  );
});

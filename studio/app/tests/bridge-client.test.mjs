import assert from "node:assert/strict";
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
function compareKeys(left, right) {
  const a = Array.from(left, (char) => char.codePointAt(0));
  const b = Array.from(right, (char) => char.codePointAt(0));
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    if (a[index] !== b[index]) return a[index] - b[index];
  }
  return a.length - b.length;
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort(compareKeys).map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function digest(value) {
  return `sha256:${crypto.createHash("sha256").update(canonicalJson(JSON.parse(JSON.stringify(value)))).digest("hex")}`;
}

async function loadCloudCanonical() {
  const compile = (relative) => ts.transpileModule(fs.readFileSync(new URL(relative, import.meta.url), "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  const cryptoUrl = moduleUrl(compile("../../../cloud/src/crypto.ts"));
  return import(moduleUrl(compile("../../../cloud/src/core-provenance.ts").replace('"./crypto.js"', JSON.stringify(cryptoUrl))));
}

function activateSession() {
  const epoch = bridge.invalidateHostedSession();
  assert.equal(bridge.activateHostedSession(epoch), true);
  return epoch;
}

function browserFor(t, initial = {}) {
  const state = { endpoint: "https://studio.example", href: "https://studio.example/start", cookie: `__Host-qf_csrf=${"c".repeat(32)}`, localToken: "", ...initial };
  const originals = new Map(["document", "window", "fetch"].map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const calls = [];
  Object.defineProperty(globalThis, "document", { configurable: true, value: {
    get cookie() { return state.cookie; },
    querySelector(selector) { return { content: selector.includes("hosted-endpoint") ? state.endpoint : state.localToken }; },
  } });
  Object.defineProperty(globalThis, "window", { configurable: true, value: { get location() { return new URL(state.href); } } });
  Object.defineProperty(globalThis, "fetch", { configurable: true, value: async (url, init) => {
    calls.push({ url, ...init });
    return new Response(JSON.stringify(await resultFor(JSON.parse(init.body))), { headers: { "Content-Type": "application/json" } });
  } });
  bridge.__resetBridgeClientForTests();
  if (initial.verified !== false) activateSession();
  t.after(() => {
    for (const [key, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
    bridge.__resetBridgeClientForTests();
  });
  return { state, calls };
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

test("frontend verification accepts the canonical Rust Bridge envelope contract", async () => {
  const request = {
    schema: "quillframe_host_bridge_request_v11",
    bridge_version: "11",
    request_id: "REQ-CROSS-LANGUAGE",
    operation: "model.service.add",
    surface: "local_app",
    args: {
      endpoint: "https://例子.invalid/v1", access_token: "CROSS-LANGUAGE-SECRET",
      metadata: { a: "lowercase", Z: "uppercase", _: "underscore", "2": "two", "10": "ten", "\ue000": "BMP", "😀": "astral" },
      ratio: 1.25,
    },
    authority: false,
  };
  const result = await resultFor(request, { data: { project_id: "novel", runtime: "rust_core" } });
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

test("hosted transport sends canonical bytes and CSRF to the same-origin Core route", async (t) => {
  const { calls } = browserFor(t);
  const cloud = await loadCloudCanonical();
  const client = new bridge.BridgeClient(new bridge.HostedHttpTransport());
  const args = { project_id: "novel", note: "中文 😀", ordering: { a: 1, Z: 2, _: 3, "2": 4, "10": 5 }, optional: undefined };
  const result = await client.invoke("project.inspect", args);
  assert.equal(result.status, "ok");
  assert.equal(calls.length, 1);
  const request = calls[0];
  assert.equal(request.url, "https://studio.example/api/core/bridge");
  assert.equal(request.method, "POST");
  assert.equal(request.credentials, "same-origin");
  assert.equal(request.redirect, "error");
  assert.equal(request.cache, "no-store");
  assert.equal(new Headers(request.headers).get("x-qf-csrf"), "c".repeat(32));
  const parsed = cloud.canonicalBridgeBody(request.body);
  assert.equal(request.body, cloud.canonicalJson(parsed.value));
  assert.equal(cloud.validateBridgeRequest(parsed.value).operation, "project.inspect");
  assert.equal(parsed.value.surface, "hosted_web");
  assert.equal(Object.hasOwn(parsed.value.args, "optional"), false);
  assert.deepEqual(parsed.value.args.ordering, args.ordering);
  assert.ok(request.body.indexOf('"10":5') < request.body.indexOf('"2":4'));
});

test("only a hosted HTTP 401 invalidates the mounted hosted session", async (t) => {
  const { state } = browserFor(t);
  let expired = 0;
  const unsubscribe = bridge.subscribeToHostedSessionExpiry(() => { expired += 1; });
  t.after(unsubscribe);
  globalThis.fetch = async () => Response.json({ message: "UNTRUSTED_SECRET" }, { status: 401 });
  await assert.rejects(() => new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("bridge.describe"), /HTTP 401/);
  assert.equal(expired, 1);
  await assert.rejects(() => new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("bridge.describe"), /Hosted Core session/);
  activateSession();
  globalThis.fetch = async () => Response.json({ code: "csrf_invalid" }, { status: 403 });
  await assert.rejects(() => new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("bridge.describe"), /HTTP 403/);
  assert.equal(expired, 1, "non-session failures must not silently sign the user out");
  state.localToken = "local-token";
  globalThis.fetch = async () => Response.json({ message: "UNTRUSTED_SECRET" }, { status: 401 });
  await assert.rejects(() => new bridge.BridgeClient(new bridge.LocalHttpTransport()).invoke("bridge.describe"), /HTTP 401/);
  assert.equal(expired, 1, "local authentication is separate from the hosted session");
  unsubscribe();
  activateSession();
  await assert.rejects(() => new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("bridge.describe"), /HTTP 401/);
  assert.equal(expired, 1);
});

test("configured hosted transport stays identifiable but refuses an unverified session", async (t) => {
  const { calls } = browserFor(t, { verified: false });
  const transport = new bridge.HostedHttpTransport();
  assert.equal(transport.available(), true);
  assert.equal(bridge.bridgeTransportName(), "hosted-http");
  await assert.rejects(() => new bridge.BridgeClient(transport).invoke("bridge.describe"), /Hosted Core session/);
  assert.equal(calls.length, 0);
});

test("an obsolete session check cannot reactivate Core after a newer check begins", async (t) => {
  const { calls } = browserFor(t, { verified: false });
  const oldEpoch = bridge.invalidateHostedSession();
  const currentEpoch = bridge.invalidateHostedSession();
  assert.equal(bridge.activateHostedSession(oldEpoch), false);
  const client = new bridge.BridgeClient(new bridge.HostedHttpTransport());
  await assert.rejects(() => client.invoke("bridge.describe"), /Hosted Core session/);
  assert.equal(calls.length, 0);
  assert.equal(bridge.activateHostedSession(currentEpoch), true);
  assert.equal((await client.invoke("bridge.describe")).status, "ok");
});

test("a late hosted 401 cannot expire a newer mounted session", async (t) => {
  const { state } = browserFor(t);
  const response = Promise.withResolvers();
  globalThis.fetch = () => response.promise;
  let previousExpired = 0;
  let currentExpired = 0;
  const unsubscribePrevious = bridge.subscribeToHostedSessionExpiry(() => { previousExpired += 1; });
  t.after(unsubscribePrevious);
  const pending = new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("bridge.describe");
  unsubscribePrevious();
  activateSession();
  state.cookie = `__Host-qf_csrf=${"d".repeat(32)}`;
  t.after(bridge.subscribeToHostedSessionExpiry(() => { currentExpired += 1; }));
  const rejected = assert.rejects(pending, /Hosted Core session/);
  response.resolve(Response.json({ code: "session_expired" }, { status: 401 }));
  await rejected;
  assert.equal(previousExpired, 0);
  assert.equal(currentExpired, 0, "an earlier request must not notify the current session");
  globalThis.fetch = async (_url, init) => Response.json(await resultFor(JSON.parse(init.body)));
  assert.equal((await new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("bridge.describe")).status, "ok", "a late failure must leave the current session active");
});

test("a late hosted success cannot return data or continue a command after session replacement", async (t) => {
  browserFor(t);
  const response = Promise.withResolvers();
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, ...init });
    if (calls.length === 1) return response.promise;
    return Response.json(await resultFor(JSON.parse(init.body)));
  };
  const client = new bridge.BridgeClient(new bridge.HostedHttpTransport());
  const pending = client.invoke("model.service.list").then(() => client.invoke("author.run.execute", { run_id: "run-old" }));
  activateSession();
  assert.equal(calls[0].signal.aborted, true);
  const rejected = assert.rejects(pending, /Hosted Core session/);
  response.resolve(Response.json(await resultFor(JSON.parse(calls[0].body))));
  await rejected;
  assert.equal(calls.length, 1, "a disposed caller must not continue using a stale successful result");
});

test("hosted session invalidation also rejects a result already awaiting JSON validation", async (t) => {
  browserFor(t);
  const parsing = Promise.withResolvers();
  const body = Promise.withResolvers();
  let request;
  globalThis.fetch = async (_url, init) => {
    request = JSON.parse(init.body);
    const response = new Response(null, { status: 200 });
    response.json = () => { parsing.resolve(); return body.promise; };
    return response;
  };
  const pending = new bridge.BridgeClient(new bridge.HostedHttpTransport()).invoke("project.inspect", { project_id: "novel" });
  await parsing.promise;
  activateSession();
  const rejected = assert.rejects(pending, /Hosted Core session/);
  body.resolve(await resultFor(request));
  await rejected;
});

test("hosted transport refuses absent, non-HTTPS, cross-origin, or non-origin endpoint configuration before fetch", async (t) => {
  const { state, calls } = browserFor(t);
  const transport = new bridge.HostedHttpTransport();
  for (const endpoint of ["", "/", "https://other.example", "http://studio.example", "https://studio.example:444", "https://user@studio.example", "https://studio.example/api", "https://studio.example/?query=1", "https://studio.example/#fragment", "not a URL"]) {
    state.endpoint = endpoint;
    assert.equal(transport.available(), false, endpoint);
    await assert.rejects(() => new bridge.BridgeClient(transport).invoke("bridge.describe"), /Hosted Core endpoint/);
  }
  state.endpoint = "";
  assert.equal(bridge.detectBridgeTransport(), null, "an HTTPS static site must not bind itself to Core");
  state.endpoint = "https://studio.example:443/";
  assert.equal(transport.available(), true);
  state.href = "http://127.0.0.1:8765/start";
  state.endpoint = "http://127.0.0.1:8765";
  assert.equal(transport.available(), false, "local HTTP uses LocalHttpTransport, not a hosted exception");
  assert.equal(calls.length, 0);
});

test("hosted transport rejects missing, malformed, or duplicate CSRF cookies without choosing one", async (t) => {
  const { state, calls } = browserFor(t);
  const client = new bridge.BridgeClient(new bridge.HostedHttpTransport());
  const valid = `__Host-qf_csrf=${"c".repeat(32)}`;
  for (const cookie of ["", "unrelated=value", "__Host-qf_csrf", "__Host-qf_csrf=short", `${valid}==`, `__Host-qf_csrf="${"c".repeat(32)}"`, `__Host-qf_csrf=%63${"c".repeat(31)}`, `${valid}; ${valid}`, `${valid}; __Host-qf_csrf=bad`, `${valid}; __Host-qf_csrf`]) {
    state.cookie = cookie;
    await assert.rejects(() => client.invoke("bridge.describe"), /Hosted Core CSRF/);
  }
  assert.equal(calls.length, 0);
  state.cookie = `unrelated=value; ${valid}`;
  assert.equal((await client.invoke("bridge.describe")).status, "ok");
  assert.equal(calls.length, 1);
  Object.defineProperty(document, "cookie", { get() { throw new Error("COOKIE_READ_SENTINEL"); } });
  await assert.rejects(() => client.invoke("bridge.describe"), (error) => error.message === "Hosted Core CSRF token is missing or invalid");
  assert.equal(calls.length, 1);
});

test("hosted body rejects unsupported values but omits optional undefined object properties", async (t) => {
  const { calls } = browserFor(t);
  const client = new bridge.BridgeClient(new bridge.HostedHttpTransport());
  const circular = {};
  circular.self = circular;
  let accessorReads = 0;
  const accessor = Object.defineProperty({}, "value", { enumerable: true, get() { accessorReads += 1; return 1; } });
  const symbolKey = { [Symbol("unsupported")]: 1 };
  const extraArrayField = Object.assign([], { extra: 1 });
  for (const value of [NaN, Infinity, -Infinity, 1.25, Number.MAX_SAFE_INTEGER + 1, 1n, () => {}, Symbol("unsupported"), new Date(), new Map(), new Uint8Array([1]), Object.create({ inherited: true }), { toJSON() { return "hidden"; } }, accessor, symbolKey, extraArrayField, [undefined], Array(1), "\ud800", "\udc00", { "中文": 1 }, circular]) {
    await assert.rejects(() => client.invoke("project.inspect", { project_id: "novel", value }), /Hosted Core request body/);
  }
  assert.equal(accessorReads, 0, "validation must not execute getters");
  assert.equal(calls.length, 0);
  await client.invoke("author.run.start", { project_id: "novel", target_ref: undefined, payload: { optional: undefined, chapter_id: "CH001" } });
  assert.deepEqual(JSON.parse(calls[0].body).args, { project_id: "novel", payload: { chapter_id: "CH001" } });
  const prototypeKey = JSON.parse('{"__proto__":{"name":"preserved"},"constructor":"data"}');
  await client.invoke("project.inspect", { project_id: "novel", metadata: prototypeKey });
  const cloud = await loadCloudCanonical();
  assert.equal(Object.hasOwn(cloud.canonicalBridgeBody(calls[1].body).value.args.metadata, "__proto__"), true);
});

test("hosted wire restrictions do not narrow Local or Tauri business JSON", async (t) => {
  const { calls } = browserFor(t, { endpoint: "", cookie: "", localToken: "local-transport-token", verified: false });
  const args = { project_id: "novel", ratio: 1.25, metadata: { "中文": "value", "2": 2, "10": 10 }, optional: undefined };
  const local = await new bridge.BridgeClient(new bridge.LocalHttpTransport()).invoke("project.inspect", args);
  assert.equal(local.status, "ok");
  assert.equal(calls[0].url, "/api/bridge/invoke");
  assert.equal(JSON.parse(calls[0].body).args.ratio, 1.25);
  window.__TAURI__ = { core: { invoke: async (command, value) => {
    assert.equal(command, "bridge_invoke");
    return resultFor(value.request);
  } } };
  assert.equal((await new bridge.BridgeClient(new bridge.TauriTransport()).invoke("project.inspect", args)).status, "ok");
  assert.equal(calls.length, 1, "Tauri must not fall back to hosted HTTP");
});

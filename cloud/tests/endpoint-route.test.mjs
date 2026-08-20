import assert from "node:assert/strict";
import test from "node:test";

import { createWorker } from "../dist/index.js";
import { WorkspaceCoordinator } from "../dist/workspace-coordinator.js";
import { MemoryBucket, MemoryState, keyBase64 } from "./helpers.mjs";

const ENDPOINT_VALIDATION_LIMIT = 16 * 1024;

async function fixture() {
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {});
  const session = await coordinator.createSession({ identity_id: "endpoint_route_owner" });
  let dnsCalls = 0;
  let probeCalls = 0;
  const env = {
    PUBLIC_ORIGIN: "https://studio.example",
    WORKOS_CLIENT_ID: "client_test",
    WORKOS_API_KEY: "sk_test",
    WORKOS_REDIRECT_URI: "https://studio.example/api/auth/callback",
    SESSION_VAULT_KEY_B64: keyBase64(10),
    PROJECT_BUNDLE_KEY_B64: keyBase64(11),
    PROJECT_BUNDLES: new MemoryBucket(),
    WORKSPACE_COORDINATOR: { getByName: () => coordinator },
    SESSION_VAULT: { getByName: () => ({ destroySession: async () => ({ destroyed: 0, authority: false }) }) },
    CORE_CONTAINER: { getByName: () => ({ fetch: async () => new Response(null, { status: 500 }) }) },
    CORE_PROOF_KEY_B64: keyBase64(12),
    CORE_PROOF_KEY_ID: "current",
    ENDPOINT_EGRESS: {
      fetch: async () => {
        probeCalls += 1;
        return new Response(null, { status: 204 });
      },
    },
    fetch: async () => {
      dnsCalls += 1;
      return Response.json({ Answer: [{ type: 1, data: "93.184.216.34" }] });
    },
  };
  const cookies = `__Host-qf_session=${session.cookie_token}; __Host-qf_csrf=${session.csrf_token}`;
  return { env, worker: createWorker(), cookies, counters: () => ({ dnsCalls, probeCalls }) };
}

function requestFor(cookies, body, headers = {}) {
  const bytes = body === undefined ? undefined : (body instanceof Uint8Array ? body : new TextEncoder().encode(body));
  const requestHeaders = {
    Origin: "https://studio.example",
    Cookie: cookies,
    "x-qf-csrf": cookies.split("__Host-qf_csrf=")[1],
    "content-type": "application/json",
    ...(bytes ? { "content-length": String(bytes.byteLength) } : {}),
    ...headers,
  };
  for (const [name, value] of Object.entries(requestHeaders)) if (value === undefined) delete requestHeaders[name];
  return new Request("https://studio.example/api/model/endpoints/validate", {
    method: "POST",
    headers: requestHeaders,
    body: bytes,
  });
}

async function assertInvalid(factory, expected = "endpoint_request_invalid") {
  const { env, worker, cookies, counters } = await fixture();
  const response = await worker.fetch(factory(cookies), env);
  assert.equal(response.status, 400);
  const text = await response.text();
  const payload = JSON.parse(text);
  assert.equal(payload.code, expected);
  assert.equal(payload.authority, false);
  assert.doesNotMatch(text, /BODY_SECRET|endpoint-secret/);
  assert.deepEqual(counters(), { dnsCalls: 0, probeCalls: 0 });
}

test("endpoint validation route accepts one bounded canonical endpoint JSON object", async () => {
  const { env, worker, cookies, counters } = await fixture();
  const request = requestFor(cookies, '{"endpoint":"https://models.example.com/v1"}');
  const response = await worker.fetch(request, env);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.schema, "quillframe_hosted_endpoint_validation_v1");
  assert.equal(body.authority, false);
  assert.deepEqual(counters(), { dnsCalls: 4, probeCalls: 1 });
});

test("endpoint validation route rejects missing, zero, oversize, and wrong content length", async () => {
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":"https://models.example.com/v1"}', { "content-length": undefined }));
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":"https://models.example.com/v1"}', { "content-length": "0" }));
  await assertInvalid((cookies) => requestFor(cookies, "x", { "content-length": String(ENDPOINT_VALIDATION_LIMIT + 1) }));
  await assertInvalid((cookies) => requestFor(cookies, "x", { "content-length": "2" }));
  await assertInvalid((cookies) => requestFor(cookies, "x", { "content-length": "abc" }));
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":"https://models.example.com/v1"}', { "content-type": "text/plain" }));
});

test("endpoint validation route rejects transfer encoding and short streams before DNS", async () => {
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":"https://models.example.com/v1"}', { "transfer-encoding": "chunked" }));
  await assertInvalid((cookies) => requestFor(cookies, "{", { "content-length": "2" }));
});

test("endpoint validation route rejects invalid UTF-8, duplicate, extra, and wrong-shape JSON", async () => {
  await assertInvalid((cookies) => requestFor(cookies, new Uint8Array([0xc3, 0x28])));
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":"https://models.example.com/v1","endpoint":"https://endpoint-secret"}'));
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":"https://models.example.com/v1","extra":"BODY_SECRET"}'));
  await assertInvalid((cookies) => requestFor(cookies, '{"endpoint":42}'));
  await assertInvalid((cookies) => requestFor(cookies, "{}"));
});

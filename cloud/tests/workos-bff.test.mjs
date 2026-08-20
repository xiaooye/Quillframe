import assert from "node:assert/strict";
import test from "node:test";

import { WorkOSClient } from "../dist/workos.js";
import { createWorker } from "../dist/index.js";
import { MemoryBucket, MemoryState, keyBase64 } from "./helpers.mjs";
import { SessionVault } from "../dist/session-vault.js";
import { WorkspaceCoordinator } from "../dist/workspace-coordinator.js";

class Namespace {
  constructor(factory) { this.factory = factory; this.instances = new Map(); }
  getByName(name) {
    if (!this.instances.has(name)) this.instances.set(name, this.factory(name));
    return this.instances.get(name);
  }
}

test("WorkOS adapter uses PKCE/state and exchanges codes without exposing the client secret", async () => {
  let captured;
  const client = new WorkOSClient({ clientId: "client_test", apiKey: "sk_test", redirectUri: "https://studio.example/api/auth/callback" }, async (request) => {
    captured = request;
    return Response.json({ user: { id: "user_1", email: "writer@example.com" }, access_token: "access-secret", refresh_token: "refresh-secret", session_id: "workos-session" });
  });
  const url = client.authorizationUrl({ state: "state_1", codeChallenge: "challenge_1" });
  assert.equal(url.origin, "https://api.workos.com");
  assert.equal(url.searchParams.get("provider"), "authkit");
  assert.equal(url.searchParams.get("code_challenge_method"), "S256");
  const result = await client.authenticateCode({ code: "code_1", codeVerifier: "verifier_1" });
  assert.equal(result.user.id, "user_1");
  const body = await captured.clone().json();
  assert.equal(body.code_verifier, "verifier_1");
  assert.equal(body.client_secret, "sk_test");
  assert.doesNotMatch(JSON.stringify(result.user), /secret/);
});

function envWithWorkOS() {
  const coordinator = new Namespace(() => new WorkspaceCoordinator(new MemoryState(), {}));
  const vault = new Namespace(() => new SessionVault(new MemoryState(), { SESSION_VAULT_KEY_B64: keyBase64(10) }));
  return {
    PUBLIC_ORIGIN: "https://studio.example",
    WORKOS_CLIENT_ID: "client_test",
    WORKOS_API_KEY: "sk_test",
    WORKOS_REDIRECT_URI: "https://studio.example/api/auth/callback",
    SESSION_VAULT_KEY_B64: keyBase64(10),
    PROJECT_BUNDLE_KEY_B64: keyBase64(11),
    WORKSPACE_COORDINATOR: coordinator,
    SESSION_VAULT: vault,
    PROJECT_BUNDLES: new MemoryBucket(),
    CORE_CONTAINER: { getByName: () => ({ fetch: async () => Response.json({ schema: "core", authority: false }) }) },
    ENDPOINT_EGRESS: { fetch: async () => new Response(null, { status: 204 }) },
    fetch: async (request) => Response.json({ user: { id: "user_1", email: "writer@example.com" }, access_token: "access-secret", refresh_token: "refresh-secret", session_id: "workos-session" }),
  };
}

test("BFF rejects callback state tampering and emits host-only opaque session cookies", async () => {
  const env = envWithWorkOS();
  const worker = createWorker();
  const begin = await worker.fetch(new Request("https://studio.example/api/auth/authorize"), env);
  assert.equal(begin.status, 302);
  const authCookie = begin.headers.get("set-cookie").split(";", 1)[0];
  const location = new URL(begin.headers.get("location"));
  const state = location.searchParams.get("state");

  const tampered = await worker.fetch(new Request(`https://studio.example/api/auth/callback?code=code_1&state=wrong`, { headers: { Cookie: authCookie } }), env);
  assert.equal(tampered.status, 400);

  // A state mismatch burns the one-time transaction. Start a fresh flow instead
  // of allowing a failed callback to be replayed with the correct state.
  const freshBegin = await worker.fetch(new Request("https://studio.example/api/auth/authorize"), env);
  const freshAuthCookie = freshBegin.headers.get("set-cookie").split(";", 1)[0];
  const freshState = new URL(freshBegin.headers.get("location")).searchParams.get("state");
  assert.notEqual(freshState, state);
  const valid = await worker.fetch(new Request(`https://studio.example/api/auth/callback?code=code_1&state=${encodeURIComponent(freshState)}`, { headers: { Cookie: freshAuthCookie } }), env);
  assert.equal(valid.status, 302);
  const cookies = valid.headers.getSetCookie ? valid.headers.getSetCookie() : [valid.headers.get("set-cookie")];
  const joined = cookies.join("\n");
  assert.match(joined, /__Host-qf_session=/);
  assert.match(joined, /HttpOnly/);
  assert.match(joined, /__Host-qf_csrf=/);
  assert.doesNotMatch(joined, /access-secret|refresh-secret/);
});

test("BFF normalizes unsafe WorkOS return_to values to the same-origin studio fallback", async () => {
  const unsafeReturnToValues = [
    "/\\\\evil.example",
    "/%2f%2fevil.example",
    "/%5c%5cevil.example",
    "/studio\u0000evil",
    "/studio\nLocation: https://evil.example",
    "//evil.example/phish",
    "https://evil.example/phish",
  ];

  for (const returnTo of unsafeReturnToValues) {
    const env = envWithWorkOS();
    const worker = createWorker();
    const begin = await worker.fetch(new Request(`https://studio.example/api/auth/authorize?return_to=${encodeURIComponent(returnTo)}`), env);
    assert.equal(begin.status, 302, returnTo);
    const authCookie = begin.headers.get("set-cookie").split(";", 1)[0];
    const state = new URL(begin.headers.get("location")).searchParams.get("state");
    const callback = await worker.fetch(new Request(`https://studio.example/api/auth/callback?code=code_1&state=${encodeURIComponent(state)}`, { headers: { Cookie: authCookie } }), env);
    assert.equal(callback.status, 302, returnTo);
    assert.equal(callback.headers.get("location"), "https://studio.example/studio", returnTo);
  }
});

test("BFF preserves valid same-origin WorkOS return_to query and hash", async () => {
  const env = envWithWorkOS();
  const worker = createWorker();
  const returnTo = "/studio/projects?tab=recent#focus";
  const begin = await worker.fetch(new Request(`https://studio.example/api/auth/authorize?return_to=${encodeURIComponent(returnTo)}`), env);
  const authCookie = begin.headers.get("set-cookie").split(";", 1)[0];
  const state = new URL(begin.headers.get("location")).searchParams.get("state");
  const callback = await worker.fetch(new Request(`https://studio.example/api/auth/callback?code=code_1&state=${encodeURIComponent(state)}`, { headers: { Cookie: authCookie } }), env);
  assert.equal(callback.status, 302);
  assert.equal(callback.headers.get("location"), "https://studio.example/studio/projects?tab=recent#focus");
});

test("BFF requires origin, CSRF, and explicit upload headers for mutations", async () => {
  const env = envWithWorkOS();
  const worker = createWorker();
  const response = await worker.fetch(new Request("https://studio.example/api/projects/p/upload", { method: "POST", headers: { Origin: "https://evil.example" }, body: "bundle" }), env);
  assert.equal(response.status, 403);
  assert.match(response.headers.get("content-security-policy"), /default-src 'none'/);
});

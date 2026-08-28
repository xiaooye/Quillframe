import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { WorkOSClient } from "../dist/workos.js";
import { createWorker } from "../dist/index.js";
import { MemoryBucket, MemoryState, keyBase64 } from "./helpers.mjs";
import { SessionVault } from "../dist/session-vault.js";
import { WorkspaceCoordinator } from "../dist/workspace-coordinator.js";
import { canonicalJsonBytes } from "../dist/core-provenance.js";

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

const studioIndexPath = new URL("../../studio/app/index.html", import.meta.url);
const studioIndex = fs.readFileSync(studioIndexPath, "utf8");
const hostedSlot = '<meta name="quillframe-studio-hosted-endpoint" content="" />';

function envWithAssets(index = studioIndex) {
  const requests = [];
  const env = envWithWorkOS();
  env.ASSETS = {
    async fetch(request) {
      requests.push(request);
      if (new URL(request.url).pathname !== "/index.html" || index === null) return new Response(null, { status: 404 });
      return new Response(index, { headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "public, max-age=86400",
        "cdn-cache-control": "public, max-age=86400",
        etag: '"unbound-index"',
        "last-modified": "Thu, 01 Jan 2026 00:00:00 GMT",
        "content-length": String(Buffer.byteLength(index)),
        "set-cookie": "asset-cookie=forbidden",
      } });
    },
  };
  return { env, requests };
}

function assertNoStore(response) {
  for (const header of ["cache-control", "cdn-cache-control", "cloudflare-cdn-cache-control"]) {
    assert.equal(response.headers.get(header), "no-store", header);
  }
  assert.equal(response.headers.get("etag"), null);
  assert.equal(response.headers.get("last-modified"), null);
}

test("hosted Studio binds only its trusted index to the configured origin without caching HTML", async () => {
  const worker = createWorker();
  assert.ok(studioIndex.includes(hostedSlot), "the real Studio template must keep an empty hosted slot");
  for (const origin of ["https://studio.example", "https://writers.example:8443"]) {
    const { env, requests } = envWithAssets();
    env.PUBLIC_ORIGIN = origin;
    for (const route of ["/", "/index.html", "/review?lang=zh&endpoint=https://evil.example"]) {
      const response = await worker.fetch(new Request(`${origin}${route}`, { headers: {
        Cookie: "__Host-qf_session=not-an-asset-credential",
        Authorization: "not-an-asset-credential",
        "if-none-match": '"unbound-index"',
      } }), env);
      assert.equal(response.status, 200, route);
      assertNoStore(response);
      assert.equal(response.headers.get("content-length"), null);
      assert.equal(response.headers.get("set-cookie"), null);
      assert.equal(await response.text(), studioIndex.replace(hostedSlot, hostedSlot.replace('content=""', `content="${origin}"`)));
      const csp = response.headers.get("content-security-policy");
      for (const kind of ["script", "style", "connect", "manifest"]) assert.match(csp, new RegExp(`${kind}-src 'self'(?:;|$)`));
      assert.match(csp, /frame-ancestors 'none'/);
      assert.doesNotMatch(csp, /unsafe-inline|unsafe-eval|\*/);
    }
    const head = await worker.fetch(new Request(`${origin}/review`, { method: "HEAD" }), env);
    assert.equal(head.status, 200);
    assertNoStore(head);
    assert.equal(await head.text(), "");
    for (const request of requests) {
      assert.equal(new URL(request.url).search, "");
      assert.equal(request.headers.get("cookie"), null);
      assert.equal(request.headers.get("authorization"), null);
      if (new URL(request.url).pathname === "/index.html") assert.equal(request.headers.get("if-none-match"), null);
    }
  }
  assert.equal(fs.readFileSync(studioIndexPath, "utf8"), studioIndex, "the static/local template must remain unchanged");
});

test("hosted Studio fails closed for missing, pre-bound, or ambiguous index assets", async () => {
  const worker = createWorker();
  for (const index of [studioIndex.replace(hostedSlot, ""), studioIndex.replace(hostedSlot, `${hostedSlot}${hostedSlot}`), studioIndex.replace('content=""', 'content="https://evil.example"')]) {
    const response = await worker.fetch(new Request("https://studio.example/"), envWithAssets(index).env);
    assert.equal(response.status, 503);
    assert.equal((await response.json()).code, "studio_shell_invalid");
  }
  const missing = await worker.fetch(new Request("https://studio.example/"), envWithAssets(null).env);
  assert.equal(missing.status, 404);
  assert.equal((await missing.json()).code, "not_found");
  const { env } = envWithAssets();
  env.ASSETS.fetch = async () => new Response(studioIndex, { headers: { "content-type": "text/plain" } });
  const wrongType = await worker.fetch(new Request("https://studio.example/"), env);
  assert.equal(wrongType.status, 503);
  assert.equal((await wrongType.json()).code, "studio_shell_invalid");
});

test("hosted Studio checks its exact HTTPS origin and preserves the no-assets 404 boundary", async () => {
  const worker = createWorker();
  for (const configured of ["http://studio.example", "https://studio.example/", "https://studio.example/path", "https://user:password@studio.example", "not an origin"]) {
    const { env, requests } = envWithAssets();
    env.PUBLIC_ORIGIN = configured;
    const requestOrigin = configured.startsWith("http:") ? "http://studio.example" : "https://studio.example";
    const response = await worker.fetch(new Request(`${requestOrigin}/`), env);
    assert.equal(response.status, 403, configured);
    assert.equal(requests.length, 0);
  }
  const { env, requests } = envWithAssets();
  const wrongHost = await worker.fetch(new Request("https://preview.example/"), env);
  assert.equal(wrongHost.status, 403);
  assert.equal(requests.length, 0);
  for (const method of ["GET", "HEAD", "POST"]) {
    const absent = await worker.fetch(new Request("https://studio.example/", { method, headers: { origin: env.PUBLIC_ORIGIN } }), envWithWorkOS());
    assert.equal(absent.status, 404);
  }
});

test("asset routing never handles API paths, failed sessions, or unsupported methods", async () => {
  const worker = createWorker();
  const { env, requests } = envWithAssets();
  for (const [route, method, expected] of [["/api", "GET", 404], ["/api/unknown", "GET", 404], ["/%61pi/session", "GET", 404], ["/api%2Fsession", "GET", 404], ["/api/core/bridge", "HEAD", 404], ["/api/session", "GET", 401], ["/api/auth/logout", "POST", 401]]) {
    const response = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}${route}`, { method, headers: { origin: env.PUBLIC_ORIGIN } }), env);
    assert.equal(response.status, expected, route);
    assertNoStore(response);
    assert.match(response.headers.get("content-type"), /application\/json/);
    assert.doesNotMatch(await response.text(), /<!doctype|<meta/i);
  }
  assert.equal(requests.length, 0);
  const post = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/review`, { method: "POST", headers: { origin: env.PUBLIC_ORIGIN } }), env);
  assert.equal(post.status, 405);
  assert.equal(post.headers.get("allow"), "GET, HEAD");
  assert.equal(requests.length, 0);
});

test("static assets retain their bytes and cache policy without credentials or HTML rebinding", async () => {
  const worker = createWorker();
  const { env, requests } = envWithAssets();
  const indexFetch = env.ASSETS.fetch;
  env.ASSETS.fetch = async (request) => {
    const pathname = new URL(request.url).pathname;
    if (pathname === "/assets/app.js" || pathname === "/other.html") {
      requests.push(request);
      return new Response(request.method === "HEAD" ? null : pathname.endsWith(".js") ? "export const ready = true;" : studioIndex, { headers: {
        "content-type": pathname.endsWith(".js") ? "text/javascript" : "text/html",
        "cache-control": "public, max-age=31536000, immutable",
        "set-cookie": "asset-cookie=forbidden",
      } });
    }
    return indexFetch(request);
  };
  const js = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/assets/app.js?token=not-an-asset-credential`, { headers: { Cookie: "session=private" } }), env);
  assert.equal(await js.text(), "export const ready = true;");
  assert.equal(js.headers.get("cache-control"), "public, max-age=31536000, immutable");
  assert.equal(js.headers.get("x-content-type-options"), "nosniff");
  assert.equal(js.headers.get("set-cookie"), null);
  assert.equal(requests[0].url, `${env.PUBLIC_ORIGIN}/assets/app.js`);
  assert.equal(requests[0].headers.get("cookie"), null);
  const head = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/assets/app.js`, { method: "HEAD" }), env);
  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  const otherHtml = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/other.html`), env);
  assert.equal(await otherHtml.text(), studioIndex, "only the trusted /index.html is bound");
  assert.match(otherHtml.headers.get("content-security-policy"), /default-src 'none'/);
  assertNoStore(otherHtml);
  for (const route of ["/assets/missing.js", "/assets/missing", "/.well-known/missing", "/missing.css"]) {
    const missing = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}${route}`), env);
    assert.equal(missing.status, 404, route);
    assert.equal((await missing.json()).code, "not_found");
  }
});

test("successful session and Core API responses cannot inherit asset or upstream caching", async () => {
  const worker = createWorker();
  const { env, requests } = envWithAssets();
  const begin = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/api/auth/authorize`), env);
  assertNoStore(begin);
  const authCookie = begin.headers.get("set-cookie").split(";", 1)[0];
  const state = new URL(begin.headers.get("location")).searchParams.get("state");
  const callback = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/api/auth/callback?code=code_1&state=${encodeURIComponent(state)}`, { headers: { cookie: authCookie } }), env);
  assertNoStore(callback);
  const cookies = callback.headers.getSetCookie().map((value) => value.split(";", 1)[0]);
  const cookieHeader = cookies.join("; ");
  const csrf = cookies.find((value) => value.startsWith("__Host-qf_csrf=")).slice("__Host-qf_csrf=".length);
  const session = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/api/session`, { headers: { cookie: cookieHeader } }), env);
  assert.equal(session.status, 200);
  assertNoStore(session);
  env.CORE_PROOF_KEY_ID = "current";
  env.CORE_PROOF_KEY_B64 = Buffer.alloc(32, 13).toString("base64url");
  env.CORE_CONTAINER = { getByName: () => ({ fetch: async () => Response.json({ schema: "core", authority: false }, { headers: {
    "cache-control": "public, max-age=86400", "cdn-cache-control": "public, max-age=86400", etag: '"private-core-result"',
  } }) }) };
  const body = canonicalJsonBytes({ schema: "quillframe_host_bridge_request_v11", bridge_version: "11", request_id: "asset_api_test", operation: "model.service.list", args: {}, surface: "hosted_web", authority: false });
  const core = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/api/core/bridge`, { method: "POST", headers: {
    cookie: cookieHeader, origin: env.PUBLIC_ORIGIN, "x-qf-csrf": csrf, "content-type": "application/json", "content-length": String(body.byteLength),
  }, body }), env);
  assert.equal(core.status, 200, await core.clone().text());
  assertNoStore(core);
  assert.equal(requests.length, 0);
});

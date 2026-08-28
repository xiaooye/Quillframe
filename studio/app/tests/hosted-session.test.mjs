import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const compile = (name) => ts.transpileModule(fs.readFileSync(new URL(`../src/${name}`, import.meta.url), "utf8"), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText;
const bridgeUrl = moduleUrl(compile("bridge.ts"));
const session = await import(moduleUrl(compile("hostedSession.ts").replace('"./bridge"', JSON.stringify(bridgeUrl))));
const now = Date.now();
const workspace = "a".repeat(24);
const projection = {
  schema: "quillframe_cloud_session_projection_v1", workspace_id: `workspace_${workspace}`,
  workspace_handle: workspace, session_id: "session_example", workos_session_id: "session_workos",
  idle_expires_at: now + 30 * 60_000, absolute_expires_at: now + 8 * 60 * 60_000, authority: false,
};

function browserFor(t) {
  const state = { endpoint: "https://studio.example", cookie: `__Host-qf_csrf=${"c".repeat(32)}`, response: () => Response.json(projection) };
  const originals = new Map(["document", "window", "fetch"].map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const calls = [];
  Object.defineProperty(globalThis, "document", { configurable: true, value: {
    get cookie() { return state.cookie; }, querySelector() { return { content: state.endpoint }; },
  } });
  Object.defineProperty(globalThis, "window", { configurable: true, value: { location: new URL("https://studio.example/start") } });
  Object.defineProperty(globalThis, "fetch", { configurable: true, value: async (url, init) => {
    calls.push({ url, ...init }); return state.response();
  } });
  t.after(() => {
    for (const [key, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  });
  return { state, calls };
}

test("hosted session bootstrap uses only same-origin cookie authentication and never caches", async (t) => {
  const { calls } = browserFor(t);
  const controller = new AbortController();
  assert.deepEqual(await session.loadHostedSession(controller.signal), projection);
  assert.equal(calls.length, 1);
  const request = calls[0];
  assert.equal(request.url, "https://studio.example/api/session");
  assert.equal(request.method, "GET");
  assert.equal(request.credentials, "same-origin");
  assert.equal(request.cache, "no-store");
  assert.equal(request.redirect, "error");
  assert.equal(request.signal, controller.signal);
  assert.equal(new Headers(request.headers).get("authorization"), null);
  assert.equal(session.hostedSignInUrl(), "https://studio.example/api/auth/authorize?return_to=%2Fstart");
});

test("missing session is signed out, while protocol and server failures stay failures", async (t) => {
  const { state } = browserFor(t);
  state.response = () => Response.json({ code: "session_invalid" }, { status: 401 });
  assert.equal(await session.loadHostedSession(), null);
  for (const response of [
    () => Response.json({ message: "PRIVATE_SENTINEL" }, { status: 500 }),
    () => new Response("<html>not an authenticated API</html>", { headers: { "Content-Type": "text/html" } }),
    () => Response.json({ ...projection, authority: true }),
    () => Response.json({ ...projection, workspace_id: "workspace_other" }),
    () => Response.json({ ...projection, absolute_expires_at: now - 1 }),
    () => Response.json({ ...projection, idle_expires_at: 1.5 }),
    () => Response.json({ ...projection, access_token: "PRIVATE_SENTINEL" }),
  ]) {
    state.response = response;
    await assert.rejects(() => session.loadHostedSession(), (error) => error.message === "Hosted session could not be verified");
  }
  state.response = () => Response.json(projection);
  state.cookie = "";
  await assert.rejects(() => session.loadHostedSession(), /CSRF token is missing or invalid/);
});

test("session calls refuse an unbound or cross-origin preview before any network request", async (t) => {
  const { state, calls } = browserFor(t);
  for (const endpoint of ["", "https://other.example", "http://studio.example"]) {
    state.endpoint = endpoint;
    assert.throws(() => session.hostedSignInUrl(), /not bound/);
    await assert.rejects(() => session.loadHostedSession(), /not bound/);
    await assert.rejects(() => session.logoutHostedSession(), /not bound/);
  }
  assert.equal(calls.length, 0);
});

test("logout requires CSRF and a verified receipt before returning the WorkOS sign-out URL", async (t) => {
  const { state, calls } = browserFor(t);
  const logoutUrl = "https://api.workos.com/user_management/sessions/logout?session_id=session_workos&return_to=https%3A%2F%2Fstudio.example";
  const receipt = { schema: "quillframe_cloud_logout_receipt_v1", destroyed: true, workos_logout_url: logoutUrl, authority: false };
  state.response = () => Response.json(receipt);
  assert.equal(await session.logoutHostedSession(), logoutUrl);
  assert.equal(calls[0].url, "https://studio.example/api/auth/logout");
  assert.equal(calls[0].method, "POST");
  assert.equal(calls[0].credentials, "same-origin");
  assert.equal(calls[0].redirect, "error");
  assert.equal(calls[0].cache, "no-store");
  assert.equal(new Headers(calls[0].headers).get("x-qf-csrf"), "c".repeat(32));
  for (const workos_logout_url of [
    "javascript:alert(1)", "https://other.example/logout", "https://api.workos.com/other",
    `${logoutUrl}&return_to=https%3A%2F%2Fother.example`,
    logoutUrl.replace("studio.example", "other.example"),
  ]) {
    state.response = () => Response.json({ ...receipt, workos_logout_url });
    await assert.rejects(() => session.logoutHostedSession(), /logout could not be verified/);
  }
  state.response = () => Response.json({ ...receipt, destroyed: false });
  await assert.rejects(() => session.logoutHostedSession(), /logout could not be verified/);
  state.response = () => Response.json({ code: "session_expired" }, { status: 401 });
  assert.equal(await session.logoutHostedSession(), null);
  const before = calls.length;
  state.cookie = "__Host-qf_csrf=bad";
  await assert.rejects(() => session.logoutHostedSession(), /CSRF/);
  assert.equal(calls.length, before);
});

test("hosted bootstrap gates Studio mount, handles expiry, and exposes only an explicit logout action", () => {
  const main = fs.readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
  const boundary = fs.readFileSync(new URL("../src/HostedSessionBoundary.tsx", import.meta.url), "utf8");
  const shell = fs.readFileSync(new URL("../src/AppShell.tsx", import.meta.url), "utf8");
  const settings = fs.readFileSync(new URL("../src/routes/Settings.tsx", import.meta.url), "utf8");
  assert.match(main, /<HostedSessionBoundary>\s*<StudioProvider>/);
  assert.match(boundary, /bridgeTransportName\(\) !== "hosted-http"/);
  assert.match(boundary, /subscribeToHostedSessionExpiry/);
  assert.match(boundary, /onCleanup/);
  assert.match(boundary, /AbortController/);
  assert.match(boundary, /const epoch = invalidateHostedSession\(\)/);
  assert.match(boundary, /current\(attempt\).*activateHostedSession\(attempt\.epoch\)/);
  assert.match(boundary, /onCleanup\(.*invalidateHostedSession\(\)/);
  assert.match(boundary, /<Show when=\{phase\(\) === "ready"\}/);
  assert.match(shell, /<HostedAccountButton\s*\/>/);
  assert.match(settings, /<HostedAccountButton\s*\/>\s*<div class="qf-settings-layout">/, "logout remains available outside the mobile-hidden sidebar and settings tabs");
  assert.doesNotMatch(boundary, /localStorage|sessionStorage|setInterval|access_token|innerHTML/);
});

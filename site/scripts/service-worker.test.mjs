import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { atomicWrite, finalizeServiceWorker, hashBuildFingerprint, listBuildFiles } from "./finalize-service-worker.mjs";

const source = await fs.readFile(new URL("../public/sw.js", import.meta.url), "utf8");

function makeRuntime({ fetchImpl = async () => new Response("network") } = {}) {
  const handlers = {};
  const namespaces = new Map();
  const calls = { open: [], match: [], put: [], add: [], delete: [], fetch: [], respond: 0, waits: [] };
  function cache(name) {
    const entries = namespaces.get(name) ?? new Map();
    namespaces.set(name, entries);
    return {
      async match(request) { calls.match.push(request.url ?? request); return entries.get(request.url ?? request) ?? undefined; },
      async put(request, response) { calls.put.push(request.url ?? request); entries.set(request.url ?? request, response); },
      async add(request) { calls.add.push(request); const response = await fetchImpl(new Request(new URL(request, "https://app.test"))); if (!response.ok) throw new Error("precache failed"); entries.set(new URL(request, "https://app.test").href, response.clone()); },
    };
  }
  const cacheStorage = { async open(name) { calls.open.push(name); return cache(name); }, async keys() { return [...namespaces.keys()]; }, async delete(name) { calls.delete.push(name); namespaces.delete(name); return true; } };
  const self = {
    location: { origin: "https://app.test" },
    clients: { async claim() { calls.claim = true; } },
    skipWaiting() { calls.skip = true; },
    addEventListener(kind, callback) { handlers[kind] = callback; },
  };
  const context = vm.createContext({ self, caches: cacheStorage, fetch: async (request) => { calls.fetch.push(request.url); return fetchImpl(request); }, URL, Request, Response, console, setTimeout });
  vm.runInContext(source, context, { filename: "sw.js" });
  return {
    calls, namespaces, handlers,
    async fetch(request) {
      const event = { request: request instanceof Request || typeof request === "object" ? request : new Request(request), respondWith(value) { calls.respond += 1; event.responsePromise = Promise.resolve(value); } };
      handlers.fetch(event);
      return event.responsePromise;
    },
    async install() {
      const event = { waitUntil(value) { calls.waits.push(Promise.resolve(value)); } };
      handlers.install(event);
      await Promise.all(calls.waits);
    },
    async activate() {
      const event = { waitUntil(value) { calls.waits.push(Promise.resolve(value)); } };
      handlers.activate(event);
      await Promise.all(calls.waits);
    },
  };
}

test("D2-01 non-GET methods bypass without respondWith", async () => {
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const runtime = makeRuntime();
    await runtime.fetch(new Request(`https://app.test/docs/?${method}`, { method }));
    assert.equal(runtime.calls.respond, 0, method);
    assert.equal(runtime.calls.open.length, 0, method);
    assert.equal(runtime.calls.fetch.length, 0, method);
    assert.equal(runtime.calls.put.length, 0, method);
  }
});

test("D2-02 HEAD bypasses", async () => {
  const runtime = makeRuntime();
  await runtime.fetch(new Request("https://app.test/docs/", { method: "HEAD" }));
  assert.equal(runtime.calls.respond, 0);
  assert.equal(runtime.calls.open.length, 0);
  assert.equal(runtime.calls.fetch.length, 0);
});

test("D2-03 cross-origin GET bypasses", async () => {
  const runtime = makeRuntime();
  await runtime.fetch("https://other.test/docs/");
  assert.equal(runtime.calls.respond, 0);
  assert.equal(runtime.calls.open.length, 0);
  assert.equal(runtime.calls.fetch.length, 0);
});

test("D2-04 API paths bypass but /apis remains eligible", async () => {
  for (const pathname of ["/api", "/api/", "/api/session", "/api/x"]) {
    const runtime = makeRuntime();
    await runtime.fetch(`https://app.test${pathname}`);
    assert.equal(runtime.calls.respond, 0, pathname);
    assert.equal(runtime.calls.open.length, 0, pathname);
    assert.equal(runtime.calls.fetch.length, 0, pathname);
  }
  const runtime = makeRuntime();
  await runtime.fetch("https://app.test/apis");
  assert.equal(runtime.calls.respond, 1);
});

test("D2-05 and D2-06 use only root Chinese and exact English docs shells", async () => {
  const runtime = makeRuntime();
  for (const pathname of ["/docs/", "/docs/en", "/docs/en/", "/docs/en/page", "/docs/en-US", "/docs/enfoo"]) {
    await runtime.fetch(`https://app.test${pathname}`);
  }
  assert.deepEqual(runtime.calls.match.map((url) => new URL(url).pathname), ["/docs/", "/docs/en", "/docs/en/", "/docs/en/page", "/docs/en-US", "/docs/enfoo"]);
});

test("D2-07 offline docs fallback probes only exact locale shell, never product root", async () => {
  for (const pathname of ["/docs", "/docs/", "/docs/en", "/docs/en/", "/docs/en/page"]) {
    const runtime = makeRuntime({ fetchImpl: async () => { throw new Error("offline"); } });
    await assert.rejects(runtime.fetch({ url: `https://app.test${pathname}`, method: "GET", mode: "navigate" }), (error) => error.message === "offline");
    const shell = pathname.startsWith("/docs/en") ? "/docs/en/" : "/docs/";
    assert.deepEqual(runtime.calls.match.map((url) => new URL(url).pathname), [pathname === "/docs" ? "/docs" : pathname, shell]);
  }
  for (const pathname of ["/docs/en-US", "/docs/enfoo", "/docs/zh-CN/", "/not-doc"]) {
    const runtime = makeRuntime({ fetchImpl: async () => { throw new Error("offline"); } });
    const original = new Error(`offline:${pathname}`);
    const result = makeRuntime({ fetchImpl: async () => { throw original; } });
    await assert.rejects(result.fetch({ url: `https://app.test${pathname}`, method: "GET", mode: "navigate" }), (error) => error === original);
    assert.equal(result.calls.match.length, 1, pathname);
  }
});

test("D2-08 query variants remain exact cache keys", async () => {
  const runtime = makeRuntime();
  await runtime.fetch("https://app.test/assets/a.js?a=1");
  await runtime.fetch("https://app.test/assets/a.js?a=2");
  assert.deepEqual(runtime.calls.put, ["https://app.test/assets/a.js?a=1", "https://app.test/assets/a.js?a=2"]);
});

test("D2-09 only successful responses are cached", async () => {
  const bad = makeRuntime({ fetchImpl: async () => new Response("bad", { status: 503 }) });
  const badResponse = await bad.fetch("https://app.test/assets/bad");
  assert.equal(badResponse.status, 503);
  assert.equal(bad.calls.put.length, 0);
  const good = makeRuntime({ fetchImpl: async () => new Response("ok") });
  await good.fetch("https://app.test/assets/good");
  assert.equal(good.calls.put.length, 1);
});

test("D2-10 install awaits and rejects failed required shells", async () => {
  const runtime = makeRuntime({ fetchImpl: async (request) => request.url.endsWith("/docs/en/") ? new Response("bad", { status: 404 }) : new Response("ok") });
  await assert.rejects(runtime.install(), /precache failed/);
});

test("D2 install success waits for both shells before skipWaiting", async () => {
  const runtime = makeRuntime({ fetchImpl: async () => new Response("ok") });
  await runtime.install();
  assert.deepEqual(runtime.calls.add, ["/docs/", "/docs/en/"]);
  assert.equal(runtime.calls.skip, true);
  assert.equal(runtime.calls.waits.length, 1);
});

test("D2-11 activate deletes only old owned caches", async () => {
  const runtime = makeRuntime();
  runtime.namespaces.set("quillframe-site-old", new Map([["https://app.test/old", new Response("old")]]));
  runtime.namespaces.set("quillframe-site-__QF_SITE_CACHE_VERSION__", new Map([["https://app.test/current", new Response("current")]]));
  runtime.namespaces.set("other-owner-cache", new Map([["https://app.test/other", new Response("other")]]));
  await runtime.activate();
  assert.deepEqual(runtime.calls.delete, ["quillframe-site-old"]);
  assert.equal(runtime.namespaces.has("quillframe-site-__QF_SITE_CACHE_VERSION__"), true);
  assert.equal(runtime.namespaces.has("other-owner-cache"), true);
});

test("D2 current namespace does not read old namespace entries", async () => {
  const runtime = makeRuntime({ fetchImpl: async () => new Response("network") });
  runtime.namespaces.set("quillframe-site-old", new Map([["https://app.test/assets/a", new Response("old")]]));
  runtime.namespaces.set("quillframe-site-__QF_SITE_CACHE_VERSION__", new Map());
  const response = await runtime.fetch("https://app.test/assets/a");
  assert.equal(await response.text(), "network");
  assert.deepEqual(runtime.calls.open, ["quillframe-site-__QF_SITE_CACHE_VERSION__"]);
});

test("D2 offline shell hit returns the exact current response and never other namespaces", async () => {
  const runtime = makeRuntime({ fetchImpl: async () => { throw new Error("offline"); } });
  const shell = new Response("EN SHELL", { status: 299, headers: { "x-shell": "current" } });
  runtime.namespaces.set("quillframe-site-__QF_SITE_CACHE_VERSION__", new Map([
    ["https://app.test/docs/en/", shell.clone()],
  ]));
  runtime.namespaces.set("quillframe-site-old", new Map([["https://app.test/docs/en/", new Response("OLD")]]));
  const response = await runtime.fetch({ url: "https://app.test/docs/en/page?x=1", method: "GET", mode: "navigate" });
  assert.equal(response.status, 299);
  assert.equal(response.headers.get("x-shell"), "current");
  assert.equal(await response.text(), "EN SHELL");
  assert.deepEqual(runtime.calls.match.map((url) => new URL(url).pathname + new URL(url).search), ["/docs/en/page?x=1", "/docs/en/"]);
  assert.equal(runtime.calls.open.every((name) => name === "quillframe-site-__QF_SITE_CACHE_VERSION__"), true);
});

test("D2 offline root and English shell hits preserve exact response fields", async () => {
  for (const [pathname, body, status, header] of [["/docs/page", "CN SHELL", 201, "cn"], ["/docs/en/page", "EN SHELL", 202, "en"]]) {
    const runtime = makeRuntime({ fetchImpl: async () => { throw new Error("offline"); } });
    runtime.namespaces.set("quillframe-site-__QF_SITE_CACHE_VERSION__", new Map([
      [pathname.startsWith("/docs/en") ? "https://app.test/docs/en/" : "https://app.test/docs/", new Response(body, { status, headers: { "x-shell": header } })],
    ]));
    const response = await runtime.fetch({ url: `https://app.test${pathname}`, method: "GET", mode: "navigate" });
    assert.equal(response.status, status);
    assert.equal(response.headers.get("x-shell"), header);
    assert.equal(await response.text(), body);
  }
});

test("D2-12 finalizer is deterministic, output-only, and records required shells", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-test-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  await fs.writeFile(path.join(dir, "sw.js"), "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';");
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  const result = await finalizeServiceWorker({ distDir: dir });
  const persisted = JSON.parse(await fs.readFile(path.join(dir, "generated/quillframe-site-service-worker.json"), "utf8"));
  assert.deepEqual(persisted, result);
  assert.equal(persisted.schema, "quillframe_site_service_worker_finalizer_v1");
  assert.equal(persisted.fingerprint, result.fingerprint);
  assert.equal(persisted.cache_name, result.cache_name);
  assert.deepEqual(persisted.source_files, [...persisted.source_files].sort());
  assert.equal(persisted.source_files.includes("sw.js"), false);
  assert.equal(persisted.source_files.includes("generated/quillframe-site-service-worker.json"), false);
  assert.deepEqual(persisted.required_shells, ["docs/", "docs/en/"]);
  assert.equal(persisted.sw_path, "sw.js");
  assert.equal(persisted.authority, false);
  assert.match(await fs.readFile(path.join(dir, "sw.js"), "utf8"), new RegExp(result.cache_name));
  const firstOutput = await fs.readFile(path.join(dir, "sw.js"), "utf8");
  const repeated = await finalizeServiceWorker({ distDir: dir });
  assert.equal(await fs.readFile(path.join(dir, "sw.js"), "utf8"), firstOutput);
  assert.deepEqual(repeated, result);
  const sourceAgain = await fs.readFile(new URL("../public/sw.js", import.meta.url), "utf8");
  assert.equal(sourceAgain, source);
  assert.match(result.cache_name, /^quillframe-site-[0-9a-f]{16}$/);
  assert.equal(result.authority, false);
  assert.deepEqual(result.required_shells, ["docs/", "docs/en/"]);
  assert.equal((await listBuildFiles(dir)).some((file) => file === "sw.js"), false);
  assert.equal((await hashBuildFingerprint(await listBuildFiles(dir), dir)).length, 71);
});

test("D2 finalizer excludes stale temp files and requires regular shell files", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-temp-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  await fs.writeFile(path.join(dir, "sw.js"), "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';");
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  await fs.writeFile(path.join(dir, "asset.tmp-123"), "stale");
  const before = await listBuildFiles(dir);
  assert.equal(before.includes("asset.tmp-123"), false);
  const result = await finalizeServiceWorker({ distDir: dir });
  assert.equal(result.source_files.includes("asset.tmp-123"), false);
  await fs.rm(path.join(dir, "docs/index.html"));
  await assert.rejects(finalizeServiceWorker({ distDir: dir }), /required shell/);
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.rm(path.join(dir, "docs/en/index.html"));
  await fs.mkdir(path.join(dir, "docs/en/index.html"));
  await assert.rejects(finalizeServiceWorker({ distDir: dir }), /required shell/);
});

test("D2 finalized rerun rejects changed dist/cache mismatch", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-mismatch-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  await fs.writeFile(path.join(dir, "sw.js"), "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';");
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  await finalizeServiceWorker({ distDir: dir });
  await fs.writeFile(path.join(dir, "docs/index.html"), "changed");
  await assert.rejects(finalizeServiceWorker({ distDir: dir }), /mismatch/);
});

test("D2 finalizer rejects symlink required shells and duplicate/missing literals", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-symlink-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  await fs.writeFile(path.join(dir, "sw.js"), "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';");
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  const outside = path.join(dir, "outside.html");
  await fs.writeFile(outside, "en");
  const linked = await fs.symlink(outside, path.join(dir, "docs/en/index.html"))
    .then(() => true)
    .catch((error) => {
      if (process.platform === "win32" && ["EPERM", "EACCES"].includes(error?.code)) return false;
      throw error;
    });
  if (linked) {
    await assert.rejects(finalizeServiceWorker({ distDir: dir }), /required shell/);
    await fs.rm(path.join(dir, "docs/en/index.html"));
  }
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  await fs.writeFile(path.join(dir, "sw.js"), "quillframe-site-__QF_SITE_CACHE_VERSION__ quillframe-site-__QF_SITE_CACHE_VERSION__");
  await assert.rejects(finalizeServiceWorker({ distDir: dir }), /placeholder/);
  await fs.writeFile(path.join(dir, "sw.js"), "quillframe-site-deadbeefdeadbeef quillframe-site-cafebabecafebabe");
  await assert.rejects(finalizeServiceWorker({ distDir: dir }), /placeholder|literal/);
});

test("D2 metadata write failure is recoverable on a later unchanged rerun", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-recover-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  await fs.writeFile(path.join(dir, "sw.js"), "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';");
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  let calls = 0;
  await assert.rejects(finalizeServiceWorker({ distDir: dir, atomicWriter: async (file, contents) => { calls += 1; if (calls === 2) throw new Error("metadata write failed"); await fs.writeFile(file, contents); } }), /metadata write failed/);
  assert.equal((await fs.readdir(dir)).some((name) => name.includes(".tmp-")), false);
  const recovered = await finalizeServiceWorker({ distDir: dir });
  const metadata = JSON.parse(await fs.readFile(path.join(dir, "generated/quillframe-site-service-worker.json"), "utf8"));
  assert.deepEqual(metadata, recovered);
  assert.equal(metadata.cache_name, recovered.cache_name);
  assert.deepEqual(metadata.source_files, [...metadata.source_files].sort());
});

test("D2 failed forward publication rolls back original sw and absent metadata", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-rollback-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  const originalSw = "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';";
  await fs.writeFile(path.join(dir, "sw.js"), originalSw);
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  let writes = 0;
  await assert.rejects(finalizeServiceWorker({ distDir: dir, atomicWriter: async (file, contents) => { writes += 1; await atomicWrite(file, contents); if (writes === 2) throw new Error("forward metadata failure"); } }), /forward metadata failure/);
  assert.equal(await fs.readFile(path.join(dir, "sw.js"), "utf8"), originalSw);
  await assert.rejects(fs.access(path.join(dir, "generated/quillframe-site-service-worker.json")));
  assert.equal((await fs.readdir(dir, { recursive: true })).some((name) => String(name).includes(".tmp-")), false);
  const recovered = await finalizeServiceWorker({ distDir: dir });
  const metadata = JSON.parse(await fs.readFile(path.join(dir, "generated/quillframe-site-service-worker.json"), "utf8"));
  assert.deepEqual(metadata, recovered);
});

test("D2 rollback failure is an AggregateError with fail-closed observable state", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "qf-sw-rollback-fail-"));
  await fs.mkdir(path.join(dir, "docs/en"), { recursive: true });
  const originalSw = "const CACHE='quillframe-site-__QF_SITE_CACHE_VERSION__';";
  await fs.writeFile(path.join(dir, "sw.js"), originalSw);
  await fs.writeFile(path.join(dir, "docs/index.html"), "cn");
  await fs.writeFile(path.join(dir, "docs/en/index.html"), "en");
  let forwardWrites = 0;
  const primary = new Error("forward metadata failure");
  const rollback = new Error("rollback sw failure");
  await assert.rejects(
    finalizeServiceWorker({
      distDir: dir,
      atomicWriter: async (file, contents) => {
        forwardWrites += 1;
        await atomicWrite(file, contents);
        if (forwardWrites === 2) throw primary;
      },
      rollbackWriter: async () => { throw rollback; },
    }),
    (error) => {
      assert.equal(error instanceof AggregateError, true);
      assert.equal(error.message, "service-worker publication failed and rollback failed");
      assert.deepEqual(error.errors, [primary, rollback]);
      return true;
    },
  );
  const observableSw = await fs.readFile(path.join(dir, "sw.js"), "utf8");
  assert.doesNotMatch(observableSw, /__QF_SITE_CACHE_VERSION__/);
  assert.match(observableSw, /quillframe-site-[0-9a-f]{16}/);
  const observableMetadata = JSON.parse(await fs.readFile(path.join(dir, "generated/quillframe-site-service-worker.json"), "utf8"));
  assert.equal(observableMetadata.authority, false);
  assert.equal((await fs.readdir(dir, { recursive: true })).some((name) => String(name).includes(".tmp-")), false);
});

const CACHE = "quillframe-site-__QF_SITE_CACHE_VERSION__";
const REQUIRED_SHELLS = ["/docs/", "/docs/en/"];

function sameOrigin(request) { return new URL(request.url).origin === self.location.origin; }
function isApiPath(pathname) { return pathname === "/api" || pathname.startsWith("/api/"); }
function docsShellPath(pathname) {
  if (pathname === "/docs" || pathname === "/docs/") return "/docs/";
  if (pathname === "/docs/en" || pathname === "/docs/en/" || pathname.startsWith("/docs/en/")) return "/docs/en/";
  if (pathname.startsWith("/docs/")) {
    const firstSegment = pathname.slice("/docs/".length).split("/", 1)[0];
    if (firstSegment.startsWith("en") || firstSegment.startsWith("zh-CN")) return null;
    return "/docs/";
  }
  return null;
}
function isNavigation(request) { return request.mode === "navigate"; }
async function cacheRequest(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) await cache.put(request, response.clone());
  return response;
}
async function offlineFallback(request, error) {
  if (!isNavigation(request)) throw error;
  const shellPath = docsShellPath(new URL(request.url).pathname);
  if (!shellPath) throw error;
  const cache = await caches.open(CACHE);
  const shell = await cache.match(new Request(new URL(shellPath, self.location.origin).href));
  if (shell) return shell;
  throw error;
}

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    for (const shell of REQUIRED_SHELLS) await cache.add(shell);
    await self.skipWaiting();
  })());
});
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith("quillframe-site-") && key !== CACHE).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || !sameOrigin(request)) return;
  if (isApiPath(new URL(request.url).pathname)) return;
  event.respondWith(cacheRequest(request).catch((error) => offlineFallback(request, error)));
});

import type { CloudEnv, FetchBinding } from "./platform.js";
import { SecurityError, safeJson, securityHeaders } from "./security.js";

const HOSTED_META_NAME = "quillframe-studio-hosted-endpoint";
const HOSTED_META_SLOT = `<meta name="${HOSTED_META_NAME}" content="" />`;
const STUDIO_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; manifest-src 'self'; worker-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";

export function assertPublicOrigin(publicOrigin: string): void {
  let parsed: URL;
  try { parsed = new URL(publicOrigin); }
  catch { throw new SecurityError("public_origin_invalid", "PUBLIC_ORIGIN must be a canonical HTTPS origin"); }
  if (parsed.protocol !== "https:" || parsed.origin !== publicOrigin) {
    throw new SecurityError("public_origin_invalid", "PUBLIC_ORIGIN must be a canonical HTTPS origin");
  }
}

export function isApiPath(pathname: string): boolean {
  if (/^\/api(?:\/|$)/.test(pathname)) return true;
  try { return /^\/api(?:[/\\]|$)/.test(decodeURIComponent(pathname)); }
  catch { return false; }
}

export function withoutCaching(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const name of ["cache-control", "cdn-cache-control", "cloudflare-cdn-cache-control"]) headers.set(name, "no-store");
  for (const name of ["etag", "last-modified", "expires"]) headers.delete(name);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function notFound(): Response {
  return safeJson({ schema: "quillframe_cloud_error_v1", code: "not_found", authority: false }, { status: 404 });
}

function invalidShell(): Response {
  return safeJson({ schema: "quillframe_cloud_error_v1", code: "studio_shell_invalid", authority: false }, { status: 503 });
}

function safeAssetHeaders(response: Response): Headers {
  const headers = new Headers(response.headers);
  for (const [name, value] of securityHeaders()) headers.set(name, value);
  headers.delete("set-cookie");
  return headers;
}

function assetRequest(request: Request, pathname: string, index = false): Request {
  const url = new URL(request.url);
  url.pathname = pathname;
  url.search = "";
  const headers = new Headers();
  // Static delivery never receives session credentials or caller identity.
  if (!index) {
    for (const name of ["accept", "if-none-match", "if-modified-since", "range", "if-range"]) {
      const value = request.headers.get(name);
      if (value !== null) headers.set(name, value);
    }
  }
  return new Request(url.href, { method: index ? "GET" : request.method, headers });
}

function mayUseIndex(pathname: string): boolean {
  let decoded: string;
  try { decoded = decodeURIComponent(pathname); } catch { return false; }
  if (/^\/(?:assets|\.well-known)(?:\/|$)/.test(decoded) || decoded.includes("\\")) return false;
  return !decoded.slice(decoded.lastIndexOf("/") + 1).includes(".");
}

async function studioIndex(request: Request, publicOrigin: string, assets: FetchBinding): Promise<Response> {
  // Only this fixed, trusted asset may supply the transport configuration.
  const response = await assets.fetch(assetRequest(request, "/index.html", true));
  if (response.status === 404) return notFound();
  if (response.status !== 200 || !/^text\/html(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "")) return invalidShell();
  const html = await response.text();
  if (html.split(HOSTED_META_SLOT).length !== 2 || html.split(HOSTED_META_NAME).length !== 2) return invalidShell();
  const origin = publicOrigin.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const boundHtml = html.replace(HOSTED_META_SLOT, HOSTED_META_SLOT.replace('content=""', `content="${origin}"`));
  const headers = safeAssetHeaders(response);
  for (const name of ["content-length", "content-encoding", "content-range", "accept-ranges"]) headers.delete(name);
  headers.set("content-type", "text/html; charset=utf-8");
  headers.set("content-security-policy", STUDIO_CSP);
  return withoutCaching(new Response(boundHtml, { headers }));
}

export async function serveStudioAsset(request: Request, env: CloudEnv): Promise<Response | null> {
  const pathname = new URL(request.url).pathname;
  if (!env.ASSETS || isApiPath(pathname)) return null;
  if (request.method !== "GET" && request.method !== "HEAD") {
    return safeJson({ schema: "quillframe_cloud_error_v1", code: "method_not_allowed", authority: false }, { status: 405, headers: { allow: "GET, HEAD" } });
  }
  if (pathname === "/" || pathname === "/index.html") return studioIndex(request, env.PUBLIC_ORIGIN, env.ASSETS);
  const response = await env.ASSETS.fetch(assetRequest(request, pathname));
  if (response.status === 404) return mayUseIndex(pathname) ? studioIndex(request, env.PUBLIC_ORIGIN, env.ASSETS) : notFound();
  const secured = new Response(response.body, { status: response.status, statusText: response.statusText, headers: safeAssetHeaders(response) });
  // Other HTML assets remain inert and unbound, even if their bytes contain a slot.
  return /^text\/html(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "") ? withoutCaching(secured) : secured;
}

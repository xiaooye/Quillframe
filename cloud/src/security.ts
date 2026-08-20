export class SecurityError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

function cookie(name: string, value: string, attributes: string[]): string {
  if (!/^[A-Za-z0-9._~-]*$/.test(value)) throw new SecurityError("cookie_value_invalid", "cookie value is invalid");
  return [`${name}=${value}`, ...attributes].join("; ");
}

export const sessionCookie = (value: string, maxAge = 8 * 60 * 60): string => cookie("__Host-qf_session", value, ["Path=/", `Max-Age=${maxAge}`, "HttpOnly", "Secure", "SameSite=Lax"]);
export const authCookie = (value: string, maxAge = 10 * 60): string => cookie("__Host-qf_auth", value, ["Path=/", `Max-Age=${maxAge}`, "HttpOnly", "Secure", "SameSite=Lax"]);
export const csrfCookie = (value: string, maxAge = 8 * 60 * 60): string => cookie("__Host-qf_csrf", value, ["Path=/", `Max-Age=${maxAge}`, "Secure", "SameSite=Strict"]);
export const clearSessionCookie = (): string => cookie("__Host-qf_session", "", ["Path=/", "Max-Age=0", "HttpOnly", "Secure", "SameSite=Lax"]);
export const clearAuthCookie = (): string => cookie("__Host-qf_auth", "", ["Path=/", "Max-Age=0", "HttpOnly", "Secure", "SameSite=Lax"]);
export const clearCsrfCookie = (): string => cookie("__Host-qf_csrf", "", ["Path=/", "Max-Age=0", "Secure", "SameSite=Strict"]);

export function parseCookies(request: Request): Map<string, string> {
  const values = new Map<string, string>();
  for (const part of (request.headers.get("cookie") ?? "").split(";")) {
    const index = part.indexOf("=");
    if (index <= 0) continue;
    values.set(part.slice(0, index).trim(), part.slice(index + 1).trim());
  }
  return values;
}

export function assertRequestOrigin(request: Request, publicOrigin: string): void {
  if (new URL(request.url).origin !== publicOrigin) throw new SecurityError("host_origin_invalid", "request host is not the configured public origin");
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    const origin = request.headers.get("origin");
    if (origin !== publicOrigin) throw new SecurityError("request_origin_invalid", "request Origin does not match");
  }
}

export function securityHeaders(): Headers {
  return new Headers({
    "Content-Security-Policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self' https://api.workos.com",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
  });
}

export function withSecurityHeaders(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [key, value] of securityHeaders()) headers.set(key, value);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

export function safeJson(value: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("cache-control", "no-store");
  return withSecurityHeaders(new Response(JSON.stringify(value), { ...init, headers }));
}

export function safeError(error: unknown): Response {
  const code = typeof error === "object" && error && "code" in error && typeof error.code === "string" ? error.code : "cloud_request_failed";
  const status = code === "auth_state_invalid" ? 400 : code.startsWith("auth_") || code.startsWith("session_") ? 401 : code.includes("origin") || code.includes("csrf") || code.includes("forbidden") ? 403 : 400;
  return safeJson({ schema: "quillframe_cloud_error_v1", code, authority: false }, { status });
}

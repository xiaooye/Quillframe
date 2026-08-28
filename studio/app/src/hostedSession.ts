import { hostedCsrfToken, hostedEndpoint } from "./bridge";

export interface HostedSessionProjection {
  schema: "quillframe_cloud_session_projection_v1";
  workspace_id: string;
  workspace_handle: string;
  session_id: string;
  workos_session_id?: string;
  idle_expires_at: number;
  absolute_expires_at: number;
  authority: false;
}

function endpoint(): string {
  const origin = hostedEndpoint();
  if (!origin) throw new Error("Hosted session is not bound");
  return origin;
}

export function hostedSignInUrl(): string {
  return `${endpoint()}/api/auth/authorize?return_to=%2Fstart`;
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function boundedId(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(value);
}

async function sessionResponse(url: string, init: RequestInit, failure: string): Promise<Response> {
  try {
    return await fetch(url, { ...init, credentials: "same-origin", cache: "no-store", redirect: "error" });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new Error(failure);
  }
}

async function responseJson(response: Response, failure: string): Promise<unknown> {
  try {
    if (!response.ok || response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase() !== "application/json") {
      throw new Error(failure);
    }
    const text = await response.text();
    if (text.length > 16_384) throw new Error(failure);
    return JSON.parse(text);
  } catch {
    // Neither an HTML fallback nor an upstream message is authentication evidence.
    throw new Error(failure);
  }
}

export async function loadHostedSession(signal?: AbortSignal): Promise<HostedSessionProjection | null> {
  const failure = "Hosted session could not be verified";
  const response = await sessionResponse(`${endpoint()}/api/session`, { method: "GET", headers: { Accept: "application/json" }, signal }, failure);
  if (response.status === 401) return null;
  const value = await responseJson(response, failure);
  const allowed = ["schema", "workspace_id", "workspace_handle", "session_id", "workos_session_id", "idle_expires_at", "absolute_expires_at", "authority"];
  const now = Date.now();
  if (!record(value) || Object.keys(value).some((key) => !allowed.includes(key)) ||
    value.schema !== "quillframe_cloud_session_projection_v1" || value.authority !== false ||
    typeof value.workspace_handle !== "string" || !/^[a-f0-9]{24}$/.test(value.workspace_handle) ||
    value.workspace_id !== `workspace_${value.workspace_handle}` || !boundedId(value.session_id) ||
    value.workos_session_id !== undefined && !boundedId(value.workos_session_id) ||
    !Number.isSafeInteger(value.idle_expires_at) || (value.idle_expires_at as number) <= now ||
    !Number.isSafeInteger(value.absolute_expires_at) || (value.absolute_expires_at as number) <= now
  ) throw new Error(failure);
  hostedCsrfToken();
  return value as unknown as HostedSessionProjection;
}

function verifiedLogoutUrl(value: unknown, origin: string): string | null {
  if (value === null) return null;
  if (typeof value !== "string") throw new Error("invalid logout URL");
  const url = new URL(value);
  const parameters = [...url.searchParams.keys()];
  const returnTo = new URL(url.searchParams.get("return_to") ?? "");
  if (url.origin !== "https://api.workos.com" || url.username || url.password || url.hash ||
    url.pathname !== "/user_management/sessions/logout" || parameters.length !== 2 ||
    url.searchParams.getAll("session_id").length !== 1 || url.searchParams.getAll("return_to").length !== 1 ||
    !boundedId(url.searchParams.get("session_id")) || returnTo.origin !== origin ||
    returnTo.username || returnTo.password || returnTo.pathname !== "/" || returnTo.search || returnTo.hash
  ) throw new Error("invalid logout URL");
  return url.href;
}

/** A null result also covers a session that the server has already expired. */
export async function logoutHostedSession(signal?: AbortSignal): Promise<string | null> {
  const origin = endpoint();
  const csrf = hostedCsrfToken();
  const failure = "Hosted logout could not be verified";
  const response = await sessionResponse(`${origin}/api/auth/logout`, {
    method: "POST", headers: { Accept: "application/json", "X-Qf-Csrf": csrf }, signal,
  }, failure);
  if (response.status === 401) return null;
  const value = await responseJson(response, failure);
  try {
    if (!record(value) || Object.keys(value).sort().join(",") !== "authority,destroyed,schema,workos_logout_url" ||
      value.schema !== "quillframe_cloud_logout_receipt_v1" || value.destroyed !== true || value.authority !== false
    ) throw new Error(failure);
    return verifiedLogoutUrl(value.workos_logout_url, origin);
  } catch {
    throw new Error(failure);
  }
}

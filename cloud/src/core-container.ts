import type { FetchBinding, RpcNamespace, SessionProjection } from "./platform.js";
import { canonicalBridgeBody, deriveProofProjectId, parseCanonicalJsonBytes, type CoreProofKeyMap, validateBridgeRequest, verifyCoreProof } from "./core-provenance.js";
import { MAX_NATIVE_BACKUP_BODY } from "./core-limits.js";
import { sha256Hex } from "./crypto.js";

export { MAX_NATIVE_BACKUP_BODY } from "./core-limits.js";

const SAFE_FORWARD_HEADERS = ["content-type", "accept", "idempotency-key"] as const;
export const MAX_CORE_BODY = 4 * 1024 * 1024;
export const MAX_ENDPOINT_VALIDATION_BODY = 16 * 1024;

export class CoreBoundaryError extends Error {
  constructor(public readonly code: string, message = "core boundary request is invalid") { super(message); }
}

function fail(code: string): never { throw new CoreBoundaryError(code); }

function nativeQuery(source: URL): { operation: "project.upload" | "project.read"; projectId: string; versionId?: string; objectKeySha256?: string; pointerVersion?: number } {
  const entries = [...source.searchParams.entries()];
  const counts = new Map<string, number>();
  for (const [key] of entries) counts.set(key, (counts.get(key) ?? 0) + 1);
  const operation = source.searchParams.get("operation");
  const projectId = source.searchParams.get("project_id");
  if (typeof operation !== "string" || typeof projectId !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(projectId) || counts.get("operation") !== 1 || counts.get("project_id") !== 1) fail("container_native_query_invalid");
  if (operation === "project.upload") {
    if (entries.length !== 2 || [...counts.keys()].some((key) => key !== "operation" && key !== "project_id")) fail("container_native_query_invalid");
    return { operation, projectId };
  }
  if (operation !== "project.read" || entries.length !== 5 || [...counts.keys()].some((key) => !["operation", "project_id", "version_id", "object_key_sha256", "pointer_version"].includes(key)) || counts.get("version_id") !== 1 || counts.get("object_key_sha256") !== 1 || counts.get("pointer_version") !== 1) fail("container_native_query_invalid");
  const versionId = source.searchParams.get("version_id") ?? "";
  const objectKeySha256 = source.searchParams.get("object_key_sha256") ?? "";
  const pointerRaw = source.searchParams.get("pointer_version") ?? "";
  if (!/^sha256:[0-9a-f]{64}$/.test(versionId) || !/^sha256:[0-9a-f]{64}$/.test(objectKeySha256) || !/^\d{1,10}$/.test(pointerRaw) || Number(pointerRaw) < 1 || Number(pointerRaw) > 2 ** 31) fail("container_native_query_invalid");
  return { operation, projectId, versionId, objectKeySha256, pointerVersion: Number(pointerRaw) };
}

export function safeCoreForwardHeaders(request: Request, proof: string): Headers {
  const headers = new Headers({ "x-qf-core-proof": proof });
  for (const name of SAFE_FORWARD_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  return headers;
}

export function coreForwardUrl(sourceUrl: string): string {
  const source = new URL(sourceUrl);
  const internal = new URL("http://core.internal");
  internal.pathname = source.pathname.replace(/^\/api\/core/, "") || "/bridge";
  internal.search = source.search;
  return internal.href;
}

export async function forwardToCore(
  namespace: RpcNamespace<FetchBinding>,
  request: Request,
  session: SessionProjection,
  proof: string,
  body: Uint8Array,
  targetPathAndSearch?: string,
): Promise<Response> {
  const container = namespace.getByName(session.workspace_handle);
  const headers = safeCoreForwardHeaders(request, proof);
  headers.set("content-length", String(body.byteLength));
  return container.fetch(new Request(targetPathAndSearch ? new URL(targetPathAndSearch, "http://core.internal").href : coreForwardUrl(request.url), {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : new Uint8Array(body),
  }));
}

export async function readCoreBody(request: Request, limit = MAX_CORE_BODY): Promise<Uint8Array> {
  const declared = request.headers.get("content-length");
  if (request.headers.has("transfer-encoding")) fail("core_transfer_encoding_forbidden");
  if (declared === null || !/^\d+$/.test(declared)) fail("core_body_length_invalid");
  const expected = Number(declared);
  if (!Number.isSafeInteger(expected) || expected > limit) fail("core_body_size_invalid");
  if (expected === 0 || !request.body) fail("core_body_length_invalid");
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = []; let total = 0;
  try {
    while (true) {
      let part: ReadableStreamReadResult<Uint8Array>;
      try { part = await reader.read(); } catch { fail("core_body_read_failed"); }
      if (part.done) break;
      if (!part.value || part.value.byteLength === 0) fail("core_body_read_failed");
      total += part.value.byteLength;
      if (total > expected) { try { await reader.cancel("core body overrun"); } catch { /* preserve typed boundary error */ } fail("core_body_overrun"); }
      if (total > limit) { try { await reader.cancel("core body too large"); } catch { /* preserve typed boundary error */ } fail("core_body_size_invalid"); }
      chunks.push(part.value);
    }
  } catch (error) { if (error instanceof CoreBoundaryError) throw error; fail("core_body_read_failed"); }
  finally { reader.releaseLock(); }
  const body = new Uint8Array(total); let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  if (total !== expected) fail("core_body_short");
  return body;
}

export async function readBoundedJsonBody(request: Request, limit = MAX_ENDPOINT_VALIDATION_BODY): Promise<unknown> {
  if (request.headers.get("content-type") !== "application/json") fail("json_content_type_invalid");
  let body: Uint8Array;
  try { body = await readCoreBody(request, limit); }
  catch { fail("json_body_invalid"); }
  try { return parseCanonicalJsonBytes(body, "body", limit); }
  catch { fail("json_body_invalid"); }
}

export async function validateCoreContainerRequest(
  request: Request,
  proofKeys: CoreProofKeyMap,
  expectedWorkspaceId: string,
  now = Date.now(),
): Promise<{ body: Uint8Array; proof: string }> {
  const source = new URL(request.url);
  const forbiddenHeaders = [
    "x-qf-workspace-id", "x-qf-session-id", "x-qf-project-id", "x-qf-identity", "x-qf-authority", "x-qf-chapter-scope",
    "x-quillframe-internal", "x-quillframe-workspace-id", "x-quillframe-session-id", "x-quillframe-project-id", "x-quillframe-identity", "x-quillframe-authority", "x-quillframe-chapter-scope",
    "authorization", "cookie",
  ];
  const nativeBackup = source.pathname === "/native/project-backup/verify";
  if (request.method !== "POST" || !["/bridge", "/native/project-backup/verify"].includes(source.pathname) || forbiddenHeaders.some((name) => request.headers.has(name))) fail("container_boundary_forbidden");
  if (nativeBackup && request.headers.get("content-type") !== "application/zip") fail("container_content_type_invalid");
  const proof = request.headers.get("x-qf-core-proof") ?? "";
  const parts = proof.split(".");
  const key = parts.length === 4 ? proofKeys instanceof Map ? proofKeys.get(parts[1]) : (proofKeys as Readonly<Record<string, Uint8Array>>)[parts[1]] : undefined;
  if (!key) fail("container_boundary_forbidden");
  try {
    const body = await readCoreBody(request, nativeBackup ? MAX_NATIVE_BACKUP_BODY : MAX_CORE_BODY);
    const claims = await verifyCoreProof(proof, { keyId: parts[1], key, now, method: request.method, path: `${source.pathname}${source.search}`, body });
    if (claims.workspace_id !== expectedWorkspaceId) throw new Error("workspace binding invalid");
    if (nativeBackup) {
      const query = nativeQuery(source);
      if (claims.project_id !== query.projectId) throw new Error("native project binding invalid");
      if (query.operation === "project.read" && query.versionId !== `sha256:${await sha256Hex(body)}`) throw new Error("native version binding invalid");
    } else {
      const parsed = canonicalBridgeBody(body);
      const { operation } = validateBridgeRequest(parsed.value);
      if (deriveProofProjectId(operation, parsed.value) !== claims.project_id) throw new Error("operation binding invalid");
    }
    if (claims.scope !== "novel") throw new Error("chapter scope invalid");
    return { body, proof };
  } catch (error) {
    if (error instanceof CoreBoundaryError && error.code === "container_boundary_forbidden") throw error;
    fail("container_boundary_invalid");
  }
}

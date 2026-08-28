import { BoundEndpointProbe, CloudflareDnsResolver, validateHostedEndpoint } from "./endpoint-validator.js";
import { forwardToCore, readBoundedJsonBody, readCoreBody, MAX_ENDPOINT_VALIDATION_BODY } from "./core-container.js";
import { EncryptedProjectStore, PROJECT_BUNDLE_TRANSPORT_LIMIT, assertNativeBackupReceipt } from "./project-store.js";
import {
  assertRequestOrigin,
  authCookie,
  clearAuthCookie,
  clearCsrfCookie,
  clearSessionCookie,
  csrfCookie,
  parseCookies,
  safeError,
  safeJson,
  sessionCookie,
  withSecurityHeaders,
} from "./security.js";
import type { CloudEnv, SessionProjection, WorkspaceCoordinatorStub } from "./platform.js";
import { WorkOSClient } from "./workos.js";
import { workspaceHandleForIdentity } from "./workspace-coordinator.js";
import { canonicalBridgeBody, canonicalJsonBytes, deriveProofProjectId, parseCanonicalJsonBytes, signCoreProof, strictProofKey, validateBridgeRequest } from "./core-provenance.js";
import { randomToken, sha256Hex } from "./crypto.js";
import { assertPublicOrigin, isApiPath, serveStudioAsset, withoutCaching } from "./studio-assets.js";

const AUTH_COORDINATOR = "__auth_transactions__";
const FORBIDDEN_CORE_HEADERS = [
  "x-qf-core-proof", "x-qf-core-proof-alias", "x-qf-workspace-id", "x-qf-session-id", "x-qf-project-id", "x-qf-identity", "x-qf-authority", "x-qf-chapter-scope",
  "x-quillframe-internal", "x-quillframe-workspace-id", "x-quillframe-session-id", "x-quillframe-project-id", "x-quillframe-identity", "x-quillframe-authority", "x-quillframe-chapter-scope",
  "authorization",
];
const MAX_CORE_RECEIPT_BYTES = 64 * 1024;
const OPERATION_ID_RE = /^[A-Za-z0-9._:-]{1,128}$/;

function explicitAction(request: Request, expected: "project.upload" | "project.delete" | "project.gc"): string {
  for (const name of FORBIDDEN_CORE_HEADERS) if (request.headers.has(name)) throw Object.assign(new Error("caller proof or identity headers are forbidden"), { code: "core_header_forbidden" });
  if (request.headers.has("x-qf-explicit-upload")) throw Object.assign(new Error("legacy upload action header is forbidden"), { code: "explicit_action_forbidden" });
  const value = request.headers.get("x-qf-explicit-action");
  if (value !== expected) throw Object.assign(new Error("explicit project action is required"), { code: "explicit_action_required" });
  return value;
}

function rejectCallerHeaders(request: Request): void {
  for (const name of FORBIDDEN_CORE_HEADERS) if (request.headers.has(name)) throw Object.assign(new Error("caller proof or identity headers are forbidden"), { code: "core_header_forbidden" });
  if (request.headers.has("x-qf-explicit-action") || request.headers.has("x-qf-explicit-upload")) throw Object.assign(new Error("caller-only action headers are forbidden"), { code: "explicit_action_forbidden" });
}

function operationId(request: Request): string {
  const value = request.headers.get("idempotency-key") ?? "";
  if (!OPERATION_ID_RE.test(value)) throw Object.assign(new Error("idempotency key is invalid"), { code: "idempotency_key_invalid" });
  return value;
}

async function boundedCoreReceipt(response: Response): Promise<unknown> {
  if (!response.ok) throw Object.assign(new Error("Core verification failed"), { code: "core_verification_failed" });
  if (response.headers.has("transfer-encoding")) throw Object.assign(new Error("Core response framing is invalid"), { code: "core_response_invalid" });
  const declared = response.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > MAX_CORE_RECEIPT_BYTES)) throw Object.assign(new Error("Core response framing is invalid"), { code: "core_response_invalid" });
  if (!response.body) throw Object.assign(new Error("Core response body is missing"), { code: "core_response_invalid" });
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      if (!part.value || part.value.byteLength === 0) throw Object.assign(new Error("Core response framing is invalid"), { code: "core_response_invalid" });
      total += part.value.byteLength;
      if (total > MAX_CORE_RECEIPT_BYTES) throw Object.assign(new Error("Core response is too large"), { code: "core_response_invalid" });
      chunks.push(part.value);
    }
  } catch (error) {
    try { await reader.cancel(); } catch { /* preserve stable boundary error */ }
    if (error && typeof error === "object" && "code" in error) throw error;
    throw Object.assign(new Error("Core response read failed"), { code: "core_response_invalid" });
  } finally { reader.releaseLock(); }
  if (declared !== null && Number(declared) !== total) throw Object.assign(new Error("Core response framing is invalid"), { code: "core_response_invalid" });
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  if (!/^application\/json(?:;\s*charset=utf-8)?$/.test(contentType)) throw Object.assign(new Error("Core response content type is invalid"), { code: "core_response_invalid" });
  try { return parseCanonicalJsonBytes(bytes, "body", MAX_CORE_RECEIPT_BYTES); } catch { throw Object.assign(new Error("Core response is not canonical JSON"), { code: "core_response_invalid" }); }
}

function projectKeyRing(env: CloudEnv): { current_key_id?: string; previous_key_id?: string; previous_key_base64?: string } {
  return { current_key_id: env.PROJECT_BUNDLE_KEY_ID, previous_key_id: env.PROJECT_BUNDLE_PREVIOUS_KEY_ID, previous_key_base64: env.PROJECT_BUNDLE_PREVIOUS_KEY_B64 };
}

function coreProofKey(env: CloudEnv): Uint8Array {
  if (!/^[A-Za-z0-9._:-]{1,128}$/.test(env.CORE_PROOF_KEY_ID) || (env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined && !/^[A-Za-z0-9._:-]{1,128}$/.test(env.CORE_PROOF_PREVIOUS_KEY_ID))) throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" });
  let key: Uint8Array;
  try { key = strictProofKey(env.CORE_PROOF_KEY_B64); if (env.CORE_PROOF_PREVIOUS_KEY_B64 !== undefined) strictProofKey(env.CORE_PROOF_PREVIOUS_KEY_B64, "previous proof key"); } catch { throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" }); }
  if (env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined && env.CORE_PROOF_PREVIOUS_KEY_ID === env.CORE_PROOF_KEY_ID || key.byteLength !== 32 || ((env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined) !== (env.CORE_PROOF_PREVIOUS_KEY_B64 !== undefined))) throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" });
  return key;
}

function redirect(location: string, cookies: string[] = []): Response {
  const headers = new Headers({ location, "cache-control": "no-store" });
  for (const value of cookies) headers.append("set-cookie", value);
  return withSecurityHeaders(new Response(null, { status: 302, headers }));
}

function cookieSession(request: Request): { token: string; handle: string } {
  const token = parseCookies(request).get("__Host-qf_session") ?? "";
  const [handle, secret, ...rest] = token.split(".");
  if (!/^[a-f0-9]{24}$/.test(handle ?? "") || !/^[A-Za-z0-9_-]{43}$/.test(secret ?? "") || rest.length) throw Object.assign(new Error("session cookie is invalid"), { code: "session_invalid" });
  return { token, handle };
}

async function authenticate(request: Request, env: CloudEnv, csrf = false): Promise<{ session: SessionProjection; coordinator: WorkspaceCoordinatorStub; token: string }> {
  const { token, handle } = cookieSession(request);
  const coordinator = env.WORKSPACE_COORDINATOR.getByName(handle);
  let csrfToken: string | undefined;
  if (csrf) {
    const cookies = parseCookies(request);
    const header = request.headers.get("x-qf-csrf") ?? "";
    const cookieValue = cookies.get("__Host-qf_csrf") ?? "";
    if (!header || header !== cookieValue) throw Object.assign(new Error("CSRF token is invalid"), { code: "csrf_invalid" });
    csrfToken = header;
  }
  return { session: await coordinator.validateSession(token, csrfToken), coordinator, token };
}

function workos(env: CloudEnv): WorkOSClient {
  return new WorkOSClient(
    { clientId: env.WORKOS_CLIENT_ID, apiKey: env.WORKOS_API_KEY, redirectUri: env.WORKOS_REDIRECT_URI },
    env.fetch ?? globalThis.fetch,
  );
}

async function handleAuthorize(request: Request, env: CloudEnv): Promise<Response> {
  const returnTo = new URL(request.url).searchParams.get("return_to") ?? "/studio";
  const transaction = await env.WORKSPACE_COORDINATOR.getByName(AUTH_COORDINATOR).beginAuth(returnTo);
  return redirect(workos(env).authorizationUrl({ state: transaction.state, codeChallenge: transaction.code_challenge }).href, [authCookie(transaction.transaction_id)]);
}

async function handleCallback(request: Request, env: CloudEnv): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code") ?? "";
  const state = url.searchParams.get("state") ?? "";
  const transactionId = parseCookies(request).get("__Host-qf_auth") ?? "";
  const transaction = await env.WORKSPACE_COORDINATOR.getByName(AUTH_COORDINATOR).consumeAuth(transactionId, state);
  const authenticated = await workos(env).authenticateCode({
    code,
    codeVerifier: transaction.code_verifier,
    ipAddress: request.headers.get("cf-connecting-ip") ?? undefined,
    userAgent: request.headers.get("user-agent") ?? undefined,
  });
  const handle = await workspaceHandleForIdentity(authenticated.user.id);
  const coordinator = env.WORKSPACE_COORDINATOR.getByName(handle);
  const session = await coordinator.createSession({ identity_id: authenticated.user.id, workos_session_id: authenticated.session_id });
  const vault = env.SESSION_VAULT.getByName(handle);
  try {
    await vault.leaseSecret({ workspace_id: session.workspace_id, session_id: session.session_id, purpose: "workos_access", secret: authenticated.access_token });
    await vault.leaseSecret({ workspace_id: session.workspace_id, session_id: session.session_id, purpose: "workos_refresh", secret: authenticated.refresh_token });
  } catch (error) {
    await vault.destroySession({ workspace_id: session.workspace_id, session_id: session.session_id });
    await coordinator.destroySession(session.cookie_token);
    throw error;
  }
  return redirect(new URL(transaction.return_to, env.PUBLIC_ORIGIN).href, [
    sessionCookie(session.cookie_token),
    csrfCookie(session.csrf_token),
    clearAuthCookie(),
  ]);
}

async function handleLogout(request: Request, env: CloudEnv): Promise<Response> {
  const authenticated = await authenticate(request, env, true);
  await env.SESSION_VAULT.getByName(authenticated.session.workspace_handle).destroySession({ workspace_id: authenticated.session.workspace_id, session_id: authenticated.session.session_id });
  await authenticated.coordinator.destroySession(authenticated.token);
  return safeJson({ schema: "quillframe_cloud_logout_receipt_v1", destroyed: true, workos_logout_url: authenticated.session.workos_session_id ? workos(env).logoutUrl(authenticated.session.workos_session_id, env.PUBLIC_ORIGIN).href : null, authority: false }, {
    headers: [["set-cookie", clearSessionCookie()], ["set-cookie", clearCsrfCookie()]],
  });
}

async function handleUpload(request: Request, env: CloudEnv, projectId: string): Promise<Response> {
  const authenticated = await authenticate(request, env, true);
  explicitAction(request, "project.upload");
  const opId = operationId(request);
  const pointer = await authenticated.coordinator.readProjectPointer(projectId);
  if (pointer && (pointer.workspace_id !== authenticated.session.workspace_id || pointer.project_id !== projectId)) throw Object.assign(new Error("project workspace binding is invalid"), { code: "workspace_binding_conflict" });
  const bundle = await readCoreBody(request, PROJECT_BUNDLE_TRANSPORT_LIMIT);
  const bodyFingerprint = `sha256:${await sha256Hex(bundle)}` as `sha256:${string}`;
  const expectedPointerVersion = pointer?.state === "active" && pointer.version_id === bodyFingerprint && pointer.pointer_version > 0 ? pointer.pointer_version - 1 : pointer?.pointer_version ?? 0;
  const now = Date.now();
  const nonce = randomToken(24);
  const key = coreProofKey(env);
  const proofPath = `/native/project-backup/verify?operation=project.upload&project_id=${encodeURIComponent(projectId)}`;
  const proof = await signCoreProof({ claims: {
    schema: "quillframe_core_proof_v1", key_id: env.CORE_PROOF_KEY_ID, method: request.method, path: proofPath,
    body_sha256: bodyFingerprint, workspace_id: authenticated.session.workspace_id, session_id: authenticated.session.session_id,
    project_id: projectId, scope: "novel", issued_at: now, expires_at: now + 30_000, nonce,
  }, key });
  await authenticated.coordinator.consumeCoreNonce({ session_id: authenticated.session.session_id, project_id: projectId, nonce, proof_digest: `sha256:${await sha256Hex(proof)}`, issued_at: now, expires_at: now + 30_000 });
  const coreResponse = await forwardToCore(env.CORE_CONTAINER, request, authenticated.session, proof, bundle, proofPath);
  const verification = await boundedCoreReceipt(coreResponse);
  assertNativeBackupReceipt(verification);
  if (verification.project_id !== projectId || verification.body_fingerprint !== bodyFingerprint || verification.bundle_fingerprint !== bodyFingerprint || verification.byte_size !== bundle.byteLength) throw Object.assign(new Error("Core verification receipt does not bind the uploaded bytes"), { code: "core_verification_mismatch" });
  const store = new EncryptedProjectStore(env.PROJECT_BUNDLES, env.PROJECT_BUNDLE_KEY_B64, projectKeyRing(env));
  const stored = await store.uploadVerified({ workspace_id: authenticated.session.workspace_id, project_id: projectId, bundle, verification });
  const inputFingerprint = `sha256:${await sha256Hex(canonicalJsonBytes({ action: "project.upload", operation_id: opId, workspace_id: authenticated.session.workspace_id, project_id: projectId, expected_pointer_version: expectedPointerVersion, version_id: stored.version_id, object_key: stored.object_key, plaintext_fingerprint: stored.plaintext_fingerprint, byte_size: stored.byte_size }))}` as `sha256:${string}`;
  const prepared = await authenticated.coordinator.prepareProjectVersion({ operation_id: opId, input_fingerprint: inputFingerprint, workspace_id: authenticated.session.workspace_id, project_id: projectId, expected_pointer_version: expectedPointerVersion, version_id: stored.version_id, object_key: stored.object_key, plaintext_fingerprint: stored.plaintext_fingerprint, byte_size: stored.byte_size });
  const next = await authenticated.coordinator.casProjectPointer({ project_id: projectId, expected_pointer_version: expectedPointerVersion, next: { workspace_id: authenticated.session.workspace_id, project_id: projectId, state: "active", version_id: stored.version_id, object_key: stored.object_key, plaintext_fingerprint: stored.plaintext_fingerprint, authority: false } });
  return safeJson({ schema: "quillframe_cloud_project_upload_receipt_v2", operation_id: opId, workspace_id: authenticated.session.workspace_id, project_id: projectId, version_id: stored.version_id, object_key: stored.object_key, body_fingerprint: stored.body_fingerprint, byte_size: stored.byte_size, pointer_version: next.pointer_version, preparation_status: prepared.status, authority: false }, { status: 201 });
}

function nativeReadPath(projectId: string, versionId: string, objectKeySha256: string, pointerVersion: number): string {
  return `/native/project-backup/verify?operation=project.read&project_id=${encodeURIComponent(projectId)}&version_id=${encodeURIComponent(versionId)}&object_key_sha256=${encodeURIComponent(objectKeySha256)}&pointer_version=${pointerVersion}`;
}

async function handleReadProject(request: Request, env: CloudEnv, projectId: string): Promise<Response> {
  const authenticated = await authenticate(request, env);
  rejectCallerHeaders(request);
  const pointer = await authenticated.coordinator.readProjectPointer(projectId);
  if (!pointer || pointer.state !== "active" || pointer.workspace_id !== authenticated.session.workspace_id || pointer.project_id !== projectId || !pointer.version_id || !pointer.object_key || !pointer.plaintext_fingerprint) throw Object.assign(new Error("project pointer is unavailable"), { code: "project_pointer_unavailable" });
  const store = new EncryptedProjectStore(env.PROJECT_BUNDLES, env.PROJECT_BUNDLE_KEY_B64, projectKeyRing(env));
  const bundle = await store.readVerified(authenticated.session.workspace_id, projectId, pointer);
  const bodyFingerprint = `sha256:${await sha256Hex(bundle)}` as `sha256:${string}`;
  if (bodyFingerprint !== pointer.version_id || bodyFingerprint !== pointer.plaintext_fingerprint) throw Object.assign(new Error("project pointer bytes do not match"), { code: "project_bundle_integrity_failed" });
  const objectKeySha256 = `sha256:${await sha256Hex(pointer.object_key)}` as `sha256:${string}`;
  const proofPath = nativeReadPath(projectId, pointer.version_id, objectKeySha256, pointer.pointer_version);
  const now = Date.now();
  const nonce = randomToken(24);
  const proof = await signCoreProof({ claims: {
    schema: "quillframe_core_proof_v1", key_id: env.CORE_PROOF_KEY_ID, method: "POST", path: proofPath,
    body_sha256: bodyFingerprint, workspace_id: authenticated.session.workspace_id, session_id: authenticated.session.session_id,
    project_id: projectId, scope: "novel", issued_at: now, expires_at: now + 30_000, nonce,
  }, key: coreProofKey(env) });
  await authenticated.coordinator.consumeCoreNonce({ session_id: authenticated.session.session_id, project_id: projectId, nonce, proof_digest: `sha256:${await sha256Hex(proof)}`, issued_at: now, expires_at: now + 30_000 });
  const coreRequest = new Request(`https://studio.example${proofPath}`, { method: "POST", headers: { "content-type": "application/zip", "content-length": String(bundle.byteLength) }, body: new Uint8Array(bundle) });
  const coreResponse = await forwardToCore(env.CORE_CONTAINER, coreRequest, authenticated.session, proof, bundle, proofPath);
  const verification = await boundedCoreReceipt(coreResponse);
  assertNativeBackupReceipt(verification);
  if (verification.project_id !== projectId || verification.body_fingerprint !== bodyFingerprint || verification.bundle_fingerprint !== bodyFingerprint || verification.byte_size !== bundle.byteLength || verification.scope !== "novel") throw Object.assign(new Error("Core verification receipt does not bind the read bytes"), { code: "core_verification_mismatch" });
  return withSecurityHeaders(new Response(new Uint8Array(bundle), { status: 200, headers: {
    "content-type": "application/zip",
    "content-length": String(bundle.byteLength),
    "cache-control": "no-store",
    "x-qf-authority": "false",
    "x-qf-project-id": projectId,
    "x-qf-version-id": pointer.version_id,
    "x-qf-pointer-version": String(pointer.pointer_version),
    "x-qf-object-key-sha256": objectKeySha256,
  } }));
}

async function handleGcProject(request: Request, env: CloudEnv, projectId: string): Promise<Response> {
  const authenticated = await authenticate(request, env, true);
  explicitAction(request, "project.gc");
  const opId = operationId(request);
  const url = new URL(request.url);
  const versionId = url.searchParams.get("version_id") ?? "";
  const queryKeys = [...url.searchParams.keys()];
  if (queryKeys.length !== 1 || queryKeys[0] !== "version_id" || !/^sha256:[0-9a-f]{64}$/.test(versionId)) throw Object.assign(new Error("project garbage-collection query is invalid"), { code: "project_gc_invalid" });
  const prior = await authenticated.coordinator.readProjectVersionGcOperation({ project_id: projectId, operation_id: opId });
  const pending = await authenticated.coordinator.beginProjectVersionGc({ project_id: projectId, version_id: versionId, operation_id: opId, retention_before: prior?.retention_before ?? Date.now() - 60 * 60 * 1000 });
  if (pending.status === "completed") return safeJson({ schema: "quillframe_cloud_project_gc_receipt_v1", operation_id: opId, project_id: projectId, version_id: versionId, status: "completed", authority: false });
  const store = new EncryptedProjectStore(env.PROJECT_BUNDLES, env.PROJECT_BUNDLE_KEY_B64, projectKeyRing(env));
  try {
    await store.deleteGcObject(authenticated.session.workspace_id, projectId, pending);
  } catch {
    await authenticated.coordinator.finishProjectVersionGc({ project_id: projectId, version_id: versionId, operation_id: opId, deleted: false });
    return safeJson({ schema: "quillframe_cloud_project_gc_receipt_v1", operation_id: opId, project_id: projectId, version_id: versionId, status: "pending", authority: false }, { status: 202 });
  }
  const complete = await authenticated.coordinator.finishProjectVersionGc({ project_id: projectId, version_id: versionId, operation_id: opId, deleted: true });
  return safeJson({ schema: "quillframe_cloud_project_gc_receipt_v1", operation_id: opId, project_id: projectId, version_id: versionId, status: complete.status, authority: false });
}

async function handleDeleteProject(request: Request, env: CloudEnv, projectId: string): Promise<Response> {
  const authenticated = await authenticate(request, env, true);
  explicitAction(request, "project.delete");
  const opId = operationId(request);
  const current = await authenticated.coordinator.readProjectPointer(projectId);
  const previous = await authenticated.coordinator.readProjectTombstoneOperation({ project_id: projectId, operation_id: opId });
  const captured = previous ?? current;
  if (!captured || captured.workspace_id !== authenticated.session.workspace_id || captured.project_id !== projectId || !captured.version_id || !captured.object_key || !captured.plaintext_fingerprint) throw Object.assign(new Error("project pointer is not active"), { code: "project_pointer_conflict" });
  if (previous) {
    if (!current || current.state !== "deleted" || current.pointer_version !== previous.pointer_version || current.object_key !== previous.object_key || current.version_id !== previous.version_id || current.plaintext_fingerprint !== previous.plaintext_fingerprint) throw Object.assign(new Error("project deletion operation no longer names the current tombstone"), { code: "project_delete_conflict" });
  } else if (!current || current.state !== "active") {
    throw Object.assign(new Error("project pointer is not active"), { code: "project_pointer_conflict" });
  }
  const tombstone = previous ?? await authenticated.coordinator.casProjectTombstone({ project_id: projectId, expected_pointer_version: captured.pointer_version, operation_id: opId, reason: "explicit_project_delete" });
  const store = new EncryptedProjectStore(env.PROJECT_BUNDLES, env.PROJECT_BUNDLE_KEY_B64, projectKeyRing(env));
  try {
    await store.deleteVerified(authenticated.session.workspace_id, projectId, { ...captured, state: "deleted" });
    return safeJson({ schema: "quillframe_cloud_project_delete_receipt_v2", operation_id: opId, project_id: projectId, pointer_version: tombstone.pointer_version, state: "deleted", object_key: captured.object_key, gc: "complete", authority: false });
  } catch (error) {
    const code = error && typeof error === "object" && "code" in error && error.code === "project_gc_pending" ? "project_gc_pending" : "project_delete_failed";
    return safeJson({ schema: "quillframe_cloud_project_delete_receipt_v2", operation_id: opId, project_id: projectId, pointer_version: tombstone.pointer_version, state: "deleted", object_key: captured.object_key, gc: "pending", code, authority: false }, { status: 202 });
  }
}

async function handleEndpointValidation(request: Request, env: CloudEnv): Promise<Response> {
  await authenticate(request, env, true);
  let body: unknown;
  try { body = await readBoundedJsonBody(request, MAX_ENDPOINT_VALIDATION_BODY); }
  catch { throw Object.assign(new Error("endpoint validation request is invalid"), { code: "endpoint_request_invalid" }); }
  const endpoint = body && typeof body === "object" && !Array.isArray(body) && Object.hasOwn(body, "endpoint") ? (body as { endpoint?: unknown }).endpoint : undefined;
  if (!body || typeof body !== "object" || Array.isArray(body) || Object.keys(body).length !== 1 || endpoint === undefined || typeof endpoint !== "string") {
    throw Object.assign(new Error("endpoint validation request is invalid"), { code: "endpoint_request_invalid" });
  }
  const proof = await validateHostedEndpoint(endpoint, {
    resolver: new CloudflareDnsResolver(env.fetch ?? globalThis.fetch),
    probe: new BoundEndpointProbe(env.ENDPOINT_EGRESS),
  });
  return safeJson(proof);
}

async function handleCore(request: Request, env: CloudEnv): Promise<Response> {
  if (request.method !== "POST" || new URL(request.url).pathname !== "/api/core/bridge") throw Object.assign(new Error("only POST /api/core/bridge is supported"), { code: "core_route_invalid" });
  for (const name of FORBIDDEN_CORE_HEADERS) if (request.headers.has(name)) throw Object.assign(new Error("caller proof or identity headers are forbidden"), { code: "core_header_forbidden" });
  if (!/^[A-Za-z0-9._:-]{1,128}$/.test(env.CORE_PROOF_KEY_ID) || (env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined && !/^[A-Za-z0-9._:-]{1,128}$/.test(env.CORE_PROOF_PREVIOUS_KEY_ID))) throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" });
  let keyBytes: Uint8Array;
  try { keyBytes = strictProofKey(env.CORE_PROOF_KEY_B64); if (env.CORE_PROOF_PREVIOUS_KEY_B64 !== undefined) strictProofKey(env.CORE_PROOF_PREVIOUS_KEY_B64, "previous proof key"); } catch { throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" }); }
  if (env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined && env.CORE_PROOF_PREVIOUS_KEY_ID === env.CORE_PROOF_KEY_ID) throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" });
  if (keyBytes.byteLength !== 32 || ((env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined) !== (env.CORE_PROOF_PREVIOUS_KEY_B64 !== undefined))) throw Object.assign(new Error("Core proof key configuration is invalid"), { code: "core_key_config_invalid" });
  const authenticated = await authenticate(request, env, true);
  if (["GET", "HEAD"].includes(request.method)) throw Object.assign(new Error("Core bridge body is required"), { code: "core_body_required" });
  const body = await readCoreBody(request);
  const parsed = canonicalBridgeBody(body);
  const { operation } = validateBridgeRequest(parsed.value);
  const projectId = deriveProofProjectId(operation, parsed.value);
  if (projectId !== null) {
    const pointer = await authenticated.coordinator.readProjectPointer(projectId);
    if (operation === "project.create" && pointer) throw Object.assign(new Error("Core project binding is invalid"), { code: "core_project_binding_invalid" });
    if (operation === "project.create") await authenticated.coordinator.assertWorkspaceBinding(authenticated.session.workspace_id);
    if (operation !== "project.create" && (!pointer || pointer.state !== "active" || pointer.workspace_id !== authenticated.session.workspace_id || pointer.project_id !== projectId)) throw Object.assign(new Error("Core project binding is invalid"), { code: "core_project_binding_invalid" });
    if (pointer && pointer.workspace_id !== authenticated.session.workspace_id) throw Object.assign(new Error("Core project binding is invalid"), { code: "core_project_binding_invalid" });
  }
  const bodyFingerprint = `sha256:${await sha256Hex(body)}` as `sha256:${string}`;
  const nonce = randomToken(24);
  const source = new URL(request.url);
  const path = source.pathname.replace(/^\/api\/core/, "") || "/bridge";
  const now = Date.now();
  const proofClaims = {
    schema: "quillframe_core_proof_v1" as const,
    key_id: env.CORE_PROOF_KEY_ID,
    method: request.method,
    path: `${path}${source.search}`,
    body_sha256: bodyFingerprint,
    workspace_id: authenticated.session.workspace_id,
    session_id: authenticated.session.session_id,
    project_id: projectId,
    scope: "novel" as const,
    issued_at: now,
    expires_at: now + 30_000,
    nonce,
  };
  const proof = await signCoreProof({ claims: proofClaims, key: keyBytes });
  await authenticated.coordinator.consumeCoreNonce({ session_id: authenticated.session.session_id, project_id: projectId, nonce, proof_digest: `sha256:${await sha256Hex(proof)}`, issued_at: now, expires_at: now + 30_000 });
  return withSecurityHeaders(await forwardToCore(env.CORE_CONTAINER, request, authenticated.session, proof, body));
}

async function handle(request: Request, env: CloudEnv): Promise<Response> {
  assertPublicOrigin(env.PUBLIC_ORIGIN);
  assertRequestOrigin(request, env.PUBLIC_ORIGIN);
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/api/auth/authorize") return handleAuthorize(request, env);
  if (request.method === "GET" && url.pathname === "/api/auth/callback") return handleCallback(request, env);
  if (request.method === "POST" && url.pathname === "/api/auth/logout") return handleLogout(request, env);
  if (request.method === "GET" && url.pathname === "/api/session") return safeJson((await authenticate(request, env)).session);
  const project = url.pathname.match(/^\/api\/projects\/([A-Za-z0-9][A-Za-z0-9._-]{0,63})(?:\/(upload|gc))?$/);
  if (project && request.method === "POST" && url.pathname.endsWith("/upload")) return handleUpload(request, env, project[1]);
  if (project && request.method === "POST" && url.pathname.endsWith("/gc")) return handleGcProject(request, env, project[1]);
  if (project && request.method === "GET" && project[2] === undefined) return handleReadProject(request, env, project[1]);
  if (project && project[2] === undefined && request.method === "DELETE") return handleDeleteProject(request, env, project[1]);
  if (request.method === "POST" && url.pathname === "/api/model/endpoints/validate") return handleEndpointValidation(request, env);
  if (request.method === "POST" && url.pathname === "/api/core/bridge") {
    return handleCore(request, env);
  }
  if (!isApiPath(url.pathname)) {
    const asset = await serveStudioAsset(request, env);
    if (asset) return asset;
  }
  return safeJson({ schema: "quillframe_cloud_error_v1", code: "not_found", authority: false }, { status: 404 });
}

export function createWorker(): { fetch(request: Request, env: CloudEnv): Promise<Response> } {
  return {
    async fetch(request, env) {
      let response: Response;
      try { response = await handle(request, env); }
      catch (error) { response = safeError(error); }
      if (isApiPath(new URL(request.url).pathname) || response.status >= 400) response = withoutCaching(response);
      return request.method === "HEAD" ? new Response(null, { status: response.status, statusText: response.statusText, headers: response.headers }) : response;
    },
  };
}

export default createWorker();

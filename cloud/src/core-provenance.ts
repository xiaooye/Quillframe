import { base64Url, fromBase64, sha256Hex } from "./crypto.js";

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });

export const CORE_PROOF_SCHEMA = "quillframe_core_proof_v1" as const;
export const CORE_PROOF_VERSION = "qfcp1" as const;
export const MAX_CORE_BODY = 4 * 1024 * 1024;
export const CORE_PROOF_SKEW_MS = 5_000;
export const CORE_PROOF_MAX_LIFETIME_MS = 30_000;
const MAX_ID = 128;
const MAX_PATH = 2048;
const MAX_NONCE = 128;
const CLAIM_KEYS = ["body_sha256", "chapter_scope", "expires_at", "issued_at", "key_id", "method", "nonce", "path", "project_id", "schema", "session_id", "workspace_id"] as const;

const PROJECT_REQUIRED = new Set([
  "project.create", "project.open", "project.inspect", "project.search", "project.backup",
  "document.create", "document.open", "document.revisions.list", "document.revision.save", "document.revision.compare",
  "author.run.start", "author.run.status", "author.run.resume", "author.run.cancel", "author.run.execute",
  "author.run.independent.submit", "author.run.independent.dispatch.prepare", "author.run.context.refresh",
  "model.route.preview", "candidate.accept", "candidate.reject", "candidate.revision.request",
  "settlement.apply", "settlement.preflight", "feedback.observe", "publication.preview", "publication.build",
  "inspector.sessions.list", "inspector.runs.list", "inspector.checkpoints.list", "inspector.context.list",
  "inspector.receipts.list", "inspector.candidates.list", "inspector.learning.list", "inspector.context.runtime",
  "document.list", "candidate.review.get", "candidate.visible.get",
]);
const PROJECT_NULL = new Set([
  "bridge.describe", "database.doctor", "project.list", "author.run.events", "model.service.add",
  "model.service.list", "model.service.get", "model.service.discover", "model.service.test",
  "model.service.token.replace", "model.service.token.remove", "model.service.delete", "model.capabilities",
]);
export const PROJECT_REQUIRED_OPERATIONS = [...PROJECT_REQUIRED].sort();
export const PROJECT_NULL_OPERATIONS = [...PROJECT_NULL].sort();

export class CoreProofError extends Error {
  constructor(public readonly code: string, message = "core provenance validation failed") { super(message); }
}

export type CoreProofClaims = {
  schema: typeof CORE_PROOF_SCHEMA;
  key_id: string;
  method: string;
  path: string;
  body_sha256: `sha256:${string}`;
  workspace_id: string;
  session_id: string;
  project_id: string | null;
  chapter_scope: "CH001";
  issued_at: number;
  expires_at: number;
  nonce: string;
};

export type CoreProofKeyMap = ReadonlyMap<string, Uint8Array> | Readonly<Record<string, Uint8Array>>;
export type ProofOptions = { claims: CoreProofClaims; key: Uint8Array };
export type VerifyOptions = {
  keyMap?: CoreProofKeyMap;
  keyId?: string;
  key?: Uint8Array;
  now: number;
  method: string;
  path: string;
  body: Uint8Array;
  workspace_id?: string;
  session_id?: string;
  project_id?: string | null;
};

export function strictProofKey(value: string, _label = "proof key"): Uint8Array {
  if (typeof value !== "string" || !/^[A-Za-z0-9_-]+$/.test(value) || value.includes("=")) fail("proof_key_config_invalid");
  let bytes: Uint8Array;
  try { bytes = fromBase64(value); } catch { fail("proof_key_config_invalid"); }
  if (base64Url(bytes) !== value || bytes.byteLength !== 32) fail("proof_key_config_invalid");
  return bytes;
}

function fail(code: string): never { throw new CoreProofError(code); }
function owned(value: Uint8Array): Uint8Array<ArrayBuffer> { const copy = new Uint8Array(value.byteLength); copy.set(value); return copy; }
function exactKeys(value: unknown, expected: readonly string[]): boolean {
  return !!value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).sort().join(",") === [...expected].sort().join(",");
}
function boundedId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_ID && /^[A-Za-z0-9._:-]+$/.test(value);
}
function nativeProjectId(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(value);
}
function boundedNonce(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_NONCE && /^[A-Za-z0-9_-]+$/.test(value);
}
function boundedMethod(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 16 && /^[A-Z][A-Z0-9-]*$/.test(value);
}
function boundedPath(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_PATH && value.startsWith("/") && !/[\u0000-\u001f\u007f-\u009f#]/.test(value);
}
function hexHash(value: unknown): value is `sha256:${string}` { return typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value); }
function safeTime(value: unknown): value is number { return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 && value <= 100_000_000_000_000; }
function hasLoneSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      if (index + 1 >= value.length) return true;
      const next = value.charCodeAt(index + 1);
      if (next < 0xdc00 || next > 0xdfff) return true;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) return true;
  }
  return false;
}

function validateJsonValue(value: unknown): void {
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "string") { if (hasLoneSurrogate(value)) fail("body_json_invalid"); return; }
  if (typeof value === "number") { if (!Number.isFinite(value) || !Number.isSafeInteger(value)) fail("body_json_invalid"); return; }
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index += 1) { if (!Object.prototype.hasOwnProperty.call(value, index)) fail("body_json_invalid"); validateJsonValue(value[index]); }
    return;
  }
  if (typeof value !== "object" || Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) fail("body_json_invalid");
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    if (/[\x80-\xff]/.test(key) || hasLoneSurrogate(key)) fail("body_json_invalid");
    validateJsonValue(child);
  }
}

function sortedValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortedValue);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value as Record<string, unknown>).sort().map((key) => [key, sortedValue((value as Record<string, unknown>)[key])]));
  return value;
}

export function canonicalJson(value: unknown): string {
  validateJsonValue(value);
  const result = JSON.stringify(sortedValue(value));
  if (typeof result !== "string") fail("body_json_invalid");
  return result;
}
export function canonicalJsonBytes(value: unknown): Uint8Array { return encoder.encode(canonicalJson(value)); }

class JsonParser {
  private index = 0;
  constructor(private readonly text: string, private readonly kind: "body" | "claims" = "body") {}
  private error(code: string): never { throw new CoreProofError(this.kind === "claims" ? "proof_claims_invalid" : code); }
  parse(): unknown { const value = this.value(); this.ws(); if (this.index !== this.text.length) this.error("body_not_canonical"); return value; }
  private ws(): void { while ([" ", "\n", "\r", "\t"].includes(this.text[this.index] ?? "")) this.index += 1; }
  private value(): unknown {
    this.ws(); const char = this.text[this.index];
    if (char === "{") return this.object(); if (char === "[") return this.array(); if (char === '"') return this.string();
    if (char === "t") return this.literal("true", true); if (char === "f") return this.literal("false", false); if (char === "n") return this.literal("null", null); return this.number();
  }
  private literal(token: string, value: unknown): unknown { if (this.text.slice(this.index, this.index + token.length) !== token) this.error("body_json_invalid"); this.index += token.length; return value; }
  private object(): Record<string, unknown> {
    this.index += 1; this.ws(); const result: Record<string, unknown> = {}; const seen = new Set<string>();
    if (this.text[this.index] === "}") { this.index += 1; return result; }
    while (true) {
      this.ws(); const key = this.string(); if (/[^\x00-\x7f]/.test(key)) this.error("body_json_invalid"); if (seen.has(key)) this.error("body_duplicate_key"); seen.add(key);
      this.ws(); if (this.text[this.index++] !== ":") this.error("body_json_invalid"); result[key] = this.value(); this.ws();
      const delimiter = this.text[this.index++]; if (delimiter === "}") return result; if (delimiter !== ",") this.error("body_json_invalid");
    }
  }
  private array(): unknown[] {
    this.index += 1; this.ws(); const result: unknown[] = []; if (this.text[this.index] === "]") { this.index += 1; return result; }
    while (true) { result.push(this.value()); this.ws(); const delimiter = this.text[this.index++]; if (delimiter === "]") return result; if (delimiter !== ",") this.error("body_json_invalid"); }
  }
  private string(): string {
    if (this.text[this.index++] !== '"') this.error("body_json_invalid"); let result = "";
    while (this.index < this.text.length) {
      const char = this.text[this.index++]; if (char === '"') return result;
      if (char === "\\") {
        const escaped = this.text[this.index++]; const map: Record<string, string> = { '"': '"', "\\": "\\", "/": "/", b: "\b", f: "\f", n: "\n", r: "\r", t: "\t" };
        if (escaped === "u") { const hex = this.text.slice(this.index, this.index + 4); if (!/^[0-9a-fA-F]{4}$/.test(hex)) this.error("body_json_invalid"); this.index += 4; result += String.fromCharCode(Number.parseInt(hex, 16)); }
        else if (escaped in map) result += map[escaped]; else this.error("body_json_invalid");
      } else { if (char < " ") this.error("body_json_invalid"); result += char; }
    }
    this.error("body_json_invalid");
  }
  private number(): number {
    const match = this.text.slice(this.index).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/); if (!match) this.error("body_json_invalid"); this.index += match[0].length;
    const value = Number(match[0]); if (!Number.isFinite(value) || !Number.isSafeInteger(value)) this.error("body_json_invalid"); return value;
  }
}

function parseCanonical(raw: Uint8Array, kind: "body" | "claims"): unknown {
  let text: string; try { text = decoder.decode(raw); } catch { fail(kind === "claims" ? "proof_claims_invalid" : "body_utf8_invalid"); }
  let value: unknown; try { value = new JsonParser(text, kind).parse(); } catch (error) { if (error instanceof CoreProofError) throw error; fail(kind === "claims" ? "proof_claims_invalid" : "body_json_invalid"); }
  let canonical: Uint8Array; try { canonical = canonicalJsonBytes(value); } catch (error) { if (error instanceof CoreProofError) throw kind === "claims" ? new CoreProofError("proof_claims_invalid") : error; throw error; }
  if (canonical.length !== raw.length || canonical.some((byte, index) => byte !== raw[index])) fail(kind === "claims" ? "proof_claims_invalid" : "body_not_canonical");
  return value;
}

export function parseCanonicalJsonBytes(raw: Uint8Array, kind: "body" | "claims" = "body", limit = MAX_CORE_BODY): unknown {
  if (raw.byteLength > limit) fail(kind === "claims" ? "proof_claims_invalid" : "body_size_invalid");
  return parseCanonical(raw, kind);
}
export function canonicalBridgeBody(raw: string | Uint8Array): { bytes: Uint8Array; value: Record<string, unknown> } {
  const bytes = typeof raw === "string" ? encoder.encode(raw) : new Uint8Array(raw); if (bytes.byteLength > MAX_CORE_BODY) fail("body_size_invalid");
  const value = parseCanonicalJsonBytes(bytes, "body"); if (!value || typeof value !== "object" || Array.isArray(value)) fail("body_json_invalid");
  return { bytes, value: value as Record<string, unknown> };
}

const BRIDGE_ROOT_KEYS = ["args", "authority", "bridge_version", "operation", "request_id", "schema", "surface"] as const;
export function validateBridgeRequest(value: unknown): { operation: string; args: Record<string, unknown> } {
  if (!exactKeys(value, BRIDGE_ROOT_KEYS)) fail("bridge_request_invalid"); const request = value as Record<string, unknown>;
  if (request.schema !== "quillframe_host_bridge_request_v11" || request.bridge_version !== "11" || request.surface !== "hosted_web" || request.authority !== false) fail("bridge_request_invalid");
  if (!boundedId(request.request_id) || typeof request.operation !== "string" || request.operation.length > MAX_ID || !/^[A-Za-z0-9._-]+$/.test(request.operation)) fail("bridge_request_invalid");
  if (!request.args || typeof request.args !== "object" || Array.isArray(request.args)) fail("bridge_request_invalid"); return { operation: request.operation, args: request.args as Record<string, unknown> };
}

export function deriveProofProjectId(operation: string, request: Record<string, unknown>): string | null {
  const args = request.args; if (!args || typeof args !== "object" || Array.isArray(args)) fail("proof_project_invalid"); const record = args as Record<string, unknown>;
  if (PROJECT_REQUIRED.has(operation)) { if (!nativeProjectId(record.project_id)) fail("proof_project_invalid"); return record.project_id; }
  if (PROJECT_NULL.has(operation)) { if (Object.prototype.hasOwnProperty.call(record, "project_id")) fail("proof_project_invalid"); return null; }
  fail("proof_operation_invalid");
}

function validateClaims(claims: unknown): asserts claims is CoreProofClaims {
  if (!exactKeys(claims, CLAIM_KEYS)) fail("proof_claims_invalid"); const value = claims as Record<string, unknown>;
  if (value.schema !== CORE_PROOF_SCHEMA || !boundedId(value.key_id) || !boundedMethod(value.method) || !boundedPath(value.path) || !hexHash(value.body_sha256) || !boundedId(value.workspace_id) || !boundedId(value.session_id) || value.project_id !== null && !nativeProjectId(value.project_id) || value.chapter_scope !== "CH001" || !safeTime(value.issued_at) || !safeTime(value.expires_at) || !boundedNonce(value.nonce)) fail("proof_claims_invalid");
  if (value.expires_at <= value.issued_at || value.expires_at - value.issued_at > CORE_PROOF_MAX_LIFETIME_MS) fail("proof_time_invalid");
}

async function hmacKey(key: Uint8Array): Promise<CryptoKey> { if (!(key instanceof Uint8Array) || key.byteLength !== 32) fail("proof_key_config_invalid"); return crypto.subtle.importKey("raw", new Uint8Array(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]); }
async function hmac(key: Uint8Array, data: Uint8Array): Promise<Uint8Array> { return new Uint8Array(await crypto.subtle.sign("HMAC", await hmacKey(key), new Uint8Array(data))); }
function strictBase64Url(value: unknown): Uint8Array { if (typeof value !== "string" || !/^[A-Za-z0-9_-]+$/.test(value) || value.includes("=")) fail("proof_invalid"); let bytes: Uint8Array; try { bytes = fromBase64(value); } catch { fail("proof_invalid"); } if (base64Url(bytes) !== value) fail("proof_invalid"); return bytes; }
function keyFrom(options: VerifyOptions, keyId: string): Uint8Array {
  if (options.keyMap) { const key = options.keyMap instanceof Map ? options.keyMap.get(keyId) : (options.keyMap as Readonly<Record<string, Uint8Array>>)[keyId]; if (!key) fail("proof_key_unknown"); return key; }
  if (!options.keyId || options.keyId !== keyId || !options.key) fail("proof_key_unknown"); return options.key;
}

export async function signCoreProof(input: ProofOptions): Promise<string> { validateClaims(input.claims); const claimsBytes = canonicalJsonBytes(input.claims); return `${CORE_PROOF_VERSION}.${input.claims.key_id}.${base64Url(claimsBytes)}.${base64Url(await hmac(input.key, claimsBytes))}`; }
export async function buildCoreProof(input: { key_id: string; key: Uint8Array; method: string; path: string; body: Uint8Array; workspace_id: string; session_id: string; project_id: string | null; chapter_scope: "CH001"; issued_at: number; expires_at: number; nonce: string }): Promise<{ header: string; claims: CoreProofClaims; proof_digest: `sha256:${string}` }> {
  const claims: CoreProofClaims = { schema: CORE_PROOF_SCHEMA, key_id: input.key_id, method: input.method, path: input.path, body_sha256: `sha256:${await sha256Hex(input.body)}`, workspace_id: input.workspace_id, session_id: input.session_id, project_id: input.project_id, chapter_scope: input.chapter_scope, issued_at: input.issued_at, expires_at: input.expires_at, nonce: input.nonce };
  const header = await signCoreProof({ claims, key: input.key }); return { header, claims, proof_digest: `sha256:${await sha256Hex(header)}` };
}
export async function verifyCoreProof(value: string, options: VerifyOptions): Promise<CoreProofClaims> {
  if (typeof value !== "string" || value.length > 32_768) fail("proof_invalid"); const parts = value.split(".");
  if (parts.length !== 4 || parts[0] !== CORE_PROOF_VERSION || typeof parts[1] !== "string" || !boundedId(parts[1])) fail("proof_invalid"); const keyId = parts[1]; const key = keyFrom(options, keyId);
  const parsed = parseCanonicalJsonBytes(strictBase64Url(parts[2]), "claims"); validateClaims(parsed); const claims = parsed;
  if (claims.key_id !== keyId || claims.method !== options.method || claims.path !== options.path) fail("proof_binding_invalid");
  if (options.workspace_id !== undefined && claims.workspace_id !== options.workspace_id || options.session_id !== undefined && claims.session_id !== options.session_id || options.project_id !== undefined && claims.project_id !== options.project_id) fail("proof_binding_invalid");
  if (!safeTime(options.now) || options.now < claims.issued_at - CORE_PROOF_SKEW_MS || options.now > claims.expires_at + CORE_PROOF_SKEW_MS) fail("proof_time_invalid");
  if (`sha256:${await sha256Hex(options.body)}` !== claims.body_sha256) fail("proof_body_invalid"); const signature = strictBase64Url(parts[3]);
  if (signature.byteLength !== 32 || !(await crypto.subtle.verify("HMAC", await hmacKey(key), owned(signature), owned(canonicalJsonBytes(claims))))) fail("proof_signature_invalid"); return claims;
}

export type BridgeStatus = "ok" | "invalid" | "unsupported" | "failed" | "error";
export type CoreSurface = "local_app" | "hosted_web";
export type TransportName = "local-http" | "hosted-http" | "tauri-ipc";
export type OperationKind =
  | "query"
  | "command"
  | "authority_command"
  | "semantic_command"
  | "secret_command"
  | "external_query"
  | "external_handoff_prepare"
  | "external_handoff"
  | "external_handoff_result";

const BRIDGE_VERSION = "11" as const;
const REQUEST_SCHEMA = "quillframe_host_bridge_request_v11" as const;
const RESULT_SCHEMA = "quillframe_host_bridge_result_v11" as const;
const TOKEN_PLACEHOLDER = "__QUILLFRAME_STUDIO_TOKEN__";

export interface BridgeRequest {
  schema: typeof REQUEST_SCHEMA;
  bridge_version: typeof BRIDGE_VERSION;
  request_id: string;
  operation: string;
  surface: CoreSurface;
  args: Record<string, unknown>;
  authority: false;
}

export interface BridgeResult<T = unknown> {
  schema: typeof RESULT_SCHEMA;
  bridge_version: typeof BRIDGE_VERSION;
  request_id: string;
  operation: string;
  surface: CoreSurface;
  status: BridgeStatus;
  request_fingerprint: string;
  result_fingerprint: string;
  data: T | null;
  error: unknown;
  secret_values_persisted: false;
  authority: false;
  canon_authority: false;
  framework_write_authority: false;
  settlement_authority: false;
}

export interface OperationContract {
  kind: OperationKind;
  required_args: string[];
  allowed_surfaces?: Array<CoreSurface | "cli" | "agent_package">;
}

export interface RawBridgeDescription {
  schema: string;
  framework_version?: string;
  contract_version?: string;
  surface?: string | null;
  operations?: string[];
  operation_contracts?: Record<string, OperationContract>;
  deferred_operations?: Record<string, unknown>;
  authority: false;
  canon_authority: false;
  framework_write_authority: false;
  settlement_authority: false;
  direct_core_store_access: false;
}

export interface BridgeCapabilities {
  frameworkVersion: string | null;
  contractVersion: string | null;
  surface: string | null;
  operations: string[];
  operationContracts: Record<string, OperationContract>;
  deferredOperations: string[];
  authority: false;
}

export interface BridgeTransport {
  readonly name: TransportName;
  readonly requestSurface: CoreSurface;
  available(): boolean;
  invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>>;
}

declare global {
  interface Window {
    __TAURI__?: {
      core?: {
        invoke?: <T>(command: string, args?: Record<string, unknown>) => Promise<T>;
      };
    };
  }
}

function documentMeta(name: string): string {
  if (typeof document === "undefined") return "";
  return document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content.trim() ?? "";
}

function localToken(): string {
  return documentMeta("quillframe-studio-token");
}

/** An explicit hosted binding; a static HTTPS page alone is not a Core binding. */
export function hostedEndpoint(): string {
  if (typeof window === "undefined") return "";
  try {
    const configured = documentMeta("quillframe-studio-hosted-endpoint");
    if (!configured || /[\u0000-\u0020\u007f\\]/.test(configured)) return "";
    const endpoint = new URL(configured);
    const page = new URL(window.location.href);
    if (
      endpoint.protocol !== "https:" || page.protocol !== "https:" || endpoint.origin !== page.origin ||
      endpoint.username || endpoint.password || endpoint.pathname !== "/" || endpoint.search || endpoint.hash
    ) return "";
    return endpoint.origin;
  } catch {
    return "";
  }
}

/** The readable CSRF cookie is separate from the HttpOnly authenticated session. */
export function hostedCsrfToken(): string {
  try {
    const values = document.cookie.split(";").flatMap((part) => {
      const separator = part.indexOf("=");
      const name = (separator < 0 ? part : part.slice(0, separator)).trim();
      return name === "__Host-qf_csrf" ? [separator < 0 ? "" : part.slice(separator + 1).trim()] : [];
    });
    // Cloud issues randomToken(24): exactly 32 unpadded base64url characters.
    if (values.length === 1 && /^[A-Za-z0-9_-]{32}$/.test(values[0])) return values[0];
  } catch {
    // Cookie access can fail in restricted contexts; never include its contents.
  }
  throw new Error("Hosted Core CSRF token is missing or invalid");
}

const RESULT_KEYS = [
  "schema", "bridge_version", "request_id", "operation", "surface", "status",
  "data", "error", "request_fingerprint", "secret_values_persisted", "authority",
  "canon_authority", "framework_write_authority", "settlement_authority", "result_fingerprint",
] as const;
const FINGERPRINT_RE = /^sha256:[0-9a-f]{64}$/;
const RESULT_STATUSES = new Set<BridgeStatus>(["ok", "invalid", "unsupported", "failed", "error"]);
const SECRET_REQUEST_KEYS = new Set(["access_token", "api_key", "apikey", "password", "secret", "token"]);
const PUBLIC_ERROR_CODE_RE = /^[a-z][a-z0-9_]{0,63}$/;

function compareCanonicalKeys(left: string, right: string): number {
  const a = Array.from(left, (char) => char.codePointAt(0)!);
  const b = Array.from(right, (char) => char.codePointAt(0)!);
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    if (a[index] !== b[index]) return a[index] - b[index];
  }
  return a.length - b.length;
}

function canonicalValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => compareCanonicalKeys(left, right))
        .map(([key, child]) => [key, canonicalValue(child)]),
    );
  }
  return value;
}

function serializeCanonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(serializeCanonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    // Emit keys directly: JSON.stringify would reorder integer-style keys.
    return `{${Object.keys(record).sort(compareCanonicalKeys).map((key) => `${JSON.stringify(key)}:${serializeCanonicalJson(record[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("Bridge fingerprint input is not JSON");
  return encoded;
}

function canonicalJson(value: unknown): string {
  const encoded = JSON.stringify(canonicalValue(value));
  if (encoded === undefined) throw new Error("Bridge fingerprint input is not JSON");
  // Keep existing JSON normalization for Local/Tauri fingerprints. Only hosted
  // request bodies use the stricter Cloud wire-value contract below.
  return serializeCanonicalJson(JSON.parse(encoded));
}

function hasLoneSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(++index);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return true;
    } else if (code >= 0xdc00 && code <= 0xdfff) return true;
  }
  return false;
}

function hostedJsonValue(value: unknown, ancestors: Set<object>): unknown {
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "string" && !hasLoneSurrogate(value)) return value;
  if (typeof value === "number" && Number.isSafeInteger(value)) return value;
  if (!value || typeof value !== "object" || ancestors.has(value)) throw new Error("Invalid hosted JSON value");
  const isArray = Array.isArray(value);
  const prototype = Object.getPrototypeOf(value);
  if (isArray ? prototype !== Array.prototype : prototype !== Object.prototype && prototype !== null) {
    throw new Error("Invalid hosted JSON prototype");
  }
  if (Object.getOwnPropertySymbols(value).length) throw new Error("Invalid hosted JSON keys");
  const descriptors = Object.getOwnPropertyDescriptors(value);
  if (Object.values(descriptors).some((descriptor) => !("value" in descriptor))) throw new Error("Invalid hosted JSON accessor");
  if (typeof descriptors.toJSON?.value === "function") throw new Error("Invalid hosted JSON conversion");
  ancestors.add(value);
  try {
    if (isArray) {
      // Sparse arrays and extra properties cannot silently change wire meaning.
      if (Object.keys(descriptors).length !== value.length + 1) throw new Error("Invalid hosted JSON array");
      return Array.from({ length: value.length }, (_, index) => {
        if (!Object.prototype.hasOwnProperty.call(descriptors, index)) throw new Error("Invalid hosted JSON array");
        return hostedJsonValue(descriptors[index].value, ancestors);
      });
    }
    const result: Record<string, unknown> = Object.create(null);
    for (const [key, descriptor] of Object.entries(descriptors)) {
      if (!descriptor.enumerable || descriptor.value === undefined) continue;
      if (/[^\x00-\x7f]/.test(key)) throw new Error("Invalid hosted JSON key");
      result[key] = hostedJsonValue(descriptor.value, ancestors);
    }
    return result;
  } finally {
    ancestors.delete(value);
  }
}

function hostedRequestBody(request: BridgeRequest): string {
  try {
    return serializeCanonicalJson(hostedJsonValue(request, new Set()));
  } catch {
    throw new Error("Hosted Core request body must use supported canonical JSON values");
  }
}

async function fingerprint(value: unknown): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error("WebCrypto is required to verify Bridge fingerprints");
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(canonicalJson(value)));
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function redactedRequest(request: BridgeRequest): BridgeRequest {
  const wire = JSON.parse(JSON.stringify(request)) as BridgeRequest;
  const secrets = new Set<string>();
  const collect = (value: unknown): void => {
    if (Array.isArray(value)) {
      value.forEach(collect);
      return;
    }
    if (!value || typeof value !== "object") return;
    for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
      if (SECRET_REQUEST_KEYS.has(key.toLowerCase().replaceAll("-", "_"))) {
        if (typeof child === "string" && child) secrets.add(child);
      } else {
        collect(child);
      }
    }
  };
  collect(wire);
  const scrub = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(scrub);
    if (value && typeof value === "object") {
      return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, child]) => [
        key,
        SECRET_REQUEST_KEYS.has(key.toLowerCase().replaceAll("-", "_")) ? "<redacted>" : scrub(child),
      ]));
    }
    if (typeof value === "string") {
      return [...secrets].sort((left, right) => right.length - left.length).reduce(
        (current, secret) => current.replaceAll(secret, "<redacted>"),
        value,
      );
    }
    return value;
  };
  return scrub(wire) as BridgeRequest;
}

export async function assertEnvelope<T>(
  value: unknown,
  expectedSurface: CoreSurface,
  expectedRequest?: BridgeRequest,
): Promise<BridgeResult<T>> {
  if (!value || typeof value !== "object") throw new Error("Bridge returned a non-object response");
  const candidate = value as Partial<BridgeResult<T>>;
  if (Object.keys(value).sort().join("\0") !== [...RESULT_KEYS].sort().join("\0")) {
    throw new Error("Bridge result fields do not match the v11 contract");
  }
  if (candidate.schema !== RESULT_SCHEMA) throw new Error("Unexpected bridge result schema");
  if (candidate.bridge_version !== BRIDGE_VERSION) throw new Error("Unexpected Host Bridge version");
  if (candidate.surface !== expectedSurface) throw new Error(`Bridge surface mismatch: expected ${expectedSurface}`);
  if (typeof candidate.request_id !== "string" || !candidate.request_id.trim()) throw new Error("Bridge request identity is invalid");
  if (typeof candidate.operation !== "string" || !candidate.operation.trim()) throw new Error("Bridge operation identity is invalid");
  if (!RESULT_STATUSES.has(candidate.status as BridgeStatus)) throw new Error("Bridge result status is invalid");
  if (!FINGERPRINT_RE.test(candidate.request_fingerprint ?? "") || !FINGERPRINT_RE.test(candidate.result_fingerprint ?? "")) {
    throw new Error("Bridge result fingerprint is invalid");
  }
  if (candidate.secret_values_persisted !== false) throw new Error("Bridge secret persistence invariant violated");
  if (
    candidate.authority !== false ||
    candidate.canon_authority !== false ||
    candidate.framework_write_authority !== false ||
    candidate.settlement_authority !== false
  ) {
    throw new Error("Bridge authority invariant violated");
  }
  if (candidate.status === "ok" ? candidate.error !== null : candidate.data !== null || candidate.error === null) {
    throw new Error("Bridge result status/data/error invariant violated");
  }
  if (candidate.status !== "ok") {
    if (!candidate.error || typeof candidate.error !== "object" || Array.isArray(candidate.error)) {
      throw new Error("Bridge public error envelope is invalid");
    }
    const publicError = candidate.error as Record<string, unknown>;
    const keys = Object.keys(publicError).sort().join("\0");
    const expectedKeys = candidate.status === "invalid"
      ? ["code", "messages", "mutation_performed"].sort().join("\0")
      : ["code", "mutation_performed"].sort().join("\0");
    if (
      keys !== expectedKeys ||
      typeof publicError.code !== "string" ||
      !PUBLIC_ERROR_CODE_RE.test(publicError.code) ||
      publicError.mutation_performed !== false
    ) {
      throw new Error("Bridge public error envelope is invalid");
    }
    if (
      candidate.status === "invalid" &&
      (publicError.code !== "invalid_request" ||
        !Array.isArray(publicError.messages) ||
        publicError.messages.length > 32 ||
        publicError.messages.some((message) => typeof message !== "string" || message.length > 256))
    ) {
      throw new Error("Bridge invalid-request diagnostics are invalid");
    }
  }
  if (
    expectedRequest &&
    (candidate.request_id !== expectedRequest.request_id ||
      candidate.operation !== expectedRequest.operation ||
      candidate.surface !== expectedRequest.surface)
  ) {
    throw new Error("Bridge result is not bound to its request");
  }
  if (expectedRequest && candidate.request_fingerprint !== await fingerprint(redactedRequest(expectedRequest))) {
    throw new Error("Bridge request fingerprint is not bound to its request");
  }
  const unsigned = Object.fromEntries(
    Object.entries(value as Record<string, unknown>).filter(([key]) => key !== "result_fingerprint"),
  );
  if (candidate.result_fingerprint !== await fingerprint(unsigned)) {
    throw new Error("Bridge result fingerprint does not bind the result envelope");
  }
  return candidate as BridgeResult<T>;
}

export async function parseHttpResult<T>(response: Response, expectedSurface: CoreSurface, request: BridgeRequest): Promise<BridgeResult<T>> {
  const value: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(`Host Bridge transport failed (HTTP ${response.status})`);
  }
  return assertEnvelope<T>(value, expectedSurface, request);
}

export class LocalHttpTransport implements BridgeTransport {
  readonly name = "local-http" as const;
  readonly requestSurface = "local_app" as const;

  available(): boolean {
    const token = localToken();
    return token.length > 0 && token !== TOKEN_PLACEHOLDER;
  }

  async invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>> {
    if (!this.available()) throw new Error("Local Quillframe Core host is not bound");
    const response = await fetch("/api/bridge/invoke", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-Quillframe-Studio-Token": localToken(),
      },
      body: JSON.stringify(request),
    });
    return parseHttpResult<T>(response, this.requestSurface, request);
  }
}

const hostedSessionExpiryListeners = new Set<() => void>();
let hostedSessionEpoch = 0;
let hostedSessionReady = false;
let hostedSessionAbort = new AbortController();

/** Close Core access before checking, ending, or disposing a hosted session. */
export function invalidateHostedSession(): number {
  hostedSessionReady = false;
  hostedSessionEpoch += 1;
  hostedSessionAbort.abort();
  hostedSessionAbort = new AbortController();
  return hostedSessionEpoch;
}

/** Only the still-current, verified session check may reopen Core access. */
export function activateHostedSession(epoch: number): boolean {
  if (epoch !== hostedSessionEpoch) return false;
  hostedSessionReady = true;
  return true;
}

function assertHostedSessionActive(epoch: number): void {
  if (!hostedSessionReady || epoch !== hostedSessionEpoch) {
    throw new Error("Hosted Core session is not verified or is no longer active");
  }
}

export function subscribeToHostedSessionExpiry(listener: () => void): () => void {
  hostedSessionExpiryListeners.add(listener);
  return () => { hostedSessionExpiryListeners.delete(listener); };
}

export class HostedHttpTransport implements BridgeTransport {
  readonly name = "hosted-http" as const;
  readonly requestSurface = "hosted_web" as const;

  available(): boolean {
    return hostedEndpoint().length > 0;
  }

  async invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>> {
    const endpoint = hostedEndpoint();
    if (!endpoint) throw new Error("Hosted Core endpoint must be a configured same-origin HTTPS origin");
    const epoch = hostedSessionEpoch;
    assertHostedSessionActive(epoch);
    const csrfToken = hostedCsrfToken();
    let response: Response;
    try {
      response = await fetch(`${endpoint}/api/core/bridge`, {
        method: "POST",
        credentials: "same-origin",
        redirect: "error",
        cache: "no-store",
        signal: hostedSessionAbort.signal,
        headers: { "Content-Type": "application/json", "X-Qf-Csrf": csrfToken },
        body: hostedRequestBody(request),
      });
    } catch (error) {
      assertHostedSessionActive(epoch);
      throw error;
    }
    assertHostedSessionActive(epoch);
    if (response.status === 401) {
      const listeners = [...hostedSessionExpiryListeners];
      invalidateHostedSession();
      for (const listener of listeners) {
        try { listener(); } catch { /* Preserve the original transport failure. */ }
      }
      throw new Error("Host Bridge transport failed (HTTP 401)");
    }
    try {
      const result = await parseHttpResult<T>(response, this.requestSurface, request);
      assertHostedSessionActive(epoch);
      return result;
    } catch (error) {
      assertHostedSessionActive(epoch);
      throw error;
    }
  }
}

export class TauriTransport implements BridgeTransport {
  readonly name = "tauri-ipc" as const;
  readonly requestSurface = "local_app" as const;

  available(): boolean {
    return typeof window !== "undefined" && typeof window.__TAURI__?.core?.invoke === "function";
  }

  async invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>> {
    const invoke = typeof window !== "undefined" ? window.__TAURI__?.core?.invoke : undefined;
    if (!invoke) throw new Error("Tauri Quillframe Core bridge is not available");
    const value = await invoke<unknown>("bridge_invoke", { request });
    return assertEnvelope<T>(value, this.requestSurface, request);
  }
}

export function normalizeBridgeDescription(raw: RawBridgeDescription): BridgeCapabilities {
  if (raw.schema !== "quillframe_host_bridge_description_v11") {
    throw new Error("Unexpected Host Bridge description schema");
  }
  if (
    raw.authority !== false ||
    raw.canon_authority !== false ||
    raw.framework_write_authority !== false ||
    raw.settlement_authority !== false ||
    raw.direct_core_store_access !== false
  ) {
    throw new Error("Bridge description authority invariant violated");
  }
  if (raw.contract_version !== BRIDGE_VERSION) {
    throw new Error(`Host Bridge version must be exactly ${BRIDGE_VERSION}`);
  }
  const operationContracts = raw.operation_contracts;
  if (!operationContracts || typeof operationContracts !== "object" || Array.isArray(operationContracts) || Object.keys(operationContracts).length === 0) {
    throw new Error("Bridge description operation_contracts metadata is required");
  }
  const kinds = new Set<OperationKind>(["query", "command", "authority_command", "semantic_command", "secret_command", "external_query", "external_handoff_prepare", "external_handoff", "external_handoff_result"]);
  const surfaces = new Set(["cli", "local_app", "hosted_web", "agent_package"]);
  for (const [operation, metadata] of Object.entries(operationContracts)) {
    if (!operation.trim() || !metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
      throw new Error(`Bridge operation metadata is invalid: ${operation || "<empty>"}`);
    }
    if (!kinds.has(metadata.kind)) throw new Error(`Bridge operation metadata kind is invalid: ${operation}`);
    if (!Array.isArray(metadata.required_args) || metadata.required_args.some((arg) => typeof arg !== "string" || !arg.trim())) {
      throw new Error(`Bridge operation metadata required_args is invalid: ${operation}`);
    }
    if (metadata.allowed_surfaces !== undefined) {
      if (!Array.isArray(metadata.allowed_surfaces) || metadata.allowed_surfaces.some((surface) => typeof surface !== "string" || !surfaces.has(surface)) || new Set(metadata.allowed_surfaces).size !== metadata.allowed_surfaces.length) {
        throw new Error(`Bridge operation metadata allowed_surfaces is invalid: ${operation}`);
      }
    }
  }
  const operations = Object.keys(operationContracts).sort();
  if (!Array.isArray(raw.operations) || raw.operations.join("\0") !== operations.join("\0")) {
    throw new Error("Bridge description operation set does not match its contracts");
  }
  return {
    frameworkVersion: raw.framework_version ?? null,
    contractVersion: raw.contract_version ?? null,
    surface: raw.surface ?? null,
    operations,
    operationContracts,
    deferredOperations: Object.keys(raw.deferred_operations ?? {}).sort(),
    authority: false,
  };
}

const localPathValue = /^(?:[A-Za-z]:[\\/]|\\\\|\/(?:Users|home|tmp|var|private|etc)(?:\/|$))/i;

function containsLocalPathKey(value: unknown, ancestors = new Set<object>()): boolean {
  if (typeof value === "string") return localPathValue.test(value);
  if (!value || typeof value !== "object" || ancestors.has(value)) return false;
  ancestors.add(value);
  try {
    const descriptors = Object.getOwnPropertyDescriptors(value);
    for (const [key, descriptor] of Object.entries(descriptors)) {
      if (!("value" in descriptor) || !descriptor.enumerable) continue;
      const normalized = key.toLowerCase().replaceAll("-", "_");
      if (normalized === "path" || normalized.endsWith("_path") || normalized.includes("local_path")) return true;
      if (containsLocalPathKey(descriptor.value, ancestors)) return true;
    }
    return false;
  } finally {
    ancestors.delete(value);
  }
}

/** Browser surfaces may reference Core-owned corpus IDs, never workstation paths. */
export function assertBridgeSurfaceArgs(surface: CoreSurface, operation: string, args: Record<string, unknown>): void {
  if (surface === "hosted_web" && operation.startsWith("corpus.") && containsLocalPathKey(args)) {
    throw new Error("Hosted Core cannot access a local corpus path");
  }
}

export class BridgeClient {
  constructor(readonly transport: BridgeTransport) {}

  get surface(): CoreSurface {
    return this.transport.requestSurface;
  }

  get transportName(): TransportName {
    return this.transport.name;
  }

  async invoke<T = unknown>(operation: string, args: Record<string, unknown> = {}): Promise<BridgeResult<T>> {
    assertBridgeSurfaceArgs(this.transport.requestSurface, operation, args);
    const request: BridgeRequest = {
      schema: REQUEST_SCHEMA,
      bridge_version: BRIDGE_VERSION,
      request_id: crypto.randomUUID(),
      operation,
      surface: this.transport.requestSurface,
      args,
      authority: false,
    };
    return this.transport.invoke<T>(request);
  }

  async describe(): Promise<BridgeCapabilities> {
    const response = await this.invoke<RawBridgeDescription>("bridge.describe");
    if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
    return normalizeBridgeDescription(response.data);
  }

  async subscribeAuthorRun<T = unknown>(runId: string, cursor: number): Promise<BridgeResult<T>> {
    return this.invoke<T>("author.run.events", { run_id: runId, cursor });
  }
}

export function detectBridgeTransport(): BridgeTransport | null {
  const tauri = new TauriTransport();
  if (tauri.available()) return tauri;
  const local = new LocalHttpTransport();
  if (local.available()) return local;
  const hosted = new HostedHttpTransport();
  if (hosted.available()) return hosted;
  return null;
}

let singleton: BridgeClient | null | undefined;

export function bridgeClient(): BridgeClient | null {
  if (singleton === undefined) {
    const transport = detectBridgeTransport();
    singleton = transport ? new BridgeClient(transport) : null;
  }
  return singleton;
}

export function bridgeTransportAvailable(): boolean {
  return bridgeClient() !== null;
}

export function studioSurface(): CoreSurface {
  return bridgeClient()?.surface ?? "hosted_web";
}

export function bridgeTransportName(): TransportName | "unbound" {
  return bridgeClient()?.transportName ?? "unbound";
}

export async function invokeBridge<T = unknown>(operation: string, args: Record<string, unknown> = {}): Promise<BridgeResult<T>> {
  const client = bridgeClient();
  if (!client) throw new Error("Quillframe Core host is not bound to this Studio surface");
  return client.invoke<T>(operation, args);
}

export function operationError(result: BridgeResult<unknown>): string {
  if (!result.error) return result.status;
  if (typeof result.error === "object" && result.error && "code" in result.error) {
    const code = (result.error as { code: unknown }).code;
    if (typeof code === "string" && PUBLIC_ERROR_CODE_RE.test(code)) return code;
  }
  return result.status;
}

/** Test-only reset. Product code should keep one transport binding for a page lifecycle. */
export function __resetBridgeClientForTests(): void {
  singleton = undefined;
  invalidateHostedSession();
}

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
  | "external_handoff"
  | "external_handoff_result";

const REQUEST_SCHEMA = "quillframe_studio_host_bridge_request_v1" as const;
const RESULT_SCHEMA = "quillframe_studio_host_bridge_result_v1" as const;
const TOKEN_PLACEHOLDER = "__QUILLFRAME_STUDIO_TOKEN__";

export interface BridgeRequest {
  schema: typeof REQUEST_SCHEMA;
  request_id: string;
  operation: string;
  surface: CoreSurface;
  args: Record<string, unknown>;
  authority: false;
}

export interface BridgeResult<T = unknown> {
  schema: typeof RESULT_SCHEMA;
  request_id: string;
  operation: string;
  surface: CoreSurface;
  status: BridgeStatus;
  request_fingerprint: string;
  result_fingerprint: string;
  data: T | null;
  error: unknown;
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
  version?: string;
  contract_version?: string;
  surface?: string | null;
  operations?: string[];
  supported_operations?: string[];
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

function hostedEndpoint(): string {
  return documentMeta("quillframe-studio-hosted-endpoint").replace(/\/$/, "");
}

function assertEnvelope<T>(value: unknown, expectedSurface: CoreSurface): asserts value is BridgeResult<T> {
  if (!value || typeof value !== "object") throw new Error("Bridge returned a non-object response");
  const candidate = value as Partial<BridgeResult<T>>;
  if (candidate.schema !== RESULT_SCHEMA) throw new Error("Unexpected bridge result schema");
  if (candidate.surface !== expectedSurface) throw new Error(`Bridge surface mismatch: expected ${expectedSurface}`);
  if (
    candidate.authority !== false ||
    candidate.canon_authority !== false ||
    candidate.framework_write_authority !== false ||
    candidate.settlement_authority !== false
  ) {
    throw new Error("Bridge authority invariant violated");
  }
}

async function parseHttpResult<T>(response: Response, expectedSurface: CoreSurface): Promise<BridgeResult<T>> {
  const value: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message = value && typeof value === "object" && "message" in value
      ? String((value as { message: unknown }).message)
      : `HTTP ${response.status}`;
    throw new Error(message);
  }
  assertEnvelope<T>(value, expectedSurface);
  return value;
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
    return parseHttpResult<T>(response, this.requestSurface);
  }
}

export class HostedHttpTransport implements BridgeTransport {
  readonly name = "hosted-http" as const;
  readonly requestSurface = "hosted_web" as const;

  available(): boolean {
    return hostedEndpoint().length > 0;
  }

  async invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>> {
    const endpoint = hostedEndpoint();
    if (!endpoint) throw new Error("Hosted Quillframe Core endpoint is not configured");
    const response = await fetch(`${endpoint}/api/bridge/invoke`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return parseHttpResult<T>(response, this.requestSurface);
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
    assertEnvelope<T>(value, this.requestSurface);
    return value;
  }
}

export function normalizeBridgeDescription(raw: RawBridgeDescription): BridgeCapabilities {
  if (raw.authority !== false || raw.canon_authority !== false || raw.framework_write_authority !== false || raw.settlement_authority !== false) {
    throw new Error("Bridge description authority invariant violated");
  }
  const operations = Array.from(new Set([...(raw.operations ?? []), ...(raw.supported_operations ?? [])])).sort();
  return {
    frameworkVersion: raw.framework_version ?? raw.version ?? null,
    contractVersion: raw.contract_version ?? null,
    surface: raw.surface ?? null,
    operations,
    operationContracts: raw.operation_contracts ?? {},
    deferredOperations: Object.keys(raw.deferred_operations ?? {}).sort(),
    authority: false,
  };
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
    const request: BridgeRequest = {
      schema: REQUEST_SCHEMA,
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
  if (typeof result.error === "string") return result.error;
  if (typeof result.error === "object" && result.error && "message" in result.error) {
    return String((result.error as { message: unknown }).message);
  }
  try {
    return JSON.stringify(result.error);
  } catch {
    return String(result.error);
  }
}

/** Test-only reset. Product code should keep one transport binding for a page lifecycle. */
export function __resetBridgeClientForTests(): void {
  singleton = undefined;
}

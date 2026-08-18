export type BridgeStatus = "ok" | "invalid" | "unsupported" | "failed" | "error";
export type StudioSurface = "local_app" | "hosted_web" | "tauri_local";
export type OperationKind = "query" | "command" | "authority_command";

const REQUEST_SCHEMA = "quillframe_studio_host_bridge_request_v1" as const;
const TOKEN_PLACEHOLDER = "__QUILLFRAME_STUDIO_TOKEN__";

export interface BridgeRequest {
  schema: typeof REQUEST_SCHEMA;
  request_id: string;
  operation: string;
  surface: StudioSurface;
  args: Record<string, unknown>;
  authority: false;
}

export interface BridgeResult<T = unknown> {
  schema: "quillframe_studio_host_bridge_result_v1";
  request_id: string;
  operation: string;
  surface: StudioSurface;
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
  allowed_surfaces?: Array<StudioSurface | "cli" | "agent_package">;
}

export interface BridgeDescription {
  schema: "quillframe_studio_host_bridge_description_v1";
  framework_version: string;
  contract_schema: string;
  contract_version: string;
  product_model: "one_product_one_core_many_transports";
  surface: StudioSurface | "cli" | "agent_package";
  supported_operations: string[];
  operation_contracts: Record<string, OperationContract>;
  deferred_operations: Record<string, string>;
  authority: false;
  canon_authority: false;
  framework_write_authority: false;
  settlement_authority: false;
  direct_core_store_access: false;
}

export interface BridgeTransport {
  readonly surface: StudioSurface;
  readonly name: "local-http" | "hosted-http" | "tauri-ipc";
  available(): boolean;
  invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>>;
}

type TauriInternals = {
  invoke?: <T>(command: string, args?: Record<string, unknown>) => Promise<T>;
};

declare global {
  interface Window {
    __TAURI_INTERNALS__?: TauriInternals;
  }
}

function meta(name: string): string {
  return document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content.trim() ?? "";
}

function localToken(): string {
  return meta("quillframe-studio-token");
}

function hostedEndpoint(): string {
  const configured = meta("quillframe-studio-hosted-endpoint");
  if (configured) return configured.replace(/\/$/, "");
  const vite = import.meta.env.VITE_QUILLFRAME_BRIDGE_URL?.trim();
  return vite ? vite.replace(/\/$/, "") : "";
}

function assertEnvelope<T>(value: unknown, expectedSurface: StudioSurface): asserts value is BridgeResult<T> {
  if (!value || typeof value !== "object") throw new Error("Bridge returned a non-object response");
  const candidate = value as Partial<BridgeResult<T>>;
  if (candidate.schema !== "quillframe_studio_host_bridge_result_v1") throw new Error("Unexpected bridge result schema");
  if (candidate.surface !== expectedSurface) throw new Error(`Bridge surface mismatch: expected ${expectedSurface}`);
  if (candidate.authority !== false || candidate.canon_authority !== false || candidate.framework_write_authority !== false || candidate.settlement_authority !== false) {
    throw new Error("Bridge authority invariant violated");
  }
}

async function readHttpResult<T>(response: Response, surface: StudioSurface): Promise<BridgeResult<T>> {
  const value: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message = value && typeof value === "object" && "message" in value
      ? String((value as { message: unknown }).message)
      : `HTTP ${response.status}`;
    throw new Error(message);
  }
  assertEnvelope<T>(value, surface);
  return value;
}

export class LocalHttpTransport implements BridgeTransport {
  readonly surface = "local_app" as const;
  readonly name = "local-http" as const;

  available(): boolean {
    const value = localToken();
    return value.length > 0 && value !== TOKEN_PLACEHOLDER;
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
    return readHttpResult<T>(response, this.surface);
  }
}

export class HostedHttpTransport implements BridgeTransport {
  readonly surface = "hosted_web" as const;
  readonly name = "hosted-http" as const;

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
    return readHttpResult<T>(response, this.surface);
  }
}

export class TauriTransport implements BridgeTransport {
  readonly surface = "tauri_local" as const;
  readonly name = "tauri-ipc" as const;

  available(): boolean {
    return typeof window.__TAURI_INTERNALS__?.invoke === "function";
  }

  async invoke<T>(request: BridgeRequest): Promise<BridgeResult<T>> {
    const invoke = window.__TAURI_INTERNALS__?.invoke;
    if (!invoke) throw new Error("Tauri Quillframe Core host is not available");
    const value = await invoke<unknown>("bridge_invoke", { request });
    assertEnvelope<T>(value, this.surface);
    return value;
  }
}

function detectTransport(): BridgeTransport | null {
  const tauri = new TauriTransport();
  if (tauri.available()) return tauri;
  const local = new LocalHttpTransport();
  if (local.available()) return local;
  const hosted = new HostedHttpTransport();
  if (hosted.available()) return hosted;
  return null;
}

export class BridgeClient {
  constructor(private readonly transport: BridgeTransport) {}

  get surface(): StudioSurface { return this.transport.surface; }
  get transportName(): BridgeTransport["name"] { return this.transport.name; }

  async invoke<T = unknown>(operation: string, args: Record<string, unknown> = {}): Promise<BridgeResult<T>> {
    if (!this.transport.available()) throw new Error("Quillframe Core transport is unavailable");
    const request: BridgeRequest = {
      schema: REQUEST_SCHEMA,
      request_id: crypto.randomUUID(),
      operation,
      surface: this.transport.surface,
      args,
      authority: false,
    };
    return this.transport.invoke<T>(request);
  }

  async describe(): Promise<BridgeResult<BridgeDescription>> {
    return this.invoke<BridgeDescription>("bridge.describe");
  }
}

let singleton: BridgeClient | null | undefined;

export function bridgeClient(): BridgeClient | null {
  if (singleton === undefined) {
    const transport = detectTransport();
    singleton = transport ? new BridgeClient(transport) : null;
  }
  return singleton;
}

export function bridgeTransportAvailable(): boolean {
  return bridgeClient() !== null;
}

export function studioSurface(): StudioSurface {
  return bridgeClient()?.surface ?? "hosted_web";
}

export function bridgeTransportName(): BridgeTransport["name"] | "unbound" {
  return bridgeClient()?.transportName ?? "unbound";
}

/** Compatibility wrapper for existing route code; all calls still flow through BridgeClient. */
export async function invokeBridge<T = unknown>(operation: string, args: Record<string, unknown> = {}): Promise<BridgeResult<T>> {
  const client = bridgeClient();
  if (!client) throw new Error("Quillframe Core host is not bound to this Studio surface");
  return client.invoke<T>(operation, args);
}

export function operationError(result: BridgeResult<unknown>): string {
  if (!result.error) return result.status;
  if (typeof result.error === "string") return result.error;
  if (typeof result.error === "object" && result.error && "message" in result.error) return String((result.error as { message: unknown }).message);
  try { return JSON.stringify(result.error); } catch { return String(result.error); }
}

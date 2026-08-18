export type BridgeStatus = "ok" | "invalid" | "unsupported" | "failed" | "error";
export type StudioSurface = "local_app" | "cloud_ui";

const TOKEN_PLACEHOLDER = "__QUILLFRAME_STUDIO_TOKEN__";

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

export interface DeferredOperation {
  kind: "query" | "command";
  reason: string;
  dependency?: string;
}

export interface OperationContract {
  kind: "query" | "command";
  core_basis: string;
  required_args: string[];
  allowed_surfaces?: StudioSurface[];
  mutation_scope?: string;
  model_execution?: boolean;
  project_write?: boolean;
  canon_write?: boolean;
  framework_write?: boolean;
  settlement?: boolean;
}

export interface BridgeDescription {
  schema: "quillframe_studio_host_bridge_description_v1";
  contract_schema: string;
  contract_version?: string;
  request_schema: string;
  result_schema: string;
  product_model: "one_product_many_hosts";
  surface: string | null;
  supported_operations: string[];
  operation_contracts?: Record<string, OperationContract>;
  deferred_operations: Record<string, DeferredOperation>;
  authority: false;
  canon_authority: false;
  framework_write_authority: false;
  settlement_authority: false;
  direct_core_store_access: false;
}

function token(): string {
  return document.querySelector<HTMLMetaElement>('meta[name="quillframe-studio-token"]')?.content.trim() ?? "";
}

export function bridgeTransportAvailable(): boolean {
  const value = token();
  return value.length > 0 && value !== TOKEN_PLACEHOLDER;
}

export function studioSurface(): StudioSurface {
  return bridgeTransportAvailable() ? "local_app" : "cloud_ui";
}

function assertEnvelope(value: unknown): asserts value is BridgeResult {
  if (!value || typeof value !== "object") throw new Error("Bridge returned a non-object response");
  const candidate = value as Partial<BridgeResult>;
  if (candidate.schema !== "quillframe_studio_host_bridge_result_v1") throw new Error("Unexpected bridge result schema");
  if (candidate.authority !== false || candidate.canon_authority !== false || candidate.framework_write_authority !== false || candidate.settlement_authority !== false) {
    throw new Error("Bridge authority invariant violated");
  }
}

export async function invokeBridge<T = unknown>(operation: string, args: Record<string, unknown> = {}): Promise<BridgeResult<T>> {
  if (!bridgeTransportAvailable()) {
    throw new Error("Quillframe Core host is not bound to this Studio surface");
  }

  const response = await fetch("/api/bridge/invoke", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-Quillframe-Studio-Token": token(),
    },
    body: JSON.stringify({
      schema: "quillframe_studio_host_bridge_request_v1",
      request_id: crypto.randomUUID(),
      operation,
      surface: "local_app",
      args,
      authority: false,
    }),
  });

  const value: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message = value && typeof value === "object" && "message" in value ? String((value as { message: unknown }).message) : `HTTP ${response.status}`;
    throw new Error(message);
  }
  assertEnvelope(value);
  return value as BridgeResult<T>;
}

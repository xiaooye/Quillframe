export type BridgeStatus = "ok" | "invalid" | "unsupported" | "error";

export interface BridgeResult<T = unknown> {
  schema: "novelforge_studio_host_bridge_result_v1";
  request_id: string;
  operation: string;
  surface: "local_app";
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

export interface BridgeDescription {
  schema: "novelforge_studio_host_bridge_description_v1";
  contract_schema: string;
  request_schema: string;
  result_schema: string;
  product_model: "one_product_many_hosts";
  surface: string | null;
  supported_operations: string[];
  deferred_operations: Record<string, DeferredOperation>;
  authority: false;
  canon_authority: false;
  framework_write_authority: false;
  settlement_authority: false;
  direct_core_store_access: false;
}

function token(): string {
  return document.querySelector<HTMLMetaElement>('meta[name="novelforge-studio-token"]')?.content ?? "";
}

function assertEnvelope(value: unknown): asserts value is BridgeResult {
  if (!value || typeof value !== "object") throw new Error("Bridge returned a non-object response");
  const candidate = value as Partial<BridgeResult>;
  if (candidate.schema !== "novelforge_studio_host_bridge_result_v1") throw new Error("Unexpected bridge result schema");
  if (candidate.authority !== false || candidate.canon_authority !== false || candidate.framework_write_authority !== false || candidate.settlement_authority !== false) {
    throw new Error("Bridge authority invariant violated");
  }
}

export async function invokeBridge<T = unknown>(operation: string, args: Record<string, unknown> = {}): Promise<BridgeResult<T>> {
  const response = await fetch("/api/bridge/invoke", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-NovelForge-Studio-Token": token(),
    },
    body: JSON.stringify({
      schema: "novelforge_studio_host_bridge_request_v1",
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

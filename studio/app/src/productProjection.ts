import { invokeBridge, type BridgeResult } from "./bridge";
import type { ProjectInspectData } from "./studio";
import "./styles/projection-workbenches.css";

export type SessionSummary = {
  session_id: string;
  resource_id: string;
  project_id?: string | null;
  role: string;
  task_mode?: string | null;
  transport?: string | null;
  backend?: string | null;
  status: string;
  run_count: number;
  checkpoint_count: number;
  session_event_count: number;
  latest_run_id?: string | null;
  latest_run_status?: string | null;
  version: number;
  payload_hash: string;
  updated_at: string;
};

export type SessionListProjection = {
  schema: "novelforge_runtime_sessions_projection_v1";
  count: number;
  sessions: SessionSummary[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

export type RunProjection = {
  run_id?: string | null;
  status?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  usage_class?: string | null;
  input_artifact_fingerprints: string[];
  output_artifact_fingerprints: string[];
};

export type CheckpointProjection = {
  checkpoint_id?: string | null;
  run_id?: string | null;
  workflow_step?: string | null;
  artifact_fingerprints: string[];
  pending_gate?: string | null;
  pending_handoff?: string | null;
  resume_policy?: string | null;
  created_at?: string | null;
};

export type SessionProjection = {
  schema: "novelforge_runtime_session_projection_v1";
  session: SessionSummary & {
    context_policy: {
      hidden_gold?: string | null;
      forbidden_context_classes: string[];
      allowed_artifact_ref_count: number;
      allowed_path_count: number;
      authority_snapshot_present: boolean;
      context_manifest_ref_present: boolean;
    };
    runs: RunProjection[];
    checkpoints: CheckpointProjection[];
    session_events: Array<{
      event_id?: string | null;
      type?: string | null;
      run_id?: string | null;
      artifact_fingerprints: string[];
      created_at?: string | null;
    }>;
    provider_session_id_exposed: false;
    external_session_ref_exposed: false;
    absolute_paths_exposed: false;
  };
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

export type RuntimeEvent = {
  event_id: string;
  event_type: string;
  resource_id: string;
  session_id?: string | null;
  run_id?: string | null;
  handoff_id?: string | null;
  authority_scope?: string | null;
  source_kind?: string | null;
  artifact_fingerprints: string[];
  payload_hash: string;
  created_at?: string | null;
  received_at: string;
};

export type EventsProjection = {
  schema: "novelforge_runtime_events_projection_v1";
  count: number;
  events: RuntimeEvent[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

export type ReceiptProjection = {
  receipt_id: string;
  resource_id: string;
  session_id: string;
  run_id: string;
  stage: string;
  subject_id: string;
  artifact_fingerprints: string[];
  semantic_jobs: Array<{
    job_id: string;
    contract_id: string;
    input_fingerprint: string;
    status: string;
    result_fingerprint?: string | null;
    worker_ref?: string | null;
  }>;
  guards: Array<{ guard_id: string; status: string; evidence_refs: string[] }>;
  created_at: string;
  authority: false;
};

export type ReceiptsProjection = {
  schema: "novelforge_run_receipts_projection_v1";
  count: number;
  receipts: ReceiptProjection[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

export type ContextProjection = Record<string, unknown> & {
  schema?: string;
  authority: false;
};

export type ProductProjectionBundle = {
  schema: "novelforge_product_projection_bundle_v1";
  project: ProjectInspectData;
  runtime: {
    sessions: SessionListProjection;
    selected_session: SessionProjection | null;
    events: EventsProjection | null;
    receipts: ReceiptsProjection | null;
  };
  context: ContextProjection | null;
  bridge_result_fingerprints: string[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  canon_authority: false;
  settlement_authority: false;
};

function requireData<T>(result: BridgeResult<T>, operation: string): T {
  if (result.status !== "ok" || !result.data) {
    let detail = "";
    try { detail = JSON.stringify(result.error); } catch { detail = String(result.error); }
    throw new Error(`${operation} failed${detail ? `: ${detail}` : ""}`);
  }
  return result.data;
}

function latestSession(sessions: SessionSummary[]): SessionSummary | undefined {
  return [...sessions].sort((a, b) => {
    const time = Date.parse(b.updated_at) - Date.parse(a.updated_at);
    if (Number.isFinite(time) && time !== 0) return time;
    return b.version - a.version;
  })[0];
}

export async function loadProductProjection(
  projectRoot: string,
  options: { contextManifest?: string; contextStage?: "writer_pre_draft" | "post_draft_critic" | "independent_reviewer" | "never" } = {},
): Promise<ProductProjectionBundle> {
  const root = projectRoot.trim();
  if (!root) throw new Error("project_root is required");

  const fingerprints: string[] = [];
  const projectResult = await invokeBridge<ProjectInspectData>("project.inspect", { project_root: root });
  fingerprints.push(projectResult.result_fingerprint);
  const project = requireData(projectResult, "project.inspect");

  const sessionsResult = await invokeBridge<SessionListProjection>("runtime.sessions.list", { project_root: root });
  fingerprints.push(sessionsResult.result_fingerprint);
  const sessions = requireData(sessionsResult, "runtime.sessions.list");
  const selected = latestSession(sessions.sessions);

  let selectedSession: SessionProjection | null = null;
  let events: EventsProjection | null = null;
  let receipts: ReceiptsProjection | null = null;
  if (selected) {
    const [sessionResult, eventsResult, receiptsResult] = await Promise.all([
      invokeBridge<SessionProjection>("runtime.session.get", { project_root: root, session_id: selected.session_id }),
      invokeBridge<EventsProjection>("runtime.events.list", { project_root: root, session_id: selected.session_id }),
      invokeBridge<ReceiptsProjection>("run.receipt.get", { project_root: root, session_id: selected.session_id }),
    ]);
    fingerprints.push(sessionResult.result_fingerprint, eventsResult.result_fingerprint, receiptsResult.result_fingerprint);
    selectedSession = requireData(sessionResult, "runtime.session.get");
    events = requireData(eventsResult, "runtime.events.list");
    receipts = requireData(receiptsResult, "run.receipt.get");
  }

  let context: ContextProjection | null = null;
  const manifest = options.contextManifest?.trim();
  if (manifest) {
    const contextResult = await invokeBridge<ContextProjection>("context.inspect", {
      project_root: root,
      manifest,
      ...(options.contextStage ? { stage: options.contextStage } : {}),
    });
    fingerprints.push(contextResult.result_fingerprint);
    context = requireData(contextResult, "context.inspect");
  }

  return {
    schema: "novelforge_product_projection_bundle_v1",
    project,
    runtime: {
      sessions,
      selected_session: selectedSession,
      events,
      receipts,
    },
    context,
    bridge_result_fingerprints: fingerprints,
    query_only: true,
    mutation_performed: false,
    authority: false,
    canon_authority: false,
    settlement_authority: false,
  };
}

export function downloadProjection(bundle: ProductProjectionBundle, fileName = "novelforge-projection.json") {
  const blob = new Blob([JSON.stringify(bundle, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

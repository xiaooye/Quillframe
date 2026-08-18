import type { BridgeCapabilities } from "../bridge";

export type AuthoringIntent = "write" | "revise" | "review" | "continuity" | "research";
export type AuthorTaskMode = "DRAFT" | "REVISE" | "AUDIT" | "RESEARCH";
export type Availability = "supported" | "awaiting_external" | "unbound";

export const AUTHORING_INTENT_TASK_MODE: Record<AuthoringIntent, AuthorTaskMode> = {
  write: "DRAFT",
  revise: "REVISE",
  review: "AUDIT",
  continuity: "AUDIT",
  research: "RESEARCH",
};

export const RUN_PROGRESS_STAGES = [
  { id: "context_frozen", en: "Context frozen", zh: "Context 已冻结" },
  { id: "story_preflight", en: "Story preflight", zh: "Story preflight" },
  { id: "character_simulation", en: "Character simulation", zh: "角色模拟" },
  { id: "reader_review", en: "Reader review", zh: "读者审查" },
  { id: "independent_review", en: "Independent review", zh: "独立语义审查" },
  { id: "continuity", en: "Continuity", zh: "连续性检查" },
] as const;

export type RunProgressStageId = (typeof RUN_PROGRESS_STAGES)[number]["id"];

export interface ProjectProjection {
  schema: "quillframe_project_projection_v1";
  authority: false;
  project: {
    project_id: string;
    title: string;
    language: string;
    project_schema_version: number;
    created_at?: string;
    updated_at?: string;
  };
  counts: Record<string, number>;
}

export interface ProjectCreateResult {
  schema: "quillframe_project_create_result_v1";
  project_id: string;
  created: true;
  authority: false;
}

export interface RevisionSaveResult {
  revision_id: string;
  content_fingerprint: string;
  deduplicated: boolean;
}

export interface AuthorRunStartResult {
  schema: "quillframe_author_run_start_result_v1";
  run_id: string;
  task_mode: string;
  target_ref: string | null;
  status: "awaiting_semantic" | string;
  request_fingerprint: string;
  raw_draft_visible: false;
  candidate_visible: false;
  authority: false;
  canon_authority: false;
  settlement_authority: false;
  message: string;
}

export type ContextRuntimeState =
  | "eligible"
  | "considered"
  | "selected"
  | "loaded"
  | "dropped_due_budget"
  | "visibility_excluded"
  | "lifecycle_excluded"
  | "stale"
  | "invalid";

export interface ContextRuntimeItem {
  source_object_id: string;
  profile_id: string | null;
  domain: string;
  authority: string;
  lifecycle: string;
  stage: string;
  state: ContextRuntimeState;
  reason_code: string | null;
  reason: string | null;
  estimated_tokens: number;
  actual_tokens: number | null;
  source_fingerprint: string | null;
  profile_fingerprint: string | null;
  selector: unknown;
  receipt: string | null;
}

export interface ContextRuntimeProjection {
  schema: "quillframe_context_runtime_inspector_v1" | string;
  run_id: string;
  context_freeze_id: string | null;
  context_fingerprint: string | null;
  states: ContextRuntimeState[];
  items: ContextRuntimeItem[];
  private_chain_of_thought_exposed: false;
  authority: false;
}

export interface InspectorListProjection<T = Record<string, unknown>> {
  schema: "quillframe_inspector_projection_v1";
  kind: string;
  project_id: string;
  items: T[];
  authority: false;
}

export interface CandidateRow {
  candidate_id: string;
  document_id?: string | null;
  revision_id?: string | null;
  run_id?: string | null;
  task_mode?: string;
  candidate_kind?: string;
  status?: string;
  content_fingerprint?: string;
  user_visible_gate?: string;
  created_at?: string;
}

export interface AcceptanceResult {
  schema: "quillframe_candidate_acceptance_result_v1";
  acceptance_id: string;
  candidate_id: string;
  candidate_fingerprint: string;
  accepted: true;
  settled: false;
  canon_mutated: false;
}

export interface SettlementResult {
  schema: "quillframe_settlement_result_v1";
  settlement_id: string;
  status: "settled" | "settlement_incomplete" | string;
  target_ref: string;
  canon_mutated: boolean;
  expected_before_fingerprint?: string;
  actual_before_fingerprint?: string;
}

export interface CoreConsumerRequirement {
  operation: string;
  userAction: string;
  minimalInput: string;
  minimalOutput: string;
  requiredErrors: string[];
  authorityExpectation: string;
  whyUiCannotImplement: string;
}

export const CORE_CONSUMER_REQUIREMENTS: CoreConsumerRequirement[] = [
  {
    operation: "project.list",
    userAction: "Open an existing Project without memorizing its stable id",
    minimalInput: "none or pagination cursor",
    minimalOutput: "project_id, title, language, last_opened_at",
    requiredErrors: ["host_unavailable"],
    authorityExpectation: "read-only projection; authority=false",
    whyUiCannotImplement: "Browser history/localStorage is not the canonical Project registry.",
  },
  {
    operation: "document.list",
    userAction: "Render the Binder from canonical Project documents",
    minimalInput: "project_id, optional document_kind",
    minimalOutput: "document_id, title, story_node_id, latest_revision_id, latest_content_fingerprint",
    requiredErrors: ["project_not_found"],
    authorityExpectation: "read-only projection; authority=false",
    whyUiCannotImplement: "The UI cannot infer manuscript structure from browser state or filesystem paths.",
  },
  {
    operation: "document.get",
    userAction: "Reload/restart Studio and restore the exact latest manuscript revision",
    minimalInput: "project_id, document_id",
    minimalOutput: "document metadata plus latest revision content/id/fingerprint/authority_class",
    requiredErrors: ["document_not_found", "revision_not_found"],
    authorityExpectation: "read-only; must preserve persisted authority_class",
    whyUiCannotImplement: "Persisting manuscript content in localStorage would create a second live authority.",
  },
  {
    operation: "model.connect",
    userAction: "Settings → AI & Models → Endpoint + Access Token → Test / Connect",
    minimalInput: "endpoint, access_token",
    minimalOutput: "service_id, connection/discovery state, discovered models/capability evidence or refs",
    requiredErrors: ["endpoint_unreachable", "authentication_failed", "unsupported_protocol", "discovery_failed"],
    authorityExpectation: "runtime observation only; secret value never returned",
    whyUiCannotImplement: "Provider protocols, discovery and secret storage are Core-owned.",
  },
  {
    operation: "model.services.list",
    userAction: "Show connected Model Services and available Models",
    minimalInput: "none",
    minimalOutput: "service metadata, credential_present boolean, discovered model/capability projections",
    requiredErrors: ["host_unavailable"],
    authorityExpectation: "read-only runtime projection; no token values",
    whyUiCannotImplement: "Endpoint history or vendor hostname is not provider health or capability evidence.",
  },
  {
    operation: "author.run.execute",
    userAction: "Continue a durably registered author Run through production semantic execution",
    minimalInput: "project_id, run_id or exact registered run receipt",
    minimalOutput: "typed run status plus candidate/result reference only after production gates",
    requiredErrors: ["semantic_pending", "model_unavailable", "context_failed", "review_failed", "cancelled"],
    authorityExpectation: "no raw-draft visibility; candidate only after Core user-visible gate",
    whyUiCannotImplement: "Semantic execution, Context Freeze and independent review are Core-owned.",
  },
  {
    operation: "run.events.list",
    userAction: "Show typed AI Dock progress without exposing private reasoning",
    minimalInput: "project_id, run_id",
    minimalOutput: "event_kind, stage/status, timestamp, safe display detail",
    requiredErrors: ["run_not_found"],
    authorityExpectation: "read-only runtime evidence; private CoT excluded",
    whyUiCannotImplement: "The UI cannot infer completed semantic stages from elapsed time or local animations.",
  },
  {
    operation: "candidate.review.get",
    userAction: "Review Incumbent vs Candidate with findings and independent evidence",
    minimalInput: "project_id, candidate_id",
    minimalOutput: "candidate/incumbent revision refs, diff source, findings, reader/character/continuity/independent evidence, fingerprints",
    requiredErrors: ["candidate_not_found", "review_pending", "stale_review"],
    authorityExpectation: "read-only evidence; exact candidate fingerprint bound",
    whyUiCannotImplement: "Candidate prose and semantic review evidence cannot be reconstructed from candidate table metadata.",
  },
  {
    operation: "settlement.preflight",
    userAction: "Open Settle… after explicit Acceptance",
    minimalInput: "project_id, acceptance_id, target_ref",
    minimalOutput: "expected_before_fingerprint, acceptance/candidate fingerprints, readiness status",
    requiredErrors: ["acceptance_not_found", "before_state_conflict", "not_settleable"],
    authorityExpectation: "read-only preflight; does not mutate Canon",
    whyUiCannotImplement: "settlement.apply requires exact canonical before-state that only Core may read.",
  },
];

export function operationAvailability(bound: boolean, capabilities: BridgeCapabilities | undefined, operation: string): Availability {
  if (!bound) return "unbound";
  if (!capabilities) return "awaiting_external";
  return capabilities.operations.includes(operation) ? "supported" : "awaiting_external";
}

export function loadedContextItems(projection: ContextRuntimeProjection | undefined): ContextRuntimeItem[] {
  return projection?.items.filter((item) => item.state === "loaded") ?? [];
}

export function consideredNotLoaded(projection: ContextRuntimeProjection | undefined): ContextRuntimeItem[] {
  return projection?.items.filter((item) => ["eligible", "considered", "selected", "dropped_due_budget"].includes(item.state) && item.state !== "loaded") ?? [];
}

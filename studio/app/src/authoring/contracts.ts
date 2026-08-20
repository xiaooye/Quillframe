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
  { id: "story_preflight", en: "Story preflight", zh: "故事 / Canon 预检" },
  { id: "character_simulation", en: "Character simulation", zh: "角色模拟" },
  { id: "reader_review", en: "Reader review", zh: "读者审查" },
  { id: "continuity", en: "Continuity", zh: "连续性检查" },
  { id: "independent_review", en: "Independent review", zh: "独立语义审查" },
] as const;

export type RunProgressStageId = (typeof RUN_PROGRESS_STAGES)[number]["id"];

export interface NativeProjectManifest {
  schema: "quillframe_project_v1_0";
  id: string;
  title: string;
  language: string;
  chapter_scope: "CH001";
}

export interface ProjectProjection {
  schema: "quillframe_project_inspection_v1_0";
  manifest: NativeProjectManifest;
  manifest_fingerprint: string;
  chapter_scope: "CH001";
  data_boundary: ".quillframe/data";
  authority: false;
  counts: Record<string, number>;
}

export interface ProjectCreateResult {
  schema: "quillframe_project_create_result_v1_0";
  manifest: NativeProjectManifest;
  manifest_fingerprint: string;
  chapter_scope: "CH001";
  data_boundary: ".quillframe/data";
  created: true;
  authority: false;
}

export interface ProjectRegistryItem {
  schema: "quillframe_project_registry_item_v1_0";
  id: string;
  title: string;
  language: string;
  chapter_scope: "CH001";
  manifest_fingerprint: string;
  data_boundary: ".quillframe/data";
  last_opened_at: string | null;
}

export interface ProjectListProjection {
  schema: "quillframe_project_list_v1_0";
  items: ProjectRegistryItem[];
  authority: false;
}

const exactKeys = (value: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(value).length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0 && !value.includes("\0");
const canonicalText = (value: unknown): value is string => text(value) && value === value.trim();
const fingerprint = (value: unknown): value is string => typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);

async function manifestFingerprint(manifest: NativeProjectManifest): Promise<string> {
  const cryptoApi = globalThis.crypto;
  if (!cryptoApi?.subtle) throw new Error("project_fingerprint_unavailable");
  const canonical = JSON.stringify({ chapter_scope: manifest.chapter_scope, id: manifest.id, language: manifest.language, schema: manifest.schema, title: manifest.title });
  const digest = await cryptoApi.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function assertManifestFingerprint(manifest: NativeProjectManifest, value: unknown): Promise<void> {
  if (!fingerprint(value) || value !== await manifestFingerprint(manifest)) throw new Error("project_fingerprint_invalid");
}

function parseManifest(value: unknown): NativeProjectManifest {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_manifest_invalid");
  const manifest = value as Record<string, unknown>;
  if (!exactKeys(manifest, ["schema", "id", "title", "language", "chapter_scope"])) throw new Error("project_manifest_invalid");
  if (manifest.schema !== "quillframe_project_v1_0" || manifest.chapter_scope !== "CH001") throw new Error("project_manifest_invalid");
  if (!text(manifest.id) || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(manifest.id)) throw new Error("project_manifest_invalid");
  if (!canonicalText(manifest.title) || !canonicalText(manifest.language)) throw new Error("project_manifest_invalid");
  return manifest as unknown as NativeProjectManifest;
}

export async function parseProjectProjection(value: unknown): Promise<ProjectProjection> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_projection_invalid");
  const result = value as Record<string, unknown>;
  if (!exactKeys(result, ["schema", "manifest", "manifest_fingerprint", "chapter_scope", "data_boundary", "authority", "counts"])) throw new Error("project_projection_invalid");
  if (result.schema !== "quillframe_project_inspection_v1_0" || result.chapter_scope !== "CH001" || result.data_boundary !== ".quillframe/data" || result.authority !== false || !fingerprint(result.manifest_fingerprint)) throw new Error("project_projection_invalid");
  const manifest = parseManifest(result.manifest);
  await assertManifestFingerprint(manifest, result.manifest_fingerprint);
  if (!result.counts || typeof result.counts !== "object" || Array.isArray(result.counts) || Object.values(result.counts).some((count) => typeof count !== "number" || !Number.isSafeInteger(count) || count < 0)) throw new Error("project_projection_invalid");
  return result as unknown as ProjectProjection;
}

export async function parseProjectListProjection(value: unknown): Promise<ProjectListProjection> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_list_invalid");
  const result = value as Record<string, unknown>;
  if (!exactKeys(result, ["schema", "items", "authority"]) || result.schema !== "quillframe_project_list_v1_0" || result.authority !== false || !Array.isArray(result.items)) throw new Error("project_list_invalid");
  for (const raw of result.items) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("project_list_invalid");
    const item = raw as Record<string, unknown>;
    if (!exactKeys(item, ["schema", "id", "title", "language", "chapter_scope", "manifest_fingerprint", "data_boundary", "last_opened_at"])) throw new Error("project_list_invalid");
    if (item.schema !== "quillframe_project_registry_item_v1_0") throw new Error("project_list_invalid");
    const manifest = parseManifest({ schema: "quillframe_project_v1_0", id: item.id, title: item.title, language: item.language, chapter_scope: item.chapter_scope });
    await assertManifestFingerprint(manifest, item.manifest_fingerprint);
    if (item.data_boundary !== ".quillframe/data" || (item.last_opened_at !== null && !text(item.last_opened_at))) throw new Error("project_list_invalid");
  }
  return result as unknown as ProjectListProjection;
}

export async function parseProjectCreateResult(value: unknown): Promise<ProjectCreateResult> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_create_invalid");
  const result = value as Record<string, unknown>;
  if (!exactKeys(result, ["schema", "manifest", "manifest_fingerprint", "chapter_scope", "data_boundary", "created", "authority"]) || result.schema !== "quillframe_project_create_result_v1_0" || result.chapter_scope !== "CH001" || result.data_boundary !== ".quillframe/data" || result.created !== true || result.authority !== false || !fingerprint(result.manifest_fingerprint)) throw new Error("project_create_invalid");
  const manifest = parseManifest(result.manifest);
  await assertManifestFingerprint(manifest, result.manifest_fingerprint);
  return result as unknown as ProjectCreateResult;
}

export interface DocumentListItem {
  document_id: string;
  story_node_id?: string | null;
  document_kind: string;
  title: string;
  created_at?: string;
  latest_revision_id?: string | null;
  latest_content_fingerprint?: string | null;
  latest_authority_class?: string | null;
  latest_revision_created_at?: string | null;
}

export interface DocumentListProjection {
  schema: "quillframe_document_list_projection_v1";
  project_id: string;
  document_kind?: string | null;
  items: DocumentListItem[];
  authority: false;
  canon_authority: false;
}

export interface DocumentRevisionProjection {
  revision_id: string;
  document_id: string;
  parent_revision_id?: string | null;
  content: string;
  content_fingerprint: string;
  created_at?: string;
  source?: string;
  authority_class: string;
  provenance?: Record<string, unknown>;
}

export interface DocumentProjection {
  schema: "quillframe_document_projection_v1";
  project_id: string;
  document: {
    document_id: string;
    story_node_id?: string | null;
    document_kind: string;
    title: string;
    created_at?: string;
  };
  latest_revision: DocumentRevisionProjection | null;
  authority: false;
}

export interface DocumentRevisionListProjection {
  schema: "quillframe_document_revision_list_v1";
  project_id: string;
  document_id: string;
  items: Array<Omit<DocumentRevisionProjection, "content">>;
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
  workflow?: { status: string; stage: string; cursor: number; authority: false };
}

export interface WorkflowRunEvent {
  schema: "quillframe_author_run_event_v1";
  project_id: string;
  run_id: string;
  chapter_id: "CH001";
  cursor: number;
  event_type: string;
  stage: string;
  payload: Record<string, unknown>;
  created_at: string;
  authority: false;
}

export interface WorkflowRunEventBatch {
  schema: "quillframe_author_run_event_batch_v1";
  project_id: string;
  run_id: string;
  events: WorkflowRunEvent[];
  next_cursor: number;
  authority: false;
}

export interface AuthorRunEvent {
  event_kind: string;
  created_at?: string;
  payload?: Record<string, unknown>;
}

export interface AuthorRunStatusProjection {
  schema: string;
  project_id: string;
  run_id: string;
  task_mode: string;
  target_ref?: string | null;
  status: string;
  result_fingerprint?: string | null;
  events: AuthorRunEvent[];
  candidate?: CandidateRow | null;
  authority: false;
}

export interface ProductionExecutionProjection {
  schema: string;
  project_id: string;
  run_id: string;
  status: string;
  awaiting?: string;
  candidate_visible: false | boolean;
  raw_draft_visible: false;
  independent_review_request?: Record<string, unknown>;
  authority: false;
}

export interface ModelProjection {
  model_id?: string;
  display_name?: string;
  protocol?: string;
  protocol_family?: string;
  context_window?: number | null;
  capabilities?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface ModelServiceProjection {
  schema?: string;
  service_id?: string;
  endpoint?: string;
  discovery_state?: string;
  credential_present?: boolean;
  last_checked_at?: string;
  models?: ModelProjection[];
  authority?: false;
}

export interface ModelServiceListProjection {
  schema: "quillframe_model_service_list_v1";
  items: ModelServiceProjection[];
  authority: false;
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
  effective_status?: string;
  content_fingerprint?: string;
  candidate_fingerprint?: string;
  user_visible_gate?: string;
  created_at?: string;
}

export interface CandidateReviewProjection {
  schema: "quillframe_candidate_review_projection_v1";
  project_id: string;
  candidate: CandidateRow & {
    candidate_fingerprint: string;
    persisted_status: string;
    effective_status: string;
  };
  candidate_revision: DocumentRevisionProjection;
  incumbent_revision: DocumentRevisionProjection | null;
  diff: { diff?: string[] } | null;
  evidence: {
    reader: Record<string, unknown>;
    character: Record<string, unknown>;
    continuity: Record<string, unknown>;
    independent: Record<string, unknown>;
    production_readiness: Record<string, unknown> | null;
    user_visible_gate: Record<string, unknown>;
  };
  revision_request?: CandidateRevisionRequestResult | null;
  private_reasoning_exposed: false;
  authority: false;
  canon_authority: false;
  settlement_authority: false;
}

export interface CandidateVisibleProjection {
  schema: "quillframe_user_visible_candidate_v1";
  project_id: string;
  candidate_id: string;
  candidate_fingerprint: string;
  document_id?: string | null;
  revision_id?: string | null;
  content: string;
  authority_class?: string | null;
  production_release: Record<string, unknown>;
  content_access: "production_release_only";
  accepted: boolean;
  settled: false;
  private_reasoning_exposed: false;
  authority: false;
  canon_authority: false;
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

export interface CandidateRejectionResult {
  schema: "quillframe_candidate_rejection_result_v1";
  candidate_id: string;
  candidate_fingerprint: string;
  before_status: "review_draft";
  status: "rejected";
  canon_mutated: false;
  settled: false;
  authority: false;
}

export interface CandidateRevisionRequestResult {
  schema: "quillframe_candidate_revision_request_result_v1";
  revision_request_id: string;
  candidate_id: string;
  candidate_fingerprint: string;
  persisted_candidate_status: string;
  effective_status: "revision_requested";
  revision_request: Record<string, unknown>;
  next_action: {
    operation: "author.run.start";
    task_mode: "REVISE";
    target_ref: string;
    requires_explicit_user_action: true;
    auto_started: false;
    source_candidate_id: string;
    source_candidate_fingerprint: string;
  };
  canon_mutated: false;
  settled: false;
  authority: false;
}

export interface SettlementPreflight {
  schema: "quillframe_settlement_preflight_v1";
  project_id: string;
  acceptance_id: string;
  candidate_id: string;
  candidate_fingerprint: string;
  document_id: string;
  revision_id: string;
  target_ref: string;
  expected_before_fingerprint: string;
  current_before_fingerprint: string;
  settleable: true;
  mutation_performed: false;
  canon_mutated: false;
  authority: false;
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
    minimalInput: "optional limit",
    minimalOutput: "id, title, language, chapter_scope, manifest_fingerprint, data_boundary, last_opened_at",
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
    operation: "document.open",
    userAction: "Reload/restart Studio and restore the exact latest manuscript revision",
    minimalInput: "project_id, document_id",
    minimalOutput: "document metadata plus latest revision content/id/fingerprint/authority_class",
    requiredErrors: ["document_not_found"],
    authorityExpectation: "read-only; persisted authority_class is preserved",
    whyUiCannotImplement: "Persisting manuscript content in localStorage would create a second live authority.",
  },
  {
    operation: "model.service.add",
    userAction: "AI & Models → Endpoint + Access Token → Test / Connect",
    minimalInput: "endpoint, access_token",
    minimalOutput: "service_id, discovery state, discovered model/capability evidence",
    requiredErrors: ["model_discovery_failed", "network_request_failed", "model_protocol_unresolved"],
    authorityExpectation: "runtime observation only; secret value never returned",
    whyUiCannotImplement: "Protocol discovery and secret storage are Core-owned.",
  },
  {
    operation: "model.service.list",
    userAction: "Show connected Model Services",
    minimalInput: "none",
    minimalOutput: "service metadata and credential_present without token values",
    requiredErrors: ["host_unavailable"],
    authorityExpectation: "read-only runtime projection",
    whyUiCannotImplement: "Endpoint history is not provider health or capability evidence.",
  },
  {
    operation: "author.run.execute",
    userAction: "Continue a registered DRAFT/REVISE run through production semantic execution",
    minimalInput: "project_id, run_id, service_id, instruction, reader_grip, authoritative rule_material",
    minimalOutput: "typed run status; normally awaiting_external before independent review",
    requiredErrors: ["semantic_pending", "stale_conflict", "failed_gate", "model_unavailable"],
    authorityExpectation: "no raw-draft visibility; no same-runtime independent substitution",
    whyUiCannotImplement: "Semantic execution, Context Freeze and independent review are Core-owned.",
  },
  {
    operation: "author.run.status",
    userAction: "Show typed AI Dock progress without exposing private reasoning",
    minimalInput: "project_id, run_id",
    minimalOutput: "status plus persisted typed events and safe Candidate projection",
    requiredErrors: ["run_not_found"],
    authorityExpectation: "read-only runtime evidence; private CoT excluded",
    whyUiCannotImplement: "Studio must not infer completed stages from elapsed time or animation.",
  },
  {
    operation: "candidate.review.get",
    userAction: "Review Incumbent vs Candidate with exact review evidence",
    minimalInput: "project_id, candidate_id",
    minimalOutput: "candidate/incumbent revision, diff, Reader/Character/Continuity/Independent/readiness evidence",
    requiredErrors: ["candidate_not_found", "review_pending", "stale_review"],
    authorityExpectation: "read-only evidence bound to exact Candidate fingerprint",
    whyUiCannotImplement: "Review prose/evidence cannot be reconstructed from browser state or candidate metadata.",
  },
  {
    operation: "candidate.visible.get",
    userAction: "Read the exact released production manuscript after the user-visible gate passes",
    minimalInput: "project_id, candidate_id",
    minimalOutput: "released candidate content, exact candidate/revision fingerprint, production release evidence",
    requiredErrors: ["candidate_not_found", "production_release_missing", "production_release_invalid", "stale_review"],
    authorityExpectation: "released production manuscript only; Core withholds content unless the exact candidate has a valid production release",
    whyUiCannotImplement: "The UI must not reconstruct or reveal pre-release manuscript content from candidate metadata, checkpoints, or local state.",
  },
  {
    operation: "candidate.reject",
    userAction: "Explicitly reject the exact Review Draft",
    minimalInput: "project_id, candidate_id, candidate_fingerprint, authorization, idempotency_key",
    minimalOutput: "rejected state and receipt projection",
    requiredErrors: ["candidate_not_found", "candidate_fingerprint_mismatch", "stale_state"],
    authorityExpectation: "Candidate lifecycle mutation only; no Canon/Settlement write",
    whyUiCannotImplement: "Candidate lifecycle belongs to Core persistence.",
  },
  {
    operation: "candidate.revision.request",
    userAction: "Request a revision of the exact Review Draft",
    minimalInput: "project_id, candidate_id, candidate_fingerprint, revision_request, authorization, idempotency_key",
    minimalOutput: "durable revision request plus explicit REVISE next action; auto_started=false",
    requiredErrors: ["candidate_not_found", "candidate_fingerprint_mismatch", "stale_state"],
    authorityExpectation: "does not auto-run REVISE and does not mutate Canon",
    whyUiCannotImplement: "A browser flag must not impersonate durable Candidate state.",
  },
  {
    operation: "settlement.preflight",
    userAction: "Open Settle… after explicit Acceptance",
    minimalInput: "project_id, acceptance_id, target_ref",
    minimalOutput: "exact expected_before_fingerprint and settleability binding",
    requiredErrors: ["acceptance_not_found", "not_settleable"],
    authorityExpectation: "read-only preflight; no Canon mutation",
    whyUiCannotImplement: "settlement.apply requires the exact current Canon before-state that only Core may read.",
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

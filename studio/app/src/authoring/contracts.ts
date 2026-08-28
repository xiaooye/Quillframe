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
}

export interface ProjectProjection {
  schema: "quillframe_project_inspection_v1_0";
  manifest: NativeProjectManifest;
  manifest_fingerprint: string;
  scope: "novel";
  data_boundary: ".quillframe/data";
  authority: false;
  counts: Record<string, number>;
}

export interface ProjectCreateResult {
  schema: "quillframe_project_create_result_v1_0";
  manifest: NativeProjectManifest;
  manifest_fingerprint: string;
  scope: "novel";
  data_boundary: ".quillframe/data";
  created: true;
  authority: false;
}

export interface ProjectRegistryItem {
  schema: "quillframe_project_registry_item_v1_0";
  id: string;
  title: string;
  language: string;
  scope: "novel";
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
  const canonical = JSON.stringify({ id: manifest.id, language: manifest.language, schema: manifest.schema, title: manifest.title });
  const digest = await cryptoApi.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function assertManifestFingerprint(manifest: NativeProjectManifest, value: unknown): Promise<void> {
  if (!fingerprint(value) || value !== await manifestFingerprint(manifest)) throw new Error("project_fingerprint_invalid");
}

function parseManifest(value: unknown): NativeProjectManifest {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_manifest_invalid");
  const manifest = value as Record<string, unknown>;
  if (!exactKeys(manifest, ["schema", "id", "title", "language"])) throw new Error("project_manifest_invalid");
  if (manifest.schema !== "quillframe_project_v1_0") throw new Error("project_manifest_invalid");
  if (!text(manifest.id) || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(manifest.id)) throw new Error("project_manifest_invalid");
  if (!canonicalText(manifest.title) || !canonicalText(manifest.language)) throw new Error("project_manifest_invalid");
  return manifest as unknown as NativeProjectManifest;
}

export async function parseProjectProjection(value: unknown): Promise<ProjectProjection> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_projection_invalid");
  const result = value as Record<string, unknown>;
  if (!exactKeys(result, ["schema", "manifest", "manifest_fingerprint", "scope", "data_boundary", "authority", "counts"])) throw new Error("project_projection_invalid");
  if (result.schema !== "quillframe_project_inspection_v1_0" || result.scope !== "novel" || result.data_boundary !== ".quillframe/data" || result.authority !== false || !fingerprint(result.manifest_fingerprint)) throw new Error("project_projection_invalid");
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
    if (!exactKeys(item, ["schema", "id", "title", "language", "scope", "manifest_fingerprint", "data_boundary", "last_opened_at"])) throw new Error("project_list_invalid");
    if (item.schema !== "quillframe_project_registry_item_v1_0" || item.scope !== "novel") throw new Error("project_list_invalid");
    const manifest = parseManifest({ schema: "quillframe_project_v1_0", id: item.id, title: item.title, language: item.language });
    await assertManifestFingerprint(manifest, item.manifest_fingerprint);
    if (item.data_boundary !== ".quillframe/data" || (item.last_opened_at !== null && !text(item.last_opened_at))) throw new Error("project_list_invalid");
  }
  return result as unknown as ProjectListProjection;
}

export async function parseProjectCreateResult(value: unknown): Promise<ProjectCreateResult> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("project_create_invalid");
  const result = value as Record<string, unknown>;
  if (!exactKeys(result, ["schema", "manifest", "manifest_fingerprint", "scope", "data_boundary", "created", "authority"]) || result.schema !== "quillframe_project_create_result_v1_0" || result.scope !== "novel" || result.data_boundary !== ".quillframe/data" || result.created !== true || result.authority !== false || !fingerprint(result.manifest_fingerprint)) throw new Error("project_create_invalid");
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
  session_id?: string;
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
  chapter_id: string;
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
  execution_journal?: unknown;
  authority: false;
}

export interface ExecutionJournalCall {
  call_id: string;
  stage_key: string;
  runtime_role: string;
  state: "dispatched" | "confirmed" | "unconfirmed" | "cancelled";
  error_code: string | null;
}

export interface ExecutionJournalProgress {
  run_status: string;
  active_executor: boolean;
  cancel_requested: boolean;
  confirmed_call_count: number;
  dispatched_call_count: number;
  model_call_budget: number | null;
  pending_calls: Array<ExecutionJournalCall & { state: "dispatched" | "unconfirmed" }>;
  last_call: ExecutionJournalCall | null;
  latest_stage_failure: { code: string; mechanism: string } | null;
  latest_gate_rejection: { mechanism: string; stage_result_fingerprint: string } | null;
}

export function projectExecutionJournal(value: unknown, expected: { project_id: string; run_id: string; document_id: string }): ExecutionJournalProgress | undefined {
  if (![expected.project_id, expected.run_id, expected.document_id].every(canonicalText) || !reviewRecord(value)
    || value.project_id !== expected.project_id || value.run_id !== expected.run_id || value.target_ref !== expected.document_id
    || value.authority !== false || !canonicalText(value.status) || !reviewRecord(value.execution_journal)) return undefined;
  const journal = value.execution_journal;
  if (journal.schema !== "quillframe_production_execution_journal_v1" || journal.run_id !== expected.run_id
    || journal.authority !== false || journal.private_payloads_visible !== false
    || typeof journal.active_executor !== "boolean" || typeof journal.cancel_requested !== "boolean"
    || journal.request_fingerprint !== null && !fingerprint(journal.request_fingerprint)
    || !Number.isSafeInteger(journal.confirmed_call_count) || (journal.confirmed_call_count as number) < 0
    || !Number.isSafeInteger(journal.dispatched_call_count) || (journal.dispatched_call_count as number) < 0
    || journal.model_call_budget !== null && (!Number.isSafeInteger(journal.model_call_budget) || (journal.model_call_budget as number) < 1)
    || !Array.isArray(journal.calls) || !Array.isArray(journal.unconfirmed_call_ids)) return undefined;
  const calls: ExecutionJournalCall[] = [];
  const callIds = new Set<string>();
  for (const raw of journal.calls) {
    if (!reviewRecord(raw) || !canonicalText(raw.call_id) || callIds.has(raw.call_id)
      || !canonicalText(raw.stage_key) || !canonicalText(raw.runtime_role)
      || !["dispatched", "confirmed", "unconfirmed", "cancelled"].includes(String(raw.state))
      || raw.error_code !== null && !canonicalText(raw.error_code)) return undefined;
    callIds.add(raw.call_id);
    calls.push({ call_id: raw.call_id, stage_key: raw.stage_key, runtime_role: raw.runtime_role,
      state: raw.state as ExecutionJournalCall["state"], error_code: raw.error_code as string | null });
  }
  const pending = calls.filter((call): call is ExecutionJournalCall & { state: "dispatched" | "unconfirmed" } => call.state === "dispatched" || call.state === "unconfirmed");
  if (journal.dispatched_call_count !== calls.length || journal.confirmed_call_count !== calls.filter((call) => call.state === "confirmed").length
    || journal.model_call_budget !== null && calls.length > (journal.model_call_budget as number)
    || journal.unconfirmed_call_ids.length !== pending.length || new Set(journal.unconfirmed_call_ids).size !== pending.length
    || journal.unconfirmed_call_ids.some((id) => !canonicalText(id) || !pending.some((call) => call.call_id === id))) return undefined;
  let latestFailure: ExecutionJournalProgress["latest_stage_failure"] = null;
  let latestGateRejection: ExecutionJournalProgress["latest_gate_rejection"] = null;
  if (Array.isArray(value.events)) {
    for (let index = value.events.length - 1; index >= 0; index -= 1) {
      const event = value.events[index];
      if (!reviewRecord(event) || event.event_kind !== "production_stage_failed") continue;
      const payload = event.payload;
      if (reviewRecord(payload) && typeof payload.code === "string" && /^[a-z][a-z0-9_]{0,95}$/.test(payload.code)
        && typeof payload.mechanism === "string" && /^[a-z][a-z0-9_]{0,95}$/.test(payload.mechanism)) latestFailure = { code: payload.code, mechanism: payload.mechanism };
      break;
    }
    for (let index = value.events.length - 1; index >= 0; index -= 1) {
      const event = value.events[index];
      if (!reviewRecord(event) || event.event_kind !== "production_gate_rejected") continue;
      const payload = event.payload;
      if (reviewRecord(payload) && typeof payload.mechanism === "string" && /^[a-z][a-z0-9_]{0,95}$/.test(payload.mechanism)
        && fingerprint(payload.stage_result_fingerprint)) latestGateRejection = { mechanism: payload.mechanism, stage_result_fingerprint: payload.stage_result_fingerprint };
      break;
    }
  }
  // Only public progress metadata leaves this projection; prompts, results and control permissions do not.
  return { run_status: value.status, active_executor: journal.active_executor, cancel_requested: journal.cancel_requested,
    confirmed_call_count: journal.confirmed_call_count as number, dispatched_call_count: journal.dispatched_call_count as number,
    model_call_budget: journal.model_call_budget as number | null, pending_calls: pending, last_call: calls.at(-1) ?? null,
    latest_stage_failure: latestFailure, latest_gate_rejection: latestGateRejection };
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
  enabled?: boolean | 0 | 1;
  discovery_state?: string;
  credential_present?: boolean | 0 | 1;
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
  authorized_by: string;
  authorization: Record<string, unknown>;
  request_fingerprint: string;
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
  preflight_fingerprint?: string;
  narrative_proposal?: Record<string, unknown> | null;
  reader_observations?: Record<string, unknown>[];
}

export interface SettlementResult {
  schema: "quillframe_settlement_result_v1";
  settlement_id: string;
  status: "settled" | "settlement_incomplete" | string;
  target_ref: string;
  canon_mutated: boolean;
  before_fingerprint?: string;
  after_fingerprint?: string;
  state_delta?: { before: Record<string, unknown> | null; after: Record<string, unknown> };
  expected_before_fingerprint?: string;
  actual_before_fingerprint?: string;
}

export function projectReaderEvidence(value: unknown, candidateFingerprint: string): {
  bound: boolean; status?: string; summary?: string; strongest_positive?: string; strongest_problem?: string; evidence_refs: string[];
} {
  if (!reviewRecord(value) || !reviewRecord(value.judgment) || !fingerprint(candidateFingerprint)
    || value.judgment.artifact_fingerprint !== candidateFingerprint) return { bound: false, evidence_refs: [] };
  const judgment = value.judgment;
  return {
    bound: true,
    status: typeof judgment.status === "string" ? judgment.status : undefined,
    summary: typeof judgment.report === "string" ? judgment.report : typeof judgment.summary === "string" ? judgment.summary : undefined,
    strongest_positive: typeof judgment.strongest_positive === "string" ? judgment.strongest_positive : undefined,
    strongest_problem: typeof judgment.strongest_problem === "string" ? judgment.strongest_problem : undefined,
    evidence_refs: (Array.isArray(judgment.evidence_refs) ? judgment.evidence_refs : Array.isArray(judgment.findings) ? judgment.findings : [])
      .filter((item): item is string => typeof item === "string"),
  };
}

export interface ChapterItem {
  chapter_id: string;
  title: string;
  ordinal: number;
  parent_id: string | null;
  document_id: string;
  current_revision_id?: string | null;
  current_acceptance_id?: string | null;
  needs_review?: boolean;
}

export interface ChapterListProjection {
  schema: "quillframe_chapter_list_v1";
  project_id: string;
  items: ChapterItem[];
  authority: false;
}

export function parseRuntimeInspectorList<T>(value: unknown, projectId: string, kind: "sessions" | "runs" | "checkpoints" | "receipts"): InspectorListProjection<T> {
  const identity = { sessions: "session_id", runs: "run_id", checkpoints: "checkpoint_id", receipts: "receipt_id" }[kind];
  if (!canonicalText(projectId) || !reviewRecord(value) || value.schema !== "quillframe_inspector_projection_v1"
    || value.project_id !== projectId || value.kind !== kind || value.authority !== false || !Array.isArray(value.items)
    || value.items.length > 500) throw new Error("runtime_inspector_binding_invalid");
  const ids = new Set<string>();
  for (const row of value.items) {
    if (!reviewRecord(row) || !canonicalText(row[identity]) || ids.has(row[identity] as string)
      || kind === "runs" && (!canonicalText(row.task_mode) || !canonicalText(row.status)
        || row.target_ref !== null && !canonicalText(row.target_ref))) throw new Error("runtime_inspector_binding_invalid");
    ids.add(row[identity] as string);
  }
  return value as unknown as InspectorListProjection<T>;
}

export function resolveRuntimeRunSelection(value: unknown, expected: { project_id: string; run_id: string; task_mode: string; target_ref: string }, chapters: unknown): {
  project_id: string; run_id: string; task_mode: "DRAFT" | "REVISE"; chapter_id: string; document_id: string;
} {
  if (![expected.project_id, expected.run_id, expected.target_ref].every(canonicalText) || !["DRAFT", "REVISE"].includes(expected.task_mode)
    || !reviewRecord(value) || value.schema !== "quillframe_production_run_status_v1" || value.project_id !== expected.project_id
    || value.run_id !== expected.run_id || value.task_mode !== expected.task_mode || value.target_ref !== expected.target_ref
    || !canonicalText(value.status) || value.authority !== false) throw new Error("runtime_run_selection_binding_invalid");
  const registered = parseChapterList(chapters, expected.project_id);
  const chapter = registered.items.find((item) => item.document_id === value.target_ref);
  if (!chapter) throw new Error("runtime_run_selection_target_unknown");
  return { project_id: expected.project_id, run_id: expected.run_id, task_mode: expected.task_mode as "DRAFT" | "REVISE",
    chapter_id: chapter.chapter_id, document_id: chapter.document_id };
}

export function parseChapterList(value: unknown, projectId: string): ChapterListProjection {
  if (!reviewRecord(value) || value.schema !== "quillframe_chapter_list_v1" || value.project_id !== projectId
    || value.authority !== false || !Array.isArray(value.items)) throw new Error("chapter_list_invalid");
  const chapterIds = new Set<string>();
  const documentIds = new Set<string>();
  for (const item of value.items) {
    if (!reviewRecord(item) || !canonicalText(item.chapter_id) || !canonicalText(item.document_id) || !canonicalText(item.title)
      || !Number.isSafeInteger(item.ordinal) || (item.ordinal as number) < 0 || item.parent_id !== null && !canonicalText(item.parent_id)
      || item.current_revision_id !== undefined && item.current_revision_id !== null && !canonicalText(item.current_revision_id)
      || item.current_acceptance_id !== undefined && item.current_acceptance_id !== null && !canonicalText(item.current_acceptance_id)
      || item.needs_review !== undefined && typeof item.needs_review !== "boolean"
      || chapterIds.has(item.chapter_id) || documentIds.has(item.document_id)) throw new Error("chapter_list_invalid");
    chapterIds.add(item.chapter_id); documentIds.add(item.document_id);
  }
  return value as unknown as ChapterListProjection;
}

export type ReaderIntent = Partial<Record<"reader_question" | "visible_reward" | "character_choice" | "cost" | "net_change" | "next_chapter_pull", string>>;
const readerIntentKeys = ["reader_question", "visible_reward", "character_choice", "cost", "net_change", "next_chapter_pull"] as const;

function validReaderIntent(value: unknown): value is ReaderIntent {
  return reviewRecord(value) && Object.keys(value).every((key) => (readerIntentKeys as readonly string[]).includes(key) && typeof value[key] === "string");
}

export interface PlanItem {
  plan_id: string;
  target_ref: string;
  title: string;
  content: string;
  version: number;
  status: string;
  reader_intent?: ReaderIntent;
  expectation_refs?: string[];
  horizon?: Record<string, unknown> | null;
}

export interface PlanInspection {
  schema: "quillframe_plan_inspection_v1";
  project_id: string;
  items: PlanItem[];
  authority: false;
}

export function parsePlanInspection(value: unknown, projectId: string, target?: string): PlanInspection {
  if (!reviewRecord(value) || value.schema !== "quillframe_plan_inspection_v1" || value.project_id !== projectId
    || value.authority !== false || !Array.isArray(value.items)) throw new Error("plan_inspection_invalid");
  for (const item of value.items) {
    if (!reviewRecord(item) || !canonicalText(item.plan_id) || !canonicalText(item.target_ref)
      || target !== undefined && item.target_ref !== target || !canonicalText(item.title) || typeof item.content !== "string"
      || !Number.isSafeInteger(item.version) || (item.version as number) < 1 || !canonicalText(item.status)
      || item.reader_intent !== undefined && !validReaderIntent(item.reader_intent)
      || item.expectation_refs !== undefined && (!Array.isArray(item.expectation_refs) || !item.expectation_refs.every(canonicalText))
      || item.horizon !== undefined && item.horizon !== null && !reviewRecord(item.horizon)) throw new Error("plan_inspection_invalid");
  }
  return value as unknown as PlanInspection;
}

export function parsePlanSave(value: unknown, expected: { project_id: string; target_ref: string; title: string; content: string; expected_version: number; reader_intent?: ReaderIntent; expectation_refs?: string[] }): PlanItem {
  if (!reviewRecord(value) || value.schema !== "quillframe_plan_save_result_v1" || value.project_id !== expected.project_id
    || value.authority !== false || value.target_ref !== expected.target_ref || value.title !== expected.title
    || value.content !== expected.content || value.version !== expected.expected_version + 1
    || expected.reader_intent !== undefined && (!validReaderIntent(value.reader_intent)
      || readerIntentKeys.some((key) => value.reader_intent && (value.reader_intent as ReaderIntent)[key] !== expected.reader_intent?.[key]))
    || expected.expectation_refs !== undefined && (!Array.isArray(value.expectation_refs)
      || value.expectation_refs.length !== expected.expectation_refs.length || value.expectation_refs.some((ref, index) => ref !== expected.expectation_refs?.[index]))) throw new Error("plan_save_binding_invalid");
  parsePlanInspection({ schema: "quillframe_plan_inspection_v1", project_id: expected.project_id, items: [value], authority: false }, expected.project_id, expected.target_ref);
  return value as unknown as PlanItem;
}

export interface StorySource {
  source_state: "current" | "stale" | "untracked";
  source_chapter_id: string | null;
}

export interface StoryInspection {
  schema: "quillframe_story_inspection_v1";
  project_id: string;
  authority: false;
  characters: Array<StorySource & { character_id: string; name: string; agenda: unknown; voice_notes: unknown; state: unknown; authority_class: string }>;
  relationships: Array<StorySource & { relationship_id: string; participant_a: string; participant_b: string; relationship_type: string; state: unknown; authority_class: string }>;
  timeline: Array<StorySource & { event_id: string; story_order: number; title: string; description: string; authority_class: string; source_ref: string | null }>;
  canon: Array<{ state_key: string; value: unknown; authority_class: string; evidence_ref: string | null; content_fingerprint: string }>;
  dependencies: Array<{ chapter_id: string; source_chapter_id: string; source_fingerprint: string; status: string }>;
  world: Array<StorySource & { entity_id: string; entity_type: string; name: string; truth: unknown; authority_class: string }>;
}

export function parseStoryInspection(value: unknown, projectId: string): StoryInspection {
  if (!reviewRecord(value) || value.schema !== "quillframe_story_inspection_v1" || value.project_id !== projectId
    || value.authority !== false) throw new Error("story_inspection_invalid");
  for (const [kind, identity] of [["characters", "character_id"], ["relationships", "relationship_id"], ["timeline", "event_id"], ["canon", "state_key"], ["world", "entity_id"]]) {
    if (!Array.isArray(value[kind]) || value[kind].some((item) => !reviewRecord(item) || !canonicalText(item[identity]) || !canonicalText(item.authority_class))) throw new Error("story_inspection_invalid");
  }
  for (const kind of ["characters", "relationships", "timeline", "world"]) {
    if ((value[kind] as Record<string, unknown>[]).some((item) => !["current", "stale", "untracked"].includes(String(item.source_state))
      || item.source_chapter_id !== null && !canonicalText(item.source_chapter_id)
      || item.source_state !== "untracked" && !canonicalText(item.source_chapter_id))) throw new Error("story_inspection_invalid");
  }
  const parsed = value as unknown as StoryInspection;
  if (parsed.characters.some((item) => !canonicalText(item.name))
    || parsed.relationships.some((item) => !canonicalText(item.participant_a) || !canonicalText(item.participant_b) || !canonicalText(item.relationship_type))
    || parsed.timeline.some((item) => !Number.isSafeInteger(item.story_order) || !canonicalText(item.title) || typeof item.description !== "string" || item.source_ref !== null && !canonicalText(item.source_ref))
    || parsed.canon.some((item) => !fingerprint(item.content_fingerprint) || item.evidence_ref !== null && !canonicalText(item.evidence_ref))
    || parsed.world.some((item) => !canonicalText(item.name) || !canonicalText(item.entity_type))) throw new Error("story_inspection_invalid");
  if (!Array.isArray(value.dependencies) || value.dependencies.some((item) => !reviewRecord(item)
    || !canonicalText(item.chapter_id) || !canonicalText(item.source_chapter_id) || !fingerprint(item.source_fingerprint) || !canonicalText(item.status))) throw new Error("story_inspection_invalid");
  return value as unknown as StoryInspection;
}

export interface ReaderExpectationsInspection {
  schema: "quillframe_reader_expectations_inspection_v1";
  project_id: string;
  authority: false;
  measured_retention: false;
  items: Array<{ expectation_id: string; kind: string; scope: string; description: string; opened_order: number;
    due_by_order: number | null; last_touched_order: number; status: "open" | "partial" | "paid" | "invalidated" | "abandoned";
    source_ref: string | null; source_fingerprint: string | null; version: number; authority: false }>;
  observations: Array<{ observation_id: string; run_id: string; chapter_id: string; document_id: string;
    candidate_id: string; candidate_fingerprint: string; reading_order: number; state: string;
    updates: unknown; source_type: "model_proxy"; authority: false }>;
}

export function parseReaderExpectations(value: unknown, projectId: string): ReaderExpectationsInspection {
  if (!reviewRecord(value) || value.schema !== "quillframe_reader_expectations_inspection_v1" || value.project_id !== projectId
    || value.authority !== false || value.measured_retention !== false || !Array.isArray(value.items) || !Array.isArray(value.observations)) throw new Error("reader_expectations_invalid");
  for (const item of value.items) {
    if (!reviewRecord(item) || !canonicalText(item.expectation_id) || !canonicalText(item.kind) || !canonicalText(item.scope)
      || typeof item.description !== "string" || !Number.isSafeInteger(item.opened_order) || !Number.isSafeInteger(item.last_touched_order)
      || item.due_by_order !== null && !Number.isSafeInteger(item.due_by_order) || !Number.isSafeInteger(item.version)
      || (item.version as number) < 1 || !["open", "partial", "paid", "invalidated", "abandoned"].includes(String(item.status))
      || item.source_ref !== null && !canonicalText(item.source_ref) || item.source_fingerprint !== null && !fingerprint(item.source_fingerprint)
      || item.authority !== false) throw new Error("reader_expectations_invalid");
  }
  for (const item of value.observations) {
    if (!reviewRecord(item) || !["observation_id", "run_id", "chapter_id", "document_id", "candidate_id", "state"].every((key) => canonicalText(item[key]))
      || !fingerprint(item.candidate_fingerprint) || !Number.isSafeInteger(item.reading_order)
      || item.source_type !== "model_proxy" || item.authority !== false) throw new Error("reader_expectations_invalid");
  }
  return value as unknown as ReaderExpectationsInspection;
}

export interface LearningSemanticCall {
  contract_id: string;
  state: string;
  call_id: string | null;
  job_fingerprint: string;
  result_hash: string | null;
  pending_reason: string | null;
}

export interface ProjectLearningFeedback {
  schema: "quillframe_project_learning_v1";
  project_id: string;
  event_id: string;
  status: string;
  run_id: string;
  session_id: string;
  candidate_id: string;
  candidate_fingerprint: string;
  document_id: string;
  evidence_kind: string;
  source_type: "author" | "human_reader" | "model_reader";
  source_id: string;
  advisory_only?: boolean;
  feedback_text?: string;
  intake: Record<string, unknown> | null;
  semantic_call: LearningSemanticCall | null;
  interpretation?: Record<string, unknown> | null;
  authority: false;
  canon_write: false;
  framework_write: false;
  durable_user_taste_write: false;
}

export interface ProjectPreference {
  schema: "quillframe_project_preference_v1";
  project_id: string;
  hypothesis_id: string;
  scope: "project";
  dimension: string;
  statement: string;
  mechanism: string;
  state: string;
  version: number;
  applicability: unknown;
  evidence_ids: string[];
  contradiction_ids: string[];
  active_for_future_production: boolean;
  activation_review?: { semantic_call: LearningSemanticCall | null; judgment: Record<string, unknown> | null };
  authority: false;
  canon_write: false;
  framework_write: false;
  durable_user_taste_write: false;
}

function learningHasNoAuthority(value: Record<string, unknown>): boolean {
  return value.authority === false && value.canon_write === false && value.framework_write === false && value.durable_user_taste_write === false;
}

export function parseProjectFeedback(value: unknown, projectId: string, eventId?: string): ProjectLearningFeedback {
  if (!reviewRecord(value) || value.schema !== "quillframe_project_learning_v1" || value.project_id !== projectId
    || !learningHasNoAuthority(value) || !["event_id", "status", "run_id", "session_id", "candidate_id", "document_id", "evidence_kind"].every((key) => canonicalText(value[key]))
    || eventId !== undefined && value.event_id !== eventId || !fingerprint(value.candidate_fingerprint)
    || value.feedback_text !== undefined && typeof value.feedback_text !== "string"
    || !["author", "human_reader", "model_reader"].includes(String(value.source_type)) || !canonicalText(value.source_id)
    || value.advisory_only !== undefined && typeof value.advisory_only !== "boolean"
    || value.source_type === "model_reader" && (value.advisory_only !== true || value.status !== "advisory" || value.intake !== null || value.semantic_call !== null)
    || value.intake !== null && !reviewRecord(value.intake)
    || value.semantic_call !== null && (!reviewRecord(value.semantic_call) || !canonicalText(value.semantic_call.state) || !fingerprint(value.semantic_call.job_fingerprint))
    || value.interpretation !== undefined && value.interpretation !== null && !reviewRecord(value.interpretation)) throw new Error("project_feedback_invalid");
  return value as unknown as ProjectLearningFeedback;
}

export function parseProjectPreference(value: unknown, projectId: string, hypothesisId?: string): ProjectPreference {
  if (!reviewRecord(value) || value.schema !== "quillframe_project_preference_v1" || value.project_id !== projectId
    || !learningHasNoAuthority(value) || value.scope !== "project" || !canonicalText(value.hypothesis_id)
    || hypothesisId !== undefined && value.hypothesis_id !== hypothesisId || !canonicalText(value.statement)
    || typeof value.mechanism !== "string" || !canonicalText(value.dimension) || !canonicalText(value.state)
    || !Number.isSafeInteger(value.version) || (value.version as number) < 1
    || !Array.isArray(value.evidence_ids) || !value.evidence_ids.every(canonicalText)
    || !Array.isArray(value.contradiction_ids) || !value.contradiction_ids.every(canonicalText)
    || value.active_for_future_production !== (value.state === "active")) throw new Error("project_preference_invalid");
  return value as unknown as ProjectPreference;
}

function projectLearningList(value: unknown, projectId: string): unknown[] {
  if (!reviewRecord(value) || value.schema !== "quillframe_project_learning_v1" || value.project_id !== projectId
    || !learningHasNoAuthority(value) || value.side_effect_free !== true || !Array.isArray(value.items)) throw new Error("project_learning_list_invalid");
  return value.items;
}

export const parseProjectFeedbackList = (value: unknown, projectId: string): ProjectLearningFeedback[] =>
  projectLearningList(value, projectId).map((item) => parseProjectFeedback(item, projectId));
export const parseProjectPreferenceList = (value: unknown, projectId: string): ProjectPreference[] =>
  projectLearningList(value, projectId).map((item) => parseProjectPreference(item, projectId));

export function parseProjectPreferenceReceipt(value: unknown, expected: {
  project_id: string; hypothesis_id: string; expected_version: number; authorized_by: string; idempotency_key: string; action: "activate" | "deactivate";
}): Record<string, unknown> {
  if (!reviewRecord(value) || !learningHasNoAuthority(value) || typeof value.replayed !== "boolean" || !reviewRecord(value.receipt)) throw new Error("project_preference_receipt_invalid");
  const receipt = value.receipt;
  if (receipt.schema !== "quillframe_project_preference_receipt_v1" || !learningHasNoAuthority(receipt)
    || !canonicalText(receipt.receipt_id) || receipt.project_id !== expected.project_id || receipt.hypothesis_id !== expected.hypothesis_id
    || receipt.expected_version !== expected.expected_version || receipt.before_version !== expected.expected_version || receipt.after_version !== expected.expected_version + 1
    || receipt.action !== expected.action || receipt.after_state !== (expected.action === "activate" ? "active" : "deprecated")
    || receipt.authorized_by !== expected.authorized_by || receipt.idempotency_key !== expected.idempotency_key || receipt.user_authorized !== true
    || !fingerprint(receipt.before_fingerprint) || !fingerprint(receipt.after_fingerprint)
    || receipt.transaction_scope !== "learning_database" || receipt.cross_database_atomic !== false) throw new Error("project_preference_receipt_invalid");
  return receipt;
}

export interface ReviewLifecycleReceipts {
  acceptance?: AcceptanceResult;
  settlement?: SettlementResult;
  receipt_window_full: boolean;
}

const reviewRecord = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const beforeFingerprint = (value: unknown): value is string => value === "absent" || fingerprint(value);

function validReviewSource(review: CandidateReviewProjection): boolean {
  return review?.schema === "quillframe_candidate_review_projection_v1"
    && canonicalText(review.project_id) && canonicalText(review.candidate?.candidate_id)
    && canonicalText(review.candidate?.document_id) && fingerprint(review.candidate?.candidate_fingerprint)
    && canonicalText(review.candidate_revision?.revision_id)
    && review.candidate_revision?.content_fingerprint === review.candidate.candidate_fingerprint
    && review.candidate.user_visible_gate === "PASS"
    && review.private_reasoning_exposed === false && review.authority === false
    && review.canon_authority === false && review.settlement_authority === false;
}

/** Resolve only a persisted chapter association, never a chapter-like document name. */
export function resolveReviewSettlementTarget(value: unknown, review: CandidateReviewProjection, chapters?: ChapterListProjection): string | undefined {
  if (!validReviewSource(review) || !reviewRecord(value)
    || value.schema !== "quillframe_document_list_projection_v1" || value.project_id !== review.project_id
    || value.authority !== false || value.canon_authority !== false || !Array.isArray(value.items)) {
    throw new Error("review_document_projection_invalid");
  }
  const matches = value.items.filter((item): item is Record<string, unknown> => reviewRecord(item) && item.document_id === review.candidate.document_id);
  if (matches.length > 1) throw new Error("review_document_binding_ambiguous");
  const document = matches[0];
  if (!chapters || document?.document_kind !== "manuscript" || !canonicalText(document.story_node_id)) return undefined;
  const registry = parseChapterList(chapters, review.project_id);
  if (!registry.items.some((chapter) => chapter.chapter_id === document.story_node_id && chapter.document_id === document.document_id)) return undefined;
  return `chapter:${document.story_node_id}`;
}

export function parseReviewAcceptanceResult(value: unknown, review: CandidateReviewProjection): AcceptanceResult {
  if (!validReviewSource(review) || !reviewRecord(value)
    || value.schema !== "quillframe_candidate_acceptance_result_v1" || !canonicalText(value.acceptance_id)
    || value.candidate_id !== review.candidate.candidate_id || value.candidate_fingerprint !== review.candidate.candidate_fingerprint
    || !canonicalText(value.authorized_by) || !reviewRecord(value.authorization) || !fingerprint(value.request_fingerprint)
    || value.accepted !== true || value.settled !== false || value.canon_mutated !== false) {
    throw new Error("review_acceptance_binding_invalid");
  }
  return value as unknown as AcceptanceResult;
}

export function parseReviewSettlementPreflight(
  value: unknown, review: CandidateReviewProjection, acceptance: AcceptanceResult, target: string,
): SettlementPreflight {
  parseReviewAcceptanceResult(acceptance, review);
  if (!reviewRecord(value) || value.schema !== "quillframe_settlement_preflight_v1"
    || !/^chapter:[^\s\0]+$/.test(target) || value.target_ref !== target || value.project_id !== review.project_id
    || value.acceptance_id !== acceptance.acceptance_id || value.candidate_id !== review.candidate.candidate_id
    || value.candidate_fingerprint !== review.candidate.candidate_fingerprint || value.document_id !== review.candidate.document_id
    || value.revision_id !== review.candidate_revision.revision_id || !beforeFingerprint(value.expected_before_fingerprint)
    || value.current_before_fingerprint !== value.expected_before_fingerprint || value.settleable !== true
    || value.mutation_performed !== false || value.canon_mutated !== false || value.authority !== false
    || value.narrative_proposal !== undefined && value.narrative_proposal !== null && !reviewRecord(value.narrative_proposal)
    || value.reader_observations !== undefined && (!Array.isArray(value.reader_observations) || !value.reader_observations.every(reviewRecord))
    || value.preflight_fingerprint !== undefined && !fingerprint(value.preflight_fingerprint)
    || (value.narrative_proposal != null || Array.isArray(value.reader_observations) && value.reader_observations.length > 0) && !fingerprint(value.preflight_fingerprint)) {
    throw new Error("review_settlement_preflight_binding_invalid");
  }
  return value as unknown as SettlementPreflight;
}

/** An incomplete result is usable only with the before-state of its bound POST. */
export function parseReviewSettlementResult(
  value: unknown, review: CandidateReviewProjection, acceptance: AcceptanceResult, target: string, expectedBefore?: string,
): SettlementResult {
  parseReviewAcceptanceResult(acceptance, review);
  const invalid = () => new Error("review_settlement_binding_invalid");
  if (!reviewRecord(value) || value.schema !== "quillframe_settlement_result_v1" || !canonicalText(value.settlement_id)
    || !/^chapter:[^\s\0]+$/.test(target) || value.target_ref !== target) throw invalid();
  if (value.status === "settlement_incomplete") {
    if (!beforeFingerprint(expectedBefore) || value.expected_before_fingerprint !== expectedBefore
      || !beforeFingerprint(value.actual_before_fingerprint) || value.canon_mutated !== false) throw invalid();
  } else if (value.status === "settled") {
    const after = reviewRecord(value.state_delta) ? value.state_delta.after : undefined;
    if (value.canon_mutated !== true || !beforeFingerprint(value.before_fingerprint) || !fingerprint(value.after_fingerprint)
      || expectedBefore !== undefined && value.before_fingerprint !== expectedBefore || !reviewRecord(after)
      || !exactKeys(after, ["acceptance_id", "candidate_id", "document_id", "revision_id", "content_fingerprint"])
      || after.acceptance_id !== acceptance.acceptance_id || after.candidate_id !== review.candidate.candidate_id
      || after.document_id !== review.candidate.document_id || after.revision_id !== review.candidate_revision.revision_id
      || after.content_fingerprint !== review.candidate.candidate_fingerprint) throw invalid();
  } else throw invalid();
  return value as unknown as SettlementResult;
}

/** This bounded inspector window proves matching receipts, never their absence. */
export function recoverReviewLifecycleReceipts(
  value: unknown, review: CandidateReviewProjection, target: string | undefined,
): ReviewLifecycleReceipts {
  if (!validReviewSource(review) || !reviewRecord(value) || value.schema !== "quillframe_inspector_projection_v1"
    || value.kind !== "receipts" || value.project_id !== review.project_id || value.authority !== false
    || !Array.isArray(value.items) || value.items.length > 500) throw new Error("review_receipts_projection_invalid");
  const recovered: ReviewLifecycleReceipts = { receipt_window_full: value.items.length === 500 };
  if (review.candidate.persisted_status !== "accepted" || review.candidate.effective_status !== "accepted") return recovered;
  const payloads: Array<{ kind: string; value: Record<string, unknown> }> = [];
  for (const row of value.items) {
    if (!reviewRecord(row) || typeof row.receipt_kind !== "string" || !["candidate_accept", "settlement"].includes(row.receipt_kind)) continue;
    let payload: unknown;
    try { payload = typeof row.payload_json === "string" ? JSON.parse(row.payload_json) : undefined; }
    catch { throw new Error("review_receipts_payload_invalid"); }
    if (!reviewRecord(payload)) throw new Error("review_receipts_payload_invalid");
    payloads.push({ kind: row.receipt_kind, value: payload });
  }
  const acceptances = payloads.filter((item) => item.kind === "candidate_accept"
    && item.value.candidate_id === review.candidate.candidate_id && item.value.candidate_fingerprint === review.candidate.candidate_fingerprint)
    .map((item) => parseReviewAcceptanceResult(item.value, review));
  if (acceptances.length > 1) throw new Error("review_acceptance_receipt_ambiguous");
  recovered.acceptance = acceptances[0];
  if (!recovered.acceptance || !target) return recovered;
  for (const item of payloads) {
    if (item.kind !== "settlement" || item.value.status !== "settled") continue;
    try {
      recovered.settlement = parseReviewSettlementResult(item.value, review, recovered.acceptance, target);
      break;
    } catch {
      // A receipt for another source/target or without an exact binding proves nothing here.
    }
  }
  return recovered;
}

export type PublicationFormat = "md" | "txt";

export interface PublicationPreviewProjection {
  schema: "quillframe_publication_preview_v1";
  persistent: false;
  source_acceptance_id: string;
  source_fingerprint: string;
  document_id: string | null;
  content: string;
}

export interface PublicationBuildProjection {
  schema: "quillframe_publication_build_v1";
  build_id: string;
  persistent: true;
  source_acceptance_id: string;
  source_fingerprint: string;
  output_ref: string;
  format: PublicationFormat;
  compiler_contract: "quillframe_core_publication_text_v1";
  identity_fingerprint: string;
  artifact_fingerprint: string;
  byte_size: number;
}

export interface PublicationCollectionProjection {
  schema: "quillframe_publication_collection_result_v1";
  project_id: string;
  build_id: string;
  source_acceptance_ids: string[];
  format: PublicationFormat;
  artifact_fingerprint: string;
  byte_size: number;
  output_ref: string;
  persistent: true;
  authority: false;
}

export interface PublicationArtifactProjection {
  schema: "quillframe_publication_artifact_v1";
  project_id: string;
  build_id: string;
  filename: string;
  media_type: string;
  byte_size: number;
  artifact_fingerprint: string;
  content_base64: string;
  source_acceptance_ids: string[];
  authority: false;
}

const sameTexts = (value: unknown, expected: readonly string[]): value is string[] => Array.isArray(value)
  && value.length === expected.length && value.every((item, index) => canonicalText(item) && item === expected[index]);

export function parsePublicationCollection(value: unknown, expected: { project_id: string; acceptance_ids: string[]; format: PublicationFormat }): PublicationCollectionProjection {
  if (!reviewRecord(value) || value.schema !== "quillframe_publication_collection_result_v1"
    || value.project_id !== expected.project_id || !canonicalText(value.build_id)
    || !expected.acceptance_ids.length || new Set(expected.acceptance_ids).size !== expected.acceptance_ids.length
    || !sameTexts(value.source_acceptance_ids, expected.acceptance_ids) || value.format !== expected.format
    || !["md", "txt"].includes(expected.format) || !fingerprint(value.artifact_fingerprint)
    || !Number.isSafeInteger(value.byte_size) || (value.byte_size as number) < 0 || !canonicalText(value.output_ref)
    || value.persistent !== true || value.authority !== false) throw new Error("publication_collection_invalid");
  return value as unknown as PublicationCollectionProjection;
}

export async function parsePublicationArtifact(value: unknown, expected: {
  project_id: string; build_id: string; artifact_fingerprint: string; byte_size: number; source_acceptance_ids: string[];
}): Promise<{ data: PublicationArtifactProjection; bytes: Uint8Array<ArrayBuffer> }> {
  if (!reviewRecord(value) || value.schema !== "quillframe_publication_artifact_v1"
    || value.project_id !== expected.project_id || value.build_id !== expected.build_id
    || value.authority !== false
    || !fingerprint(value.artifact_fingerprint) || value.artifact_fingerprint !== expected.artifact_fingerprint
    || !Number.isSafeInteger(value.byte_size) || (value.byte_size as number) < 0 || value.byte_size !== expected.byte_size
    || !sameTexts(value.source_acceptance_ids, expected.source_acceptance_ids)
    || !canonicalText(value.filename) || /[\\/\x00-\x1f\x7f]/u.test(value.filename) || !/\.(md|txt)$/u.test(value.filename)
    || typeof value.media_type !== "string" || !/^text\/(plain|markdown)(?:;\s*charset=utf-8)?$/i.test(value.media_type)
    || typeof value.content_base64 !== "string" || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value.content_base64)) throw new Error("publication_artifact_invalid");
  const decoded = atob(value.content_base64);
  if (decoded.length !== value.byte_size || btoa(decoded) !== value.content_base64) throw new Error("publication_artifact_bytes_invalid");
  const bytes = Uint8Array.from(decoded, (character) => character.charCodeAt(0));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const actual = `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
  if (actual !== value.artifact_fingerprint) throw new Error("publication_artifact_fingerprint_mismatch");
  return { data: value as unknown as PublicationArtifactProjection, bytes };
}

export function parsePublicationPreview(value: unknown, acceptanceId: string): PublicationPreviewProjection {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("publication_preview_invalid");
  const result = value as Record<string, unknown>;
  if (result.schema !== "quillframe_publication_preview_v1" || result.persistent !== false
    || result.source_acceptance_id !== acceptanceId || !canonicalText(result.source_acceptance_id)
    || !fingerprint(result.source_fingerprint) || typeof result.content !== "string"
    || (result.document_id !== null && !canonicalText(result.document_id))) throw new Error("publication_preview_invalid");
  return result as unknown as PublicationPreviewProjection;
}

export function parsePublicationBuild(value: unknown, preview: PublicationPreviewProjection, format: PublicationFormat): PublicationBuildProjection {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("publication_build_invalid");
  const result = value as Record<string, unknown>;
  if (result.schema !== "quillframe_publication_build_v1" || result.persistent !== true
    || !canonicalText(result.build_id) || !canonicalText(result.output_ref)
    || result.source_acceptance_id !== preview.source_acceptance_id || result.source_fingerprint !== preview.source_fingerprint
    || !["md", "txt"].includes(format) || result.format !== format
    || result.compiler_contract !== "quillframe_core_publication_text_v1"
    || !fingerprint(result.identity_fingerprint) || !fingerprint(result.artifact_fingerprint)
    || typeof result.byte_size !== "number" || !Number.isSafeInteger(result.byte_size) || result.byte_size < 0) throw new Error("publication_build_invalid");
  return result as unknown as PublicationBuildProjection;
}

export function createPublicationRequestGuard(currentSource: () => { project_id: string; acceptance_id: string; format: PublicationFormat }) {
  let version = 0;
  return {
    invalidate: () => { version += 1; },
    begin: () => {
      const requestVersion = ++version;
      const source = { ...currentSource() };
      return {
        source,
        isCurrent: () => {
          const current = currentSource();
          return requestVersion === version && source.project_id === current.project_id
            && source.acceptance_id === current.acceptance_id && source.format === current.format;
        },
      };
    },
  };
}

export function createPublicationCollectionRequestGuard(currentSource: () => { project_id: string; acceptance_ids: string[]; format: PublicationFormat }) {
  let version = 0;
  return {
    invalidate: () => { version += 1; },
    begin: () => {
      const requestVersion = ++version;
      const current = currentSource();
      const source = { ...current, acceptance_ids: [...current.acceptance_ids] };
      return { source, isCurrent: () => {
        const latest = currentSource();
        return requestVersion === version && source.project_id === latest.project_id && source.format === latest.format
          && sameTexts(latest.acceptance_ids, source.acceptance_ids);
      } };
    },
  };
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
    minimalOutput: "id, title, language, scope=novel, manifest_fingerprint, data_boundary, last_opened_at",
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
    minimalInput: "endpoint, optional access_token",
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

export function connectedModelService(items: ModelServiceProjection[]): ModelServiceProjection | undefined {
  return items.find((item) => canonicalText(item.service_id)
    && (item.enabled === true || item.enabled === 1) && item.discovery_state === "connected");
}

export function pendingIndependentReview(
  current: Pick<AuthorRunStatusProjection, "project_id" | "run_id" | "status" | "events">,
  execution: ProductionExecutionProjection | undefined,
): "independent_provenance" | "independent_semantic_review" | undefined {
  if (current.status !== "awaiting_external") return undefined;
  const latest = current.events.filter((event) => ["production_candidate_qualified", "production_independent_requested"].includes(event.event_kind)).at(-1);
  if (latest?.event_kind === "production_independent_requested") return "independent_semantic_review";
  if (!execution || execution.project_id !== current.project_id || execution.run_id !== current.run_id
    || execution.status !== "awaiting_external" || execution.candidate_visible !== false || execution.raw_draft_visible !== false) return undefined;
  if (execution.awaiting === "independent_provenance") return execution.awaiting;
  if (execution.awaiting === "independent_semantic_review" && latest?.event_kind !== "production_candidate_qualified") return execution.awaiting;
  return undefined;
}

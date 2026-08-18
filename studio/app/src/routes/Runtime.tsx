import { For, Show, createMemo, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

type SessionSummary = {
  session_id: string;
  resource_id: string;
  project_id?: string | null;
  parent_session_id?: string | null;
  role: string;
  task_mode?: string | null;
  transport?: string | null;
  backend?: string | null;
  usage_class?: string | null;
  status: string;
  memory_policy?: string | null;
  resume_policy?: string | null;
  run_count: number;
  checkpoint_count: number;
  session_event_count: number;
  latest_run_id?: string | null;
  latest_run_status?: string | null;
  version: number;
  payload_hash: string;
  updated_at: string;
};

type SessionListProjection = {
  schema: "quillframe_runtime_sessions_projection_v1";
  count: number;
  sessions: SessionSummary[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

type RunProjection = {
  run_id?: string | null;
  status?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  usage_class?: string | null;
  input_artifact_fingerprints: string[];
  output_artifact_fingerprints: string[];
};

type CheckpointProjection = {
  checkpoint_id?: string | null;
  run_id?: string | null;
  workflow_step?: string | null;
  artifact_fingerprints: string[];
  pending_gate?: string | null;
  pending_handoff?: string | null;
  resume_policy?: string | null;
  created_at?: string | null;
};

type SessionProjection = {
  schema: "quillframe_runtime_session_projection_v1";
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
    session_events: Array<{ event_id?: string | null; type?: string | null; run_id?: string | null; artifact_fingerprints: string[]; created_at?: string | null }>;
    provider_session_id_exposed: false;
    external_session_ref_exposed: false;
    absolute_paths_exposed: false;
  };
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

type RuntimeEvent = {
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

type EventsProjection = {
  schema: "quillframe_runtime_events_projection_v1";
  count: number;
  events: RuntimeEvent[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

type ReceiptProjection = {
  receipt_id: string;
  resource_id: string;
  session_id: string;
  run_id: string;
  stage: string;
  subject_id: string;
  artifact_fingerprints: string[];
  semantic_jobs: Array<{ job_id: string; contract_id: string; input_fingerprint: string; status: string; result_fingerprint?: string | null; worker_ref?: string | null }>;
  guards: Array<{ guard_id: string; status: string; evidence_refs: string[] }>;
  created_at: string;
  authority: false;
};

type ReceiptsProjection = {
  schema: "quillframe_run_receipts_projection_v1";
  count: number;
  receipts: ReceiptProjection[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

type HandoffProjection = {
  schema: "quillframe_runtime_handoff_projection_v1";
  handoff: {
    handoff_id: string;
    source_session_id: string;
    target_session_class: string;
    resource_id: string;
    task_mode?: string | null;
    state: string;
    artifact_fingerprints: string[];
    artifact_ref_count: number;
    context_policy: { hidden_gold?: string | null; allowed_artifact_ref_count: number };
    permissions: { canon_write?: boolean | null; framework_behavior_write?: boolean | null; durable_user_taste_write?: boolean | null; allowed_result_scope?: string | null };
    return_contract: { schema?: string | null; fingerprint_required?: boolean | null };
    attempts: number;
    payload_hash: string;
    result_present: boolean;
    result_hash?: string | null;
    created_at: string;
    updated_at: string;
    lease_owner_exposed: false;
    result_payload_exposed: false;
  };
  query_only: true;
  mutation_performed: false;
  authority: false;
  projection_fingerprint: string;
};

const copyByLocale = {
  "en-US": {
    eyebrow: "Runtime observatory",
    title: "Sessions, checkpoints, events, and receipts",
    body: "Inspect the durable execution lineage exposed by Quillframe Core. These projections are read-only and side-effect-free; Studio never opens the runtime store directly.",
    root: "Project root",
    rootPlaceholder: "/path/to/project",
    load: "Load runtime",
    refresh: "Refresh runtime",
    sessions: "Sessions",
    runs: "Runs",
    checkpoints: "Checkpoints",
    events: "Events",
    receipts: "Receipts",
    selected: "Selected session",
    none: "None",
    readOnly: "READ-ONLY",
    sideEffectFree: "Side-effect-free Core projection",
    resumeDeferred: "Resume stays deferred",
    resumeBody: "This surface can inspect checkpoints but cannot resume, replay, fork, claim, complete, or mutate runtime state.",
    emptyTitle: "No durable sessions in this runtime store",
    emptyBody: "The query succeeded without creating or initializing runtime persistence.",
    chooseTitle: "Choose a session",
    chooseBody: "Open one session to inspect its runs, checkpoints, typed event timeline, and metadata-only run receipts.",
    role: "Role",
    status: "Status",
    mode: "Task mode",
    transport: "Transport",
    backend: "Backend",
    memory: "Memory policy",
    resumePolicy: "Resume policy",
    version: "Version",
    updated: "Updated",
    privacy: "Private provider session identifiers and absolute host paths are not exposed by this projection.",
    open: "Inspect",
    workflowStep: "Workflow step",
    pendingGate: "Pending gate",
    pendingHandoff: "Pending handoff",
    inspectHandoff: "Inspect handoff",
    handoff: "Handoff",
    attempts: "Attempts",
    result: "Result",
    present: "present",
    absent: "not present",
    permissions: "Permissions",
    raw: "Raw safe projection",
  },
  "zh-CN": {
    eyebrow: "Runtime 观测台",
    title: "Session、Checkpoint、Event 与 Receipt",
    body: "检查 Quillframe Core 暴露的持久执行 lineage。所有投影均为只读、无副作用；Studio 不会直接打开 runtime store。",
    root: "项目根目录",
    rootPlaceholder: "/path/to/project",
    load: "加载 Runtime",
    refresh: "刷新 Runtime",
    sessions: "Sessions",
    runs: "Runs",
    checkpoints: "Checkpoints",
    events: "Events",
    receipts: "Receipts",
    selected: "当前 Session",
    none: "无",
    readOnly: "只读",
    sideEffectFree: "Core 无副作用投影",
    resumeDeferred: "Resume 仍未开放",
    resumeBody: "这里可以检查 checkpoint，但不能 resume、replay、fork、claim、complete 或修改任何 runtime state。",
    emptyTitle: "当前 Runtime Store 没有持久 Session",
    emptyBody: "查询成功完成，并且没有创建或初始化任何 runtime persistence。",
    chooseTitle: "选择一个 Session",
    chooseBody: "打开 Session 后可以检查它的 Run、Checkpoint、类型化 Event timeline，以及 metadata-only Run Receipt。",
    role: "角色",
    status: "状态",
    mode: "Task mode",
    transport: "Transport",
    backend: "Backend",
    memory: "Memory policy",
    resumePolicy: "Resume policy",
    version: "版本",
    updated: "更新时间",
    privacy: "Private provider session identifier 与绝对宿主路径不会出现在这个投影里。",
    open: "检查",
    workflowStep: "Workflow step",
    pendingGate: "Pending gate",
    pendingHandoff: "Pending handoff",
    inspectHandoff: "检查 Handoff",
    handoff: "Handoff",
    attempts: "尝试次数",
    result: "结果",
    present: "已存在",
    absent: "不存在",
    permissions: "权限",
    raw: "原始安全投影",
  },
} as const;

function errorText(value: unknown): string {
  if (typeof value === "string") return value;
  try { return JSON.stringify(value); } catch { return String(value); }
}

export default function RuntimeRoute() {
  const { locale, t } = useI18n();
  const studio = useStudio();
  const copy = createMemo(() => copyByLocale[locale()]);
  const [sessions, setSessions] = createSignal<SessionListProjection>();
  const [session, setSession] = createSignal<SessionProjection>();
  const [events, setEvents] = createSignal<EventsProjection>();
  const [receipts, setReceipts] = createSignal<ReceiptsProjection>();
  const [handoff, setHandoff] = createSignal<HandoffProjection>();
  const [loading, setLoading] = createSignal(false);
  const [detailLoading, setDetailLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();

  const loadRuntime = async () => {
    const root = studio.projectRoot().trim();
    if (!root) {
      setError(locale() === "zh-CN" ? "需要项目根目录。" : "Project root is required.");
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      const response = await invokeBridge<SessionListProjection>("runtime.sessions.list", { project_root: root });
      if (response.status !== "ok" || !response.data) {
        setSessions(undefined);
        setError(errorText(response.error));
        return;
      }
      setSessions(response.data);
      setSession(undefined);
      setEvents(undefined);
      setReceipts(undefined);
      setHandoff(undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  };

  const openSession = async (sessionId: string) => {
    const root = studio.projectRoot().trim();
    if (!root) return;
    setDetailLoading(true);
    setError(undefined);
    setHandoff(undefined);
    try {
      const [sessionResponse, eventResponse, receiptResponse] = await Promise.all([
        invokeBridge<SessionProjection>("runtime.session.get", { project_root: root, session_id: sessionId }),
        invokeBridge<EventsProjection>("runtime.events.list", { project_root: root, session_id: sessionId }),
        invokeBridge<ReceiptsProjection>("run.receipt.get", { project_root: root, session_id: sessionId }),
      ]);
      if (sessionResponse.status !== "ok" || !sessionResponse.data) throw new Error(errorText(sessionResponse.error));
      if (eventResponse.status !== "ok" || !eventResponse.data) throw new Error(errorText(eventResponse.error));
      if (receiptResponse.status !== "ok" || !receiptResponse.data) throw new Error(errorText(receiptResponse.error));
      setSession(sessionResponse.data);
      setEvents(eventResponse.data);
      setReceipts(receiptResponse.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setDetailLoading(false);
    }
  };

  const inspectHandoff = async (handoffId: string) => {
    const root = studio.projectRoot().trim();
    if (!root) return;
    setDetailLoading(true);
    setError(undefined);
    try {
      const response = await invokeBridge<HandoffProjection>("runtime.handoff.inspect", { project_root: root, handoff_id: handoffId });
      if (response.status !== "ok" || !response.data) throw new Error(errorText(response.error));
      setHandoff(response.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <section class="nf-page nf-runtime-page">
      <PageIntro eyebrow={copy().eyebrow} title={copy().title} body={copy().body} />

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <div class="nf-inspector-toolbar nf-form-grid">
          <label class="nf-field-label">
            <span>{copy().root}</span>
            <input
              class="wui-input nf-mono"
              value={studio.projectRoot()}
              onInput={(event) => studio.setProjectRoot(event.currentTarget.value)}
              placeholder={copy().rootPlaceholder}
              spellcheck={false}
            />
          </label>
          <button class="wui-button wui-button--solid nf-form-action" type="button" disabled={loading() || !studio.projectRoot().trim()} onClick={() => void loadRuntime()}>
            {loading() ? t("common.loading") : sessions() ? copy().refresh : copy().load}
          </button>
        </div>
        <p class="nf-playground-footnote">{t("project.pathPrivacy")}</p>
        <QueryError message={error()} />

        <Show when={sessions()}>
          {(runtime) => (
            <section class="wui-card wui-card--outlined nf-inspector-surface nf-catalog-workstation" aria-labelledby="runtime-sessions-heading">
              <div class="nf-observe-section-head">
                <div>
                  <span class="nf-eyebrow">{copy().sideEffectFree}</span>
                  <h2 id="runtime-sessions-heading">{copy().sessions}</h2>
                  <p>{copy().privacy}</p>
                </div>
                <div class="nf-catalog-counts">
                  <span><strong>{runtime().count}</strong>{copy().sessions}</span>
                  <span><strong>0</strong>authority</span>
                  <span><strong>0</strong>mutations</span>
                </div>
              </div>

              <div class="nf-pack-list">
                <For each={runtime().sessions}>
                  {(item) => (
                    <article class="nf-pack-row">
                      <div class="nf-pack-heading">
                        <div>
                          <strong class="nf-mono">{item.session_id}</strong>
                          <small>{item.role} · {item.task_mode ?? "—"}</small>
                        </div>
                        <span class="wui-badge wui-badge--outline">{item.status}</span>
                      </div>
                      <div class="nf-pack-description">
                        <strong>{item.resource_id}</strong><br />
                        {item.run_count} {copy().runs} · {item.checkpoint_count} {copy().checkpoints} · {item.session_event_count} session events
                      </div>
                      <div class="nf-pack-load-boundary">
                        <span>{copy().updated}</span>
                        <strong class="nf-mono">{item.updated_at}</strong>
                        <button class="wui-button wui-button--outline" type="button" disabled={detailLoading()} onClick={() => void openSession(item.session_id)}>{copy().open}</button>
                      </div>
                    </article>
                  )}
                </For>
              </div>

              <Show when={runtime().count === 0}>
                <div class="nf-playground-empty"><strong>{copy().emptyTitle}</strong><p>{copy().emptyBody}</p></div>
              </Show>
            </section>
          )}
        </Show>

        <Show when={sessions() && !session() && sessions()!.count > 0}>
          <div class="nf-playground-empty"><strong>{copy().chooseTitle}</strong><p>{copy().chooseBody}</p></div>
        </Show>

        <Show when={session()}>
          {(snapshot) => (
            <section class="wui-card wui-card--outlined nf-inspector-surface nf-catalog-workstation" aria-labelledby="runtime-session-heading">
              <div class="nf-observe-section-head">
                <div>
                  <span class="nf-eyebrow">{copy().selected}</span>
                  <h2 id="runtime-session-heading" class="nf-mono">{snapshot().session.session_id}</h2>
                  <p>{copy().resumeBody}</p>
                </div>
                <div class="nf-chip-row">
                  <span class="wui-badge wui-badge--success">{copy().readOnly}</span>
                  <span class="wui-badge wui-badge--outline">{copy().resumeDeferred}</span>
                </div>
              </div>

              <div class="nf-diagnostic-facts">
                <div><span>{copy().role}</span><strong>{snapshot().session.role}</strong></div>
                <div><span>{copy().status}</span><strong>{snapshot().session.status}</strong></div>
                <div><span>{copy().mode}</span><strong class="nf-mono">{snapshot().session.task_mode ?? "—"}</strong></div>
                <div><span>{copy().transport}</span><strong>{snapshot().session.transport ?? "—"}</strong></div>
                <div><span>{copy().backend}</span><strong>{snapshot().session.backend ?? "—"}</strong></div>
                <div><span>{copy().memory}</span><strong>{snapshot().session.memory_policy ?? "—"}</strong></div>
                <div><span>{copy().resumePolicy}</span><strong>{snapshot().session.resume_policy ?? "—"}</strong></div>
                <div><span>{copy().version}</span><strong>{snapshot().session.version}</strong></div>
              </div>

              <div class="nf-observe-section-head">
                <div><span class="nf-card-label">01</span><h2>{copy().runs}</h2></div>
                <span class="wui-badge wui-badge--outline">{snapshot().session.runs.length}</span>
              </div>
              <div class="nf-pack-list">
                <For each={snapshot().session.runs}>
                  {(run) => (
                    <article class="nf-pack-row">
                      <div class="nf-pack-heading"><strong class="nf-mono">{run.run_id ?? "—"}</strong><span class="wui-badge wui-badge--outline">{run.status ?? "—"}</span></div>
                      <div class="nf-pack-description">{run.started_at ?? "—"} → {run.ended_at ?? "…"}</div>
                      <div class="nf-pack-load-boundary"><span>inputs</span><strong>{run.input_artifact_fingerprints.length}</strong><span>outputs</span><strong>{run.output_artifact_fingerprints.length}</strong></div>
                    </article>
                  )}
                </For>
              </div>

              <div class="nf-observe-section-head">
                <div><span class="nf-card-label">02</span><h2>{copy().checkpoints}</h2></div>
                <span class="wui-badge wui-badge--outline">{snapshot().session.checkpoints.length}</span>
              </div>
              <div class="nf-pack-list">
                <For each={snapshot().session.checkpoints}>
                  {(checkpoint) => (
                    <article class="nf-pack-row">
                      <div class="nf-pack-heading"><strong class="nf-mono">{checkpoint.checkpoint_id ?? "—"}</strong><span class="wui-badge wui-badge--outline">{checkpoint.resume_policy ?? "—"}</span></div>
                      <div class="nf-pack-description"><strong>{copy().workflowStep}</strong><br />{checkpoint.workflow_step ?? "—"}</div>
                      <div class="nf-pack-load-boundary">
                        <span>{copy().pendingGate}</span><strong>{checkpoint.pending_gate ?? copy().none}</strong>
                        <span>{copy().pendingHandoff}</span><strong class="nf-mono">{checkpoint.pending_handoff ?? copy().none}</strong>
                        <Show when={checkpoint.pending_handoff}><button class="wui-button wui-button--outline" type="button" onClick={() => void inspectHandoff(checkpoint.pending_handoff!)}>{copy().inspectHandoff}</button></Show>
                      </div>
                    </article>
                  )}
                </For>
              </div>

              <div class="nf-observe-section-head">
                <div><span class="nf-card-label">03</span><h2>{copy().events}</h2></div>
                <span class="wui-badge wui-badge--outline">{events()?.count ?? 0}</span>
              </div>
              <div class="nf-playground-contract-list">
                <For each={events()?.events ?? []}>
                  {(event, index) => (
                    <code>
                      {String(index() + 1).padStart(2, "0")} · {event.event_type} · {event.authority_scope ?? "—"} · {event.run_id ?? "—"}
                      <Show when={event.handoff_id}> · <button class="wui-button wui-button--ghost" type="button" onClick={() => void inspectHandoff(event.handoff_id!)}>{event.handoff_id}</button></Show>
                    </code>
                  )}
                </For>
              </div>

              <div class="nf-observe-section-head">
                <div><span class="nf-card-label">04</span><h2>{copy().receipts}</h2></div>
                <span class="wui-badge wui-badge--outline">{receipts()?.count ?? 0}</span>
              </div>
              <div class="nf-pack-list">
                <For each={receipts()?.receipts ?? []}>
                  {(receipt) => (
                    <article class="nf-pack-row">
                      <div class="nf-pack-heading"><strong class="nf-mono">{receipt.receipt_id}</strong><span class="wui-badge wui-badge--success">authority=false</span></div>
                      <div class="nf-pack-description"><strong>{receipt.stage}</strong><br />{receipt.subject_id}</div>
                      <div class="nf-pack-load-boundary"><span>semantic jobs</span><strong>{receipt.semantic_jobs.length}</strong><span>guards</span><strong>{receipt.guards.length}</strong></div>
                    </article>
                  )}
                </For>
              </div>

              <details class="nf-raw-evidence"><summary>{copy().raw}</summary><JsonBlock value={snapshot()} label={snapshot().schema} /></details>
            </section>
          )}
        </Show>

        <Show when={handoff()}>
          {(projection) => (
            <section class="wui-card wui-card--outlined nf-inspector-surface nf-catalog-workstation" aria-labelledby="runtime-handoff-heading">
              <div class="nf-observe-section-head">
                <div><span class="nf-eyebrow">{copy().handoff}</span><h2 id="runtime-handoff-heading" class="nf-mono">{projection().handoff.handoff_id}</h2></div>
                <span class="wui-badge wui-badge--outline">{projection().handoff.state}</span>
              </div>
              <div class="nf-diagnostic-facts">
                <div><span>{copy().role}</span><strong>{projection().handoff.target_session_class}</strong></div>
                <div><span>{copy().mode}</span><strong>{projection().handoff.task_mode ?? "—"}</strong></div>
                <div><span>{copy().attempts}</span><strong>{projection().handoff.attempts}</strong></div>
                <div><span>{copy().result}</span><strong>{projection().handoff.result_present ? copy().present : copy().absent}</strong></div>
                <div><span>{copy().permissions}</span><strong class="nf-mono">canon={String(projection().handoff.permissions.canon_write)} · framework={String(projection().handoff.permissions.framework_behavior_write)}</strong></div>
              </div>
              <details class="nf-raw-evidence"><summary>{copy().raw}</summary><JsonBlock value={projection()} label={projection().schema} /></details>
            </section>
          )}
        </Show>
      </Show>
    </section>
  );
}

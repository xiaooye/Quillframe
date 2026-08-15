import { A } from "@solidjs/router";
import { For, Show, createMemo, createSignal } from "solid-js";
import { invokeBridge, type BridgeResult } from "../bridge";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { downloadProjection, loadProductProjection, type ProductProjectionBundle } from "../productProjection";
import { useStudio } from "../studio";

type ResumePreflight = {
  schema: "novelforge_session_resume_preflight_v1";
  status: "READY" | "BLOCKED";
  ready: boolean;
  checks: Record<string, boolean>;
  blockers: string[];
  unresolved: string[];
  session?: {
    session_id?: string;
    current_version?: number;
    expected_version?: number;
    payload_hash?: string;
    status?: string;
  } | null;
  checkpoint?: {
    checkpoint_id?: string;
    run_id?: string | null;
    workflow_step?: string | null;
  } | null;
  mutation_performed: false;
  authority: false;
  result_fingerprint: string;
};

type CommandReceipt = {
  schema: "novelforge_runtime_command_receipt_v1";
  command_id: string;
  session_id: string;
  idempotency_key: string;
  receipt_fingerprint: string;
  before_state: {
    session_version: number;
    session_payload_hash: string;
    session_status: string;
    checkpoint_id: string;
  };
  after_state: {
    session_version: number;
    session_payload_hash: string;
    session_status: string;
    checkpoint_id: string;
  };
  event: { event_id: string; event_fingerprint: string };
  runtime_mutation_performed: true;
  model_execution: false;
  authority: false;
};

type CommandExecution = {
  schema: "novelforge_runtime_command_execution_result_v1";
  status: "applied" | "duplicate" | "rejected" | "conflict" | "failed";
  failure_class?: string | null;
  errors: string[];
  receipt?: CommandReceipt | null;
  replayed_receipt: boolean;
  runtime_mutation_performed: boolean;
  model_execution: false;
  authority: false;
  result_fingerprint: string;
};

type CommandReceiptProjection = {
  schema: "novelforge_runtime_command_receipt_projection_v1";
  count: number;
  receipts: CommandReceipt[];
  query_only: true;
  mutation_performed: false;
  authority: false;
};

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function bridgeFailure(result: BridgeResult<unknown>, operation: string): Error {
  let detail = "";
  try { detail = JSON.stringify(result.error); } catch { detail = String(result.error); }
  return new Error(`${operation} failed${detail ? `: ${detail}` : ""}`);
}

export default function Control() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [bundle, setBundle] = createSignal<ProductProjectionBundle>();
  const [manifest, setManifest] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const [authorityEvidence, setAuthorityEvidence] = createSignal("");
  const [preflight, setPreflight] = createSignal<ResumePreflight>();
  const [commandResult, setCommandResult] = createSignal<CommandExecution>();
  const [commandId, setCommandId] = createSignal<string>();
  const [commandBusy, setCommandBusy] = createSignal(false);
  const [commandError, setCommandError] = createSignal<string>();

  const refresh = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const next = await loadProductProjection(studio.projectRoot(), manifest().trim() ? { contextManifest: manifest().trim() } : {});
      setBundle(next);
    } catch (value) {
      setError(value instanceof Error ? value.message : String(value));
    } finally {
      setLoading(false);
    }
  };

  const session = createMemo(() => bundle()?.runtime.selected_session?.session);
  const latestRun = createMemo(() => session()?.runs?.find((run) => run.run_id === session()?.latest_run_id) ?? session()?.runs?.at(-1));
  const receipts = createMemo(() => bundle()?.runtime.receipts?.receipts ?? []);
  const guards = createMemo(() => receipts().flatMap((receipt) => receipt.guards));
  const failedGuards = createMemo(() => guards().filter((guard) => !/^(pass|passed|ok|success)$/i.test(guard.status)));
  const checkpoints = createMemo(() => session()?.checkpoints ?? []);
  const latestCheckpoint = createMemo(() => checkpoints().length ? checkpoints()[checkpoints().length - 1] : undefined);
  const pendingGates = createMemo(() => checkpoints().filter((checkpoint) => checkpoint.pending_gate));
  const settlementReceipts = createMemo(() => receipts().filter((receipt) => /settle/i.test(receipt.stage)));
  const resumable = createMemo(() => ["idle", "awaiting_user", "awaiting_external", "failed"].includes(session()?.status ?? ""));
  const canPreflight = createMemo(() => Boolean(
    session()?.session_id
    && session()?.version
    && latestCheckpoint()?.checkpoint_id
    && authorityEvidence().trim()
    && resumable(),
  ));

  const resumeArgs = () => {
    const current = session();
    const checkpoint = latestCheckpoint();
    if (!current?.session_id || !checkpoint?.checkpoint_id) throw new Error("Current session/latest checkpoint is unavailable");
    return {
      project_root: studio.projectRoot(),
      session_id: current.session_id,
      checkpoint_id: checkpoint.checkpoint_id,
      expected_session_version: current.version,
      authority_evidence: authorityEvidence().trim(),
    };
  };

  const runResumePreflight = async () => {
    setCommandBusy(true);
    setCommandError(undefined);
    setCommandResult(undefined);
    setPreflight(undefined);
    try {
      const result = await invokeBridge<ResumePreflight>("session.resume.preflight", resumeArgs());
      if (result.status !== "ok" || !result.data) throw bridgeFailure(result, "session.resume.preflight");
      setPreflight(result.data);
      setCommandId(result.data.ready ? `CMD-STUDIO-${crypto.randomUUID()}` : undefined);
    } catch (value) {
      setCommandError(value instanceof Error ? value.message : String(value));
      setCommandId(undefined);
    } finally {
      setCommandBusy(false);
    }
  };

  const recoverReceipt = async (id: string): Promise<CommandExecution | undefined> => {
    try {
      const result = await invokeBridge<CommandReceiptProjection>("runtime.command.receipt.get", {
        project_root: studio.projectRoot(),
        command_id: id,
      });
      const receipt = result.status === "ok" && result.data?.count === 1 ? result.data.receipts[0] : undefined;
      if (!receipt) return undefined;
      return {
        schema: "novelforge_runtime_command_execution_result_v1",
        status: "duplicate",
        errors: [],
        receipt,
        replayed_receipt: true,
        runtime_mutation_performed: false,
        model_execution: false,
        authority: false,
        result_fingerprint: result.result_fingerprint,
      };
    } catch {
      return undefined;
    }
  };

  const authorizeAndResume = async () => {
    const ready = preflight();
    const id = commandId();
    if (!ready?.ready || !id) return;
    setCommandBusy(true);
    setCommandError(undefined);
    try {
      const result = await invokeBridge<CommandExecution>("session.resume", {
        ...resumeArgs(),
        command_id: id,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw bridgeFailure(result, "session.resume");
      if (!result.data.receipt || !["applied", "duplicate"].includes(result.data.status)) {
        throw new Error(`session.resume returned ${result.data.status}: ${result.data.errors.join(", ")}`);
      }
      setCommandResult(result.data);
      setPreflight(undefined);
      await refresh();
    } catch (value) {
      const recovered = await recoverReceipt(id);
      if (recovered) {
        setCommandResult(recovered);
        setPreflight(undefined);
        await refresh();
      } else {
        setCommandError(value instanceof Error ? value.message : String(value));
      }
    } finally {
      setCommandBusy(false);
    }
  };

  const cards = createMemo(() => [
    {
      key: "project",
      label: "Project",
      value: bundle()?.project.project.project.title ?? bundle()?.project.project.project.id ?? "—",
      meta: text(bundle()?.project.project.framework_lock.commit),
      href: "/project",
      state: bundle() ? "ready" : "idle",
    },
    {
      key: "runtime",
      label: "Runtime",
      value: session()?.session_id ?? (zh() ? "没有 Session" : "No session"),
      meta: `${session()?.task_mode ?? "—"} · ${session()?.status ?? "—"} · v${session()?.version ?? "—"}`,
      href: "/runtime",
      state: session() ? "ready" : "empty",
    },
    {
      key: "run",
      label: "Run",
      value: latestRun()?.run_id ?? (zh() ? "没有 Run" : "No run"),
      meta: `${latestRun()?.status ?? "—"} · ${latestRun()?.output_artifact_fingerprints?.length ?? 0} outputs`,
      href: "/architecture",
      state: latestRun() ? "ready" : "empty",
    },
    {
      key: "gate",
      label: "Gate",
      value: pendingGates().length ? `${pendingGates().length} pending` : `${guards().length} guards`,
      meta: failedGuards().length ? `${failedGuards().length} non-pass` : (zh() ? "没有非 PASS guard" : "No non-pass guard"),
      href: "/architecture",
      state: failedGuards().length || pendingGates().length ? "attention" : guards().length ? "ready" : "empty",
    },
    {
      key: "settlement",
      label: "Settlement",
      value: settlementReceipts().length ? `${settlementReceipts().length} receipt` : (zh() ? "未公开" : "Not exposed"),
      meta: settlementReceipts().map((receipt) => receipt.stage).join(", ") || (zh() ? "不根据文件名推断结算状态" : "No settlement inference from filesystem state"),
      href: "/architecture",
      state: settlementReceipts().length ? "ready" : "empty",
    },
    {
      key: "publication",
      label: "Publication",
      value: zh() ? "真实 Compiler" : "Real compiler",
      meta: "publication/compiler.py · derived only",
      href: "/publication",
      state: "ready",
    },
  ]);

  return (
    <section class="nf-page nf-control-plane-page">
      <PageIntro
        eyebrow="GUARDED RUNTIME CONTROL"
        title={zh() ? "先读真实状态，再只执行被授权的那一步。" : "Read real state first, then execute only the authorized step."}
        body={zh()
          ? "Control Plane 仍以 Core projection 为证据源；现在唯一开放的写操作是 Local Studio 的 session.resume。它会重新 preflight、校验显式用户授权、CAS 当前 Session，并留下持久 command receipt；不会运行模型，也不会写 Project、Canon、Framework 或 Settlement。"
          : "The Control Plane still takes Core projections as evidence. Its only exposed write is local Studio session.resume: fresh preflight, explicit user authorization, exact Session CAS, and a durable command receipt. It does not run a model or write Project, Canon, Framework, or Settlement state."}
        actions={<span class="wui-badge wui-badge--outline">runtime-state only</span>}
      />

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <section class="nf-control-query wui-card wui-card--outlined">
          <div class="nf-control-query-fields">
            <label><span>{zh() ? "项目根目录" : "Project root"}</span><input class="wui-input" value={studio.projectRoot()} onInput={(event) => studio.setProjectRoot(event.currentTarget.value)} placeholder="/path/to/project" spellcheck={false} /></label>
            <label><span>{zh() ? "可选 Context Manifest" : "Optional Context Manifest"}</span><input class="wui-input" value={manifest()} onInput={(event) => setManifest(event.currentTarget.value)} placeholder="context-manifest.json" spellcheck={false} /></label>
          </div>
          <div class="nf-control-query-actions">
            <button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void refresh()}>{loading() ? (zh() ? "刷新中…" : "Refreshing…") : (zh() ? "刷新真实状态" : "Refresh real state")}</button>
            <Show when={bundle()}><button class="wui-button wui-button--outline" type="button" onClick={() => downloadProjection(bundle()!)}>{zh() ? "导出 projection bundle" : "Export projection bundle"}</button></Show>
          </div>
        </section>
        <QueryError message={error()} />

        <Show when={bundle()} fallback={<div class="wui-empty-state nf-empty"><p>{zh() ? "输入项目根目录后加载 Core 状态。" : "Enter a project root to load Core state."}</p></div>}>
          <section class="nf-control-state-grid">
            <For each={cards()}>{(card) => (
              <A href={card.href} class="nf-control-state-card" data-state={card.state}>
                <header><span class="nf-eyebrow">{card.label}</span><i aria-hidden="true">{card.state === "ready" ? "✓" : card.state === "attention" ? "!" : "○"}</i></header>
                <strong>{card.value}</strong>
                <small class="nf-mono">{card.meta}</small>
              </A>
            )}</For>
          </section>

          <section class="nf-control-command wui-card wui-card--outlined" data-state={preflight()?.status?.toLowerCase() ?? (commandResult() ? "applied" : "idle")}>
            <header>
              <div>
                <span class="nf-eyebrow">SESSION.RESUME · LOCAL APP ONLY</span>
                <h2>{zh() ? "受保护的 Runtime Command" : "Guarded runtime command"}</h2>
              </div>
              <span class="wui-badge wui-badge--outline">{preflight()?.status ?? commandResult()?.status ?? "preflight first"}</span>
            </header>

            <div class="nf-control-command-grid">
              <div class="nf-control-command-inputs">
                <label>
                  <span>{zh() ? "Authority evidence（项目相对路径）" : "Authority evidence (project-relative)"}</span>
                  <input
                    class="wui-input"
                    value={authorityEvidence()}
                    onInput={(event) => {
                      setAuthorityEvidence(event.currentTarget.value);
                      setPreflight(undefined);
                      setCommandId(undefined);
                    }}
                    placeholder="resume-authority.json"
                    spellcheck={false}
                  />
                </label>
                <div class="nf-control-command-facts">
                  <span><small>Session</small><strong class="nf-mono">{session()?.session_id ?? "—"}</strong></span>
                  <span><small>Status</small><strong>{session()?.status ?? "—"}</strong></span>
                  <span><small>Version</small><strong>v{session()?.version ?? "—"}</strong></span>
                  <span><small>Latest checkpoint</small><strong class="nf-mono">{latestCheckpoint()?.checkpoint_id ?? "—"}</strong></span>
                </div>
                <button class="wui-button wui-button--outline" type="button" disabled={commandBusy() || !canPreflight()} onClick={() => void runResumePreflight()}>
                  {commandBusy() ? (zh() ? "检查中…" : "Checking…") : (zh() ? "运行 fresh preflight" : "Run fresh preflight")}
                </button>
                <Show when={!resumable() && session()}>
                  <p class="nf-control-command-note">{zh() ? `当前状态 ${session()!.status} 不属于 resumable 状态。` : `Current status ${session()!.status} is not resumable.`}</p>
                </Show>
              </div>

              <div class="nf-control-command-result">
                <Show when={preflight()} fallback={
                  <div class="nf-control-command-placeholder">
                    <strong>{zh() ? "还没有执行 preflight" : "Preflight has not run yet"}</strong>
                    <p>{zh() ? "先绑定 authority evidence；READY 只表示可以进入授权步骤，不代表已经获得任何写权限。" : "Bind authority evidence first. READY only unlocks the authorization step; it does not grant ambient write authority."}</p>
                  </div>
                }>
                  {(check) => (
                    <>
                      <div class="nf-control-preflight-summary">
                        <strong>{check().ready ? (zh() ? "READY · 当前证据仍有效" : "READY · current evidence still holds") : (zh() ? "BLOCKED · 不执行写入" : "BLOCKED · no write will execute")}</strong>
                        <small class="nf-mono">{check().result_fingerprint}</small>
                      </div>
                      <Show when={check().blockers.length || check().unresolved.length}>
                        <ul class="nf-control-command-list">
                          <For each={[...check().blockers, ...check().unresolved]}>{(item) => <li class="nf-mono">{item}</li>}</For>
                        </ul>
                      </Show>
                      <Show when={check().ready}>
                        <div class="nf-control-authorize-box">
                          <p>{zh()
                            ? "点击下面按钮即明确授权：仅把这个 Session 从当前精确 before-state 恢复为 running。执行器会再次 preflight，并用 version + payload hash CAS。"
                            : "Clicking below explicitly authorizes only this Session transition from the exact current before-state to running. The executor preflights again and CASes version + payload hash."}</p>
                          <code class="nf-mono">{commandId()}</code>
                          <button class="wui-button wui-button--solid" type="button" disabled={commandBusy()} onClick={() => void authorizeAndResume()}>
                            {commandBusy() ? (zh() ? "执行中…" : "Executing…") : (zh() ? "授权并恢复 Session" : "Authorize & resume Session")}
                          </button>
                        </div>
                      </Show>
                    </>
                  )}
                </Show>
              </div>
            </div>

            <QueryError message={commandError()} />
            <Show when={commandResult()?.receipt}>
              {(receipt) => (
                <section class="nf-control-command-receipt">
                  <header><div><span class="nf-eyebrow">DURABLE COMMAND RECEIPT</span><h3>{receipt().command_id}</h3></div><span class="wui-badge wui-badge--outline">{commandResult()?.status}</span></header>
                  <dl>
                    <div><dt>Before</dt><dd>{receipt().before_state.session_status} · v{receipt().before_state.session_version}</dd></div>
                    <div><dt>After</dt><dd>{receipt().after_state.session_status} · v{receipt().after_state.session_version}</dd></div>
                    <div><dt>Checkpoint</dt><dd class="nf-mono">{receipt().after_state.checkpoint_id}</dd></div>
                    <div><dt>Event</dt><dd class="nf-mono">{receipt().event.event_id}</dd></div>
                    <div><dt>Receipt</dt><dd class="nf-mono">{receipt().receipt_fingerprint}</dd></div>
                    <div><dt>Idempotency</dt><dd class="nf-mono">{receipt().idempotency_key}</dd></div>
                  </dl>
                  <footer><span>model_execution=false</span><span>project_write=false</span><span>canon_write=false</span><span>settlement=false</span><span>authority=false</span></footer>
                </section>
              )}
            </Show>
          </section>

          <section class="nf-control-lineage wui-card wui-card--outlined">
            <header><div><span class="nf-eyebrow">LINEAGE</span><h2>{zh() ? "读路径和写路径分开" : "Read path and command path stay separate"}</h2></div><span class="wui-badge wui-badge--outline">authority=false</span></header>
            <div class="nf-control-lineage-flow">
              <span>Project Adapter</span><i>→</i><span>Runtime Query</span><i>→</i><span>Product Projection</span><i>→</i><strong>Studio UI</strong>
            </div>
            <div class="nf-control-lineage-flow nf-control-lineage-flow--command">
              <span>Explicit click</span><i>→</i><span>Fresh Preflight</span><i>→</i><span>Typed Authorization</span><i>→</i><span>CAS</span><i>→</i><strong>Command Receipt</strong>
            </div>
            <footer>
              <span>{bundle()!.bridge_result_fingerprints.length} projection fingerprints</span>
              <span>query path: mutation=false</span>
              <span>command scope: runtime session only</span>
              <span>direct_store_access=false</span>
            </footer>
          </section>
        </Show>
      </Show>
    </section>
  );
}

import { For, Show, createSignal, onMount } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { InspectorListProjection } from "../authoring/contracts";

type SessionRow = { session_id?: string; status?: string; framework_fingerprint?: string; version?: number; created_at?: string; updated_at?: string };
type RunRow = { run_id?: string; session_id?: string | null; task_mode?: string; target_ref?: string | null; status?: string; request_fingerprint?: string; result_fingerprint?: string | null; created_at?: string; updated_at?: string };
type CheckpointRow = { checkpoint_id?: string; run_id?: string; checkpoint_kind?: string; artifact_fingerprint?: string | null; created_at?: string };
type ReceiptRow = { receipt_id?: string; run_id?: string | null; receipt_kind?: string; idempotency_key?: string | null; created_at?: string };

export default function RuntimeRoute() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const [sessions, setSessions] = createSignal<SessionRow[]>([]);
  const [runs, setRuns] = createSignal<RunRow[]>([]);
  const [checkpoints, setCheckpoints] = createSignal<CheckpointRow[]>([]);
  const [receipts, setReceipts] = createSignal<ReceiptRow[]>([]);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];

  const load = async () => {
    if (!projectId()) return;
    setLoading(true); setError(undefined);
    try {
      if (operations().includes("inspector.sessions.list")) {
        const response = await invokeBridge<InspectorListProjection<SessionRow>>("inspector.sessions.list", { project_id: projectId(), limit: 100 });
        if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
        setSessions(response.data.items);
      }
      if (operations().includes("inspector.runs.list")) {
        const response = await invokeBridge<InspectorListProjection<RunRow>>("inspector.runs.list", { project_id: projectId(), limit: 100 });
        if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
        setRuns(response.data.items);
      }
      if (operations().includes("inspector.checkpoints.list")) {
        const response = await invokeBridge<InspectorListProjection<CheckpointRow>>("inspector.checkpoints.list", { project_id: projectId(), limit: 100 });
        if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
        setCheckpoints(response.data.items);
      }
      if (operations().includes("inspector.receipts.list")) {
        const response = await invokeBridge<InspectorListProjection<ReceiptRow>>("inspector.receipts.list", { project_id: projectId(), limit: 100 });
        if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
        setReceipts(response.data.items);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  onMount(() => { if (projectId()) void load(); });

  return (
    <section class="nf-page qf-runtime-page">
      <PageIntro eyebrow="INSPECTOR · RUNTIME" title={zh() ? "运行证据放在这里，不占据 Writer home。" : "Execution evidence lives here, not on the Writer home."} body={zh() ? "这里只消费 SQLite-backed Inspector projection：Session、Run、Checkpoint 与 Receipt。它们是 execution facts，不是 Canon authority，也不会暴露 private CoT。" : "This view consumes SQLite-backed Inspector projections only: Sessions, Runs, Checkpoints and Receipts. They are execution facts, not Canon authority, and never expose private CoT."} />
      <div class="qf-section-head"><div><span class="nf-eyebrow">{projectId() || "NO PROJECT"}</span><strong>{studio.lastRunId() ? `last run · ${studio.lastRunId()}` : (zh() ? "无最近 Run" : "No recent Run")}</strong></div><button class="wui-button wui-button--outline" type="button" disabled={loading() || !projectId()} onClick={() => void load()}>{loading() ? (zh() ? "刷新中…" : "Refreshing…") : (zh() ? "刷新" : "Refresh")}</button></div>
      <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><span class="wui-alert__description">{message()}</span></div></div>}</Show>
      <div class="qf-runtime-columns">
        <section><header><span>SESSIONS</span><strong>{sessions().length}</strong></header><For each={sessions()}>{(row) => <article><code>{row.session_id ?? "—"}</code><strong>{row.status ?? "—"}</strong><small>{row.updated_at ?? row.created_at ?? ""}</small></article>}</For></section>
        <section><header><span>RUNS</span><strong>{runs().length}</strong></header><For each={runs()}>{(row) => <article data-current={row.run_id === studio.lastRunId() ? "true" : undefined}><div><code>{row.run_id ?? "—"}</code><strong>{row.status ?? "—"}</strong></div><p>{row.task_mode ?? "—"} · {row.target_ref ?? "no target"}</p><small>{row.updated_at ?? row.created_at ?? ""}</small></article>}</For></section>
        <section><header><span>CHECKPOINTS</span><strong>{checkpoints().length}</strong></header><For each={checkpoints()}>{(row) => <article><code>{row.checkpoint_id ?? "—"}</code><strong>{row.checkpoint_kind ?? "—"}</strong><small>{row.run_id ?? ""}</small></article>}</For></section>
        <section><header><span>RECEIPTS</span><strong>{receipts().length}</strong></header><For each={receipts()}>{(row) => <article><code>{row.receipt_id ?? "—"}</code><strong>{row.receipt_kind ?? "—"}</strong><small>{row.run_id ?? ""}</small></article>}</For></section>
      </div>
      <p class="qf-inspector-boundary">authority=false · {zh() ? "Runtime metadata 不授予 Project/Canon/Settlement authority。" : "Runtime metadata grants no Project/Canon/Settlement authority."}</p>
    </section>
  );
}

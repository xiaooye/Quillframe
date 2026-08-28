import { For, Show, createEffect, createSignal, on, onCleanup } from "solid-js";
import { useLocation, useNavigate } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { parseRuntimeInspectorList, resolveRuntimeRunSelection } from "../authoring/contracts";

type SessionRow = { session_id?: string; status?: string; framework_fingerprint?: string; version?: number; created_at?: string; updated_at?: string };
type RunRow = { run_id?: string; session_id?: string | null; task_mode?: string; target_ref?: string | null; status?: string; request_fingerprint?: string; result_fingerprint?: string | null; created_at?: string; updated_at?: string };
type CheckpointRow = { checkpoint_id?: string; run_id?: string; checkpoint_kind?: string; artifact_fingerprint?: string | null; created_at?: string };
type ReceiptRow = { receipt_id?: string; run_id?: string | null; receipt_kind?: string; idempotency_key?: string | null; created_at?: string };

export default function RuntimeRoute() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const navigate = useNavigate();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const [sessions, setSessions] = createSignal<SessionRow[]>([]);
  const [runs, setRuns] = createSignal<RunRow[]>([]);
  const [checkpoints, setCheckpoints] = createSignal<CheckpointRow[]>([]);
  const [receipts, setReceipts] = createSignal<ReceiptRow[]>([]);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const [selectingRunId, setSelectingRunId] = createSignal("");
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];
  let loadGeneration = 0;
  let selectionGeneration = 0;
  let disposed = false;
  let runListProjectId = "";

  const load = async () => {
    const requestedProject = projectId(); const generation = ++loadGeneration;
    const current = () => !disposed && generation === loadGeneration && projectId() === requestedProject;
    selectionGeneration += 1; setSelectingRunId(""); runListProjectId = "";
    setSessions([]); setRuns([]); setCheckpoints([]); setReceipts([]);
    if (!requestedProject) { setLoading(false); return; }
    setLoading(true); setError(undefined);
    try {
      const kinds = ["sessions", "runs", "checkpoints", "receipts"] as const;
      const results = await Promise.allSettled(kinds.map((kind) => operations().includes(`inspector.${kind}.list`)
        ? invokeBridge(`inspector.${kind}.list`, { project_id: requestedProject, limit: 100 }) : Promise.resolve(undefined)));
      if (!current()) return;
      const failures: string[] = [];
      results.forEach((result, index) => {
        try {
          if (result.status === "rejected") throw result.reason;
          const response = result.value; const kind = kinds[index];
          if (!response) return;
          if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
          if (kind === "sessions") setSessions(parseRuntimeInspectorList<SessionRow>(response.data, requestedProject, kind).items);
          else if (kind === "runs") { setRuns(parseRuntimeInspectorList<RunRow>(response.data, requestedProject, kind).items); runListProjectId = requestedProject; }
          else if (kind === "checkpoints") setCheckpoints(parseRuntimeInspectorList<CheckpointRow>(response.data, requestedProject, kind).items);
          else setReceipts(parseRuntimeInspectorList<ReceiptRow>(response.data, requestedProject, kind).items);
        } catch (cause) { failures.push(cause instanceof Error ? cause.message : String(cause)); }
      });
      if (failures.length) setError(failures.join(" · "));
    } catch (cause) { if (current()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (current()) setLoading(false); }
  };

  const selectRun = async (row: RunRow) => {
    const requestedProject = projectId();
    if (selectingRunId() || !row.run_id || !row.target_ref || !["DRAFT", "REVISE"].includes(row.task_mode ?? "")
      || !operations().includes("author.run.status") || !operations().includes("chapter.list")
      || requestedProject !== studio.projectId() || studio.projectProjection()?.manifest.id !== requestedProject
      || runListProjectId !== requestedProject || !runs().includes(row)) return;
    const expected = { project_id: requestedProject, run_id: row.run_id, task_mode: row.task_mode!, target_ref: row.target_ref };
    const generation = ++selectionGeneration;
    const current = () => !disposed && generation === selectionGeneration && projectId() === requestedProject
      && studio.projectId() === requestedProject && studio.projectProjection()?.manifest.id === requestedProject
      && operations().includes("author.run.status") && operations().includes("chapter.list");
    setSelectingRunId(expected.run_id); setError(undefined);
    try {
      const status = await invokeBridge("author.run.status", { project_id: requestedProject, run_id: expected.run_id });
      if (!current()) return;
      if (status.status !== "ok" || !status.data) throw new Error(operationError(status));
      const chapters = await invokeBridge("chapter.list", { project_id: requestedProject });
      if (!current()) return;
      if (chapters.status !== "ok" || !chapters.data) throw new Error(operationError(chapters));
      const selected = resolveRuntimeRunSelection(status.data, expected, chapters.data);
      const registeredInStudio = () => studio.chapters().some((chapter) => chapter.chapter_id === selected.chapter_id && chapter.document_id === selected.document_id);
      if (!registeredInStudio()) await studio.refreshChapters();
      if (!current()) return;
      if (!registeredInStudio()) throw new Error("runtime_run_selection_chapter_unavailable");
      studio.setChapterId(selected.chapter_id);
      if (!current() || studio.selectedChapter()?.chapter_id !== selected.chapter_id || studio.selectedChapter()?.document_id !== selected.document_id) return;
      studio.setLastRunId(selected.run_id);
      navigate(`/manuscript?project=${encodeURIComponent(selected.project_id)}&document=${encodeURIComponent(selected.document_id)}`);
    } catch (cause) { if (current()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (current()) setSelectingRunId(""); }
  };

  createEffect(on([projectId, operations], () => { void load(); }));
  onCleanup(() => { disposed = true; loadGeneration += 1; selectionGeneration += 1; });

  return (
    <section class="nf-page qf-runtime-page">
      <PageIntro eyebrow="INSPECTOR · RUNTIME" title={zh() ? "运行证据放在这里，不占据 Writer home。" : "Execution evidence lives here, not on the Writer home."} body={zh() ? "这里只消费 SQLite-backed Inspector projection：Session、Run、Checkpoint 与 Receipt。它们是 execution facts，不是 Canon authority，也不会暴露 private CoT。" : "This view consumes SQLite-backed Inspector projections only: Sessions, Runs, Checkpoints and Receipts. They are execution facts, not Canon authority, and never expose private CoT."} />
      <div class="qf-section-head"><div><span class="nf-eyebrow">{projectId() || "NO PROJECT"}</span><strong>{studio.lastRunId() ? `last run · ${studio.lastRunId()}` : (zh() ? "无最近 Run" : "No recent Run")}</strong></div><button class="wui-button wui-button--outline" type="button" disabled={loading() || !!selectingRunId() || !projectId()} onClick={() => void load()}>{loading() ? (zh() ? "刷新中…" : "Refreshing…") : (zh() ? "刷新" : "Refresh")}</button></div>
      <p class="qf-inspector-boundary">{zh() ? "“查看这次运行”只核对并打开对应章节。打开 AI 助手后可刷新真实进度；执行、恢复、取消和接受仍需分别操作。" : "View this run only verifies the run and opens its chapter. Open the AI assistant and refresh to inspect progress; execution, resumption, cancellation and acceptance remain separate actions."}</p>
      <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><span class="wui-alert__description">{message()}</span></div></div>}</Show>
      <div class="qf-runtime-columns">
        <section><header><span>SESSIONS</span><strong>{sessions().length}</strong></header><For each={sessions()}>{(row) => <article><code>{row.session_id ?? "—"}</code><strong>{row.status ?? "—"}</strong><small>{row.updated_at ?? row.created_at ?? ""}</small></article>}</For></section>
        <section><header><span>RUNS</span><strong>{runs().length}</strong></header><For each={runs()}>{(row) => <article data-current={row.run_id === studio.lastRunId() ? "true" : undefined}><div><code>{row.run_id ?? "—"}</code><strong>{row.status ?? "—"}</strong></div><p>{row.task_mode ?? "—"} · {row.target_ref ?? "no target"}</p><small>{row.updated_at ?? row.created_at ?? ""}</small><Show when={["DRAFT", "REVISE"].includes(row.task_mode ?? "")}><button class="wui-button wui-button--outline" type="button" disabled={!!selectingRunId() || loading() || !row.run_id || !row.target_ref || studio.projectId() !== projectId() || studio.projectProjection()?.manifest.id !== projectId() || !operations().includes("author.run.status") || !operations().includes("chapter.list")} aria-busy={selectingRunId() === row.run_id} onClick={() => void selectRun(row)}>{selectingRunId() === row.run_id ? (zh() ? "核对运行与章节…" : "Verifying run and chapter…") : (zh() ? "查看这次运行" : "View this run")}</button></Show></article>}</For></section>
        <section><header><span>CHECKPOINTS</span><strong>{checkpoints().length}</strong></header><For each={checkpoints()}>{(row) => <article><code>{row.checkpoint_id ?? "—"}</code><strong>{row.checkpoint_kind ?? "—"}</strong><small>{row.run_id ?? ""}</small></article>}</For></section>
        <section><header><span>RECEIPTS</span><strong>{receipts().length}</strong></header><For each={receipts()}>{(row) => <article><code>{row.receipt_id ?? "—"}</code><strong>{row.receipt_kind ?? "—"}</strong><small>{row.run_id ?? ""}</small></article>}</For></section>
      </div>
      <p class="qf-inspector-boundary">authority=false · {zh() ? "Runtime metadata 不授予 Project/Canon/Settlement authority。" : "Runtime metadata grants no Project/Canon/Settlement authority."}</p>
    </section>
  );
}

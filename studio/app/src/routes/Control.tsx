import { A } from "@solidjs/router";
import { For, Show, createMemo, createSignal } from "solid-js";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { downloadProjection, loadProductProjection, type ProductProjectionBundle } from "../productProjection";
import { useStudio } from "../studio";

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export default function Control() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [bundle, setBundle] = createSignal<ProductProjectionBundle>();
  const [manifest, setManifest] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();

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
  const pendingGates = createMemo(() => checkpoints().filter((checkpoint) => checkpoint.pending_gate));
  const settlementReceipts = createMemo(() => receipts().filter((receipt) => /settle/i.test(receipt.stage)));

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
      meta: `${session()?.task_mode ?? "—"} · ${session()?.status ?? "—"}`,
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
        eyebrow="READ-ONLY CONTROL PLANE"
        title={zh() ? "一个项目的真实状态，从这里汇总。" : "One project state, summarized from real Core projections."}
        body={zh()
          ? "Control Plane 只组合 Project Adapter 与 Runtime/Context 查询结果。它不会把 preflight、preview 或宿主能力提升成 Canon、Settlement 或写权限。"
          : "The Control Plane composes Project Adapter plus Runtime/Context queries only. It never upgrades preflight, preview, or host capability into Canon, Settlement, or write authority."}
        actions={<span class="wui-badge wui-badge--outline">query-only</span>}
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

        <Show when={bundle()} fallback={<div class="wui-empty-state nf-empty"><p>{zh() ? "输入项目根目录后加载只读 Core 状态。" : "Enter a project root to load read-only Core state."}</p></div>}>
          <section class="nf-control-state-grid">
            <For each={cards()}>{(card) => (
              <A href={card.href} class="nf-control-state-card" data-state={card.state}>
                <header><span class="nf-eyebrow">{card.label}</span><i aria-hidden="true">{card.state === "ready" ? "✓" : card.state === "attention" ? "!" : "○"}</i></header>
                <strong>{card.value}</strong>
                <small class="nf-mono">{card.meta}</small>
              </A>
            )}</For>
          </section>

          <section class="nf-control-lineage wui-card wui-card--outlined">
            <header><div><span class="nf-eyebrow">LINEAGE</span><h2>{zh() ? "这份界面数据从哪里来" : "Where this UI state comes from"}</h2></div><span class="wui-badge wui-badge--outline">authority=false</span></header>
            <div class="nf-control-lineage-flow">
              <span>Project Adapter</span><i>→</i><span>Runtime Query</span><i>→</i><span>{manifest().trim() ? "Context Inspector" : "Context optional"}</span><i>→</i><span>Product Projection Bundle</span><i>→</i><strong>Studio UI</strong>
            </div>
            <footer>
              <span>{bundle()!.bridge_result_fingerprints.length} fingerprint-bound bridge results</span>
              <span>mutation_performed=false</span>
              <span>direct_store_access=false</span>
            </footer>
          </section>
        </Show>
      </Show>
    </section>
  );
}

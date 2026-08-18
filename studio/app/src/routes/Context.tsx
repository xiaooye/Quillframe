import { For, Show, createMemo, createSignal, onMount } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { ContextRuntimeItem, ContextRuntimeProjection } from "../authoring/contracts";
import { AuthorityLabel, WriterContextStrip } from "../authoring/AuthoringUI";

const order = ["loaded", "selected", "considered", "eligible", "dropped_due_budget", "visibility_excluded", "lifecycle_excluded", "stale", "invalid"];

export default function ContextRoute() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const [runId, setRunId] = createSignal(new URLSearchParams(location.search).get("run")?.trim() || studio.lastRunId());
  const [projection, setProjection] = createSignal<ContextRuntimeProjection>();
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();

  const grouped = createMemo(() => {
    const result: Record<string, ContextRuntimeItem[]> = {};
    for (const state of order) result[state] = [];
    for (const item of projection()?.items ?? []) (result[item.state] ??= []).push(item);
    return result;
  });

  const inspect = async () => {
    if (!projectId() || !runId().trim()) return;
    setLoading(true); setError(undefined);
    try {
      const response = await invokeBridge<ContextRuntimeProjection>("inspector.context.runtime", { project_id: projectId(), run_id: runId().trim() });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setProjection(response.data);
      studio.setLastRunId(runId().trim());
    } catch (cause) { setProjection(undefined); setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  onMount(() => { if (projectId() && runId()) void inspect(); });

  return (
    <section class="nf-page qf-context-page">
      <PageIntro eyebrow="CONTEXT INSPECTOR" title={zh() ? "相关，不等于实际加载。" : "Relevant is not the same as actually loaded."} body={zh() ? "Writer Mode 只轻量展示实际 Loaded Context；这里完整展示 Eligible / Considered / Selected / Loaded / Dropped / Excluded / Stale，并且 authority 永远用文字标注。" : "Writer Mode lightly shows actually Loaded Context; this Inspector exposes Eligible / Considered / Selected / Loaded / Dropped / Excluded / Stale, always with textual authority labels."} />

      <form class="qf-context-query" onSubmit={(event) => { event.preventDefault(); void inspect(); }}>
        <label class="nf-field-label"><span>Project ID</span><input class="wui-input nf-mono" value={projectId()} disabled aria-readonly="true" /></label>
        <label class="nf-field-label"><span>Run ID</span><input class="wui-input nf-mono" value={runId()} onInput={(event) => setRunId(event.currentTarget.value)} placeholder="run_…" /></label>
        <button class="wui-button wui-button--solid" disabled={loading() || !projectId() || !runId().trim()}>{loading() ? (zh() ? "读取中…" : "Loading…") : (zh() ? "读取 Core Context" : "Inspect Core Context")}</button>
      </form>

      <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Context</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>

      <Show when={projection()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "选择一个真实 Run" : "Choose a real Run"}</strong><p>{zh() ? "没有 run_id 时，Studio 不会生成示例 Context。" : "Without a run_id, Studio does not generate sample Context."}</p></div>}>
        {(snapshot) => <>
          <WriterContextStrip projection={snapshot()} zh={zh()} />
          <section class="qf-context-summary" aria-label={zh() ? "Context 状态摘要" : "Context state summary"}>
            <div><span>ACTUALLY LOADED INTO THIS STAGE</span><strong>{grouped().loaded?.length ?? 0}</strong></div>
            <div><span>MODEL CONSIDERED RELEVANT</span><strong>{(grouped().considered?.length ?? 0) + (grouped().selected?.length ?? 0)}</strong></div>
            <div><span>DROPPED / EXCLUDED / STALE</span><strong>{["dropped_due_budget","visibility_excluded","lifecycle_excluded","stale","invalid"].reduce((sum, state) => sum + (grouped()[state]?.length ?? 0), 0)}</strong></div>
            <div><span>Context Freeze</span><strong>{snapshot().context_freeze_id ?? (zh() ? "尚无 freeze" : "no freeze")}</strong></div>
          </section>

          <section class="qf-context-inspector-table" aria-labelledby="context-items-heading">
            <header><div><span class="nf-eyebrow">RUNTIME EVIDENCE</span><h2 id="context-items-heading">{zh() ? "Context items" : "Context items"}</h2></div><div><span>authority=false</span><span>private CoT: {String(snapshot().private_chain_of_thought_exposed)}</span></div></header>
            <div class="qf-context-table-head" aria-hidden="true"><span>State</span><span>Object</span><span>Stage</span><span>Authority</span><span>Reason</span><span>Tokens</span></div>
            <For each={snapshot().items.slice().sort((a, b) => order.indexOf(a.state) - order.indexOf(b.state) || a.source_object_id.localeCompare(b.source_object_id))}>
              {(item) => <article class="qf-context-table-row" data-state={item.state}>
                <strong class="qf-context-state">{item.state}</strong>
                <div><code>{item.source_object_id}</code><small>{item.domain} · {item.lifecycle}</small></div>
                <code>{item.stage}</code>
                <AuthorityLabel value={item.authority} />
                <div><strong>{item.reason_code ?? "—"}</strong><small>{item.reason ?? ""}</small></div>
                <span>{item.actual_tokens ?? item.estimated_tokens ?? 0}</span>
              </article>}
            </For>
          </section>

          <details class="qf-context-fingerprints"><summary>{zh() ? "指纹与 receipt" : "Fingerprints & receipts"}</summary><dl><dt>context_fingerprint</dt><dd><code>{snapshot().context_fingerprint ?? "—"}</code></dd><dt>run_id</dt><dd><code>{snapshot().run_id}</code></dd></dl><For each={snapshot().items}>{(item) => <div><code>{item.source_object_id}</code><span>{item.state}</span><code>{item.receipt ?? "—"}</code></div>}</For></details>
        </>}
      </Show>
    </section>
  );
}

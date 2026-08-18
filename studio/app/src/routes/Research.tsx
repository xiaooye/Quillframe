import { For, Show, createSignal } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";

type SearchRow = { entity_type: string; entity_id: string; title: string; snippet: string; rank: number };

export default function Research() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [query, setQuery] = createSignal("");
  const [rows, setRows] = createSignal<SearchRow[]>([]);
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);

  const search = async () => {
    if (!studio.projectId() || !query().trim()) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<{ results: SearchRow[] }>("project.search", { project_id: studio.projectId(), query: query().trim(), limit: 30 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setRows(result.data.results ?? []);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  return (
    <section class="nf-page qf-research-page">
      <PageIntro eyebrow="RESEARCH & CORPUS" title={zh() ? "研究是证据，不是 Canon。" : "Research is evidence, not Canon."} body={zh() ? "这里可以搜索 Core 已索引的 Project 内容；Research、Corpus、Character Knowledge 与 Accepted Canon 始终保持不同语义。" : "Search content indexed by Core here. Research, Corpus, Character Knowledge and Accepted Canon remain distinct semantics."} />
      <div class="qf-editorial-sheet">
        <form class="qf-search-line" onSubmit={(event) => { event.preventDefault(); void search(); }}><label class="nf-field-label"><span>{zh() ? "搜索 Project evidence" : "Search Project evidence"}</span><input class="wui-input" value={query()} onInput={(event) => setQuery(event.currentTarget.value)} /></label><button class="wui-button wui-button--solid" disabled={loading() || !query().trim() || !studio.projectId()}>{loading() ? (zh() ? "搜索中…" : "Searching…") : (zh() ? "搜索" : "Search")}</button></form>
        <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><span class="wui-alert__description">{message()}</span></div></div>}</Show>
        <div class="qf-search-results" aria-live="polite"><For each={rows()}>{(row) => <article><div><strong>{row.title}</strong><span class="qf-authority-label">evidence</span></div><small class="nf-mono">{row.entity_type} · {row.entity_id}</small><p>{row.snippet}</p></article>}</For><Show when={!rows().length && query()}><p>{zh() ? "没有返回结果。" : "No results returned."}</p></Show></div>
      </div>
      <aside class="qf-awaiting-core" role="status"><div><strong>awaiting_external</strong><code>research/corpus projections</code></div><p>{zh() ? "Corpus ingest、source provenance、rights 与 research claim 列表需要 Core-owned typed operations；Studio 不会从 search result 猜这些状态。" : "Corpus ingest, source provenance, rights and research-claim lists require Core-owned typed operations; Studio will not infer them from search results."}</p></aside>
    </section>
  );
}

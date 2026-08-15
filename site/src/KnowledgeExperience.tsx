import { For, Show, createMemo, createResource, createSignal } from "solid-js";
import type { JSX } from "solid-js";
import DocumentRenderer from "./DocumentRenderer";
import {
  loadKnowledgeIndex,
  loadProductDocument,
  searchKnowledge,
  type DocIndexEntry,
  type KnowledgeLocale,
} from "./knowledge";
import {
  humanDocKind,
  knowledgeJourneyDefinition,
  knowledgeJourneyFor,
  knowledgeJourneys,
  readableDocSummary,
  recommendedStartDocs,
  type KnowledgeJourney,
} from "./knowledgePresentation";

const copy = {
  "zh-CN": {
    eyebrow: "NovelForge 知识库",
    title: "先说你想做什么，再决定要不要往深处读。",
    lede: "这里按实际使用场景来组织内容，不要求你先记住框架里的术语。可以从推荐路线开始，也可以直接搜一个问题。",
    search: "搜索文档、概念或问题…",
    start: "从这里开始",
    startLede: "第一次了解 NovelForge，建议先看这几篇。",
    browse: "按你现在要做的事来找",
    browseLede: "不用先知道内部模块叫什么。选中你正在做的事，就能看到相关内容。",
    results: "搜索结果",
    clear: "清除搜索",
    empty: "没找到相关内容。换个说法再试试 (｡•́︿•̀｡)",
    docs: "篇",
    back: "返回知识库",
    toc: "本页内容",
    source: "来源与版本",
    sourceLede: "需要核对仓库来源时再展开；平时阅读不用管它。",
    popular: "建议先读",
    searchHint: "会搜索标题、章节和正文",
    openError: "这篇文档刚才没有打开。",
    retry: "再试一次",
  },
  "en-US": {
    eyebrow: "NovelForge Knowledge",
    title: "Start with the problem you need to solve, then go as deep as you want.",
    lede: "Knowledge is organized around the creative journey, not internal framework taxonomy. Follow a recommended path or search for a question directly.",
    search: "Search docs, concepts, or questions…",
    start: "Start here",
    startLede: "New to NovelForge? This is the recommended reading path.",
    browse: "Browse by goal",
    browseLede: "You do not need to know the framework's internal vocabulary first. Pick what you are trying to do.",
    results: "Search results",
    clear: "Clear search",
    empty: "Nothing matched that search — try another phrase (｡•́︿•̀｡)",
    docs: "docs",
    back: "Back to Knowledge",
    toc: "On this page",
    source: "Technical source",
    sourceLede: "Repository provenance lives here so it does not interrupt the reading experience.",
    popular: "Recommended",
    searchHint: "Searches titles, sections, and document text",
    openError: "This guide did not open.",
    retry: "Try again",
  },
} as const;

function text(locale: KnowledgeLocale) {
  return copy[locale];
}

function localDocs(index: Awaited<ReturnType<typeof loadKnowledgeIndex>> | undefined, locale: KnowledgeLocale) {
  return index?.documents.filter((doc) => doc.locale === locale) ?? [];
}

function navigateSpa(event: MouseEvent, href: string) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  if (window.location.pathname === href) return;

  // main.tsx wraps pushState and emits novelforge:locationchange for this
  // replacement surface. Do not also synthesize popstate: @solidjs/router owns
  // that event and would re-render the legacy route under our portal mid-click.
  window.history.pushState({}, "", href);
  window.scrollTo(0, 0);
}

function KnowledgeLink(props: { href: string; class?: string; children: JSX.Element }) {
  return <a class={props.class} href={props.href} onClick={(event) => navigateSpa(event, props.href)}>{props.children}</a>;
}

function GuideRow(props: { doc: DocIndexEntry; locale: KnowledgeLocale; featured?: boolean }) {
  const journey = () => knowledgeJourneyDefinition(knowledgeJourneyFor(props.doc));
  const href = () => `/docs/${encodeURIComponent(props.doc.id)}`;
  return (
    <KnowledgeLink class={`knowledge-guide-row ${props.featured ? "knowledge-guide-row--featured" : ""}`} href={href()}>
      <span class="knowledge-guide-icon" aria-hidden="true">{journey().icon}</span>
      <span class="knowledge-guide-copy">
        <span class="knowledge-guide-kicker">{journey().label[props.locale]} · {humanDocKind(props.doc, props.locale)}</span>
        <strong>{props.doc.title}</strong>
        <small>{readableDocSummary(props.doc, props.locale)}</small>
      </span>
      <span class="knowledge-guide-arrow" aria-hidden="true">→</span>
    </KnowledgeLink>
  );
}

export function KnowledgeExplorer(props: { locale: KnowledgeLocale }) {
  const t = () => text(props.locale);
  const [index] = createResource(loadKnowledgeIndex);
  const [query, setQuery] = createSignal("");
  const [journey, setJourney] = createSignal<KnowledgeJourney>("start");

  const allDocs = createMemo(() => localDocs(index(), props.locale));
  const startDocs = createMemo(() => recommendedStartDocs(allDocs()));
  const journeyDocs = createMemo(() => allDocs().filter((doc) => knowledgeJourneyFor(doc) === journey()).slice(0, 18));
  const results = createMemo(() => searchKnowledge(index(), props.locale, query(), 40));
  const activeJourney = createMemo(() => knowledgeJourneyDefinition(journey()));
  const journeyCount = (key: KnowledgeJourney) => allDocs().filter((doc) => knowledgeJourneyFor(doc) === key).length;
  const searching = createMemo(() => query().trim().length > 0);

  return (
    <div class="knowledge-v2 page-width">
      <section class="knowledge-v2-hero">
        <div class="knowledge-v2-heading">
          <p class="eyebrow">{t().eyebrow}</p>
          <h1>{t().title}</h1>
          <p>{t().lede}</p>
        </div>
        <label class="knowledge-v2-search wui-input-group">
          <span class="wui-input-group__prefix" aria-hidden="true">⌕</span>
          <input
            class="wui-input wui-input--with-addons"
            value={query()}
            onInput={(event) => setQuery(event.currentTarget.value)}
            placeholder={t().search}
            aria-label={t().search}
          />
          <Show when={query()}>
            <button type="button" class="wui-input-group__clear" onClick={() => setQuery("")} aria-label={t().clear}>×</button>
          </Show>
        </label>
        <div class="knowledge-v2-search-meta"><span>{allDocs().length} {t().docs}</span><span>{t().searchHint}</span></div>
      </section>

      <Show when={!index.loading} fallback={<div class="knowledge-v2-loading">✧ {props.locale === "zh-CN" ? "正在整理书架…" : "Organizing the library…"}</div>}>
        <Show when={searching()} fallback={
          <>
            <section class="knowledge-start-here">
              <div class="knowledge-section-heading"><div><span>✦</span><div><h2>{t().start}</h2><p>{t().startLede}</p></div></div><small>{t().popular}</small></div>
              <div class="knowledge-start-grid">
                <For each={startDocs()}>{(doc) => <GuideRow doc={doc} locale={props.locale} featured />}</For>
              </div>
            </section>

            <section class="knowledge-browse-v2">
              <div class="knowledge-section-heading"><div><span>⌁</span><div><h2>{t().browse}</h2><p>{t().browseLede}</p></div></div></div>
              <div class="knowledge-browser-shell">
                <nav class="knowledge-journey-nav" aria-label={t().browse}>
                  <For each={knowledgeJourneys}>{(item) => (
                    <button type="button" data-active={journey() === item.key} onClick={() => setJourney(item.key)}>
                      <span class="knowledge-journey-icon" aria-hidden="true">{item.icon}</span>
                      <span><strong>{item.label[props.locale]}</strong><small>{item.description[props.locale]}</small></span>
                      <b>{journeyCount(item.key)}</b>
                    </button>
                  )}</For>
                </nav>

                <div class="knowledge-topic-panel">
                  <header><span class="knowledge-topic-icon" aria-hidden="true">{activeJourney().icon}</span><div><h2>{activeJourney().label[props.locale]}</h2><p>{activeJourney().description[props.locale]}</p></div></header>
                  <div class="knowledge-topic-list">
                    <For each={journeyDocs()}>{(doc) => <GuideRow doc={doc} locale={props.locale} />}</For>
                  </div>
                </div>
              </div>
            </section>
          </>
        }>
          <section class="knowledge-search-results">
            <div class="knowledge-section-heading"><div><span>⌕</span><div><h2>{t().results}</h2><p>{results().length} {t().docs}</p></div></div><button class="wui-button wui-button--ghost" type="button" onClick={() => setQuery("")}>{t().clear}</button></div>
            <Show when={results().length > 0} fallback={<div class="knowledge-v2-empty"><span>₍^. .^₎⟆</span><h3>{t().empty}</h3></div>}>
              <div class="knowledge-result-list"><For each={results()}>{(doc) => <GuideRow doc={doc} locale={props.locale} />}</For></div>
            </Show>
          </section>
        </Show>
      </Show>
    </div>
  );
}

export function KnowledgeDocumentPage(props: { locale: KnowledgeLocale; docId: string }) {
  const t = () => text(props.locale);
  const [document, { refetch }] = createResource(() => [props.locale, props.docId] as const, ([lang, id]) => loadProductDocument(lang, id));
  const [index] = createResource(loadKnowledgeIndex);
  const entry = createMemo(() => index()?.documents.find((doc) => doc.locale === props.locale && doc.id === props.docId));
  const journey = createMemo(() => entry() ? knowledgeJourneyDefinition(knowledgeJourneyFor(entry()!)) : knowledgeJourneys[0]);
  const related = createMemo(() => {
    const current = entry();
    if (!current) return [];
    return localDocs(index(), props.locale)
      .filter((doc) => doc.id !== current.id && knowledgeJourneyFor(doc) === knowledgeJourneyFor(current))
      .slice(0, 5);
  });

  return (
    <div class="knowledge-document-v2 page-width">
      <div class="knowledge-document-topbar">
        <KnowledgeLink class="wui-button wui-button--ghost" href="/docs">← {t().back}</KnowledgeLink>
        <Show when={entry()}>{(doc) => <span class="knowledge-document-kind">{journey().icon} {journey().label[props.locale]} · {humanDocKind(doc(), props.locale)}</span>}</Show>
      </div>
      <Show when={!document.loading} fallback={<div class="knowledge-v2-loading">✧ {props.locale === "zh-CN" ? "正在打开文档…" : "Opening guide…"}</div>}>
        <Show when={document()} fallback={
          <div class="knowledge-v2-empty">
            <span>₍^. .^₎⟆</span>
            <h3>{t().openError}</h3>
            <button type="button" class="wui-button wui-button--soft" onClick={() => refetch()}>{t().retry}</button>
          </div>
        }>
          {(doc) => (
            <div class="knowledge-document-layout">
              <aside class="knowledge-document-context">
                <strong>{journey().label[props.locale]}</strong>
                <p>{journey().description[props.locale]}</p>
                <Show when={related().length > 0}>
                  <span class="knowledge-context-label">{props.locale === "zh-CN" ? "同主题继续阅读" : "Continue this topic"}</span>
                  <For each={related()}>{(item) => <KnowledgeLink href={`/docs/${encodeURIComponent(item.id)}`}>{item.title}<span>→</span></KnowledgeLink>}</For>
                </Show>
              </aside>

              <DocumentRenderer document={doc()} locale={props.locale} />

              <aside class="knowledge-document-toc">
                <strong>{t().toc}</strong>
                <For each={doc().toc.filter((item) => item.level <= 3).slice(0, 28)}>{(item) => <a href={`#${item.id}`} class={`toc-level-${item.level}`}>{item.text}</a>}</For>
                <details class="knowledge-source-details">
                  <summary>{t().source}</summary>
                  <p>{t().sourceLede}</p>
                  <code>{doc().sourcePath}</code>
                </details>
              </aside>
            </div>
          )}
        </Show>
      </Show>
    </div>
  );
}

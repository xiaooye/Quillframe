import { A, Route, Router, useLocation, useNavigate, useParams } from "@solidjs/router";
import {
  For,
  Show,
  createEffect,
  createMemo,
  createResource,
  createSignal,
  onCleanup,
  type JSX,
} from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import DocumentRenderer from "./DocumentRenderer";
import { githubRoot, type Locale } from "./content";
import { enUS } from "./content.en-US";
import { zhCN } from "./content.zh-CN";
import {
  loadKnowledgeIndex,
  loadProductDocument,
  searchKnowledge,
  type DocIndexEntry,
} from "./knowledge";

const siteCopy = { "en-US": enUS, "zh-CN": zhCN } as const;
const studioUrl = "https://studio.novelforge.wei-dev.com";

type TransitionDocument = Document & {
  startViewTransition?: (update: () => void) => unknown;
};

type CommandResult = {
  kind: "route" | "external" | "doc";
  icon: string;
  label: string;
  description: string;
  href: string;
  badge?: string;
};

const entryCopy = {
  "zh-CN": {
    search: "搜索 NovelForge",
    searchPlaceholder: "搜索产品、文档、架构、出版…",
    openStudio: "打开 Studio",
    launch: "开始探索",
    heroEyebrow: "长篇小说创作系统 · 0.8.x",
    heroTitle: "让故事越写越长，系统仍然知道自己在做什么。",
    heroLede: "NovelForge 把创作、上下文、角色知识、质量审查与出版连成一套可检查的工作流。你可以从这里直接进入 Studio、搜索真实文档、探索架构，或者试试关键机制。",
    cuteHint: "今天也把故事织得更漂亮一点吧 (｡•̀ᴗ-)✧",
    capabilityTitle: "六条真实产品能力",
    capabilityLede: "不是 feature list；每一项都对应当前主分支里的真实契约。点开看看它解决什么问题。",
    labEyebrow: "可以直接玩",
    labTitle: "别只读介绍，动一下系统边界。",
    contextTitle: "上下文预算实验",
    contextNote: "示意推演 · authority=false",
    gateTitle: "候选稿就绪实验",
    gateNote: "同一候选稿的必要条件必须全部通过",
    ready: "可以进入审查 ✨",
    notReady: "还差一点点 (´• ω •`)ﾉ",
    productWorld: "从一个入口进入整个产品",
    knowledgeTitle: "真实文档已经进入产品本身",
    knowledgeLede: "文档在构建时从仓库权威源编译进 SPA。可以搜索、阅读、深链，不需要先跳去 GitHub。",
    docs: "知识库",
    architecture: "架构探索",
    publication: "出版",
    product: "产品能力",
    changelog: "版本状态",
    home: "首页",
    commandHint: "⌘K / Ctrl+K",
    filters: "筛选",
    all: "全部",
    noResults: "没有找到，再换个词试试 ฅ^•ﻌ•^ฅ",
    source: "来源",
    openDocument: "打开文档",
    current: "当前",
    illustrative: "示意",
    hostedStudio: "Hosted Studio",
    unbound: "未绑定 Core",
    hostedNote: "当前云端 Studio 是真实的只读产品壳，但不会假装已经绑定你的 Core。",
    openHosted: "进入 Hosted Studio ↗",
    architectureTitle: "点一个子系统，看它真正负责什么。",
    publicationTitle: "同一份接受稿，可以确定地生成不同派生格式。",
    productTitle: "NovelForge 的价值不在“会写”，而在“长期不会乱”。",
    releaseTitle: "0.8.x 仍在 1.0 前快速演进",
    backDocs: "返回知识库",
    toc: "本页目录",
    copied: "复制好啦 ✨",
    reading: "正在织入文档…",
    error: "读取失败了 (╥﹏╥)",
  },
  "en-US": {
    search: "Search NovelForge",
    searchPlaceholder: "Search product, docs, architecture, publication…",
    openStudio: "Open Studio",
    launch: "Explore",
    heroEyebrow: "Long-form fiction system · 0.8.x",
    heroTitle: "Let the story grow without letting the system lose the plot.",
    heroLede: "NovelForge connects creation, context, character knowledge, quality gates, and publication into one inspectable workflow. Launch Studio, search real docs, explore architecture, or play with the core boundaries from here.",
    cuteHint: "Let’s weave something lovely today (｡•̀ᴗ-)✧",
    capabilityTitle: "Six real product capabilities",
    capabilityLede: "Not a feature wall. Every item maps to a contract that exists on current main. Pick one to inspect the problem it owns.",
    labEyebrow: "Try it",
    labTitle: "Don’t just read the pitch. Touch the boundaries.",
    contextTitle: "Context budget lab",
    contextNote: "illustrative derivation · authority=false",
    gateTitle: "Candidate readiness lab",
    gateNote: "all required evidence for the same candidate must pass",
    ready: "Ready for review ✨",
    notReady: "Not quite yet (´• ω •`)ﾉ",
    productWorld: "One entry point into the whole product",
    knowledgeTitle: "Real documentation now lives inside the product",
    knowledgeLede: "Docs are compiled at build time from repository authority into the SPA. Search, read, and deep-link without leaving for GitHub first.",
    docs: "Knowledge",
    architecture: "Architecture",
    publication: "Publication",
    product: "Product",
    changelog: "Release status",
    home: "Home",
    commandHint: "⌘K / Ctrl+K",
    filters: "Filters",
    all: "All",
    noResults: "Nothing here yet — try another search ฅ^•ﻌ•^ฅ",
    source: "Source",
    openDocument: "Open document",
    current: "Current",
    illustrative: "Illustrative",
    hostedStudio: "Hosted Studio",
    unbound: "Core unbound",
    hostedNote: "The hosted Studio is a real read-only product shell. It does not pretend a Core host is already bound.",
    openHosted: "Open Hosted Studio ↗",
    architectureTitle: "Pick a subsystem and inspect what it actually owns.",
    publicationTitle: "One accepted manuscript can deterministically produce several derived formats.",
    productTitle: "NovelForge is valuable not because it can write, but because a long-running book does not quietly lose its rules.",
    releaseTitle: "0.8.x is still moving quickly before 1.0",
    backDocs: "Back to Knowledge",
    toc: "On this page",
    copied: "Copied ✨",
    reading: "Weaving document…",
    error: "Couldn’t load that one (╥﹏╥)",
  },
} as const;

const initialLocale = (): Locale => {
  const saved = localStorage.getItem("novelforge.locale");
  if (saved === "zh-CN" || saved === "en-US") return saved;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
};

const initialDark = (): boolean => {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
};

const [locale, setLocale] = createSignal<Locale>(initialLocale());
const [dark, setDark] = createSignal(initialDark());
const copy = () => siteCopy[locale()];
const ui = () => entryCopy[locale()];

function withViewTransition(update: () => void) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const doc = document as TransitionDocument;
  if (reduced || typeof doc.startViewTransition !== "function") {
    update();
    return;
  }
  doc.startViewTransition(update);
}

function syncDocumentState() {
  const lang = locale();
  document.documentElement.lang = lang === "zh-CN" ? "zh-CN" : "en";
  document.documentElement.dataset.locale = lang;
  document.documentElement.classList.toggle("dark", dark());
  localStorage.setItem("novelforge.locale", lang);
  localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
}

function updatePointerLight(event: PointerEvent & { currentTarget: HTMLElement }) {
  if (event.pointerType === "touch") return;
  const rect = event.currentTarget.getBoundingClientRect();
  const x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100));
  const y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100));
  event.currentTarget.style.setProperty("--pointer-x", `${x}%`);
  event.currentTarget.style.setProperty("--pointer-y", `${y}%`);
}

function AppShell(props: { children?: JSX.Element }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = createSignal(false);
  const [query, setQuery] = createSignal("");
  const [highlighted, setHighlighted] = createSignal(0);
  const [knowledge] = createResource(loadKnowledgeIndex);
  let commandDialog: HTMLDialogElement | undefined;
  let commandInput: HTMLInputElement | undefined;

  createEffect(syncDocumentState);
  createEffect(() => {
    location.pathname;
    setMenuOpen(false);
  });

  const labels = () => copy().nav;
  const nav = () => [
    ["/product", labels().product],
    ["/studio", labels().studio],
    ["/architecture", labels().architecture],
    ["/publication", labels().publication],
    ["/docs", labels().docs],
  ] as const;

  const routeResults = (): CommandResult[] => [
    { kind: "route", icon: "⌂", label: ui().home, description: ui().heroLede, href: "/" },
    { kind: "external", icon: "✦", label: ui().openStudio, description: ui().hostedNote, href: studioUrl, badge: ui().current },
    { kind: "route", icon: "♡", label: ui().product, description: copy().routes.product.lede, href: "/product" },
    { kind: "route", icon: "⌘", label: ui().architecture, description: copy().routes.architecture.lede, href: "/architecture" },
    { kind: "route", icon: "✧", label: ui().publication, description: copy().routes.publication.lede, href: "/publication" },
    { kind: "route", icon: "📚", label: ui().docs, description: ui().knowledgeLede, href: "/docs" },
    { kind: "route", icon: "↗", label: ui().changelog, description: copy().routes.changelog.lede, href: "/changelog" },
  ];

  const commandResults = createMemo<CommandResult[]>(() => {
    const q = query().trim().toLocaleLowerCase();
    const routes = routeResults().filter((item) => !q || `${item.label} ${item.description}`.toLocaleLowerCase().includes(q));
    const docs = searchKnowledge(knowledge(), locale(), query(), 8).map((doc) => ({
      kind: "doc" as const,
      icon: doc.tier === "A" ? "✦" : doc.tier === "B" ? "·" : "#",
      label: doc.title,
      description: doc.excerpt,
      href: `/docs/${encodeURIComponent(doc.id)}`,
      badge: `Tier ${doc.tier}`,
    }));
    return [...routes, ...docs].slice(0, 12);
  });

  const closeCommand = () => commandDialog?.open && commandDialog.close();
  const openCommand = () => {
    if (!commandDialog?.open) commandDialog?.showModal();
    setHighlighted(0);
    queueMicrotask(() => commandInput?.focus());
  };

  const runResult = (result: CommandResult) => {
    closeCommand();
    setQuery("");
    if (result.kind === "external") {
      window.open(result.href, "_blank", "noopener,noreferrer");
      return;
    }
    withViewTransition(() => navigate(result.href));
  };

  const handleCommandKey = (event: KeyboardEvent) => {
    const results = commandResults();
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((value) => Math.min(results.length - 1, value + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((value) => Math.max(0, value - 1));
    } else if (event.key === "Enter" && results[highlighted()]) {
      event.preventDefault();
      runResult(results[highlighted()]);
    }
  };

  createEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        openCommand();
      }
    };
    window.addEventListener("keydown", listener);
    onCleanup(() => window.removeEventListener("keydown", listener));
  });

  const zh = () => locale() === "zh-CN";
  const toggleLocale = () => withViewTransition(() => setLocale(zh() ? "en-US" : "zh-CN"));
  const toggleDark = () => withViewTransition(() => setDark((value) => !value));

  return (
    <div class="site-shell product-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <A href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </A>

        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "主导航" : "Primary navigation"}>
          <For each={nav()}>{([href, label]) => <A href={href} class="wui-app-bar__link" activeClass="active" end={false}>{label}</A>}</For>
        </nav>

        <div class="wui-app-bar__actions header-actions">
          <button type="button" class="wui-button wui-button--soft header-search" onClick={openCommand}>
            <span aria-hidden="true">⌕</span><span>{ui().search}</span><kbd>{ui().commandHint}</kbd>
          </button>
          <a class="wui-button wui-button--solid studio-cta" href={studioUrl} target="_blank" rel="noreferrer">✦ {ui().openStudio}</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={toggleLocale} aria-label={zh() ? "切换到英文" : "Switch language"}>{copy().languageName}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={toggleDark} aria-label={labels().appearance}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
          <button class="wui-button wui-button--ghost wui-button--icon-only mobile-menu-button" type="button" aria-expanded={menuOpen()} aria-controls="mobile-navigation" onClick={() => setMenuOpen((value) => !value)} aria-label={menuOpen() ? labels().close : labels().menu}><span aria-hidden="true">{menuOpen() ? "×" : "≡"}</span></button>
        </div>
      </header>

      <Show when={menuOpen()}>
        <nav id="mobile-navigation" class="mobile-nav wui-card" aria-label={zh() ? "移动端导航" : "Mobile navigation"}>
          <For each={nav()}>{([href, label]) => <A href={href} class="wui-sidebar__item" activeClass="active">{label}</A>}</For>
          <button type="button" class="wui-sidebar__item" onClick={openCommand}>⌕ {ui().search}</button>
          <a class="wui-sidebar__item" href={studioUrl} target="_blank" rel="noreferrer">✦ {ui().openStudio}</a>
        </nav>
      </Show>

      <main id="main-content">{props.children}</main>

      <nav class="wui-bottom-nav mobile-bottom-nav" aria-label={zh() ? "快速导航" : "Quick navigation"}>
        <A href="/" class="wui-bottom-nav__item" activeClass="active" end><span class="wui-bottom-nav__icon">⌂</span><span class="wui-bottom-nav__label">{ui().home}</span></A>
        <a href={studioUrl} target="_blank" rel="noreferrer" class="wui-bottom-nav__item"><span class="wui-bottom-nav__icon">✦</span><span class="wui-bottom-nav__label">Studio</span></a>
        <A href="/docs" class="wui-bottom-nav__item" activeClass="active"><span class="wui-bottom-nav__icon">📚</span><span class="wui-bottom-nav__label">{ui().docs}</span></A>
        <button type="button" class="wui-bottom-nav__item" onClick={openCommand}><span class="wui-bottom-nav__icon">⌕</span><span class="wui-bottom-nav__label">{ui().search}</span></button>
      </nav>

      <footer class="site-footer">
        <div class="page-width footer-grid">
          <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{ui().cuteHint}</p></div>
          <div class="footer-links"><A href="/product">{ui().product}</A><A href="/architecture">{ui().architecture}</A><A href="/publication">{ui().publication}</A><A href="/docs">{ui().docs}</A></div>
          <div class="footer-links"><a href={studioUrl} target="_blank" rel="noreferrer">Hosted Studio ↗</a><A href="/changelog">0.8.x</A><a href={githubRoot} target="_blank" rel="noreferrer">GitHub ↗</a></div>
        </div>
      </footer>

      <dialog ref={commandDialog} class="command-dialog" onClose={() => setQuery("")} onClick={(event) => { if (event.target === commandDialog) closeCommand(); }}>
        <div class="wui-command command-surface">
          <div class="command-cute-strip"><span>✦</span><strong>{ui().search}</strong><span>{ui().cuteHint}</span></div>
          <div class="wui-command__input-wrapper">
            <span class="wui-command__icon" aria-hidden="true">⌕</span>
            <input
              ref={commandInput}
              class="wui-command__input"
              value={query()}
              onInput={(event) => { setQuery(event.currentTarget.value); setHighlighted(0); }}
              onKeyDown={handleCommandKey}
              placeholder={ui().searchPlaceholder}
              aria-label={ui().search}
            />
            <kbd>Esc</kbd>
          </div>
          <div class="wui-command__list" role="listbox">
            <Show when={!knowledge.loading} fallback={<div class="wui-command-palette__loading">✧ {locale() === "zh-CN" ? "正在载入知识索引…" : "Loading knowledge index…"}</div>}>
              <Show when={commandResults().length > 0} fallback={<div class="wui-command__empty">{ui().noResults}</div>}>
                <For each={commandResults()}>{(result, index) => (
                  <button type="button" class="wui-command__item command-result" data-highlighted={highlighted() === index()} role="option" aria-selected={highlighted() === index()} onMouseEnter={() => setHighlighted(index())} onClick={() => runResult(result)}>
                    <span class="command-result-icon" aria-hidden="true">{result.icon}</span>
                    <span class="command-result-copy"><strong>{result.label}</strong><small>{result.description}</small></span>
                    <Show when={result.badge}><span class="wui-badge wui-badge--outline">{result.badge}</span></Show>
                    <span aria-hidden="true">→</span>
                  </button>
                )}</For>
              </Show>
            </Show>
          </div>
        </div>
      </dialog>
    </div>
  );
}

const capabilityIcons = ["🧵", "🫧", "🧠", "♡", "✓", "📖"];
const capabilityLanes = ["project", "runtime", "editorial", "evidence", "validated", "publication"];

function HomePage() {
  const c = () => copy().home;
  const [activeCapability, setActiveCapability] = createSignal(0);
  const [budget, setBudget] = createSignal(3);
  const [gates, setGates] = createSignal([true, true, false, true]);
  const [knowledge] = createResource(loadKnowledgeIndex);
  const zh = () => locale() === "zh-CN";

  const evidence = () => zh() ? [
    "当前场景计划",
    "角色此刻已知事实",
    "上章连续性摘要",
    "远期世界观资料",
    "未来章节伏笔",
  ] : [
    "Current scene plan",
    "Character-visible facts",
    "Previous chapter continuity",
    "Long-horizon world research",
    "Future chapter setup",
  ];

  const gateNames = () => zh() ? ["文本表面", "读者参与", "连续性", "独立语义"] : ["Surface", "Reader", "Continuity", "Independent semantic"];
  const readiness = () => gates().every(Boolean);
  const tierADocs = createMemo(() => knowledge()?.documents.filter((doc) => doc.locale === locale() && doc.tier === "A").slice(0, 5) ?? []);

  return (
    <>
      <section class="entry-hero" onPointerMove={updatePointerLight}>
        <div class="hero-aurora" aria-hidden="true" />
        <div class="hero-sparkles" aria-hidden="true"><i>✦</i><i>♡</i><i>✧</i><i>⋆</i></div>
        <div class="page-width entry-hero-grid">
          <div class="entry-hero-copy">
            <div class="hero-status-row"><span class="wui-badge wui-badge--soft">{ui().heroEyebrow}</span><span class="tiny-kawaii">ฅ^•ﻌ•^ฅ</span></div>
            <h1>{ui().heroTitle}</h1>
            <p>{ui().heroLede}</p>
            <div class="hero-actions">
              <a class="wui-button wui-button--solid wui-button--xl hero-primary" href={studioUrl} target="_blank" rel="noreferrer">✦ {ui().openStudio}</a>
              <A class="wui-button wui-button--soft wui-button--xl" href="/docs">📚 {ui().docs}</A>
              <A class="wui-button wui-button--ghost wui-button--xl" href="/architecture">⌘ {ui().architecture}</A>
            </div>
            <div class="hero-trust"><span class="status-pulse" /><span>{zh() ? "产品主张来自 current main 已存在的契约" : "Product claims map to contracts that exist on current main"}</span></div>
          </div>

          <div class="hero-launcher wui-card material-panel" data-lane="runtime">
            <div class="launcher-topbar">
              <div><small>{zh() ? "产品入口" : "PRODUCT ENTRY"}</small><strong>{ui().launch}</strong></div>
              <span class="kawaii-bubble">{ui().cuteHint}</span>
            </div>
            <button type="button" class="wui-input-group launcher-search" onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}>
              <span class="wui-input-group__prefix">⌕</span><span class="launcher-search-label">{ui().searchPlaceholder}</span><span class="wui-input-group__suffix">{ui().commandHint}</span>
            </button>
            <div class="launcher-grid">
              <a class="launcher-tile lane-project" href={studioUrl} target="_blank" rel="noreferrer"><span>✦</span><div><strong>Studio</strong><small>{zh() ? "真正开始操作" : "Start operating"}</small></div><b>↗</b></a>
              <A class="launcher-tile lane-editorial" href="/product"><span>♡</span><div><strong>{ui().product}</strong><small>{zh() ? "看它解决什么" : "See what it solves"}</small></div><b>→</b></A>
              <A class="launcher-tile lane-evidence" href="/docs"><span>📚</span><div><strong>{ui().docs}</strong><small>{zh() ? "搜索真实文档" : "Search real docs"}</small></div><b>→</b></A>
              <A class="launcher-tile lane-validated" href="/publication"><span>✧</span><div><strong>{ui().publication}</strong><small>{zh() ? "从接受稿到派生格式" : "Accepted text to formats"}</small></div><b>→</b></A>
            </div>
            <div class="launcher-footer"><span>0.8.x</span><span>{zh() ? "pre-1.0 · 快速演进" : "pre-1.0 · actively evolving"}</span><span>authority=false</span></div>
          </div>
        </div>

        <div class="page-width capability-ribbon" aria-label={ui().capabilityTitle}>
          <For each={c().proofs}>{(card, index) => (
            <button type="button" class="capability-chip" data-lane={capabilityLanes[index()] ?? "runtime"} data-active={activeCapability() === index()} onClick={() => setActiveCapability(index())}>
              <span>{capabilityIcons[index()] ?? "✦"}</span><div><small>{card.eyebrow}</small><strong>{card.title}</strong></div>
            </button>
          )}</For>
        </div>
      </section>

      <section class="capability-focus page-width section-compact">
        <div class="section-kicker"><span>✦</span><div><small>{ui().capabilityTitle}</small><strong>{ui().capabilityLede}</strong></div></div>
        <div class="capability-focus-grid" data-lane={capabilityLanes[activeCapability()] ?? "runtime"}>
          <div class="capability-orb" aria-hidden="true"><span>{capabilityIcons[activeCapability()]}</span></div>
          <div><p class="eyebrow">{c().proofs[activeCapability()].eyebrow}</p><h2>{c().proofs[activeCapability()].title}</h2><p>{c().proofs[activeCapability()].body}</p><code>{c().proofs[activeCapability()].meta}</code></div>
          <div class="capability-actions"><A class="wui-button wui-button--soft" href="/product">{ui().product} →</A><A class="wui-button wui-button--ghost" href="/docs">{ui().docs} →</A></div>
        </div>
      </section>

      <section class="product-lab section-pad-soft">
        <div class="page-width">
          <div class="section-heading compact-heading"><p class="eyebrow">{ui().labEyebrow}</p><h2>{ui().labTitle}</h2></div>
          <div class="lab-grid">
            <article class="wui-card lab-card context-lab" data-lane="runtime">
              <div class="lab-card-header"><div><span class="lab-icon">🫧</span><small>{ui().contextNote}</small><h3>{ui().contextTitle}</h3></div><span class="wui-badge wui-badge--soft">{budget()}/5</span></div>
              <input class="budget-slider" type="range" min="1" max="5" step="1" value={budget()} onInput={(event) => setBudget(Number(event.currentTarget.value))} aria-label={ui().contextTitle} />
              <div class="evidence-stack"><For each={evidence()}>{(item, index) => <div class="evidence-row" data-loaded={index() < budget()}><span>{index() < budget() ? "✓" : "·"}</span><strong>{item}</strong><small>{index() < budget() ? (zh() ? "进入上下文" : "loaded") : (zh() ? "预算外" : "outside budget")}</small></div>}</For></div>
              <p class="lab-caption">{zh() ? "“系统里有”不等于“这次模型看到了”。" : "Stored by the system does not mean loaded for this call."}</p>
            </article>

            <article class="wui-card lab-card readiness-lab" data-lane={readiness() ? "validated" : "editorial"}>
              <div class="lab-card-header"><div><span class="lab-icon">♡</span><small>{ui().gateNote}</small><h3>{ui().gateTitle}</h3></div><span class={`wui-badge ${readiness() ? "wui-badge--success" : "wui-badge--warning"}`}>{readiness() ? "PASS" : "PENDING"}</span></div>
              <div class="gate-buttons"><For each={gateNames()}>{(name, index) => <button type="button" class="gate-toggle" aria-pressed={gates()[index()]} onClick={() => setGates((current) => current.map((value, i) => i === index() ? !value : value))}><span>{gates()[index()] ? "✓" : "○"}</span><strong>{name}</strong><small>{gates()[index()] ? "PASS" : "PENDING"}</small></button>}</For></div>
              <div class="readiness-result" data-ready={readiness()}><span aria-hidden="true">{readiness() ? "✦" : "♡"}</span><strong>{readiness() ? ui().ready : ui().notReady}</strong><code>fp: exact-candidate</code></div>
            </article>
          </div>
        </div>
      </section>

      <section class="product-world page-width section-compact">
        <div class="section-heading compact-heading"><p class="eyebrow">{ui().productWorld}</p><h2>{zh() ? "真正的产品入口，不是“继续阅读”。" : "Real product doors, not another ‘read more’."}</h2></div>
        <div class="portal-grid">
          <a class="portal-card studio-portal" href={studioUrl} target="_blank" rel="noreferrer"><div class="portal-icon">✦</div><div><small>{ui().hostedStudio}</small><h3>NovelForge Studio</h3><p>{ui().hostedNote}</p></div><span>↗</span></a>
          <A class="portal-card docs-portal" href="/docs"><div class="portal-icon">📚</div><div><small>{ui().docs}</small><h3>{ui().knowledgeTitle}</h3><p>{ui().knowledgeLede}</p></div><span>→</span></A>
          <A class="portal-card architecture-portal" href="/architecture"><div class="portal-icon">⌘</div><div><small>{ui().architecture}</small><h3>{ui().architectureTitle}</h3><p>{copy().routes.architecture.lede}</p></div><span>→</span></A>
          <A class="portal-card publication-portal" href="/publication"><div class="portal-icon">✧</div><div><small>{ui().publication}</small><h3>{ui().publicationTitle}</h3><p>{copy().routes.publication.lede}</p></div><span>→</span></A>
        </div>
      </section>

      <section class="knowledge-preview section-pad-soft">
        <div class="page-width knowledge-preview-grid">
          <div class="knowledge-preview-copy"><span class="kawaii-sticker">📚✨</span><p class="eyebrow">{ui().docs}</p><h2>{ui().knowledgeTitle}</h2><p>{ui().knowledgeLede}</p><A class="wui-button wui-button--solid" href="/docs">{ui().openDocument} →</A></div>
          <div class="knowledge-preview-list wui-card">
            <div class="knowledge-preview-meta"><span>{knowledge()?.documentCount ?? "…"} docs</span><span>build-time · authority=false</span></div>
            <For each={tierADocs()}>{(doc) => <A class="knowledge-preview-row" href={`/docs/${doc.id}`}><span class="wui-badge wui-badge--soft">Tier {doc.tier}</span><div><strong>{doc.title}</strong><small>{doc.excerpt}</small></div><span>→</span></A>}</For>
          </div>
        </div>
      </section>
    </>
  );
}

function ProductPage() {
  const cards = () => copy().routes.product.cards;
  const [selected, setSelected] = createSignal(0);
  return <InteractiveRouteFrame icon="♡" eyebrow={ui().product} title={ui().productTitle} lede={copy().routes.product.lede}>
    <div class="focus-browser">
      <div class="focus-browser-list"><For each={cards()}>{(card, index) => <button type="button" class="focus-browser-item" data-active={selected() === index()} onClick={() => setSelected(index())}><span>0{index() + 1}</span><strong>{card.title}</strong><small>{card.body}</small></button>}</For></div>
      <div class="focus-browser-detail wui-card" data-lane={capabilityLanes[selected()] ?? "runtime"}><span class="detail-kawaii">{capabilityIcons[selected()] ?? "✦"}</span><p class="eyebrow">{ui().product}</p><h2>{cards()[selected()].title}</h2><p>{cards()[selected()].body}</p><div class="detail-actions"><A class="wui-button wui-button--soft" href="/docs">📚 {ui().docs}</A><A class="wui-button wui-button--ghost" href="/architecture">⌘ {ui().architecture}</A></div></div>
    </div>
  </InteractiveRouteFrame>;
}

function StudioPage() {
  const cards = () => copy().routes.studio.cards;
  const [selected, setSelected] = createSignal(0);
  return <InteractiveRouteFrame icon="✦" eyebrow="NovelForge Studio" title={zhText("把创作放在前台，把系统证据放在需要时展开。", "Creation first. Evidence when you need it.")} lede={ui().hostedNote}>
    <div class="studio-entry-banner wui-card"><div><span class="wui-badge wui-badge--success">{ui().current}</span><h2>{ui().hostedStudio}</h2><p>{zhText("Phase 2D 已经有真实 Cloudflare-hosted 只读产品壳；默认保持 Core 未绑定，authority=false。", "Phase 2D ships a real Cloudflare-hosted read-only shell; Core remains unbound by default and authority=false.")}</p></div><a class="wui-button wui-button--solid wui-button--xl" href={studioUrl} target="_blank" rel="noreferrer">{ui().openHosted}</a></div>
    <div class="studio-capability-grid"><For each={cards()}>{(card, index) => <button type="button" class="wui-card wui-card--interactive studio-capability" data-active={selected() === index()} onClick={() => setSelected(index())}><span class="studio-cap-index">0{index() + 1}</span><small>{card.eyebrow}</small><h3>{card.title}</h3><p>{card.body}</p></button>}</For></div>
    <div class="studio-state-strip"><span>☁ Cloudflare Pages</span><span>◎ read-only</span><span>⊘ Core unbound</span><span>authority=false</span><span class="cute-state">(๑•̀ㅂ•́)و✧</span></div>
  </InteractiveRouteFrame>;
}

function ArchitecturePage() {
  const cards = () => copy().home.architecture.cards;
  const [selected, setSelected] = createSignal(0);
  return <InteractiveRouteFrame icon="⌘" eyebrow={ui().architecture} title={ui().architectureTitle} lede={copy().routes.architecture.lede}>
    <div class="architecture-explorer">
      <div class="architecture-map wui-card" aria-label={ui().architectureTitle}>
        <svg viewBox="0 0 700 520" aria-hidden="true"><path d="M350 260 C210 110 125 160 88 86 M350 260 C480 96 584 122 628 76 M350 260 C182 270 128 372 80 430 M350 260 C518 268 582 370 632 430 M350 260 C350 90 350 80 350 36 M350 260 C350 430 350 438 350 486" /></svg>
        <div class="architecture-core"><img src={brandMark} alt="" /><strong>NovelForge</strong><small>Core contracts</small></div>
        <For each={cards()}>{(card, index) => <button type="button" class={`architecture-node node-${index() + 1}`} data-active={selected() === index()} onClick={() => setSelected(index())}><span>{capabilityIcons[index()]}</span><strong>{card.title}</strong></button>}</For>
      </div>
      <aside class="architecture-detail wui-card" data-lane={capabilityLanes[selected()] ?? "runtime"}><p class="eyebrow">{cards()[selected()].eyebrow}</p><h2>{cards()[selected()].title}</h2><p>{cards()[selected()].body}</p><A class="wui-button wui-button--soft" href="/docs/architecture-atlas">📚 {ui().openDocument}</A></aside>
    </div>
  </InteractiveRouteFrame>;
}

function PublicationPage() {
  const profiles = () => copy().home.publication.profiles;
  const cards = () => copy().routes.publication.cards;
  const [selected, setSelected] = createSignal(0);
  return <InteractiveRouteFrame icon="✧" eyebrow={ui().publication} title={ui().publicationTitle} lede={copy().routes.publication.lede}>
    <div class="publication-explorer">
      <div class="publication-profile-tabs wui-tabs"><div class="wui-tabs__list" role="tablist"><For each={profiles()}>{(profile, index) => <button class="wui-tabs__trigger" type="button" role="tab" aria-selected={selected() === index()} onClick={() => setSelected(index())}>{profile}</button>}</For></div></div>
      <div class="publication-stage wui-card" data-lane={selected() === 3 ? "editorial" : selected() === 2 ? "evidence" : "validated"}>
        <div class="publication-source-chip"><span>✓</span><div><small>{zhText("接受正文", "ACCEPTED MANUSCRIPT")}</small><strong>sha256 · exact</strong></div></div><span class="publication-flow-arrow">→</span><div class="publication-output"><span class="publication-output-icon">{["TXT", "WEB", "PRINT", "EPUB"][selected()]}</span><div><small>{profiles()[selected()]}</small><h2>{cards()[selected()]?.title ?? profiles()[selected()]}</h2><p>{cards()[selected()]?.body}</p></div></div>
      </div>
      <div class="wui-alert wui-alert--info"><span>ⓘ</span><div><strong>authority=false</strong><p>{copy().home.publication.note}</p></div></div>
    </div>
  </InteractiveRouteFrame>;
}

function DocsExplorer() {
  const [knowledge] = createResource(loadKnowledgeIndex);
  const [query, setQuery] = createSignal("");
  const [tier, setTier] = createSignal("all");
  const docs = createMemo(() => {
    const result = searchKnowledge(knowledge(), locale(), query(), 80);
    return tier() === "all" ? result : result.filter((doc) => doc.tier === tier());
  });
  return <InteractiveRouteFrame icon="📚" eyebrow={ui().docs} title={ui().knowledgeTitle} lede={ui().knowledgeLede}>
    <div class="knowledge-explorer">
      <aside class="knowledge-sidebar wui-card">
        <div class="knowledge-search wui-input-group"><span class="wui-input-group__prefix">⌕</span><input class="wui-input wui-input--with-addons" value={query()} onInput={(event) => setQuery(event.currentTarget.value)} placeholder={ui().searchPlaceholder} aria-label={ui().search} /><Show when={query()}><button type="button" class="wui-input-group__clear" onClick={() => setQuery("")}>×</button></Show></div>
        <div class="knowledge-filter"><small>{ui().filters}</small><button type="button" class="wui-sidebar__item" data-active={tier() === "all"} onClick={() => setTier("all")}>{ui().all}<span>{knowledge()?.documents.filter((doc) => doc.locale === locale()).length ?? 0}</span></button><For each={["A", "B", "C"]}>{(value) => <button type="button" class="wui-sidebar__item" data-active={tier() === value} onClick={() => setTier(value)}>Tier {value}<span>{knowledge()?.documents.filter((doc) => doc.locale === locale() && doc.tier === value).length ?? 0}</span></button>}</For></div>
        <div class="knowledge-cute">📚<strong>{zhText("文档真的在这里。", "The docs really live here.")}</strong><span>₍^. .^₎⟆</span></div>
      </aside>
      <section class="knowledge-library">
        <div class="knowledge-library-bar"><span>{docs().length} results</span><span>build-time · authority=false</span></div>
        <Show when={!knowledge.loading} fallback={<div class="knowledge-loading">✧ {ui().reading}</div>}>
          <Show when={docs().length > 0} fallback={<div class="wui-empty-state knowledge-empty"><div class="wui-empty-state__icon">ฅ^•ﻌ•^ฅ</div><h3>{ui().noResults}</h3></div>}>
            <div class="knowledge-card-grid"><For each={docs()}>{(doc) => <KnowledgeCard doc={doc} />}</For></div>
          </Show>
        </Show>
      </section>
    </div>
  </InteractiveRouteFrame>;
}

function KnowledgeCard(props: { doc: DocIndexEntry }) {
  return <A class="wui-card wui-card--interactive knowledge-card" href={`/docs/${props.doc.id}`}><div class="knowledge-card-top"><span class="wui-badge wui-badge--soft">Tier {props.doc.tier}</span><span class="wui-badge wui-badge--outline">{props.doc.status}</span></div><h3>{props.doc.title}</h3><p>{props.doc.excerpt}</p><div class="knowledge-card-meta"><span>📄 {props.doc.sourcePath}</span><span>→</span></div></A>;
}

function DocumentPage() {
  const params = useParams();
  const [document] = createResource(() => [locale(), params.docId] as const, ([lang, id]) => loadProductDocument(lang, id));
  return <div class="document-page page-width">
    <div class="document-page-toolbar"><A class="wui-button wui-button--soft" href="/docs">← {ui().backDocs}</A><span class="wui-badge wui-badge--outline">build-time derivative</span></div>
    <Show when={!document.loading} fallback={<div class="knowledge-loading">✧ {ui().reading}</div>}>
      <Show when={document()} fallback={<div class="knowledge-loading">{ui().error}</div>}>
        {(doc) => <div class="document-layout"><aside class="document-toc wui-card"><strong>{ui().toc}</strong><For each={doc().toc.filter((item) => item.level <= 3).slice(0, 32)}>{(item) => <a href={`#${item.id}`} class={`toc-level-${item.level}`}>{item.text}</a>}</For><div class="toc-cute">(｡•̀ᴗ-)✧</div></aside><DocumentRenderer document={doc()} locale={locale()} /></div>}
      </Show>
    </Show>
  </div>;
}

function ChangelogPage() {
  const cards = () => copy().routes.changelog.cards;
  return <InteractiveRouteFrame icon="↗" eyebrow={ui().changelog} title={ui().releaseTitle} lede={copy().routes.changelog.lede}>
    <div class="release-board"><div class="release-current wui-card"><span class="release-version">0.8.x</span><div><span class="wui-badge wui-badge--success">{ui().current}</span><h2>{copy().routes.changelog.title}</h2><p>{copy().routes.changelog.lede}</p></div></div><div class="release-timeline"><For each={cards()}>{(card, index) => <div class="release-item"><span class="release-dot">{index() + 1}</span><div><h3>{card.title}</h3><p>{card.body}</p></div></div>}</For></div></div>
  </InteractiveRouteFrame>;
}

function InteractiveRouteFrame(props: { icon: string; eyebrow: string; title: string; lede: string; children: JSX.Element }) {
  return <div class="interactive-route"><section class="route-toolbar page-width"><div class="route-heading"><span class="route-icon">{props.icon}</span><div><p class="eyebrow">{props.eyebrow}</p><h1>{props.title}</h1><p>{props.lede}</p></div></div><div class="route-quick-actions"><A class="wui-button wui-button--soft" href="/docs">📚 {ui().docs}</A><a class="wui-button wui-button--solid" href={studioUrl} target="_blank" rel="noreferrer">✦ Studio</a></div></section><section class="route-content page-width">{props.children}</section></div>;
}

function zhText(zh: string, en: string) {
  return locale() === "zh-CN" ? zh : en;
}

export default function App() {
  return (
    <Router root={AppShell}>
      <Route path="/" component={HomePage} />
      <Route path="/product" component={ProductPage} />
      <Route path="/studio" component={StudioPage} />
      <Route path="/architecture" component={ArchitecturePage} />
      <Route path="/publication" component={PublicationPage} />
      <Route path="/docs" component={DocsExplorer} />
      <Route path="/docs/:docId" component={DocumentPage} />
      <Route path="/changelog" component={ChangelogPage} />
    </Router>
  );
}

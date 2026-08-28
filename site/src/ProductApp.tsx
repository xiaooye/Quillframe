import { A, Route, Router, useLocation, useNavigate } from "@solidjs/router";
import {
  For,
  Show,
  createContext,
  createEffect,
  createMemo,
  createResource,
  createSignal,
  onCleanup,
  useContext,
  type Accessor,
  type JSX,
} from "solid-js";
import brandMark from "../../assets/brand/quillframe-mark.svg?url";
import { githubRoot, type Locale } from "./content";
import { enUS } from "./content.en-US";
import { zhCN } from "./content.zh-CN";
import { loadKnowledgeIndex, searchKnowledge } from "./knowledge";
import ProjectInspector from "./ProjectInspector";
import LocalPlayground from "./LocalPlayground";
import QuickDemo from "./QuickDemo";
import PublicationWorkbench from "./PublicationWorkbench";
import { ProductSectionHeading, ProductSurfaceHero } from "./ProductSurface";

const siteCopy = { "en-US": enUS, "zh-CN": zhCN } as const;
const studioUrl = "https://studio.quillframe.wei-dev.com";
const productVersion = "1.0.0-dev.0";

const homeEntryCopy = {
  "zh-CN": {
    searchPlaceholder: "搜索产品、文档、架构、出版…",
    openStudio: "打开 Studio",
    launch: "开始探索",
    heroEyebrow: `长篇小说创作系统 · ${productVersion}`,
    heroTitle: "让故事越写越长，系统仍然知道自己在做什么。",
    heroLede: "Quillframe 把创作、上下文、角色知识、质量审查与出版连成一套可检查的工作流。你可以从这里直接进入 Studio、搜索真实文档、探索架构，或者试试关键机制。",
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
    knowledgeLede: "文档在构建时从仓库权威源编译进站点。可以搜索、阅读、深链，不需要先跳去 GitHub。",
    docs: "知识库",
    architecture: "架构探索",
    publication: "出版",
    product: "产品能力",
    hostedStudio: "Hosted Studio",
    hostedNote: "当前云端 Studio 是真实的只读产品壳，但不会假装已经绑定你的 Core。",
    architectureTitle: "点一个子系统，看它真正负责什么。",
    publicationTitle: "同一份接受稿，可以确定地生成不同派生格式。",
    openDocument: "打开文档",
    commandHint: "⌘K / Ctrl+K",
  },
  "en-US": {
    searchPlaceholder: "Search product, docs, architecture, publication…",
    openStudio: "Open Studio",
    launch: "Explore",
    heroEyebrow: `Long-form fiction system · ${productVersion}`,
    heroTitle: "Let the story grow without letting the system lose the plot.",
    heroLede: "Quillframe connects creation, context, character knowledge, quality gates, and publication into one inspectable workflow. Launch Studio, search real docs, explore architecture, or play with the core boundaries from here.",
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
    knowledgeLede: "Docs are compiled at build time from repository authority into the site. Search, read, and deep-link without leaving for GitHub first.",
    docs: "Knowledge",
    architecture: "Architecture",
    publication: "Publication",
    product: "Product",
    hostedStudio: "Hosted Studio",
    hostedNote: "The hosted Studio is a real read-only product shell. It does not pretend a Core host is already bound.",
    architectureTitle: "Pick a subsystem and inspect what it actually owns.",
    publicationTitle: "One accepted manuscript can deterministically produce several derived formats.",
    openDocument: "Open document",
    commandHint: "⌘K / Ctrl+K",
  },
} as const;

const capabilityIcons = ["🧵", "🫧", "🧠", "♡", "✓", "📖"];
const capabilityLanes = ["project", "runtime", "editorial", "evidence", "validated", "publication"];

type UiContextValue = {
  locale: Accessor<Locale>;
  dark: Accessor<boolean>;
  zh: Accessor<boolean>;
  toggleLocale: () => void;
  toggleDark: () => void;
};

type ShellNavItem = {
  kind: "route" | "document" | "external";
  href: string;
  label: string;
  icon?: string;
};

const UiContext = createContext<UiContextValue>();

function initialLocale(): Locale {
  const saved = localStorage.getItem("quillframe.locale");
  if (saved === "zh-CN" || saved === "en-US") return saved;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function initialDark() {
  const saved = localStorage.getItem("quillframe.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

const [locale, setLocale] = createSignal<Locale>(initialLocale());
const [dark, setDark] = createSignal(initialDark());
const copy = () => siteCopy[locale()];
const zh = () => locale() === "zh-CN";
const homeUi = () => homeEntryCopy[locale()];

function useUi() {
  const value = useContext(UiContext);
  if (!value) throw new Error("Product UI context is missing");
  return value;
}

function syncDocumentState() {
  document.documentElement.lang = zh() ? "zh-CN" : "en";
  document.documentElement.dataset.locale = locale();
  document.documentElement.classList.toggle("dark", dark());
  localStorage.setItem("quillframe.locale", locale());
  localStorage.setItem("quillframe.appearance", dark() ? "dark" : "light");
}

function updatePointerLight(event: PointerEvent & { currentTarget: HTMLElement }) {
  if (event.pointerType === "touch") return;
  const rect = event.currentTarget.getBoundingClientRect();
  const x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100));
  const y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100));
  event.currentTarget.style.setProperty("--pointer-x", `${x}%`);
  event.currentTarget.style.setProperty("--pointer-y", `${y}%`);
}

type CommandResult = {
  kind: "route" | "external";
  icon: string;
  label: string;
  description: string;
  href: string;
};

function ProductShell(props: { children?: JSX.Element }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = createSignal(false);
  const [query, setQuery] = createSignal("");
  const [highlighted, setHighlighted] = createSignal(0);
  const [knowledge] = createResource(loadKnowledgeIndex);
  let commandDialog: HTMLDialogElement | undefined;
  let commandInput: HTMLInputElement | undefined;
  let commandOpener: HTMLElement | undefined;

  const toggleLocale = () => setLocale((value) => value === "zh-CN" ? "en-US" : "zh-CN");
  const toggleDark = () => setDark((value) => !value);

  createEffect(syncDocumentState);
  createEffect(() => {
    location.pathname;
    setMenuOpen(false);
  });

  const primaryNav = (): ShellNavItem[] => [
    { kind: "route", href: "/product", label: copy().nav.product },
    { kind: "route", href: "/studio", label: copy().nav.studio },
    { kind: "route", href: "/architecture", label: copy().nav.architecture },
    { kind: "route", href: "/publication", label: copy().nav.publication },
    { kind: "document", href: zh() ? "/docs" : "/docs/en", label: copy().nav.docs, icon: "📚" },
    { kind: "external", href: githubRoot, label: copy().nav.github, icon: "↗" },
  ];

  const utilityNav = (): ShellNavItem[] => [
    { kind: "route", href: "/inspect", label: zh() ? "检查项目" : "Inspect", icon: "▣" },
    { kind: "route", href: "/playground", label: "Playground", icon: "▷" },
    { kind: "route", href: "/agents", label: zh() ? "Agent 集成" : "Agents", icon: "◈" },
    { kind: "route", href: "/changelog", label: copy().nav.changelog, icon: "◇" },
  ];

  const navLink = (item: ShellNavItem, className: string) => {
    const label = <>{item.icon ? <span aria-hidden="true">{item.icon}</span> : null}{item.label}</>;
    if (item.kind === "route") return <A href={item.href} class={className} activeClass="active">{label}</A>;
    if (item.kind === "external") return <a class={className} href={item.href} target="_blank" rel="noopener noreferrer">{label}</a>;
    return <a class={className} href={item.href}>{label}</a>;
  };

  const routeResults = createMemo<CommandResult[]>(() => [
    { kind: "route", icon: "⌂", label: zh() ? "首页" : "Home", description: copy().home.lede, href: "/" },
    { kind: "route", icon: "♡", label: copy().nav.product, description: copy().routes.product.lede, href: "/product" },
    { kind: "route", icon: "✦", label: copy().nav.studio, description: copy().routes.studio.lede, href: "/studio" },
    { kind: "route", icon: "⌘", label: copy().nav.architecture, description: copy().routes.architecture.lede, href: "/architecture" },
    { kind: "route", icon: "✧", label: copy().nav.publication, description: copy().routes.publication.lede, href: "/publication" },
    { kind: "external", icon: "📚", label: copy().nav.docs, description: zh() ? "搜索与阅读仓库权威文档。" : "Search and read repository-authoritative documentation.", href: zh() ? "/docs" : "/docs/en" },
    { kind: "external", icon: "↗", label: copy().nav.github, description: zh() ? "打开 Quillframe GitHub 仓库。" : "Open the Quillframe GitHub repository.", href: githubRoot },
    { kind: "route", icon: "▣", label: zh() ? "检查项目" : "Inspect project", description: zh() ? "在浏览器本地检查四键 Project manifest、context v1_0 与 .quillframe/data。" : "Inspect the four-key Project manifest, context v1_0, and .quillframe/data locally in the browser.", href: "/inspect" },
    { kind: "route", icon: "▷", label: "Playground", description: zh() ? "本地确定性 execution trace。" : "Local deterministic execution trace.", href: "/playground" },
    { kind: "route", icon: "◈", label: zh() ? "Agent 集成" : "Agent integration", description: zh() ? "通过 portable skill 与 Host Bridge 接入 coding agent。" : "Connect coding agents through the portable skill and Host Bridge.", href: "/agents" },
    { kind: "route", icon: "◇", label: copy().nav.changelog, description: copy().routes.changelog.lede, href: "/changelog" },
    { kind: "external", icon: "✦", label: zh() ? "Hosted Studio" : "Hosted Studio", description: zh() ? "打开 Hosted Studio；这是外部运行入口，不是 Studio 产品介绍页。" : "Open Hosted Studio; this is the external runtime entry, not the Studio product landing.", href: studioUrl },
  ]);

  const commandResults = createMemo(() => {
    const q = query().trim().toLocaleLowerCase();
    const routes = routeResults().filter((item) => !q || `${item.label} ${item.description}`.toLocaleLowerCase().includes(q));
    const docs = searchKnowledge(knowledge(), locale(), query(), 6).map((doc) => ({
      kind: "external" as const,
      icon: "📚",
      label: doc.title,
      description: doc.excerpt,
      href: locale() === "zh-CN" ? `/docs/${encodeURIComponent(doc.id)}` : `/docs/en/${encodeURIComponent(doc.id)}`,
    }));
    return [...routes, ...docs].slice(0, 12);
  });

  const openCommand = (trigger?: HTMLElement) => {
    if (!commandDialog?.open) {
      commandOpener = trigger ?? (typeof HTMLElement !== "undefined" && document.activeElement instanceof HTMLElement ? document.activeElement : undefined);
    }
    if (!commandDialog?.open) commandDialog?.showModal();
    setHighlighted(0);
    queueMicrotask(() => commandInput?.focus());
  };
  const closeCommand = () => commandDialog?.open && commandDialog.close();
  const handleCommandClose = () => {
    setQuery("");
    const target = commandOpener;
    commandOpener = undefined;
    queueMicrotask(() => {
      if (target?.isConnected && !("disabled" in target && Boolean((target as HTMLButtonElement).disabled)) && !target.inert) {
        target.focus();
        return;
      }
      document.querySelector<HTMLElement>(".header-search")?.focus();
    });
  };
  const runResult = (result: CommandResult) => {
    closeCommand();
    setQuery("");
    if (result.kind === "external") {
      if (result.href.startsWith("/docs")) window.location.assign(result.href);
      else window.open(result.href, "_blank", "noopener,noreferrer");
      return;
    }
    navigate(result.href);
  };

  createEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openCommand();
      }
    };
    window.addEventListener("keydown", listener);
    onCleanup(() => window.removeEventListener("keydown", listener));
  });

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

  const context: UiContextValue = { locale, dark, zh, toggleLocale, toggleDark };

  return (
    <UiContext.Provider value={context}>
      <div class="site-shell product-entry unified-product-shell">
        <header class="wui-app-bar product-appbar" data-position="sticky">
          <A href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "Quillframe 首页" : "Quillframe home"}>
            <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
            <span>Quillframe</span>
            <span class="wui-badge wui-badge--soft version-chip">{productVersion}</span>
          </A>
          <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "主导航" : "Primary navigation"}>
            <For each={primaryNav()}>{(item) => navLink(item, "wui-app-bar__link")}</For>
          </nav>
          <div class="wui-app-bar__actions header-actions">
            <button type="button" class="wui-button wui-button--soft header-search" aria-label={zh() ? "搜索 Quillframe" : "Search Quillframe"} onClick={(event) => openCommand(event.currentTarget)}><span>⌕</span><span>{zh() ? "搜索 Quillframe" : "Search Quillframe"}</span><kbd>⌘K / Ctrl+K</kbd></button>
            <a class="wui-button wui-button--solid studio-cta" href={studioUrl} target="_blank" rel="noopener noreferrer">✦ {zh() ? "打开 Studio" : "Open Studio"}</a>
            <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={toggleLocale} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{copy().languageName}</button>
            <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={toggleDark} aria-label={copy().nav.appearance}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
            <button class="wui-button wui-button--ghost wui-button--icon-only mobile-menu-button" type="button" aria-expanded={menuOpen()} onClick={() => setMenuOpen((value) => !value)}><span aria-hidden="true">{menuOpen() ? "×" : "≡"}</span></button>
          </div>
        </header>

        <Show when={menuOpen()}>
          <nav class="mobile-nav wui-card" aria-label={zh() ? "移动端导航" : "Mobile navigation"}>
            <For each={primaryNav()}>{(item) => navLink(item, "wui-sidebar__item")}</For>
            <For each={utilityNav()}>{(item) => navLink(item, "wui-sidebar__item")}</For>
            <a class="wui-sidebar__item" href={studioUrl} target="_blank" rel="noopener noreferrer">✦ Hosted Studio ↗</a>
          </nav>
        </Show>

        <main id="main-content" tabIndex={-1}>{props.children}</main>

        <footer class="site-footer unified-product-footer">
          <div class="page-width footer-grid">
            <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>Quillframe</strong></div><p>{zh() ? "一个产品壳，共享同一套导航、主题与语言状态。" : "One product shell, one navigation, theme, and locale state."}</p></div>
            <div class="footer-links"><For each={primaryNav()}>{(item) => navLink(item, "footer-link")}</For></div>
            <div class="footer-links"><For each={utilityNav()}>{(item) => navLink(item, "footer-link")}</For><a href={studioUrl} target="_blank" rel="noopener noreferrer">Hosted Studio ↗</a></div>
          </div>
        </footer>

        <dialog ref={commandDialog} class="command-dialog" aria-modal="true" aria-labelledby="product-command-heading" tabIndex={-1} onClose={handleCommandClose} onClick={(event) => { if (event.target === commandDialog) closeCommand(); }}>
          <div class="wui-command command-surface">
            <div class="command-cute-strip"><span>✦</span><h2 id="product-command-heading" class="wui-sr-only">{zh() ? "搜索 Quillframe" : "Search Quillframe"}</h2><strong aria-hidden="true">{zh() ? "搜索 Quillframe" : "Search Quillframe"}</strong><span>{zh() ? "今天也把故事织得漂亮一点吧" : "Weave something lovely today"}</span></div>
            <div class="wui-command__input-wrapper"><span class="wui-command__icon">⌕</span><input ref={commandInput} class="wui-command__input" value={query()} onInput={(event) => { setQuery(event.currentTarget.value); setHighlighted(0); }} onKeyDown={handleCommandKey} placeholder={zh() ? "搜索产品、文档、架构、出版…" : "Search product, docs, architecture, publication…"} /><kbd>Esc</kbd></div>
            <div class="wui-command__list" role="listbox"><For each={commandResults()}>{(result, index) => <button type="button" class="wui-command__item command-result" data-highlighted={highlighted() === index()} role="option" aria-selected={highlighted() === index()} onMouseEnter={() => setHighlighted(index())} onClick={() => runResult(result)}><span class="command-result-icon">{result.icon}</span><span class="command-result-copy"><strong>{result.label}</strong><small>{result.description}</small></span><span>→</span></button>}</For></div>
          </div>
        </dialog>
      </div>
    </UiContext.Provider>
  );
}

function HomePage() {
  const c = () => copy().home;
  const [activeCapability, setActiveCapability] = createSignal(0);
  const [budget, setBudget] = createSignal(3);
  const [gates, setGates] = createSignal([true, true, false, true]);
  const [knowledge] = createResource(loadKnowledgeIndex);
  const isZh = () => locale() === "zh-CN";
  const docsRoot = () => isZh() ? "/docs" : "/docs/en";
  const docHref = (id: string) => `${docsRoot()}/${encodeURIComponent(id)}`;

  const evidence = () => isZh() ? [
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

  const gateNames = () => isZh() ? ["文本表面", "读者参与", "连续性", "独立语义"] : ["Surface", "Reader", "Continuity", "Independent semantic"];
  const readiness = () => gates().every(Boolean);
  const tierADocs = createMemo(() => knowledge()?.documents.filter((doc) => doc.locale === locale() && doc.tier === "A").slice(0, 5) ?? []);

  return (
    <>
      <section id="thesis" class="entry-hero" data-home-section="thesis" onPointerMove={updatePointerLight}>
        <div class="hero-aurora" aria-hidden="true" />
        <div class="hero-sparkles" aria-hidden="true"><i>✦</i><i>♡</i><i>✧</i><i>⋆</i></div>
        <div class="page-width entry-hero-grid">
          <div class="entry-hero-copy">
            <div class="hero-status-row"><span class="wui-badge wui-badge--soft">{homeUi().heroEyebrow}</span><span class="tiny-kawaii">ฅ^•ﻌ•^ฅ</span></div>
            <h1>{homeUi().heroTitle}</h1>
            <p>{homeUi().heroLede}</p>
            <div class="hero-actions">
              <a class="wui-button wui-button--solid wui-button--xl hero-primary" href={studioUrl} target="_blank" rel="noreferrer">✦ {homeUi().openStudio}</a>
              <a class="wui-button wui-button--soft wui-button--xl" href={docsRoot()}>📚 {homeUi().docs}</a>
              <A class="wui-button wui-button--ghost wui-button--xl" href="/architecture">⌘ {homeUi().architecture}</A>
            </div>
            <div class="hero-trust"><span class="status-pulse" /><span>{isZh() ? "产品主张来自 current main 已存在的契约" : "Product claims map to contracts that exist on current main"}</span></div>
          </div>

          <div class="hero-launcher wui-card material-panel" data-lane="runtime">
            <div class="launcher-topbar">
              <div><small>{isZh() ? "产品入口" : "PRODUCT ENTRY"}</small><strong>{homeUi().launch}</strong></div>
              <span class="kawaii-bubble">{homeUi().cuteHint}</span>
            </div>
            <button type="button" class="wui-input-group launcher-search" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}>
              <span class="wui-input-group__prefix">⌕</span><span class="launcher-search-label">{homeUi().searchPlaceholder}</span><span class="wui-input-group__suffix">{homeUi().commandHint}</span>
            </button>
            <div class="launcher-grid">
              <a class="launcher-tile lane-project" href={studioUrl} target="_blank" rel="noreferrer"><span>✦</span><div><strong>Studio</strong><small>{isZh() ? "真正开始操作" : "Start operating"}</small></div><b>↗</b></a>
              <A class="launcher-tile lane-editorial" href="/product"><span>♡</span><div><strong>{homeUi().product}</strong><small>{isZh() ? "看它解决什么" : "See what it solves"}</small></div><b>→</b></A>
              <a class="launcher-tile lane-evidence" href={docsRoot()}><span>📚</span><div><strong>{homeUi().docs}</strong><small>{isZh() ? "搜索真实文档" : "Search real docs"}</small></div><b>→</b></a>
              <A class="launcher-tile lane-validated" href="/publication"><span>✧</span><div><strong>{homeUi().publication}</strong><small>{isZh() ? "从接受稿到派生格式" : "Accepted text to formats"}</small></div><b>→</b></A>
            </div>
            <div class="launcher-footer"><span>{productVersion}</span><span>{isZh() ? "1.0 预发布 · 验收中" : "1.0 preview · acceptance in progress"}</span><span>authority=false</span></div>
          </div>
        </div>

        <div class="page-width capability-ribbon" aria-label={homeUi().capabilityTitle}>
          <For each={c().proofs}>{(card, index) => (
            <button type="button" class="capability-chip" data-lane={capabilityLanes[index()] ?? "runtime"} data-active={activeCapability() === index()} onClick={() => setActiveCapability(index())}>
              <span>{capabilityIcons[index()] ?? "✦"}</span><div><small>{card.eyebrow}</small><strong>{card.title}</strong></div>
            </button>
          )}</For>
        </div>
      </section>

      <QuickDemo locale={locale()} />

      <section id="workflow" class="capability-focus page-width section-compact" data-home-section="workflow">
        <div class="section-kicker"><span>✦</span><div><small>{homeUi().capabilityTitle}</small><strong>{homeUi().capabilityLede}</strong></div></div>
        <div class="capability-focus-grid" data-lane={capabilityLanes[activeCapability()] ?? "runtime"}>
          <div class="capability-orb" aria-hidden="true"><span>{capabilityIcons[activeCapability()]}</span></div>
          <div><p class="eyebrow">{c().proofs[activeCapability()].eyebrow}</p><h2>{c().proofs[activeCapability()].title}</h2><p>{c().proofs[activeCapability()].body}</p><code>{c().proofs[activeCapability()].meta}</code></div>
          <div class="capability-actions"><A class="wui-button wui-button--soft" href="/product">{homeUi().product} →</A><a class="wui-button wui-button--ghost" href={docsRoot()}>{homeUi().docs} →</a></div>
        </div>
      </section>

      <section id="evidence" class="product-lab section-pad-soft" data-home-section="evidence">
        <div class="page-width">
          <div class="section-heading compact-heading"><p class="eyebrow">{homeUi().labEyebrow}</p><h2>{homeUi().labTitle}</h2></div>
          <div class="lab-grid">
            <article class="wui-card lab-card context-lab" data-lane="runtime">
              <div class="lab-card-header"><div><span class="lab-icon">🫧</span><small>{homeUi().contextNote}</small><h3>{homeUi().contextTitle}</h3></div><span class="wui-badge wui-badge--soft">{budget()}/5</span></div>
              <input class="budget-slider" type="range" min="1" max="5" step="1" value={budget()} onInput={(event) => setBudget(Number(event.currentTarget.value))} aria-label={homeUi().contextTitle} />
              <div class="evidence-stack"><For each={evidence()}>{(item, index) => <div class="evidence-row" data-loaded={index() < budget()}><span>{index() < budget() ? "✓" : "·"}</span><strong>{item}</strong><small>{index() < budget() ? (isZh() ? "进入上下文" : "loaded") : (isZh() ? "预算外" : "outside budget")}</small></div>}</For></div>
              <p class="lab-caption">{isZh() ? "“系统里有”不等于“这次模型看到了”。" : "Stored by the system does not mean loaded for this call."}</p>
            </article>

            <article class="wui-card lab-card readiness-lab" data-lane={readiness() ? "validated" : "editorial"}>
              <div class="lab-card-header"><div><span class="lab-icon">♡</span><small>{homeUi().gateNote}</small><h3>{homeUi().gateTitle}</h3></div><span class={`wui-badge ${readiness() ? "wui-badge--success" : "wui-badge--warning"}`}>{readiness() ? "PASS" : "PENDING"}</span></div>
              <div class="gate-buttons"><For each={gateNames()}>{(name, index) => <button type="button" class="gate-toggle" aria-pressed={gates()[index()]} onClick={() => setGates((current) => current.map((value, i) => i === index() ? !value : value))}><span>{gates()[index()] ? "✓" : "○"}</span><strong>{name}</strong><small>{gates()[index()] ? "PASS" : "PENDING"}</small></button>}</For></div>
              <div class="readiness-result" data-ready={readiness()}><span aria-hidden="true">{readiness() ? "✦" : "♡"}</span><strong>{readiness() ? homeUi().ready : homeUi().notReady}</strong><code>fp: exact-candidate</code></div>
            </article>
          </div>
        </div>
      </section>

      <section id="privacy" class="qf-home-privacy page-width section-compact" data-home-section="privacy">
        <div class="section-heading compact-heading"><p class="eyebrow">{isZh() ? "隐私与控制" : "PRIVACY & CONTROL"}</p><h2>{isZh() ? "本地默认，云端显式；密钥永远不是作品数据。" : "Local by default, cloud by choice; secrets are never story data."}</h2></div>
        <div class="portal-grid">
          <article class="portal-card studio-portal"><div class="portal-icon">⌁</div><div><small>LOCAL</small><h3>{isZh() ? "回环地址内运行" : "Loopback-only execution"}</h3><p>{isZh() ? "quillframe launch 只绑定本机；不需要账号，也不会自动上传 Project。" : "quillframe launch binds only to this machine, needs no account, and never uploads a Project implicitly."}</p></div><span>0 ↑</span></article>
          <article class="portal-card docs-portal"><div class="portal-icon">◇</div><div><small>CLOUD</small><h3>{isZh() ? "每次上传都要明确选择" : "Every upload is explicit"}</h3><p>{isZh() ? "SSO 只建立个人工作区会话；模型 token 使用短期加密 lease，不进入 Project bundle。" : "SSO establishes a personal-workspace session only; model tokens use short encrypted leases and never enter the Project bundle."}</p></div><span>opt-in</span></article>
        </div>
      </section>

      <section id="start" class="product-world page-width section-compact" data-home-section="start">
        <div class="section-heading compact-heading"><p class="eyebrow">{homeUi().productWorld}</p><h2>{isZh() ? "真正的产品入口，不是“继续阅读”。" : "Real product doors, not another ‘read more’."}</h2></div>
        <div class="portal-grid">
          <a class="portal-card studio-portal" href={studioUrl} target="_blank" rel="noreferrer"><div class="portal-icon">✦</div><div><small>{homeUi().hostedStudio}</small><h3>Quillframe Studio</h3><p>{homeUi().hostedNote}</p></div><span>↗</span></a>
          <a class="portal-card docs-portal" href={docsRoot()}><div class="portal-icon">📚</div><div><small>{homeUi().docs}</small><h3>{homeUi().knowledgeTitle}</h3><p>{homeUi().knowledgeLede}</p></div><span>→</span></a>
          <A class="portal-card architecture-portal" href="/architecture"><div class="portal-icon">⌘</div><div><small>{homeUi().architecture}</small><h3>{homeUi().architectureTitle}</h3><p>{copy().routes.architecture.lede}</p></div><span>→</span></A>
          <A class="portal-card publication-portal" href="/publication"><div class="portal-icon">✧</div><div><small>{homeUi().publication}</small><h3>{homeUi().publicationTitle}</h3><p>{copy().routes.publication.lede}</p></div><span>→</span></A>
        </div>
      </section>

      <section class="knowledge-preview section-pad-soft">
        <div class="page-width knowledge-preview-grid">
          <div class="knowledge-preview-copy"><span class="kawaii-sticker">📚✨</span><p class="eyebrow">{homeUi().docs}</p><h2>{homeUi().knowledgeTitle}</h2><p>{homeUi().knowledgeLede}</p><a class="wui-button wui-button--solid" href={docsRoot()}>{homeUi().openDocument} →</a></div>
          <div class="knowledge-preview-list wui-card">
            <div class="knowledge-preview-meta"><span>{knowledge()?.documentCount ?? "…"} docs</span><span>build-time · authority=false</span></div>
            <For each={tierADocs()}>{(doc) => <a class="knowledge-preview-row" href={docHref(doc.id)}><span class="wui-badge wui-badge--soft">Tier {doc.tier}</span><div><strong>{doc.title}</strong><small>{doc.excerpt}</small></div><span>→</span></a>}</For>
          </div>
        </div>
      </section>
    </>
  );
}

function ProductPage() {
  const route = () => siteCopy[locale()].routes.product;
  return <div class="page-width section-compact unified-route-page"><ProductSurfaceHero tone="project" eyebrow={<span>{route().eyebrow}</span>} title={route().title} lede={<p>{route().lede}</p>} visual={<div class="unified-stack-visual"><span>Canon</span><span>Context</span><span>Evidence</span><span>Candidate</span><span>Settlement</span></div>} /><div class="unified-card-grid"><For each={route().cards}>{(card, index) => <article class="wui-card unified-info-card"><small>0{index() + 1}</small><h3>{card.title}</h3><p>{card.body}</p></article>}</For></div></div>;
}

function StudioPage() {
  const route = () => siteCopy[locale()].routes.studio;
  return <div class="page-width section-compact unified-route-page"><ProductSurfaceHero tone="runtime" eyebrow={<span>{route().eyebrow}</span>} title={route().title} lede={<p>{route().lede}</p>} actions={<a class="wui-button wui-button--solid" href={studioUrl} target="_blank" rel="noreferrer">✦ {zh() ? "打开 Hosted Studio" : "Open Hosted Studio"}</a>} visual={<div class="unified-studio-terminal"><div><i /><i /><i /><strong>studio.quillframe.wei-dev.com</strong></div><pre>host: cloudflare{`\n`}core: unbound{`\n`}authority: false{`\n`}mode: read-only</pre></div>} /><div class="unified-card-grid"><For each={route().cards}>{(card) => <article class="wui-card unified-info-card"><small>{card.eyebrow}</small><h3>{card.title}</h3><p>{card.body}</p></article>}</For></div></div>;
}

type Lane = "project" | "runtime" | "evidence" | "editorial" | "validated";
const architectureNodes = [
  { id: "project", icon: "⌂", lane: "project" as Lane, title: "Project", zh: "Project", compactZh: "身份 · native manifest", compactEn: "identity · native manifest", descZh: "解析四键 quillframe.toml、scope=novel、.quillframe/data 与 manifest fingerprint。", descEn: "Resolve the four-key quillframe.toml, scope=novel, .quillframe/data, and manifest fingerprint.", input: ["quillframe.toml", "scope=novel", ".quillframe/data"], output: ["project identity", "context v1_0", "manifest_fingerprint"], authorityZh: "项目文件拥有权威；UI 只读，authority=false。", authorityEn: "Project files own authority; the UI is read-only with authority=false.", contracts: ["quillframe_project_v1_0", "quillframe_project_context_v1_0"] },
  { id: "manager", icon: "✦", lane: "runtime" as Lane, title: "Manager", zh: "Manager", compactZh: "Session · Run", compactEn: "session · run", descZh: "协调 Session / Run、checkpoint、routing 与 Control Plane lineage。", descEn: "Coordinate Session / Run identity, checkpoints, routing, and control-plane lineage.", input: ["resolved project", "task intent", "host capability"], output: ["run identity", "checkpoint boundary", "execution path"], authorityZh: "运行协调不等于 Canon authority。", authorityEn: "Operational coordination is not Canon authority.", contracts: ["quillframe_host_capabilities_v1"] },
  { id: "context", icon: "🫧", lane: "evidence" as Lane, title: "Context", zh: "Context", compactZh: "稀疏上下文", compactEn: "sparse context", descZh: "选择稀疏、带 authority 的工作集，并区分 support 与实际 loaded context。", descEn: "Select a sparse authority-aware working set and distinguish support from loaded context.", input: ["eligible sources", "visibility", "budget"], output: ["context view", "loaded support", "excluded evidence"], authorityZh: "Context selection 是工作证据，不会变成 Canon。", authorityEn: "Context selection is working evidence, not Canon.", contracts: ["quillframe_context_inspector_v2", "quillframe_run_receipt_v1"] },
  { id: "worker", icon: "⌘", lane: "editorial" as Lane, title: "Worker", zh: "Worker", compactZh: "typed semantic I/O", compactEn: "typed semantic I/O", descZh: "执行 typed semantic contract，并返回可检查的 result identity。", descEn: "Execute a typed semantic contract and return inspectable result identity.", input: ["typed task", "visible context", "contract"], output: ["typed result", "fingerprint", "worker status"], authorityZh: "Worker result 是 evidence，不授予写权限。", authorityEn: "Worker results are evidence and grant no write authority.", contracts: ["semantic contract catalog"] },
  { id: "gate", icon: "✓", lane: "validated" as Lane, title: "Gate", zh: "Gate", compactZh: "candidate 指纹校验", compactEn: "candidate fingerprint", descZh: "围绕同一个 exact candidate fingerprint 汇合必要证据。", descEn: "Conjoin required evidence around one exact candidate fingerprint.", input: ["candidate fingerprint", "deterministic checks", "semantic evidence"], output: ["gate status", "blocking evidence", "readiness"], authorityZh: "Production readiness 是 gate evidence，不是 Canon acceptance。", authorityEn: "Production readiness is gate evidence, not Canon acceptance.", contracts: ["quillframe_production_readiness_v1"] },
  { id: "settlement", icon: "◇", lane: "evidence" as Lane, title: "Settlement", zh: "Settlement", compactZh: "语义提交", compactEn: "semantic commit", descZh: "通过 Core-owned settlement semantics 应用 eligible accepted changes。", descEn: "Apply eligible accepted changes through Core-owned settlement semantics.", input: ["accepted decision", "state changes", "provenance"], output: ["settlement receipt", "committed transition"], authorityZh: "UI 不能制造 settlement authority。", authorityEn: "The UI cannot manufacture settlement authority.", contracts: ["Control Plane lineage"] },
  { id: "publication", icon: "📖", lane: "validated" as Lane, title: "Publication", zh: "Publication", compactZh: "文本物化", compactEn: "text materialization", descZh: "把 accepted manuscript 确定性编译成带 provenance 的派生出版物。", descEn: "Compile accepted manuscript text deterministically into derived publication artifacts.", input: ["accepted manuscript", "publication profile"], output: ["TXT", "Web", "Print", "EPUB 3.3"], authorityZh: "Publication artifact 是 derived，authority=false。", authorityEn: "Publication artifacts are derived and authority=false.", contracts: ["quillframe_publication_ir_v1", "publication/compiler.py"] },
];

function ArchitecturePage() {
  const { zh } = useUi();
  const [selected, setSelected] = createSignal(0);
  const [runStep, setRunStep] = createSignal(-1);
  const current = createMemo(() => architectureNodes[selected()]);
  const runState = (index: number) => runStep() < 0 ? "idle" : index < runStep() ? "complete" : index === runStep() ? "current" : "pending";
  const next = () => {
    const value = runStep() < 0 ? 0 : Math.min(architectureNodes.length - 1, runStep() + 1);
    setRunStep(value);
    setSelected(value);
  };
  return <div class="page-width section-compact unified-route-page architecture-entry">
    <ProductSurfaceHero
      class="architecture-intro"
      tone="project"
      eyebrow={<span>INTERACTIVE ARCHITECTURE</span>}
      badges={<span class="wui-badge wui-badge--outline">authority=false</span>}
      title={zh() ? "看一条 Quillframe 运行，怎样穿过整个系统。" : "See how one Quillframe run moves through the system."}
      lede={<p>{zh() ? "Project → Manager → Context → Worker → Gate → Settlement → Publication。共享的是同一个产品壳；每个节点只拥有自己的机制边界。" : "Project → Manager → Context → Worker → Gate → Settlement → Publication. One product shell, with each node owning only its mechanism boundary."}</p>}
      actions={<><a class="wui-button wui-button--soft" href={zh() ? "/docs/architecture" : "/docs/en/architecture"}>📚 {zh() ? "阅读架构文档" : "Read architecture docs"}</a><A class="wui-button wui-button--ghost" href="/playground">▷ Playground</A></>}
      visual={<div class="architecture-hero-path">{architectureNodes.map((node, index) => <><button type="button" data-active={selected() === index} onClick={() => setSelected(index)}><span>{node.icon}</span><strong>{node.title}</strong></button>{index < architectureNodes.length - 1 ? <i>→</i> : null}</>)}</div>}
    />
    <section class="wui-card architecture-canvas">
      <div class="architecture-toolbar"><div><small>{zh() ? "可观察执行路径" : "OBSERVABLE EXECUTION PATH"}</small><strong>{runStep() < 0 ? (zh() ? "选择节点，或开始模拟" : "Select a node or start a preview") : `${runStep() + 1} / ${architectureNodes.length} · ${architectureNodes[runStep()].title}`}</strong></div><div class="architecture-run-actions"><button class="wui-button wui-button--solid" type="button" disabled={runStep() === architectureNodes.length - 1} onClick={next}>{runStep() < 0 ? (zh() ? "模拟一次 run" : "Simulate a run") : (zh() ? "下一步" : "Next step")}</button><button class="wui-button wui-button--ghost" type="button" disabled={runStep() < 0} onClick={() => setRunStep(-1)}>{zh() ? "重置" : "Reset"}</button></div></div>
      <div class="architecture-flow"><For each={architectureNodes}>{(node, index) => <button type="button" class="architecture-node" data-lane={node.lane} data-active={selected() === index()} data-run-state={runState(index())} onClick={() => setSelected(index())}><span class="architecture-node-step">{String(index() + 1).padStart(2, "0")}</span><span class="architecture-node-icon">{node.icon}</span><span class="architecture-node-copy"><strong>{node.title}</strong><small>{zh() ? node.compactZh : node.compactEn}</small></span><span class="architecture-node-status">{runState(index()) === "complete" ? "✓" : runState(index()) === "current" ? "●" : "→"}</span></button>}</For></div>
    </section>
    <section class="architecture-inspector-grid">
      <article class="wui-card architecture-detail" data-lane={current().lane}><header class="architecture-detail-head"><div class="architecture-detail-icon">{current().icon}</div><div><small>{zh() ? "当前节点" : "SELECTED NODE"}</small><h2>{current().title}</h2><p>{zh() ? current().descZh : current().descEn}</p></div></header><div class="architecture-detail-grid"><section><span>{zh() ? "输入" : "Inputs"}</span><ul><For each={current().input}>{(item) => <li>{item}</li>}</For></ul></section><section><span>{zh() ? "输出" : "Outputs"}</span><ul><For each={current().output}>{(item) => <li>{item}</li>}</For></ul></section><section class="architecture-authority"><span>Authority</span><p>{zh() ? current().authorityZh : current().authorityEn}</p></section><section><span>Contracts</span><div class="architecture-contracts"><For each={current().contracts}>{(item) => <code>{item}</code>}</For></div></section></div></article>
      <aside class="wui-card architecture-run-evidence"><div class="architecture-run-head"><div><small>{zh() ? "模拟 trace" : "PREVIEW TRACE"}</small><h2>{zh() ? "只展示公开可观察边界" : "Public observable boundaries only"}</h2></div><span class="wui-badge wui-badge--outline">deterministic</span></div><p>{zh() ? "这里不是一次真实 Core execution，不调用模型、不写 Canon。" : "This is not a real Core execution. It makes no model call and writes no Canon."}</p><ol class="architecture-trace-list"><For each={architectureNodes}>{(node, index) => <li data-state={runState(index())}><span>{runState(index()) === "complete" ? "✓" : runState(index()) === "current" ? "●" : String(index() + 1).padStart(2, "0")}</span><div><strong>{node.title}</strong><small>{runState(index()) === "current" ? (zh() ? "当前边界" : "current") : runState(index()) === "complete" ? (zh() ? "已通过" : "passed") : (zh() ? "等待" : "pending")}</small></div></li>}</For></ol></aside>
    </section>
  </div>;
}

function PublicationPage() {
  const { locale } = useUi();
  return <PublicationWorkbench locale={locale()} />;
}

function InspectorPage() {
  const { locale, zh } = useUi();
  return <div class="page-width section-compact unified-route-page inspector-entry"><ProductSurfaceHero tone="project" eyebrow={<span>PROJECT INSPECTOR</span>} title={zh() ? "先确认项目是谁，再让任何工具碰它。" : "Resolve the project before any tool touches it."} lede={<p>{zh() ? "本地检查四键 manifest、context v1_0、scope=novel、manifest fingerprint 与 .quillframe/data。文件不会上传，旧 metadata 只会被拒绝。" : "Inspect the four-key manifest, context v1_0, scope=novel, manifest fingerprint, and .quillframe/data locally. Files are not uploaded; legacy metadata is rejected."}</p>} visual={<div class="unified-inspector-visual"><span>quillframe.toml</span><span>context v1_0</span><span>scope=novel · .quillframe/data</span><strong>✓ local only · authority=false</strong></div>} /><ProjectInspector locale={locale()} /></div>;
}

function PlaygroundPage() {
  const { locale, zh } = useUi();
  return <div class="page-width section-compact unified-route-page playground-entry"><ProductSurfaceHero tone="evidence" eyebrow={<span>LOCAL PLAYGROUND</span>} title={zh() ? "把执行路径变成可以玩的确定性预览。" : "Make the execution path a deterministic thing you can play with."} lede={<p>{zh() ? "输入工作文本、选择 task mode，然后查看一个浏览器本地 trace。不调用模型，不写 Project state。" : "Paste working text, choose a task mode, and inspect a browser-local trace. No model call and no Project-state write."}</p>} visual={<div class="unified-playground-visual"><span>DRAFT</span><i>→</i><span>Context</span><i>→</i><span>Evidence</span><i>→</i><strong>Result</strong></div>} /><LocalPlayground locale={locale()} /></div>;
}

const agentHosts = ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"];
function AgentsPage() {
  const { zh } = useUi();
  const [selected, setSelected] = createSignal(1);
  return <div class="page-width section-compact unified-route-page agent-integration-entry"><ProductSurfaceHero tone="runtime" eyebrow={<span>AGENT SKILL · HOST BRIDGE V11</span>} badges={<span class="wui-badge wui-badge--outline">authority=false</span>} title={zh() ? "让你的 Agent 接入 Quillframe，而不是绕过 Quillframe。" : "Let your agent use Quillframe without bypassing Quillframe."} lede={<p>{zh() ? "portable Agent Skill 通过公开 Host Bridge 发现能力、检查 Project / Context / semantic contracts，并把写权限明确留在 Core。" : "The portable Agent Skill uses the public Host Bridge to discover capabilities and inspect Project, Context, and semantic contracts while writes remain Core-owned."}</p>} visual={<div class="unified-agent-hosts"><For each={agentHosts}>{(host, index) => <button type="button" data-active={selected() === index()} onClick={() => setSelected(index())}><span>{host.slice(0, 1)}</span><strong>{host}</strong></button>}</For></div>} /><section class="agent-host-workbench"><ProductSectionHeading eyebrow={zh() ? "宿主 recipe" : "HOST RECIPE"} title={zh() ? `${agentHosts[selected()]} 使用同一条公开边界。` : `${agentHosts[selected()]} uses the same public boundary.`} /><div class="agent-host-detail"><article class="agent-host-profile"><div class="agent-host-profile-badges"><span class="wui-badge wui-badge--soft">{agentHosts[selected()]}</span><span class="wui-badge wui-badge--outline">generic read-only bridge</span></div><h3>{zh() ? "能力匹配，不制造新的权威层。" : "Match capabilities without inventing another authority layer."}</h3><ul class="agent-host-facts"><li><span>{zh() ? "入口" : "Entry"}</span><strong>agent-skills/quillframe/SKILL.md</strong></li><li><span>{zh() ? "发现" : "Discovery"}</span><strong>bridge.describe</strong></li><li><span>{zh() ? "写权限" : "Write authority"}</span><strong>0 · authority=false</strong></li></ul></article><article class="agent-host-instruction"><div class="agent-host-instruction-head"><div><small>HOST INSTRUCTION</small><strong>{zh() ? "最小安全边界" : "Minimal safe boundary"}</strong></div></div><pre><code>{`1. Read agent-skills/quillframe/SKILL.md\n2. Run bridge self-test\n3. Run bridge.describe\n4. Invoke advertised operations only\n5. authority: false\n6. Never read private runtime stores directly`}</code></pre></article></div></section></div>;
}

function ChangelogPage() {
  const route = () => siteCopy[locale()].routes.changelog;
  return <div class="page-width section-compact unified-route-page"><ProductSurfaceHero tone="validated" eyebrow={<span>{route().eyebrow}</span>} title={route().title} lede={<p>{route().lede}</p>} visual={<div class="unified-release-badge"><strong>{productVersion}</strong><span>{zh() ? "current main" : "current main"}</span></div>} /><div class="unified-card-grid"><For each={route().cards}>{(card, index) => <article class="wui-card unified-info-card"><small>0{index() + 1}</small><h3>{card.title}</h3><p>{card.body}</p></article>}</For></div></div>;
}

export default function ProductApp() {
  return <Router root={ProductShell}>
    <Route path="/" component={HomePage} />
    <Route path="/product" component={ProductPage} />
    <Route path="/studio" component={StudioPage} />
    <Route path="/architecture" component={ArchitecturePage} />
    <Route path="/publication" component={PublicationPage} />
    <Route path="/inspect" component={InspectorPage} />
    <Route path="/playground" component={PlaygroundPage} />
    <Route path="/agents" component={AgentsPage} />
    <Route path="/changelog" component={ChangelogPage} />
  </Router>;
}

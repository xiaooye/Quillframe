import { A, Navigate, Route, Router, useLocation, useNavigate } from "@solidjs/router";
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
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import { type Locale } from "./content";
import { enUS } from "./content.en-US";
import { zhCN } from "./content.zh-CN";
import { loadKnowledgeIndex, searchKnowledge } from "./knowledge";
import ProjectInspector from "./ProjectInspector";
import LocalPlayground from "./LocalPlayground";
import { ProductSectionHeading, ProductSurfaceHero } from "./ProductSurface";

const siteCopy = { "en-US": enUS, "zh-CN": zhCN } as const;
const studioUrl = "https://studio.novelforge.wei-dev.com";

type UiContextValue = {
  locale: Accessor<Locale>;
  dark: Accessor<boolean>;
  zh: Accessor<boolean>;
  toggleLocale: () => void;
  toggleDark: () => void;
};

const UiContext = createContext<UiContextValue>();

function initialLocale(): Locale {
  const saved = localStorage.getItem("novelforge.locale");
  if (saved === "zh-CN" || saved === "en-US") return saved;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function initialDark() {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

const [locale, setLocale] = createSignal<Locale>(initialLocale());
const [dark, setDark] = createSignal(initialDark());
const copy = () => siteCopy[locale()];
const zh = () => locale() === "zh-CN";

function useUi() {
  const value = useContext(UiContext);
  if (!value) throw new Error("Product UI context is missing");
  return value;
}

function syncDocumentState() {
  document.documentElement.lang = zh() ? "zh-CN" : "en";
  document.documentElement.dataset.locale = locale();
  document.documentElement.classList.toggle("dark", dark());
  localStorage.setItem("novelforge.locale", locale());
  localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
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

  const toggleLocale = () => setLocale((value) => value === "zh-CN" ? "en-US" : "zh-CN");
  const toggleDark = () => setDark((value) => !value);

  createEffect(syncDocumentState);
  createEffect(() => {
    location.pathname;
    setMenuOpen(false);
  });

  const nav = () => [
    ["/product", copy().nav.product],
    ["/studio", copy().nav.studio],
    ["/architecture", copy().nav.architecture],
    ["/publication", copy().nav.publication],
  ] as const;

  const routeResults = createMemo<CommandResult[]>(() => [
    { kind: "route", icon: "⌂", label: zh() ? "首页" : "Home", description: copy().home.lede, href: "/" },
    { kind: "route", icon: "♡", label: copy().nav.product, description: copy().routes.product.lede, href: "/product" },
    { kind: "route", icon: "⌘", label: copy().nav.architecture, description: copy().routes.architecture.lede, href: "/architecture" },
    { kind: "route", icon: "✧", label: copy().nav.publication, description: copy().routes.publication.lede, href: "/publication" },
    { kind: "route", icon: "▣", label: zh() ? "检查项目" : "Inspect project", description: zh() ? "在浏览器本地检查 Project manifest、lock 与 attestation。" : "Inspect Project manifest, lock, and attestation locally in the browser.", href: "/inspect" },
    { kind: "route", icon: "▷", label: "Playground", description: zh() ? "本地确定性 execution trace。" : "Local deterministic execution trace.", href: "/playground" },
    { kind: "route", icon: "◈", label: zh() ? "Agent 集成" : "Agent integration", description: zh() ? "通过 portable skill 与 Host Bridge 接入 coding agent。" : "Connect coding agents through the portable skill and Host Bridge.", href: "/agents" },
    { kind: "external", icon: "✦", label: zh() ? "打开 Studio" : "Open Studio", description: zh() ? "打开 Hosted Studio。" : "Open the hosted Studio.", href: studioUrl },
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

  const openCommand = () => {
    if (!commandDialog?.open) commandDialog?.showModal();
    setHighlighted(0);
    queueMicrotask(() => commandInput?.focus());
  };
  const closeCommand = () => commandDialog?.open && commandDialog.close();
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
          <A href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
            <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
            <span>NovelForge</span>
            <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
          </A>
          <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "主导航" : "Primary navigation"}>
            <For each={nav()}>{([href, label]) => <A href={href} class="wui-app-bar__link" activeClass="active">{label}</A>}</For>
            <a class="wui-app-bar__link" href={zh() ? "/docs" : "/docs/en"}>{copy().nav.docs}</a>
          </nav>
          <div class="wui-app-bar__actions header-actions">
            <button type="button" class="wui-button wui-button--soft header-search" onClick={openCommand}><span>⌕</span><span>{zh() ? "搜索 NovelForge" : "Search NovelForge"}</span><kbd>⌘K / Ctrl+K</kbd></button>
            <a class="wui-button wui-button--solid studio-cta" href={studioUrl} target="_blank" rel="noreferrer">✦ {zh() ? "打开 Studio" : "Open Studio"}</a>
            <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={toggleLocale} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{copy().languageName}</button>
            <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={toggleDark} aria-label={copy().nav.appearance}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
            <button class="wui-button wui-button--ghost wui-button--icon-only mobile-menu-button" type="button" aria-expanded={menuOpen()} onClick={() => setMenuOpen((value) => !value)}><span aria-hidden="true">{menuOpen() ? "×" : "≡"}</span></button>
          </div>
        </header>

        <Show when={menuOpen()}>
          <nav class="mobile-nav wui-card" aria-label={zh() ? "移动端导航" : "Mobile navigation"}>
            <For each={nav()}>{([href, label]) => <A href={href} class="wui-sidebar__item" activeClass="active">{label}</A>}</For>
            <a class="wui-sidebar__item" href={zh() ? "/docs" : "/docs/en"}>📚 {copy().nav.docs}</a>
            <A class="wui-sidebar__item" href="/inspect">▣ {zh() ? "检查项目" : "Inspect project"}</A>
            <A class="wui-sidebar__item" href="/playground">▷ Playground</A>
            <A class="wui-sidebar__item" href="/agents">◈ {zh() ? "Agent 集成" : "Agent integration"}</A>
          </nav>
        </Show>

        <main id="main-content">{props.children}</main>

        <footer class="site-footer unified-product-footer">
          <div class="page-width footer-grid">
            <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{zh() ? "一个产品壳，共享同一套导航、主题与语言状态。" : "One product shell, one navigation, theme, and locale state."}</p></div>
            <div class="footer-links"><A href="/product">{copy().nav.product}</A><A href="/architecture">{copy().nav.architecture}</A><A href="/publication">{copy().nav.publication}</A><a href={zh() ? "/docs" : "/docs/en"}>{copy().nav.docs}</a></div>
            <div class="footer-links"><A href="/inspect">{zh() ? "检查项目" : "Inspect"}</A><A href="/playground">Playground</A><A href="/agents">{zh() ? "Agent 集成" : "Agents"}</A><a href={studioUrl} target="_blank" rel="noreferrer">Studio ↗</a></div>
          </div>
        </footer>

        <dialog ref={commandDialog} class="command-dialog" onClose={() => setQuery("")} onClick={(event) => { if (event.target === commandDialog) closeCommand(); }}>
          <div class="wui-command command-surface">
            <div class="command-cute-strip"><span>✦</span><strong>{zh() ? "搜索 NovelForge" : "Search NovelForge"}</strong><span>{zh() ? "今天也把故事织得漂亮一点吧" : "Weave something lovely today"}</span></div>
            <div class="wui-command__input-wrapper"><span class="wui-command__icon">⌕</span><input ref={commandInput} class="wui-command__input" value={query()} onInput={(event) => { setQuery(event.currentTarget.value); setHighlighted(0); }} onKeyDown={handleCommandKey} placeholder={zh() ? "搜索产品、文档、架构、出版…" : "Search product, docs, architecture, publication…"} /><kbd>Esc</kbd></div>
            <div class="wui-command__list" role="listbox"><For each={commandResults()}>{(result, index) => <button type="button" class="wui-command__item command-result" data-highlighted={highlighted() === index()} role="option" aria-selected={highlighted() === index()} onMouseEnter={() => setHighlighted(index())} onClick={() => runResult(result)}><span class="command-result-icon">{result.icon}</span><span class="command-result-copy"><strong>{result.label}</strong><small>{result.description}</small></span><span>→</span></button>}</For></div>
          </div>
        </dialog>
      </div>
    </UiContext.Provider>
  );
}

function HomePage() {
  const { zh } = useUi();
  const capabilities = () => siteCopy[locale()].home.proofs;
  return (
    <div class="unified-home page-width section-compact">
      <ProductSurfaceHero
        class="unified-home-hero"
        tone="editorial"
        eyebrow={<span>{siteCopy[locale()].home.eyebrow}</span>}
        badges={<><span class="wui-badge wui-badge--soft">local-first</span><span class="wui-badge wui-badge--outline">authority-aware</span></>}
        title={siteCopy[locale()].home.title}
        lede={<p>{siteCopy[locale()].home.lede}</p>}
        actions={<><A class="wui-button wui-button--solid wui-button--xl" href="/product">✦ {siteCopy[locale()].home.primaryCta}</A><A class="wui-button wui-button--soft wui-button--xl" href="/architecture">⌘ {siteCopy[locale()].home.secondaryCta}</A></>}
        visual={<div class="unified-home-loom" aria-hidden="true"><div class="loom-cloud">☁</div><div class="loom-thread">Project · · Context · · Worker · · Gate · · Publication</div><div class="loom-book"><span>PROJECT</span><strong>NovelForge</strong><small>Canon · Context · Evidence · Publication</small><b>♡</b></div></div>}
      />
      <section class="unified-proof-section">
        <ProductSectionHeading eyebrow={siteCopy[locale()].home.proofLabel} title={zh() ? "真实能力，不靠同一张万能卡片解释。" : "Real capabilities, not one generic card repeated everywhere."} />
        <div class="unified-card-grid"><For each={capabilities()}>{(item) => <article class="wui-card unified-info-card"><small>{item.eyebrow}</small><h3>{item.title}</h3><p>{item.body}</p><code>{item.meta}</code></article>}</For></div>
      </section>
    </div>
  );
}

function ProductPage() {
  const route = () => siteCopy[locale()].routes.product;
  return <div class="page-width section-compact unified-route-page"><ProductSurfaceHero tone="project" eyebrow={<span>{route().eyebrow}</span>} title={route().title} lede={<p>{route().lede}</p>} visual={<div class="unified-stack-visual"><span>Canon</span><span>Context</span><span>Evidence</span><span>Candidate</span><span>Settlement</span></div>} /><div class="unified-card-grid"><For each={route().cards}>{(card, index) => <article class="wui-card unified-info-card"><small>0{index() + 1}</small><h3>{card.title}</h3><p>{card.body}</p></article>}</For></div></div>;
}

function StudioPage() {
  const route = () => siteCopy[locale()].routes.studio;
  return <div class="page-width section-compact unified-route-page"><ProductSurfaceHero tone="runtime" eyebrow={<span>{route().eyebrow}</span>} title={route().title} lede={<p>{route().lede}</p>} actions={<a class="wui-button wui-button--solid" href={studioUrl} target="_blank" rel="noreferrer">✦ {zh() ? "打开 Hosted Studio" : "Open Hosted Studio"}</a>} visual={<div class="unified-studio-terminal"><div><i /><i /><i /><strong>studio.novelforge.wei-dev.com</strong></div><pre>host: cloudflare{`\n`}core: unbound{`\n`}authority: false{`\n`}mode: read-only</pre></div>} /><div class="unified-card-grid"><For each={route().cards}>{(card) => <article class="wui-card unified-info-card"><small>{card.eyebrow}</small><h3>{card.title}</h3><p>{card.body}</p></article>}</For></div></div>;
}

type Lane = "project" | "runtime" | "evidence" | "editorial" | "validated";
const architectureNodes = [
  { id: "project", icon: "⌂", lane: "project" as Lane, title: "Project", zh: "Project", compactZh: "身份 · Framework lock", compactEn: "identity · framework lock", descZh: "解析项目身份、精确 Framework lock、attestation 与项目逻辑域。", descEn: "Resolve project identity, exact Framework lock, attestation, and logical domains.", input: ["novelforge.toml", "novelforge.lock.json", "framework.attestation.json"], output: ["project identity", "Framework identity", "adapter resolution"], authorityZh: "项目文件拥有权威；UI 只读。", authorityEn: "Project files own authority; the UI is read-only.", contracts: ["novelforge_project_adapter_resolution_v1"] },
  { id: "manager", icon: "✦", lane: "runtime" as Lane, title: "Manager", zh: "Manager", compactZh: "Session · Run", compactEn: "session · run", descZh: "协调 Session / Run、checkpoint、routing 与 Control Plane lineage。", descEn: "Coordinate Session / Run identity, checkpoints, routing, and control-plane lineage.", input: ["resolved project", "task intent", "host capability"], output: ["run identity", "checkpoint boundary", "execution path"], authorityZh: "运行协调不等于 Canon authority。", authorityEn: "Operational coordination is not Canon authority.", contracts: ["novelforge_host_capabilities_v1"] },
  { id: "context", icon: "🫧", lane: "evidence" as Lane, title: "Context", zh: "Context", compactZh: "稀疏上下文", compactEn: "sparse context", descZh: "选择稀疏、带 authority 的工作集，并区分 support 与实际 loaded context。", descEn: "Select a sparse authority-aware working set and distinguish support from loaded context.", input: ["eligible sources", "visibility", "budget"], output: ["context view", "loaded support", "excluded evidence"], authorityZh: "Context selection 是工作证据，不会变成 Canon。", authorityEn: "Context selection is working evidence, not Canon.", contracts: ["novelforge_context_inspector_v2", "novelforge_run_receipt_v1"] },
  { id: "worker", icon: "⌘", lane: "editorial" as Lane, title: "Worker", zh: "Worker", compactZh: "typed semantic I/O", compactEn: "typed semantic I/O", descZh: "执行 typed semantic contract，并返回可检查的 result identity。", descEn: "Execute a typed semantic contract and return inspectable result identity.", input: ["typed task", "visible context", "contract"], output: ["typed result", "fingerprint", "worker status"], authorityZh: "Worker result 是 evidence，不授予写权限。", authorityEn: "Worker results are evidence and grant no write authority.", contracts: ["semantic contract catalog"] },
  { id: "gate", icon: "✓", lane: "validated" as Lane, title: "Gate", zh: "Gate", compactZh: "candidate 指纹校验", compactEn: "candidate fingerprint", descZh: "围绕同一个 exact candidate fingerprint 汇合必要证据。", descEn: "Conjoin required evidence around one exact candidate fingerprint.", input: ["candidate fingerprint", "deterministic checks", "semantic evidence"], output: ["gate status", "blocking evidence", "readiness"], authorityZh: "Production readiness 是 gate evidence，不是 Canon acceptance。", authorityEn: "Production readiness is gate evidence, not Canon acceptance.", contracts: ["novelforge_production_readiness_v1"] },
  { id: "settlement", icon: "◇", lane: "evidence" as Lane, title: "Settlement", zh: "Settlement", compactZh: "语义提交", compactEn: "semantic commit", descZh: "通过 Core-owned settlement semantics 应用 eligible accepted changes。", descEn: "Apply eligible accepted changes through Core-owned settlement semantics.", input: ["accepted decision", "state changes", "provenance"], output: ["settlement receipt", "committed transition"], authorityZh: "UI 不能制造 settlement authority。", authorityEn: "The UI cannot manufacture settlement authority.", contracts: ["Control Plane lineage"] },
  { id: "publication", icon: "📖", lane: "validated" as Lane, title: "Publication", zh: "Publication", compactZh: "文本物化", compactEn: "text materialization", descZh: "把 accepted manuscript 确定性编译成带 provenance 的派生出版物。", descEn: "Compile accepted manuscript text deterministically into derived publication artifacts.", input: ["accepted manuscript", "publication profile"], output: ["TXT", "Web", "Print", "EPUB 3.3"], authorityZh: "Publication artifact 是 derived，authority=false。", authorityEn: "Publication artifacts are derived and authority=false.", contracts: ["novelforge_publication_ir_v1", "publication/compiler.py"] },
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
      title={zh() ? "看一条 NovelForge 运行，怎样穿过整个系统。" : "See how one NovelForge run moves through the system."}
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

type PublicationProfile = { id: "text" | "web" | "print" | "epub"; icon: string; labelZh: string; labelEn: string; artifact: string; titleZh: string; titleEn: string };
const publicationProfiles: PublicationProfile[] = [
  { id: "text", icon: "TXT", labelZh: "纯文本", labelEn: "Clean text", artifact: ".txt", titleZh: "只保留正文，不叠加表现层", titleEn: "Exact text, no presentation layer" },
  { id: "web", icon: "WEB", labelZh: "网页", labelEn: "Web", artifact: ".html + .css", titleZh: "适配屏幕的阅读表面", titleEn: "Responsive reading surface" },
  { id: "print", icon: "PRINT", labelZh: "印刷版", labelEn: "Print", artifact: "print HTML/CSS", titleZh: "面向纸面的分页排版", titleEn: "Paged-media composition" },
  { id: "epub", icon: "EPUB", labelZh: "EPUB", labelEn: "EPUB", artifact: ".epub", titleZh: "可重排的电子书包", titleEn: "Reflowable ebook package" },
];

function PublicationSnapshot(props: { profile: PublicationProfile; active: boolean; onClick: () => void }) {
  const { zh } = useUi();
  return <button type="button" class={`unified-publication-snapshot snapshot-${props.profile.id}`} data-active={props.active} onClick={props.onClick}><span class="snapshot-label">{props.profile.icon}</span><div class="snapshot-mini-page"><strong>{zh() ? "第一章 · 夜幕与灯火" : "Chapter 1 · Nightfall and lights"}</strong><i /><i /><i /><i /></div><small>{zh() ? props.profile.labelZh : props.profile.labelEn}</small></button>;
}

function PublicationPage() {
  const { zh } = useUi();
  const [selected, setSelected] = createSignal(3);
  const current = createMemo(() => publicationProfiles[selected()]);
  return <div class="page-width section-compact unified-route-page publication-workbench-entry">
    <ProductSurfaceHero
      class="kawaii-publication-hero"
      tone="publication"
      eyebrow={<span>🎀 {zh() ? "出版工作台" : "PUBLICATION WORKBENCH"}</span>}
      badges={<><span class="wui-badge wui-badge--outline">deterministic</span><span class="wui-badge wui-badge--outline">authority=false</span></>}
      title={zh() ? <>同一份接受稿，生成多种<span>确定性派生格式。</span></> : <>One accepted manuscript, <span>many deterministic derivatives.</span></>}
      lede={<p>{zh() ? "基于唯一 Publication IR，从一次构建生成 TXT、Web、Print、EPUB。版式可以不同，正文事实始终只有一份。" : "One Publication IR produces TXT, Web, Print, and EPUB. Presentation changes; manuscript truth does not."}</p>}
      visual={<div class="unified-publication-gallery"><For each={publicationProfiles}>{(profile, index) => <PublicationSnapshot profile={profile} active={selected() === index()} onClick={() => setSelected(index())} />}</For></div>}
    />
    <section class="publication-profile-rail"><div class="publication-rail-title"><span>🛠</span><div><strong>{zh() ? "出版工作台" : "Publication workbench"}</strong><small>{zh() ? "选择目标格式并查看预览、配置与 provenance。" : "Choose a format and inspect preview, configuration, and provenance."}</small></div></div><For each={publicationProfiles}>{(profile, index) => <button type="button" class="publication-profile-card" data-active={selected() === index()} data-profile={profile.id} onClick={() => setSelected(index())}><span class="publication-profile-icon">{profile.icon}</span><span class="publication-profile-copy"><small>{zh() ? profile.labelZh : profile.labelEn}</small><strong>{zh() ? profile.titleZh : profile.titleEn}</strong><span>{profile.artifact}</span></span><span class="publication-profile-arrow">{selected() === index() ? "✓" : "→"}</span></button>}</For></section>
    <section class="publication-workbench-grid"><article class="wui-card publication-preview-card" data-profile={current().id}><div class="publication-preview-toolbar"><div><small>{zh() ? "阅读预览" : "READING PREVIEW"}</small><strong>{zh() ? current().labelZh : current().labelEn}</strong></div><div class="publication-preview-state"><span class="wui-badge wui-badge--success">exact text</span><span class="wui-badge wui-badge--outline">preview only</span></div></div><div class="unified-large-publication-preview" data-profile={current().id}><span class="preview-device-label">{current().icon}</span><article><small>NovelForge · {current().icon}</small><h2>{zh() ? "第一章 · 夜幕与灯火" : "Chapter 1 · Nightfall and lights"}</h2><p>{zh() ? "夜幕降临，城市的灯光一盏盏亮起，像星星坠落在河面上。" : "Night fell and city lights came on one by one, like stars settling on the river."}</p><p>{zh() ? "他站在桥边，手里握着一封信，风从河面吹来。" : "He stood by the bridge holding a letter while wind moved across the river."}</p></article></div></article><aside class="publication-inspector"><section class="wui-card publication-profile-inspector"><div class="publication-inspector-head"><span class="publication-inspector-icon">{current().icon}</span><div><small>{zh() ? "格式配置与元数据" : "PROFILE & METADATA"}</small><h2>{zh() ? current().titleZh : current().titleEn}</h2></div></div><div class="publication-token-grid"><div><span>artifact</span><strong>{current().artifact}</strong></div><div><span>source</span><strong>sha256 · exact</strong></div><div><span>authority</span><strong>false</strong></div><div><span>render</span><strong>deterministic</strong></div></div></section></aside></section>
    <section class="wui-card publication-provenance"><div class="publication-provenance-head"><div><small>PROVENANCE</small><h2>{zh() ? "每个派生物都能回到同一份接受正文。" : "Every derivative resolves back to the same accepted manuscript."}</h2></div></div><div class="publication-pipeline"><div class="publication-pipeline-node" data-kind="source"><span>✓</span><div><small>ACCEPTED</small><strong>Accepted manuscript</strong><code>sha256 · exact</code></div></div><span class="publication-pipeline-arrow">→</span><div class="publication-pipeline-node" data-kind="ir"><span>IR</span><div><small>PUBLICATION IR</small><strong>novelforge_publication_ir_v1</strong><code>schema-bound</code></div></div><span class="publication-pipeline-arrow">→</span><div class="publication-pipeline-node" data-kind="renderer"><span>⌘</span><div><small>COMPILER</small><strong>publication/compiler.py</strong><code>deterministic</code></div></div><span class="publication-pipeline-arrow">→</span><div class="publication-pipeline-node" data-kind="artifact"><span>{current().icon}</span><div><small>ARTIFACT</small><strong>{current().artifact}</strong><code>authority=false</code></div></div></div></section>
  </div>;
}

function InspectorPage() {
  const { locale, zh } = useUi();
  return <div class="page-width section-compact unified-route-page inspector-entry"><ProductSurfaceHero tone="project" eyebrow={<span>PROJECT INSPECTOR</span>} title={zh() ? "先确认项目是谁，再让任何工具碰它。" : "Resolve the project before any tool touches it."} lede={<p>{zh() ? "本地检查 manifest、精确 Framework lock、attestation 与结构证据。文件不会上传，检查结果也不会产生新的 Project authority。" : "Inspect the manifest, exact Framework lock, attestation, and structural evidence locally. Files are not uploaded and inspection grants no new Project authority."}</p>} visual={<div class="unified-inspector-visual"><span>novelforge.toml</span><span>novelforge.lock.json</span><span>framework.attestation.json</span><strong>✓ local only</strong></div>} /><ProjectInspector locale={locale()} /></div>;
}

function PlaygroundPage() {
  const { locale, zh } = useUi();
  return <div class="page-width section-compact unified-route-page playground-entry"><ProductSurfaceHero tone="evidence" eyebrow={<span>LOCAL PLAYGROUND</span>} title={zh() ? "把执行路径变成可以玩的确定性预览。" : "Make the execution path a deterministic thing you can play with."} lede={<p>{zh() ? "输入工作文本、选择 task mode，然后查看一个浏览器本地 trace。不调用模型，不写 Project state。" : "Paste working text, choose a task mode, and inspect a browser-local trace. No model call and no Project-state write."}</p>} visual={<div class="unified-playground-visual"><span>DRAFT</span><i>→</i><span>Context</span><i>→</i><span>Evidence</span><i>→</i><strong>Result</strong></div>} /><LocalPlayground locale={locale()} /></div>;
}

const agentHosts = ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"];
function AgentsPage() {
  const { zh } = useUi();
  const [selected, setSelected] = createSignal(1);
  return <div class="page-width section-compact unified-route-page agent-integration-entry"><ProductSurfaceHero tone="runtime" eyebrow={<span>AGENT SKILL · HOST BRIDGE V1</span>} badges={<span class="wui-badge wui-badge--outline">authority=false</span>} title={zh() ? "让你的 Agent 接入 NovelForge，而不是绕过 NovelForge。" : "Let your agent use NovelForge without bypassing NovelForge."} lede={<p>{zh() ? "portable Agent Skill 通过公开 Host Bridge 发现能力、检查 Project / Context / semantic contracts，并把写权限明确留在 Core。" : "The portable Agent Skill uses the public Host Bridge to discover capabilities and inspect Project, Context, and semantic contracts while writes remain Core-owned."}</p>} visual={<div class="unified-agent-hosts"><For each={agentHosts}>{(host, index) => <button type="button" data-active={selected() === index()} onClick={() => setSelected(index())}><span>{host.slice(0, 1)}</span><strong>{host}</strong></button>}</For></div>} /><section class="agent-host-workbench"><ProductSectionHeading eyebrow={zh() ? "宿主 recipe" : "HOST RECIPE"} title={zh() ? `${agentHosts[selected()]} 使用同一条公开边界。` : `${agentHosts[selected()]} uses the same public boundary.`} /><div class="agent-host-detail"><article class="agent-host-profile"><div class="agent-host-profile-badges"><span class="wui-badge wui-badge--soft">{agentHosts[selected()]}</span><span class="wui-badge wui-badge--outline">generic read-only bridge</span></div><h3>{zh() ? "能力匹配，不制造新的权威层。" : "Match capabilities without inventing another authority layer."}</h3><ul class="agent-host-facts"><li><span>{zh() ? "入口" : "Entry"}</span><strong>agent-skills/novelforge/SKILL.md</strong></li><li><span>{zh() ? "发现" : "Discovery"}</span><strong>bridge.describe</strong></li><li><span>{zh() ? "写权限" : "Write authority"}</span><strong>0 · authority=false</strong></li></ul></article><article class="agent-host-instruction"><div class="agent-host-instruction-head"><div><small>HOST INSTRUCTION</small><strong>{zh() ? "最小安全边界" : "Minimal safe boundary"}</strong></div></div><pre><code>{`1. Read agent-skills/novelforge/SKILL.md\n2. Run bridge self-test\n3. Run bridge.describe\n4. Invoke advertised operations only\n5. authority: false\n6. Never read private runtime stores directly`}</code></pre></article></div></section></div>;
}

function ChangelogPage() {
  const route = () => siteCopy[locale()].routes.changelog;
  return <div class="page-width section-compact unified-route-page"><ProductSurfaceHero tone="validated" eyebrow={<span>{route().eyebrow}</span>} title={route().title} lede={<p>{route().lede}</p>} visual={<div class="unified-release-badge"><strong>0.8.x</strong><span>{zh() ? "current main" : "current main"}</span></div>} /><div class="unified-card-grid"><For each={route().cards}>{(card, index) => <article class="wui-card unified-info-card"><small>0{index() + 1}</small><h3>{card.title}</h3><p>{card.body}</p></article>}</For></div></div>;
}

export default function ProductApp() {
  return <Router root={ProductShell}>
    <Route path="/" component={HomePage} />
    <Route path="/start" component={() => <Navigate href="/" />} />
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

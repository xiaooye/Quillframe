import { A, Route, Router, useLocation } from "@solidjs/router";
import { For, Show, createEffect, createSignal, type JSX } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import { githubRoot, sourceUrl, type Locale, type RouteCopy } from "./content";
import { enUS } from "./content.en-US";
import { zhCN } from "./content.zh-CN";

const siteCopy = { "en-US": enUS, "zh-CN": zhCN } as const;

type TransitionDocument = Document & {
  startViewTransition?: (update: () => void) => unknown;
};

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
  const target = event.currentTarget;
  const rect = target.getBoundingClientRect();
  const x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100));
  const y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100));
  target.style.setProperty("--pointer-x", `${x}%`);
  target.style.setProperty("--pointer-y", `${y}%`);
}

function AppShell(props: { children?: JSX.Element }) {
  const [menuOpen, setMenuOpen] = createSignal(false);
  const location = useLocation();

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

  const zh = () => locale() === "zh-CN";
  const toggleLocale = () => withViewTransition(() => setLocale(zh() ? "en-US" : "zh-CN"));
  const toggleDark = () => withViewTransition(() => setDark((value) => !value));

  return (
    <div class="site-shell">
      <header class="site-header">
        <div class="site-header-inner">
          <A href="/" class="brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
            <span class="brand-mark-wrap"><img src={brandMark} alt="" width="34" height="34" aria-hidden="true" /></span>
            <span class="brand-wordmark">NovelForge</span>
            <span class="version-chip">0.8.x</span>
          </A>

          <nav class="desktop-nav" aria-label={zh() ? "主导航" : "Primary navigation"}>
            <For each={nav()}>{([href, label]) => <A href={href} activeClass="active" end={false}>{label}</A>}</For>
          </nav>

          <div class="header-actions">
            <A href="/changelog" class="header-text-link">{labels().changelog}</A>
            <button class="chrome-button locale-button" type="button" onClick={toggleLocale} aria-label={zh() ? "切换到英文" : "Switch language"}>
              {copy().languageName}
            </button>
            <button class="chrome-button appearance-button" type="button" onClick={toggleDark} aria-label={labels().appearance}>
              <span aria-hidden="true">{dark() ? "☼" : "◐"}</span>
            </button>
            <a class="header-text-link github-link" href={githubRoot} target="_blank" rel="noreferrer">{labels().github}</a>
            <button
              class="chrome-button mobile-menu-button"
              type="button"
              aria-expanded={menuOpen()}
              aria-controls="mobile-navigation"
              aria-label={menuOpen() ? labels().close : labels().menu}
              onClick={() => setMenuOpen((value) => !value)}
            >
              <span class="menu-glyph" aria-hidden="true">{menuOpen() ? "×" : "≡"}</span>
            </button>
          </div>
        </div>

        <Show when={menuOpen()}>
          <nav id="mobile-navigation" class="mobile-nav" aria-label={zh() ? "移动端导航" : "Mobile navigation"}>
            <For each={nav()}>{([href, label]) => <A href={href} activeClass="active">{label}</A>}</For>
            <A href="/changelog">{labels().changelog}</A>
            <a href={githubRoot} target="_blank" rel="noreferrer">GitHub</a>
          </nav>
        </Show>
      </header>

      <main id="main-content">{props.children}</main>

      <footer class="site-footer">
        <div class="page-width footer-main">
          <div class="footer-identity">
            <div class="footer-brand"><img src={brandMark} alt="" aria-hidden="true" /><strong>NovelForge</strong></div>
            <p>{zh() ? "长篇创作需要的不只是生成能力，还需要可追溯的记忆、边界与接受流程。" : "Long-form fiction needs more than generation: it needs traceable memory, boundaries, and acceptance."}</p>
          </div>
          <div class="footer-nav">
            <div><small>{zh() ? "产品" : "Product"}</small><A href="/product">{labels().product}</A><A href="/studio">Studio</A><A href="/publication">{labels().publication}</A></div>
            <div><small>{zh() ? "系统" : "System"}</small><A href="/architecture">{labels().architecture}</A><A href="/docs">{labels().docs}</A><A href="/changelog">{labels().changelog}</A></div>
            <div><small>{zh() ? "源代码" : "Source"}</small><a href={githubRoot} target="_blank" rel="noreferrer">GitHub ↗</a><span>0.8.x · pre-1.0</span></div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function SectionIntro(props: { eyebrow: string; title: string; lede?: string; class?: string }) {
  return (
    <div class={`section-intro ${props.class ?? ""}`}>
      <p class="eyebrow">{props.eyebrow}</p>
      <h2>{props.title}</h2>
      <Show when={props.lede}><p class="section-lede">{props.lede}</p></Show>
    </div>
  );
}

function LoomInstrument() {
  const zh = () => locale() === "zh-CN";
  return (
    <figure class="loom-instrument" aria-label={zh() ? "NovelForge 创作与证据流程示意" : "Illustrative NovelForge creative evidence instrument"}>
      <svg class="instrument-weave" viewBox="0 0 760 620" aria-hidden="true">
        <defs>
          <linearGradient id="loom-project" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="var(--nf-lane-project-stroke)" />
            <stop offset="1" stop-color="var(--nf-lane-runtime-stroke)" />
          </linearGradient>
          <linearGradient id="loom-editorial" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stop-color="var(--nf-lane-editorial-stroke)" />
            <stop offset="1" stop-color="var(--nf-lane-evidence-stroke)" />
          </linearGradient>
          <filter id="loom-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="7" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <path class="weave-path weave-path-a" d="M78 478 C184 186 290 190 386 316 S588 526 690 172" fill="none" stroke="url(#loom-project)" stroke-width="3" />
        <path class="weave-path weave-path-b" d="M70 162 C206 526 312 466 412 280 S598 114 700 454" fill="none" stroke="url(#loom-editorial)" stroke-width="2.4" />
        <path class="weave-path weave-path-c" d="M106 318 C242 250 300 436 430 386 S570 214 668 298" fill="none" stroke="var(--nf-lane-validated-stroke)" stroke-width="1.5" opacity=".75" />
        <circle cx="386" cy="316" r="116" fill="none" stroke="currentColor" opacity=".08" />
        <circle cx="386" cy="316" r="178" fill="none" stroke="currentColor" opacity=".045" />
      </svg>

      <div class="instrument-orbit orbit-one" aria-hidden="true" />
      <div class="instrument-orbit orbit-two" aria-hidden="true" />

      <div class="instrument-pane pane-manuscript">
        <span class="pane-index">01</span>
        <small>{zh() ? "正文" : "MANUSCRIPT"}</small>
        <strong>{zh() ? "候选稿仍是候选稿" : "A candidate stays a candidate"}</strong>
        <p>{zh() ? "接受之前，不把模型输出偷偷升级成事实。" : "Model output does not quietly become truth before acceptance."}</p>
      </div>

      <div class="instrument-pane pane-context">
        <span class="pane-index">02</span>
        <small>{zh() ? "上下文" : "CONTEXT"}</small>
        <strong>{zh() ? "有帮助 ≠ 已载入" : "Support ≠ loaded"}</strong>
        <div class="context-meter" aria-hidden="true"><span /><span /><span class="muted" /><span /></div>
      </div>

      <div class="instrument-pane pane-gates">
        <span class="pane-index">03</span>
        <small>{zh() ? "同一候选稿" : "SAME CANDIDATE"}</small>
        <div class="gate-mini"><span>{zh() ? "文本" : "Surface"}</span><b>PASS</b></div>
        <div class="gate-mini"><span>{zh() ? "读者" : "Reader"}</span><b>PASS</b></div>
        <div class="gate-mini"><span>{zh() ? "连续性" : "Continuity"}</span><b>PASS</b></div>
        <div class="gate-mini"><span>{zh() ? "语义" : "Semantic"}</span><b>PASS</b></div>
      </div>

      <div class="instrument-seal">
        <span class="seal-dot" aria-hidden="true">✓</span>
        <div><small>{zh() ? "进入审查" : "REVIEW-READY"}</small><strong>{zh() ? "可审查，还不是正典" : "Visible, still not Canon"}</strong></div>
      </div>

      <figcaption>{zh() ? "示意界面 · 所有状态都来自当前契约语义" : "Illustrative interface · states reflect current contract semantics"}</figcaption>
    </figure>
  );
}

function HeroContractRail() {
  const zh = () => locale() === "zh-CN";
  const items = () => zh() ? [
    ["上下文", "有帮助 ≠ 已载入"],
    ["角色", "只使用此刻可知证据"],
    ["审查", "同一候选稿指纹"],
    ["出版", "接受正文逐字保持"],
  ] : [
    ["Context", "support ≠ loaded"],
    ["Character", "story-time visible evidence"],
    ["Readiness", "one candidate fingerprint"],
    ["Publication", "exact accepted text"],
  ];
  return (
    <div class="hero-contract-rail" aria-label={zh() ? "产品契约摘要" : "Product contract summary"}>
      <For each={items()}>{([label, value], index) => (
        <div class="contract-rail-item"><span>0{index() + 1}</span><small>{label}</small><strong>{value}</strong></div>
      )}</For>
    </div>
  );
}

function ForgeVisual(props: { steps: readonly (readonly [string, string, string])[] }) {
  return (
    <div class="forge-visual" aria-hidden="true">
      <svg class="forge-visual-thread" viewBox="0 0 620 720">
        <defs>
          <linearGradient id="forge-thread-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="var(--nf-lane-project-stroke)" />
            <stop offset=".34" stop-color="var(--nf-lane-runtime-stroke)" />
            <stop offset=".68" stop-color="var(--nf-lane-editorial-stroke)" />
            <stop offset="1" stop-color="var(--nf-lane-validated-stroke)" />
          </linearGradient>
        </defs>
        <path class="forge-thread-track" d="M310 42 C124 130 510 206 310 288 S112 442 310 518 S492 640 310 682" fill="none" />
        <path class="forge-thread-progress" d="M310 42 C124 130 510 206 310 288 S112 442 310 518 S492 640 310 682" fill="none" stroke="url(#forge-thread-gradient)" />
      </svg>
      <div class="forge-core"><img src={brandMark} alt="" /><span>NovelForge</span></div>
      <For each={props.steps}>{([index, title]) => (
        <div class={`forge-node forge-node-${index}`}>
          <span>{index}</span><strong>{title}</strong>
        </div>
      )}</For>
    </div>
  );
}

function StudioScene() {
  const zh = () => locale() === "zh-CN";
  return (
    <div class="studio-scene" role="img" aria-label={zh() ? "NovelForge Studio 示意工作台" : "Illustrative NovelForge Studio workspace"}>
      <div class="studio-scene-top"><span>NovelForge Studio</span><div><i /><i /><i /></div></div>
      <div class="studio-scene-body">
        <aside class="studio-rail">
          <b>{zh() ? "正文" : "Manuscript"}</b><span>{zh() ? "故事" : "Story"}</span><span>{zh() ? "审查" : "Review"}</span><span>{zh() ? "出版" : "Publish"}</span>
        </aside>
        <div class="studio-manuscript">
          <small>{zh() ? "当前场景 · CH-014" : "CURRENT SCENE · CH-014"}</small>
          <h3>{zh() ? "正文占据工作台中心。" : "The manuscript owns the center."}</h3>
          <p>{zh() ? "系统证据不抢走创作界面；只有需要追溯时，检查器才展开。" : "System evidence stays out of the way until the creator asks to inspect it."}</p>
          <div class="manuscript-lines" aria-hidden="true"><span /><span /><span /><span /><span /></div>
        </div>
        <aside class="studio-inspector">
          <div class="inspector-head"><small>{zh() ? "检查器" : "INSPECTOR"}</small><span>{zh() ? "按需展开" : "on demand"}</span></div>
          <div class="inspector-item"><i class="lane project" /><div><small>{zh() ? "项目" : "PROJECT"}</small><strong>{zh() ? "已接受状态" : "Accepted state"}</strong></div></div>
          <div class="inspector-item"><i class="lane runtime" /><div><small>{zh() ? "上下文" : "CONTEXT"}</small><strong>{zh() ? "7 条实际载入" : "7 blocks loaded"}</strong></div></div>
          <div class="inspector-item"><i class="lane editorial" /><div><small>{zh() ? "审查" : "REVIEW"}</small><strong>{zh() ? "同一候选稿" : "same candidate"}</strong></div></div>
        </aside>
      </div>
      <div class="studio-scene-bottom"><span>Local Web</span><span>authority=false</span><span>{zh() ? "无默认轮询" : "no default polling"}</span></div>
    </div>
  );
}

function PublicationPress() {
  const zh = () => locale() === "zh-CN";
  const profiles = ["clean_text", "web_reflow", "print_book", "epub3"];
  return (
    <div class="publication-press" role="img" aria-label={zh() ? "确定性出版流程示意" : "Illustrative deterministic publication press"}>
      <div class="press-source">
        <span class="press-stamp">ACCEPTED</span>
        <small>{zh() ? "已接受正文" : "ACCEPTED MANUSCRIPT"}</small>
        <strong>{zh() ? "来源指纹精确匹配" : "source fingerprint: exact"}</strong>
        <div class="press-copy-lines" aria-hidden="true"><span /><span /><span /><span /></div>
      </div>
      <div class="press-spine" aria-hidden="true"><span>↓</span></div>
      <div class="press-output-grid">
        <For each={profiles}>{(profile, index) => <div class={`press-output output-${index() + 1}`}><span>0{index() + 1}</span><code>{profile}</code><small>{zh() ? "派生输出" : "derived output"}</small></div>}</For>
      </div>
      <div class="press-authority">authority=false</div>
    </div>
  );
}

function ArchitectureConstellation() {
  const cards = () => copy().home.architecture.cards;
  return (
    <div class="architecture-constellation">
      <svg class="architecture-links" viewBox="0 0 1000 620" preserveAspectRatio="none" aria-hidden="true">
        <path d="M160 142 C310 60 430 160 500 302" />
        <path d="M840 136 C710 74 618 188 500 302" />
        <path d="M168 478 C286 548 424 438 500 302" />
        <path d="M832 486 C698 554 606 432 500 302" />
        <path d="M500 302 C500 184 500 138 500 74" />
        <path d="M500 302 C500 426 500 480 500 552" />
      </svg>
      <div class="architecture-core"><img src={brandMark} alt="" /><strong>NovelForge</strong><small>Core boundaries</small></div>
      <For each={cards()}>{(card, index) => (
        <article class={`architecture-node architecture-node-${index() + 1}`}>
          <span class="node-index">0{index() + 1}</span>
          <small>{card.eyebrow}</small>
          <h3>{card.title}</h3>
          <p>{card.body}</p>
        </article>
      )}</For>
    </div>
  );
}

function HomePage() {
  const c = () => copy().home;
  const zh = () => locale() === "zh-CN";

  return (
    <>
      <section class="flagship-hero" onPointerMove={updatePointerLight}>
        <div class="hero-mesh mesh-a" aria-hidden="true" />
        <div class="hero-mesh mesh-b" aria-hidden="true" />
        <div class="hero-thread-field" aria-hidden="true" />
        <div class="page-width flagship-hero-inner">
          <div class="hero-copy">
            <div class="hero-kicker"><span class="kicker-signal" />{c().eyebrow}</div>
            <h1>{c().title}</h1>
            <p class="hero-lede">{c().lede}</p>
            <div class="hero-actions">
              <a class="button button-primary" href="#forge">{c().primaryCta}<span aria-hidden="true">↘</span></a>
              <A class="button button-ghost" href="/architecture">{c().secondaryCta}<span aria-hidden="true">↗</span></A>
            </div>
            <div class="hero-proof-note"><span class="proof-note-dot" />{zh() ? "每一项产品主张都能回到当前主分支中的真实契约。" : "Every product claim resolves back to a real contract on current main."}</div>
          </div>
          <LoomInstrument />
          <HeroContractRail />
        </div>
        <div class="hero-scroll-mark" aria-hidden="true"><span>{zh() ? "向下阅读" : "SCROLL TO READ"}</span><i /></div>
      </section>

      <section class="problem-chapter chapter-light">
        <div class="page-width problem-layout">
          <div class="problem-statement">
            <p class="eyebrow">{c().problem.eyebrow}</p>
            <h2>{c().problem.title}</h2>
            <p class="section-lede">{c().problem.lede}</p>
          </div>
          <div class="problem-rails">
            <For each={c().problem.cards}>{(card, index) => (
              <article class="problem-rail">
                <div class="rail-index">0{index() + 1}</div>
                <div><h3>{card.title}</h3><p>{card.body}</p></div>
                <span class="rail-mark" aria-hidden="true" />
              </article>
            )}</For>
          </div>
        </div>
      </section>

      <section id="forge" class="forge-chapter chapter-dark">
        <div class="page-width forge-layout-v3">
          <div class="forge-sticky-stage">
            <p class="eyebrow">{c().forge.eyebrow}</p>
            <h2>{c().forge.title}</h2>
            <p class="section-lede">{c().forge.lede}</p>
            <ForgeVisual steps={c().forge.steps} />
            <A class="chapter-link" href="/product">{zh() ? "查看产品模型" : "Explore the product model"}<span>↗</span></A>
          </div>
          <ol class="forge-step-ledger">
            <For each={c().forge.steps}>{([index, title, body]) => (
              <li>
                <span class="step-index">{index}</span>
                <div><small>{zh() ? "阶段" : "STAGE"} {index}</small><h3>{title}</h3><p>{body}</p></div>
              </li>
            )}</For>
          </ol>
        </div>
      </section>

      <section class="proof-chapter chapter-paper">
        <div class="page-width">
          <div class="proof-heading-row">
            <SectionIntro eyebrow={c().proofLabel} title={zh() ? "不是一张漂亮的流程图，而是一串可以追溯的证据。" : "Not a pretty flowchart — a chain of evidence you can inspect."} />
            <p>{zh() ? "我们只展示当前实现真正能证明的边界。没有虚构评分，没有假客户，没有把计划写成能力。" : "Only boundaries current implementation can actually prove. No invented scores, fake customers, or roadmap-as-capability."}</p>
          </div>
          <div class="proof-field">
            <For each={c().proofs}>{(card, index) => (
              <article class={`proof-object proof-object-${index() + 1}`}>
                <div class="proof-object-top"><span>0{index() + 1}</span><small>{card.eyebrow}</small></div>
                <h3>{card.title}</h3>
                <p>{card.body}</p>
                <Show when={card.meta}><code>{card.meta}</code></Show>
              </article>
            )}</For>
          </div>
        </div>
      </section>

      <section class="studio-chapter chapter-ink">
        <div class="page-width studio-chapter-grid">
          <div class="studio-copy">
            <SectionIntro eyebrow={c().studio.eyebrow} title={c().studio.title} lede={c().studio.lede} />
            <div class="studio-bullets"><For each={c().studio.bullets}>{(item, index) => <div><span>0{index() + 1}</span><p>{item}</p></div>}</For></div>
            <A class="button button-light" href="/studio">{c().studio.cta}<span>↗</span></A>
          </div>
          <StudioScene />
        </div>
      </section>

      <section class="publication-chapter chapter-light">
        <div class="page-width publication-chapter-grid">
          <PublicationPress />
          <div class="publication-copy">
            <SectionIntro eyebrow={c().publication.eyebrow} title={c().publication.title} lede={c().publication.lede} />
            <p class="boundary-note">{c().publication.note}</p>
            <A class="chapter-link dark-link" href="/publication">{c().publication.cta}<span>↗</span></A>
          </div>
        </div>
      </section>

      <section class="architecture-chapter chapter-deep">
        <div class="page-width">
          <div class="architecture-heading-row">
            <SectionIntro eyebrow={c().architecture.eyebrow} title={c().architecture.title} lede={c().architecture.lede} />
            <A class="chapter-link" href="/architecture">{c().architecture.cta}<span>↗</span></A>
          </div>
          <ArchitectureConstellation />
        </div>
      </section>

      <section class="delivery-chapter chapter-paper">
        <div class="page-width delivery-grid-v3">
          <div>
            <SectionIntro eyebrow={c().delivery.eyebrow} title={c().delivery.title} />
            <p class="delivery-note">{zh() ? "宿主决定交互方式，不决定故事事实。" : "The host changes interaction, never story truth."}</p>
          </div>
          <div class="host-rail-v3">
            <For each={c().delivery.hosts}>{([host, body], index) => (
              <div class="host-segment"><span>0{index() + 1}</span><strong>{host}</strong><p>{body}</p></div>
            )}</For>
          </div>
        </div>
      </section>

      <section class="release-chapter chapter-light">
        <div class="page-width release-lockup">
          <div class="release-seal"><span>0.8</span><small>pre-1.0</small></div>
          <div class="release-copy"><p class="eyebrow">{c().release.eyebrow}</p><h2>{c().release.title}</h2><p>{c().release.lede}</p></div>
          <A class="button button-ghost dark-ghost" href="/changelog">{c().release.cta}<span>↗</span></A>
        </div>
      </section>

      <section class="final-chapter chapter-black" onPointerMove={updatePointerLight}>
        <div class="final-glow" aria-hidden="true" />
        <div class="page-width final-lockup">
          <span class="final-mark"><img src={brandMark} alt="" /></span>
          <h2>{c().final.title}</h2>
          <div class="final-actions">
            <A class="button button-light" href="/docs">{c().final.docs}<span>↗</span></A>
            <a class="button button-outline-light" href={githubRoot} target="_blank" rel="noreferrer">{c().final.github}<span>↗</span></a>
          </div>
        </div>
      </section>
    </>
  );
}

const routeSources: Record<Locale, Record<string, string[]>> = {
  "en-US": {
    product: ["README.en.md", "docs/production-pipeline.en.md"],
    studio: ["studio/README.en.md", "studio/PRODUCT_ARCHITECTURE.en.md"],
    architecture: ["docs/architecture-atlas.en.md", "docs/architecture.en.md"],
    publication: ["publication/publication_ir.schema.json", "publication/compiler.py"],
    changelog: ["CHANGELOG.en.md", "docs/8-0-development-inventory.en.md"],
  },
  "zh-CN": {
    product: ["README.zh-CN.md", "docs/production-pipeline.zh-CN.md"],
    studio: ["studio/README.zh-CN.md", "studio/PRODUCT_ARCHITECTURE.zh-CN.md"],
    architecture: ["docs/architecture-atlas.zh-CN.md", "docs/architecture.zh-CN.md"],
    publication: ["publication/publication_ir.schema.json", "publication/compiler.py"],
    changelog: ["CHANGELOG.zh-CN.md", "docs/8-0-development-inventory.zh-CN.md"],
  },
};

type RouteKind = keyof typeof enUS["routes"];

function DetailPage(props: { kind: RouteKind }) {
  const data = () => copy().routes[props.kind] as RouteCopy;
  const isDocs = () => props.kind === "docs";
  const zh = () => locale() === "zh-CN";

  return (
    <div class="detail-page">
      <section class="route-hero">
        <div class="route-hero-glow" aria-hidden="true" />
        <div class="page-width route-hero-grid">
          <div><p class="eyebrow">{data().eyebrow}</p><h1>{data().title}</h1></div>
          <p class="hero-lede">{data().lede}</p>
        </div>
      </section>

      <section class="route-ledger-section">
        <div class="page-width route-ledger">
          <For each={data().cards}>{(card, index) => (
            <article class="route-ledger-row">
              <span class="route-index">0{index() + 1}</span>
              <div class="route-title"><Show when={card.eyebrow}><small>{card.eyebrow}</small></Show><h2>{card.title}</h2></div>
              <p>{card.body}</p>
              <Show when={card.meta}><code>{card.meta}</code></Show>
            </article>
          )}</For>
          <Show when={data().note}><p class="boundary-note route-note">{data().note}</p></Show>
        </div>
      </section>

      <section class="route-sources-section">
        <div class="page-width route-sources">
          <div><p class="eyebrow">{isDocs() ? (zh() ? "持续维护的权威文档" : "Maintained sources of truth") : (zh() ? "权威来源" : "Canonical sources")}</p><h2>{zh() ? "继续读原始契约。" : "Continue into the source contracts."}</h2></div>
          <div class="source-links-v3">
            <Show when={isDocs()} fallback={
              <For each={routeSources[locale()][props.kind] ?? []}>{(path) => <a href={sourceUrl(path)} target="_blank" rel="noreferrer"><code>{path}</code><span>↗</span></a>}</For>
            }>
              <For each={data().cards}>{(card) => <Show when={card.meta}><a href={sourceUrl(card.meta!)} target="_blank" rel="noreferrer"><code>{card.meta}</code><span>↗</span></a></Show>}</For>
            </Show>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  return (
    <Router root={AppShell}>
      <Route path="/" component={HomePage} />
      <Route path="/product" component={() => <DetailPage kind="product" />} />
      <Route path="/studio" component={() => <DetailPage kind="studio" />} />
      <Route path="/architecture" component={() => <DetailPage kind="architecture" />} />
      <Route path="/publication" component={() => <DetailPage kind="publication" />} />
      <Route path="/docs" component={() => <DetailPage kind="docs" />} />
      <Route path="/changelog" component={() => <DetailPage kind="changelog" />} />
    </Router>
  );
}

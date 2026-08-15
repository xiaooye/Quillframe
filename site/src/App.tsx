import { A, Route, Router, useLocation } from "@solidjs/router";
import { For, Show, createEffect, createSignal, type JSX } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import { copy, githubRoot, sourceUrl, type Card, type Locale, type RouteCopy } from "./content";

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

function syncDocumentState() {
  const lang = locale();
  document.documentElement.lang = lang === "zh-CN" ? "zh-CN" : "en";
  document.documentElement.classList.toggle("dark", dark());
  localStorage.setItem("novelforge.locale", lang);
  localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
}

function AppShell(props: { children?: JSX.Element }) {
  const [menuOpen, setMenuOpen] = createSignal(false);
  const location = useLocation();

  createEffect(syncDocumentState);
  createEffect(() => {
    location.pathname;
    setMenuOpen(false);
  });

  const labels = () => copy[locale()].nav;
  const nav = () => [
    ["/product", labels().product],
    ["/studio", labels().studio],
    ["/architecture", labels().architecture],
    ["/publication", labels().publication],
    ["/docs", labels().docs],
  ] as const;

  const toggleLocale = () => setLocale(locale() === "en-US" ? "zh-CN" : "en-US");
  const toggleDark = () => setDark((value) => !value);

  return (
    <div class="site-shell">
      <header class="site-header">
        <div class="site-header-inner">
          <A href="/" class="brand-link" aria-label="NovelForge home">
            <img src={brandMark} alt="" width="34" height="34" aria-hidden="true" />
            <span class="brand-wordmark">NovelForge</span>
            <span class="version-chip">0.8.x</span>
          </A>

          <nav class="desktop-nav" aria-label="Primary navigation">
            <For each={nav()}>{([href, label]) => <A href={href} activeClass="active" end={false}>{label}</A>}</For>
          </nav>

          <div class="header-actions">
            <A href="/changelog" class="header-text-link">{labels().changelog}</A>
            <button class="icon-button locale-button" type="button" onClick={toggleLocale} aria-label="Switch language">
              {copy[locale()].languageName}
            </button>
            <button class="icon-button" type="button" onClick={toggleDark} aria-label={labels().appearance}>
              <span aria-hidden="true">{dark() ? "☼" : "◐"}</span>
            </button>
            <a class="header-text-link github-link" href={githubRoot} target="_blank" rel="noreferrer">{labels().github}</a>
            <button
              class="icon-button mobile-menu-button"
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
          <nav id="mobile-navigation" class="mobile-nav" aria-label="Mobile navigation">
            <For each={nav()}>{([href, label]) => <A href={href} activeClass="active">{label}</A>}</For>
            <A href="/changelog">{labels().changelog}</A>
            <a href={githubRoot} target="_blank" rel="noreferrer">{labels().github}</a>
          </nav>
        </Show>
      </header>

      <main id="main-content">{props.children}</main>

      <footer class="site-footer">
        <div class="footer-grid">
          <div>
            <div class="footer-brand"><img src={brandMark} alt="" aria-hidden="true" /><strong>NovelForge</strong></div>
            <p>{locale() === "zh-CN" ? "自适应小说 Agent Framework。创作判断交给模型，边界交给可检查的系统。" : "Adaptive fiction agent framework. Creative judgment for models; inspectable boundaries for the system."}</p>
          </div>
          <div class="footer-links">
            <strong>{locale() === "zh-CN" ? "产品" : "Product"}</strong>
            <A href="/studio">Studio</A>
            <A href="/architecture">{labels().architecture}</A>
            <A href="/publication">{labels().publication}</A>
          </div>
          <div class="footer-links">
            <strong>{locale() === "zh-CN" ? "深入" : "Go deeper"}</strong>
            <A href="/docs">{labels().docs}</A>
            <A href="/changelog">{labels().changelog}</A>
            <a href={githubRoot} target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </div>
        <div class="footer-meta">
          <span>0.8.x · pre-1.0</span>
          <span>{locale() === "zh-CN" ? "latest main 是开发基线" : "latest main is the development baseline"}</span>
        </div>
      </footer>
    </div>
  );
}

function SectionHeading(props: { eyebrow: string; title: string; lede?: string; align?: "left" | "center" }) {
  return (
    <div class={`section-heading ${props.align === "center" ? "center" : ""}`}>
      <p class="eyebrow">{props.eyebrow}</p>
      <h2>{props.title}</h2>
      <Show when={props.lede}><p class="section-lede">{props.lede}</p></Show>
    </div>
  );
}

function CardView(props: { card: Card; class?: string }) {
  return (
    <article class={`info-card ${props.class ?? ""}`}>
      <Show when={props.card.eyebrow}><p class="card-eyebrow">{props.card.eyebrow}</p></Show>
      <h3>{props.card.title}</h3>
      <p>{props.card.body}</p>
      <Show when={props.card.meta}><code class="meta-code">{props.card.meta}</code></Show>
    </article>
  );
}

function ForgeCanvas() {
  const zh = () => locale() === "zh-CN";
  return (
    <div class="forge-canvas" role="img" aria-label={zh() ? "Illustrative NovelForge workflow canvas" : "Illustrative NovelForge workflow canvas"}>
      <div class="canvas-topline">
        <span class="canvas-kicker">FORGE CANVAS</span>
        <span class="illustrative-chip">{zh() ? "示意界面" : "illustrative UI"}</span>
      </div>
      <div class="canvas-stage project-stage">
        <span class="stage-dot project-dot" aria-hidden="true" />
        <div><small>PROJECT</small><strong>{zh() ? "当前创作上下文" : "Current creative context"}</strong></div>
        <span class="stage-state">accepted + plan</span>
      </div>
      <div class="canvas-thread" aria-hidden="true" />
      <div class="canvas-stage runtime-stage">
        <span class="stage-dot runtime-dot" aria-hidden="true" />
        <div><small>CONTEXT</small><strong>{zh() ? "可见 evidence → loaded subset" : "Visible evidence → loaded subset"}</strong></div>
        <span class="stage-state">bounded</span>
      </div>
      <div class="canvas-thread" aria-hidden="true" />
      <div class="canvas-stage editorial-stage">
        <span class="stage-dot editorial-dot" aria-hidden="true" />
        <div><small>DRAFT</small><strong>{zh() ? "候选稿绑定 fingerprint" : "Candidate bound to fingerprint"}</strong></div>
        <span class="stage-state">candidate</span>
      </div>
      <div class="gate-panel">
        <div class="gate-title"><span>{zh() ? "同一候选稿 Gate" : "Same-candidate gates"}</span><code>fp: exact</code></div>
        <div class="gate-row"><span>Surface</span><strong>PASS</strong></div>
        <div class="gate-row"><span>Reader Engagement</span><strong>PASS</strong></div>
        <div class="gate-row"><span>Continuity</span><strong>PASS</strong></div>
        <div class="gate-row"><span>Independent Semantic</span><strong>PASS</strong></div>
      </div>
      <div class="canvas-output">
        <span class="output-mark" aria-hidden="true">✓</span>
        <div><small>USER-VISIBLE</small><strong>{zh() ? "可以进入 Review，不等于 Canon" : "Ready for review, not Canon"}</strong></div>
      </div>
    </div>
  );
}

function HomePage() {
  const c = () => copy[locale()].home;
  return (
    <>
      <section class="hero section-pad">
        <div class="page-width hero-grid">
          <div class="hero-copy">
            <p class="eyebrow">{c().eyebrow}</p>
            <h1>{c().title}</h1>
            <p class="hero-lede">{c().lede}</p>
            <div class="hero-actions">
              <a class="button primary" href="#forge">{c().primaryCta}</a>
              <A class="button secondary" href="/architecture">{c().secondaryCta}</A>
            </div>
            <div class="hero-trustline">
              <span class="trust-dot" aria-hidden="true" />
              <span>{locale() === "zh-CN" ? "所有产品 claim 都绑定 current main 的真实 contract" : "Product claims are grounded in contracts that exist on current main"}</span>
            </div>
          </div>
          <ForgeCanvas />
        </div>
      </section>

      <section class="section-pad subtle-section">
        <div class="page-width">
          <SectionHeading eyebrow={c().problem.eyebrow} title={c().problem.title} lede={c().problem.lede} />
          <div class="three-grid problem-grid"><For each={c().problem.cards}>{(card) => <CardView card={card} />}</For></div>
        </div>
      </section>

      <section id="forge" class="section-pad forge-story">
        <div class="page-width forge-layout">
          <div class="forge-sticky-copy">
            <SectionHeading eyebrow={c().forge.eyebrow} title={c().forge.title} lede={c().forge.lede} />
            <A class="text-link" href="/product">{locale() === "zh-CN" ? "了解 Product model →" : "Explore the product model →"}</A>
          </div>
          <ol class="forge-steps">
            <For each={c().forge.steps}>{([index, title, body]) => (
              <li>
                <span class="step-number">{index}</span>
                <div><h3>{title}</h3><p>{body}</p></div>
              </li>
            )}</For>
          </ol>
        </div>
      </section>

      <section class="section-pad proof-section">
        <div class="page-width">
          <SectionHeading eyebrow={c().proofLabel} title={locale() === "zh-CN" ? "系统自己留下可以检查的痕迹。" : "The system leaves evidence you can inspect."} align="center" />
          <div class="proof-grid"><For each={c().proofs}>{(card) => <CardView card={card} class="proof-card" />}</For></div>
        </div>
      </section>

      <section class="section-pad product-band studio-band">
        <div class="page-width split-feature">
          <div>
            <SectionHeading eyebrow={c().studio.eyebrow} title={c().studio.title} lede={c().studio.lede} />
            <A class="button secondary" href="/studio">{c().studio.cta}</A>
          </div>
          <div class="workbench-preview" aria-label="Studio architecture preview">
            <div class="preview-tabs"><span class="active">Creator</span><span>Inspector</span></div>
            <div class="preview-manuscript"><small>SCENE</small><strong>{locale() === "zh-CN" ? "正文是主界面，不是日志附件" : "The manuscript is the workspace, not a log attachment"}</strong><p>{locale() === "zh-CN" ? "Context、Reader、Continuity 与 Runtime evidence 按需展开。" : "Context, Reader, Continuity, and Runtime evidence appear on demand."}</p></div>
            <div class="preview-stack"><For each={c().studio.bullets}>{(item) => <span>{item}</span>}</For></div>
          </div>
        </div>
      </section>

      <section class="section-pad publication-band">
        <div class="page-width split-feature publication-layout">
          <div class="publication-preview">
            <div class="publication-source"><small>ACCEPTED MANUSCRIPT</small><strong>fingerprint: exact</strong></div>
            <div class="publication-arrow" aria-hidden="true">↓</div>
            <div class="profile-grid"><For each={c().publication.profiles}>{(profile) => <code>{profile}</code>}</For></div>
            <span class="derived-label">authority=false · derived output</span>
          </div>
          <div>
            <SectionHeading eyebrow={c().publication.eyebrow} title={c().publication.title} lede={c().publication.lede} />
            <p class="boundary-note">{c().publication.note}</p>
            <A class="button secondary" href="/publication">{c().publication.cta}</A>
          </div>
        </div>
      </section>

      <section class="section-pad architecture-section">
        <div class="page-width">
          <SectionHeading eyebrow={c().architecture.eyebrow} title={c().architecture.title} lede={c().architecture.lede} />
          <div class="bento-grid"><For each={c().architecture.cards}>{(card, index) => <CardView card={card} class={`bento-card bento-${index() + 1}`} />}</For></div>
          <A class="text-link section-link" href="/architecture">{c().architecture.cta} →</A>
        </div>
      </section>

      <section class="section-pad delivery-section">
        <div class="page-width delivery-layout">
          <SectionHeading eyebrow={c().delivery.eyebrow} title={c().delivery.title} />
          <div class="host-list"><For each={c().delivery.hosts}>{([host, body]) => <div class="host-row"><strong>{host}</strong><span>{body}</span></div>}</For></div>
        </div>
      </section>

      <section class="section-pad release-section">
        <div class="page-width release-card">
          <div><p class="eyebrow">{c().release.eyebrow}</p><h2>{c().release.title}</h2><p>{c().release.lede}</p></div>
          <A class="button secondary" href="/changelog">{c().release.cta}</A>
        </div>
      </section>

      <section class="section-pad final-cta">
        <div class="page-width final-cta-inner">
          <h2>{c().final.title}</h2>
          <div class="hero-actions">
            <A class="button primary" href="/docs">{c().final.docs}</A>
            <a class="button secondary" href={githubRoot} target="_blank" rel="noreferrer">{c().final.github}</a>
          </div>
        </div>
      </section>
    </>
  );
}

const routeSources: Record<string, string[]> = {
  product: ["README.en.md", "docs/production-pipeline.en.md"],
  studio: ["studio/README.en.md", "studio/PRODUCT_ARCHITECTURE.en.md"],
  architecture: ["docs/architecture-atlas.en.md", "docs/architecture.en.md"],
  publication: ["publication/publication_ir.schema.json", "publication/compiler.py"],
  changelog: ["CHANGELOG.en.md", "docs/8-0-development-inventory.en.md"],
};

function DetailPage(props: { kind: keyof typeof copy["en-US"]["routes"] }) {
  const data = () => copy[locale()].routes[props.kind] as RouteCopy;
  const isDocs = () => props.kind === "docs";
  return (
    <div class="detail-page">
      <section class="detail-hero section-pad">
        <div class="page-width narrow-width">
          <p class="eyebrow">{data().eyebrow}</p>
          <h1>{data().title}</h1>
          <p class="hero-lede">{data().lede}</p>
        </div>
      </section>
      <section class="section-pad detail-content">
        <div class="page-width">
          <div class="detail-grid">
            <For each={data().cards}>{(card) => (
              <CardView card={card} class="detail-card" />
            )}</For>
          </div>
          <Show when={data().note}><p class="boundary-note detail-note">{data().note}</p></Show>

          <Show when={isDocs()} fallback={
            <div class="source-panel">
              <p class="eyebrow">{locale() === "zh-CN" ? "Canonical sources" : "Canonical sources"}</p>
              <div class="source-links"><For each={routeSources[props.kind] ?? []}>{(path) => <a href={sourceUrl(path)} target="_blank" rel="noreferrer"><code>{path}</code><span>↗</span></a>}</For></div>
            </div>
          }>
            <div class="source-panel docs-panel">
              <p class="eyebrow">{locale() === "zh-CN" ? "维护中的 Source of Truth" : "Maintained sources of truth"}</p>
              <div class="source-links">
                <For each={data().cards}>{(card) => <Show when={card.meta}><a href={sourceUrl(card.meta!)} target="_blank" rel="noreferrer"><code>{card.meta}</code><span>↗</span></a></Show>}</For>
              </div>
            </div>
          </Show>
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

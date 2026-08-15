import { For, Show, createEffect, createMemo, createSignal } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import type { Locale } from "./content";

type Props = { initialLocale: Locale };
type ProfileId = "text" | "web" | "print" | "epub";

type ProfileToken = {
  label: string;
  labelZh: string;
  value: string;
  valueZh?: string;
};

type PublicationProfile = {
  id: ProfileId;
  icon: string;
  label: string;
  labelZh: string;
  title: string;
  titleZh: string;
  summary: string;
  summaryZh: string;
  artifact: string;
  pipelineLabel: string;
  pipelineLabelZh: string;
  tokens: ProfileToken[];
};

const profiles: PublicationProfile[] = [
  {
    id: "text",
    icon: "TXT",
    label: "Clean text",
    labelZh: "纯文本",
    title: "Exact text, no presentation layer",
    titleZh: "只保留正文，不叠加表现层",
    summary: "A clean text derivative for archival, diffing, transfer, and downstream tooling.",
    summaryZh: "用于归档、diff、转交与下游工具的干净文本派生物。",
    artifact: ".txt",
    pipelineLabel: "clean text",
    pipelineLabelZh: "clean text",
    tokens: [
      { label: "encoding", labelZh: "编码", value: "UTF-8" },
      { label: "layout", labelZh: "布局", value: "none", valueZh: "无表现层" },
      { label: "flow", labelZh: "文本流", value: "linear", valueZh: "线性正文" },
      { label: "authority", labelZh: "权威", value: "derived · false" },
    ],
  },
  {
    id: "web",
    icon: "WEB",
    label: "Web",
    labelZh: "网页",
    title: "Responsive reading surface",
    titleZh: "适配屏幕的阅读表面",
    summary: "Semantic HTML and presentation CSS wrap the same accepted text for browser reading.",
    summaryZh: "用语义 HTML 与展示 CSS 包住同一份接受正文，适配浏览器阅读。",
    artifact: ".html + .css",
    pipelineLabel: "Web HTML",
    pipelineLabelZh: "Web HTML",
    tokens: [
      { label: "measure", labelZh: "行宽", value: "responsive" },
      { label: "navigation", labelZh: "导航", value: "chapter anchors", valueZh: "章节锚点" },
      { label: "type", labelZh: "字体", value: "reader-facing", valueZh: "阅读端样式" },
      { label: "authority", labelZh: "权威", value: "derived · false" },
    ],
  },
  {
    id: "print",
    icon: "PRINT",
    label: "Print",
    labelZh: "印刷版",
    title: "Paged-media composition",
    titleZh: "面向纸面的分页排版",
    summary: "Print-oriented HTML/CSS adds page geometry, running matter, folios, and typographic rhythm without rewriting the manuscript.",
    summaryZh: "面向印刷的 HTML/CSS 增加页形、页眉页脚、页码与排版节奏，但不改写正文。",
    artifact: "print HTML/CSS",
    pipelineLabel: "print-oriented HTML/CSS",
    pipelineLabelZh: "print-oriented HTML / CSS",
    tokens: [
      { label: "pagination", labelZh: "分页", value: "paged media" },
      { label: "running matter", labelZh: "页眉页脚", value: "profile-owned", valueZh: "由 profile 决定" },
      { label: "folios", labelZh: "页码", value: "enabled", valueZh: "启用" },
      { label: "authority", labelZh: "权威", value: "derived · false" },
    ],
  },
  {
    id: "epub",
    icon: "EPUB",
    label: "EPUB",
    labelZh: "EPUB",
    title: "Reflowable ebook package",
    titleZh: "可重排的电子书包",
    summary: "EPUB 3.3 packages semantic chapters, navigation, metadata, and reading resources around the accepted text.",
    summaryZh: "EPUB 3.3 围绕接受正文组织语义章节、导航、metadata 与阅读资源。",
    artifact: ".epub",
    pipelineLabel: "EPUB 3.3",
    pipelineLabelZh: "EPUB 3.3",
    tokens: [
      { label: "standard", labelZh: "标准", value: "EPUB 3.3" },
      { label: "layout", labelZh: "布局", value: "reflowable", valueZh: "可重排" },
      { label: "navigation", labelZh: "导航", value: "nav + toc" },
      { label: "authority", labelZh: "权威", value: "derived · false" },
    ],
  },
];

function initialDark() {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export default function PublicationWorkbenchEntry(props: Props) {
  const [locale, setLocale] = createSignal<Locale>(props.initialLocale);
  const [dark, setDark] = createSignal(initialDark());
  const [selected, setSelected] = createSignal(3);
  const [fontScale, setFontScale] = createSignal(100);
  const [leading, setLeading] = createSignal(175);
  const [guides, setGuides] = createSignal(false);
  const zh = () => locale() === "zh-CN";
  const current = createMemo(() => profiles[selected()]);

  createEffect(() => {
    document.documentElement.lang = zh() ? "zh-CN" : "en";
    document.documentElement.dataset.locale = locale();
    document.documentElement.classList.toggle("dark", dark());
    localStorage.setItem("novelforge.locale", locale());
    localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
  });

  const resetPreview = () => {
    setFontScale(100);
    setLeading(175);
    setGuides(false);
  };

  const sampleTitle = () => zh() ? "第一章 · 夜幕与灯火" : "Chapter 1 · Nightfall and lights";
  const sampleParagraphs = () => zh()
    ? [
      "夜幕降临，城市的灯光一盏盏亮起，像星星坠落在河面上。",
      "他站在桥边，手里握着一封信，纸角已经被汗水浸湿。",
      "风从河面吹来，带着潮湿的气息，也吹散了他心里那些犹豫。",
    ]
    : [
      "Night fell and the city lights came on one by one, like stars settling on the river.",
      "He stood by the bridge holding a letter, its corners already damp in his hand.",
      "Wind moved across the river carrying wet air, loosening some of the hesitation he had carried with him.",
    ];

  return (
    <div class="site-shell product-entry publication-workbench-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <a href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </a>
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "产品导航" : "Product navigation"}>
          <a class="wui-app-bar__link" href="/product">{zh() ? "产品" : "Product"}</a>
          <a class="wui-app-bar__link" href="/studio">Studio</a>
          <a class="wui-app-bar__link" href="/architecture">{zh() ? "架构" : "Architecture"}</a>
          <a class="wui-app-bar__link active" href="/publication" aria-current="page">{zh() ? "出版" : "Publication"}</a>
          <a class="wui-app-bar__link" href="/docs">{zh() ? "知识库" : "Knowledge"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href="https://studio.novelforge.wei-dev.com" target="_blank" rel="noreferrer">✦ {zh() ? "打开 Studio" : "Open Studio"}</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact publication-workbench-main">
        <section class="publication-intro kawaii-publication-hero">
          <div class="publication-hero-copy">
            <div class="publication-badges">
              <span class="publication-ribbon">🎀 {zh() ? "出版工作台" : "PUBLICATION WORKBENCH"}</span>
              <span class="wui-badge wui-badge--outline">deterministic</span>
            </div>
            <h1>{zh() ? <>同一份接受稿，<br />生成多种<span>确定性派生格式。</span></> : <>One accepted manuscript,<br /><span>many deterministic derivatives.</span></>}</h1>
            <p>{zh() ? "基于唯一的 Publication IR，从一次构建生成 TXT、Web、Print、EPUB 等多种载体。版式可以不同，正文事实始终只有一份。" : "One Publication IR deterministically produces TXT, Web, Print, and EPUB surfaces. Presentation may change; manuscript truth does not."}</p>
            <div class="publication-hero-features">
              <div><span>▣</span><strong>{zh() ? "格式一致" : "Consistent"}</strong><small>{zh() ? "同一份 IR 渲染" : "one IR"}</small></div>
              <div><span>✓</span><strong>{zh() ? "确定性" : "Deterministic"}</strong><small>{zh() ? "可重复构建" : "repeatable"}</small></div>
              <div><span>◎</span><strong>{zh() ? "可追溯" : "Traceable"}</strong><small>{zh() ? "完整 provenance" : "full provenance"}</small></div>
              <div><span>◇</span><strong>{zh() ? "可验证" : "Validated"}</strong><small>EPUBCheck</small></div>
            </div>
          </div>

          <div class="publication-hero-gallery" aria-label={zh() ? "出版格式示例" : "Publication format examples"}>
            <button type="button" class="publication-hero-snapshot snapshot-text" data-active={selected() === 0} onClick={() => setSelected(0)} aria-label={zh() ? "查看纯文本示例" : "View clean text example"}>
              <span class="snapshot-label">TXT</span>
              <span class="snapshot-paperclip">⌇</span>
              <span class="snapshot-line-number">1<br />2<br />3<br />4<br />5<br />6</span>
              <span class="snapshot-text-body"><strong>{sampleTitle()}</strong><i>{sampleParagraphs()[0]}</i><i>{sampleParagraphs()[1]}</i><i>{sampleParagraphs()[2]}</i></span>
              <span class="snapshot-sticker">✿</span>
            </button>

            <button type="button" class="publication-hero-snapshot snapshot-web" data-active={selected() === 1} onClick={() => setSelected(1)} aria-label={zh() ? "查看网页示例" : "View web example"}>
              <span class="snapshot-label">Web</span>
              <span class="snapshot-windowbar"><i /><i /><i /><b>novel / ch1</b></span>
              <span class="snapshot-web-body"><strong>{sampleTitle()}</strong><i>{sampleParagraphs()[0]}</i><i>{sampleParagraphs()[1]}</i><em>☾</em></span>
              <span class="snapshot-horizon">⌁ ✦ ⌁</span>
            </button>

            <button type="button" class="publication-hero-snapshot snapshot-print" data-active={selected() === 2} onClick={() => setSelected(2)} aria-label={zh() ? "查看印刷示例" : "View print example"}>
              <span class="snapshot-label">Print</span>
              <span class="snapshot-bookmark">▾</span>
              <span class="snapshot-print-page"><strong>{sampleTitle()}</strong><i>{sampleParagraphs()[0]}</i><i>{sampleParagraphs()[1]}</i><small>— 12 —</small></span>
              <span class="snapshot-flower">❀</span>
            </button>

            <button type="button" class="publication-hero-snapshot snapshot-epub" data-active={selected() === 3} onClick={() => setSelected(3)} aria-label={zh() ? "查看 EPUB 示例" : "View EPUB example"}>
              <span class="snapshot-label">EPUB</span>
              <span class="snapshot-device-top"><b>9:41</b><i>A</i><i>A</i><i>♡</i></span>
              <span class="snapshot-epub-body"><strong>{sampleTitle()}</strong><i>{sampleParagraphs()[0]}</i><i>{sampleParagraphs()[1]}</i><i>{sampleParagraphs()[2]}</i></span>
              <span class="snapshot-progress">12 / 523 · 3%</span>
              <span class="snapshot-heart">♡</span>
            </button>
          </div>
        </section>

        <section class="publication-profile-rail" aria-label={zh() ? "出版 profile" : "Publication profiles"}>
          <div class="publication-rail-title"><span>🛠</span><div><strong>{zh() ? "出版工作台" : "Publication workbench"}</strong><small>{zh() ? "选择目标格式并查看预览、配置与元数据。" : "Choose a target format and inspect preview, profile, and metadata."}</small></div></div>
          <For each={profiles}>{(profile, index) => (
            <button
              type="button"
              class="publication-profile-card"
              data-active={selected() === index()}
              data-profile={profile.id}
              aria-pressed={selected() === index()}
              onClick={() => setSelected(index())}
            >
              <span class="publication-profile-icon">{profile.icon}</span>
              <span class="publication-profile-copy">
                <small>{zh() ? profile.labelZh : profile.label}</small>
                <strong>{zh() ? profile.titleZh : profile.title}</strong>
                <span>{profile.artifact}</span>
              </span>
              <span class="publication-profile-arrow" aria-hidden="true">{selected() === index() ? "✓" : "→"}</span>
            </button>
          )}</For>
        </section>

        <section class="publication-workbench-grid">
          <article
            class="wui-card publication-preview-card"
            data-profile={current().id}
            data-guides={guides()}
            style={`--publication-font-scale:${fontScale() / 100};--publication-leading:${leading() / 100};`}
          >
            <div class="publication-preview-toolbar">
              <div>
                <small>{zh() ? "阅读预览" : "READING PREVIEW"}</small>
                <strong>{zh() ? current().labelZh : current().label}</strong>
              </div>
              <div class="publication-preview-state">
                <span class="wui-badge wui-badge--success">exact text</span>
                <span class="wui-badge wui-badge--outline">preview only</span>
              </div>
            </div>

            <div class="publication-preview-stage">
              <Show when={current().id === "text"}>
                <div class="publication-text-preview">
                  <div class="publication-text-gutter"><span>01</span><span>02</span><span>03</span><span>04</span><span>05</span><span>06</span><span>07</span></div>
                  <pre>{`${sampleTitle()}\n\n${sampleParagraphs().join("\n\n")}`}</pre>
                </div>
              </Show>

              <Show when={current().id === "web"}>
                <div class="publication-browser-preview">
                  <div class="publication-browser-chrome"><span /><span /><span /><strong>novel.example / chapter-1</strong></div>
                  <article class="publication-reading-page">
                    <span class="publication-preview-kicker">NOVELFORGE · WEB</span>
                    <h2>{sampleTitle()}</h2>
                    <For each={sampleParagraphs()}>{(paragraph) => <p>{paragraph}</p>}</For>
                    <div class="publication-chapter-nav"><span>←</span><span>1 / 64</span><span>2 →</span></div>
                  </article>
                </div>
              </Show>

              <Show when={current().id === "print"}>
                <div class="publication-print-preview">
                  <article class="publication-paper-page publication-paper-left">
                    <header><span>NovelForge</span><span>01</span></header>
                    <div class="publication-paper-body"><span class="publication-preview-kicker">CHAPTER 1</span><h2>{sampleTitle()}</h2><p>{sampleParagraphs()[0]}</p><p>{sampleParagraphs()[1]}</p></div>
                    <footer>12</footer>
                  </article>
                  <article class="publication-paper-page publication-paper-right">
                    <header><span>{sampleTitle()}</span><span>01</span></header>
                    <div class="publication-paper-body"><p>{sampleParagraphs()[2]}</p><div class="publication-print-ornament">✦</div></div>
                    <footer>13</footer>
                  </article>
                </div>
              </Show>

              <Show when={current().id === "epub"}>
                <div class="publication-ereader-preview">
                  <div class="publication-ereader-top"><span>‹</span><strong>NovelForge</strong><span>Aa</span></div>
                  <article class="publication-reading-page publication-ereader-page">
                    <span class="publication-preview-kicker">01 · EPUB 3.3</span>
                    <h2>{sampleTitle()}</h2>
                    <For each={sampleParagraphs()}>{(paragraph) => <p>{paragraph}</p>}</For>
                  </article>
                  <div class="publication-ereader-progress"><span style="width:3%" /><small>3%</small></div>
                </div>
              </Show>
            </div>

            <div class="publication-preview-controls" aria-label={zh() ? "本地预览控制" : "Local preview controls"}>
              <label><span>{zh() ? "字号" : "Type"}</span><input type="range" min="92" max="116" step="1" value={fontScale()} onInput={(event) => setFontScale(Number(event.currentTarget.value))} /><strong>{fontScale()}%</strong></label>
              <label><span>{zh() ? "行距" : "Leading"}</span><input type="range" min="150" max="205" step="5" value={leading()} onInput={(event) => setLeading(Number(event.currentTarget.value))} /><strong>{(leading() / 100).toFixed(2)}</strong></label>
              <button type="button" class="publication-guide-toggle" data-active={guides()} aria-pressed={guides()} onClick={() => setGuides((value) => !value)}>⌗ {zh() ? "版心辅助线" : "Measure guides"}</button>
              <button type="button" class="wui-button wui-button--ghost" onClick={resetPreview}>{zh() ? "重置预览" : "Reset preview"}</button>
            </div>
          </article>

          <aside class="publication-inspector">
            <section class="wui-card publication-profile-inspector">
              <div class="publication-inspector-head">
                <span class="publication-inspector-icon">{current().icon}</span>
                <div><small>{zh() ? "格式配置与元数据" : "PROFILE & METADATA"}</small><h2>{zh() ? current().titleZh : current().title}</h2></div>
              </div>
              <p>{zh() ? current().summaryZh : current().summary}</p>
              <div class="publication-token-grid">
                <For each={current().tokens}>{(token) => <div><span>{zh() ? token.labelZh : token.label}</span><strong>{zh() ? (token.valueZh ?? token.value) : token.value}</strong></div>}</For>
                <div><span>{zh() ? "来源" : "source"}</span><strong>sha256 · exact</strong></div>
                <div><span>{zh() ? "验证" : "validation"}</span><strong>{current().id === "epub" ? "EPUBCheck" : "deterministic"}</strong></div>
              </div>
              <div class="publication-inspector-note"><span>✦</span><p>{zh() ? "这些 token 描述展示 profile；上面的预览控制只在浏览器本地生效，不写入 manuscript，也不会制造第二套 truth model。" : "These tokens describe presentation only. Preview controls are browser-local and never create a second manuscript truth model."}</p></div>
            </section>

            <section class="wui-card publication-artifact-card">
              <small>{zh() ? "当前出版配置" : "CURRENT PUBLICATION PROFILE"}</small>
              <div><strong>{current().artifact}</strong><span>{zh() ? current().pipelineLabelZh : current().pipelineLabel}</span></div>
              <code>profile: {current().id}<br />authority: false<br />source: accepted-manuscript<br />render: deterministic</code>
            </section>
          </aside>
        </section>

        <section class="wui-card publication-provenance" aria-label={zh() ? "出版 provenance" : "Publication provenance"}>
          <div class="publication-provenance-head"><div><small>PROVENANCE</small><h2>{zh() ? "出版流水线：每个派生物都能回到同一份接受正文。" : "Publication pipeline: every derivative resolves back to the same accepted manuscript."}</h2></div><span class="wui-badge wui-badge--soft">deterministic pipeline</span></div>
          <div class="publication-pipeline">
            <div class="publication-pipeline-node" data-kind="source"><span>✓</span><div><small>{zh() ? "接受正文" : "ACCEPTED"}</small><strong>{zh() ? "接稿原文" : "Accepted manuscript"}</strong><code>sha256 · exact</code></div></div>
            <span class="publication-pipeline-arrow">→</span>
            <div class="publication-pipeline-node" data-kind="ir"><span>IR</span><div><small>{zh() ? "出版 IR" : "PUBLICATION IR"}</small><strong>novelforge_publication_ir_v1</strong><code>schema-bound</code></div></div>
            <span class="publication-pipeline-arrow">→</span>
            <div class="publication-pipeline-node" data-kind="renderer"><span>⌘</span><div><small>{zh() ? "编译器" : "COMPILER"}</small><strong>publication/compiler.py</strong><code>format · layout · package · validate</code></div></div>
            <span class="publication-pipeline-arrow">→</span>
            <div class="publication-pipeline-node" data-kind="artifact"><span>{current().icon}</span><div><small>{zh() ? "派生物" : "ARTIFACT"}</small><strong>{zh() ? current().pipelineLabelZh : current().pipelineLabel}</strong><code>authority=false</code></div></div>
          </div>
          <div class="publication-contract-strip"><span>single manuscript truth</span><span>exact accepted text</span><span>replaceable presentation</span><span>provenance retained</span></div>
        </section>
      </main>

      <footer class="publication-footer page-width">
        <span>NovelForge · Publication Workbench</span>
        <span>{zh() ? "展示派生物，不伪造权威。 ✦" : "Preview derivatives without manufacturing authority. ✦"}</span>
      </footer>
    </div>
  );
}
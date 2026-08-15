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
  const [selected, setSelected] = createSignal(1);
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

  const sampleTitle = () => zh() ? "第三十七章 · 灯火落在纸上" : "Chapter 37 · Light on the page";
  const sampleParagraphs = () => zh()
    ? [
      "夜色压到窗沿时，桌上的最后一页终于安静下来。正文没有因为换了一种载体，就变成另一份故事。",
      "出版层只负责如何让它被阅读：屏幕有屏幕的行宽，纸面有纸面的页边，电子书把最终决定留给读者的设备。",
      "接受正文仍然是唯一的文本事实；这里看到的字号、行距、页码与装饰，全部属于可替换的派生表现。",
    ]
    : [
      "By the time night reached the window, the last page on the desk had finally gone quiet. A new medium did not turn the manuscript into a different story.",
      "The publication layer only decides how that text is read: screens own responsive measure, paper owns page geometry, and ebooks leave final typography to the reader's device.",
      "The accepted manuscript remains the single textual truth. Type size, leading, folios, and ornaments here are replaceable derived presentation.",
    ];

  return (
    <div class="site-shell product-entry publication-workbench-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <a href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </a>
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "出版导航" : "Publication navigation"}>
          <a class="wui-app-bar__link" href="/">{zh() ? "产品" : "Product"}</a>
          <a class="wui-app-bar__link" href="/architecture">{zh() ? "架构" : "Architecture"}</a>
          <a class="wui-app-bar__link active" href="/publication" aria-current="page">{zh() ? "出版" : "Publication"}</a>
          <a class="wui-app-bar__link" href="/docs">{zh() ? "知识库" : "Knowledge"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href="https://studio.novelforge.wei-dev.com" target="_blank" rel="noreferrer">✦ Studio</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact publication-workbench-main">
        <section class="publication-intro">
          <div>
            <div class="publication-badges">
              <span class="wui-badge wui-badge--soft">PUBLICATION WORKBENCH</span>
              <span class="wui-badge wui-badge--outline">authority=false</span>
              <span class="wui-badge wui-badge--outline">deterministic derivative</span>
            </div>
            <h1>{zh() ? "同一份接受正文，换的是载体，不是事实。" : "One accepted manuscript. Different surfaces, not different truth."}</h1>
            <p>{zh() ? "把出版页从“格式按钮”升级成真正的派生工作台：先选目标载体，再看阅读预览、profile token 与 provenance。所有控件只改变本地预览，不会改正文、Canon 或 Settlement。" : "Treat publication as a derivation workbench rather than a row of format buttons: choose a target surface, inspect the reading preview, profile tokens, and provenance. Every control changes local preview only; manuscript, Canon, and Settlement remain untouched."}</p>
          </div>
          <div class="publication-intro-actions">
            <a class="wui-button wui-button--soft" href="/docs">📚 {zh() ? "查看出版契约" : "Read publication contracts"}</a>
            <a class="wui-button wui-button--ghost" href="/architecture">⌘ {zh() ? "回到架构" : "Architecture"}</a>
          </div>
        </section>

        <section class="publication-profile-rail" aria-label={zh() ? "出版 profile" : "Publication profiles"}>
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
              <span class="publication-profile-arrow" aria-hidden="true">→</span>
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
                  <div class="publication-browser-chrome"><span /><span /><span /><strong>novel.example / chapter-37</strong></div>
                  <article class="publication-reading-page">
                    <span class="publication-preview-kicker">NOVELFORGE · WEB</span>
                    <h2>{sampleTitle()}</h2>
                    <For each={sampleParagraphs()}>{(paragraph) => <p>{paragraph}</p>}</For>
                    <div class="publication-chapter-nav"><span>← 36</span><span>37 / 64</span><span>38 →</span></div>
                  </article>
                </div>
              </Show>

              <Show when={current().id === "print"}>
                <div class="publication-print-preview">
                  <article class="publication-paper-page publication-paper-left">
                    <header><span>NovelForge</span><span>37</span></header>
                    <div class="publication-paper-body"><span class="publication-preview-kicker">CHAPTER 37</span><h2>{sampleTitle()}</h2><p>{sampleParagraphs()[0]}</p><p>{sampleParagraphs()[1]}</p></div>
                    <footer>184</footer>
                  </article>
                  <article class="publication-paper-page publication-paper-right">
                    <header><span>{sampleTitle()}</span><span>37</span></header>
                    <div class="publication-paper-body"><p>{sampleParagraphs()[2]}</p><div class="publication-print-ornament">✦</div></div>
                    <footer>185</footer>
                  </article>
                </div>
              </Show>

              <Show when={current().id === "epub"}>
                <div class="publication-ereader-preview">
                  <div class="publication-ereader-top"><span>‹</span><strong>NovelForge</strong><span>Aa</span></div>
                  <article class="publication-reading-page publication-ereader-page">
                    <span class="publication-preview-kicker">37 · EPUB 3.3</span>
                    <h2>{sampleTitle()}</h2>
                    <For each={sampleParagraphs()}>{(paragraph) => <p>{paragraph}</p>}</For>
                  </article>
                  <div class="publication-ereader-progress"><span style="width:58%" /><small>58%</small></div>
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
                <div><small>{zh() ? "派生 profile" : "DERIVATION PROFILE"}</small><h2>{zh() ? current().titleZh : current().title}</h2></div>
              </div>
              <p>{zh() ? current().summaryZh : current().summary}</p>
              <div class="publication-token-grid">
                <For each={current().tokens}>{(token) => <div><span>{zh() ? token.labelZh : token.label}</span><strong>{zh() ? (token.valueZh ?? token.value) : token.value}</strong></div>}</For>
              </div>
              <div class="publication-inspector-note"><span>ⓘ</span><p>{zh() ? "这些 token 描述的是展示 profile；上面的 slider 只是浏览器本地实验，不写入 manuscript，也不制造第二套 truth model。" : "These tokens describe a presentation profile. The sliders above are browser-local experiments; they do not write to the manuscript or create a second truth model."}</p></div>
            </section>

            <section class="wui-card publication-artifact-card">
              <small>{zh() ? "目标产物" : "TARGET ARTIFACT"}</small>
              <div><strong>{current().artifact}</strong><span>{zh() ? current().pipelineLabelZh : current().pipelineLabel}</span></div>
              <code>authority=false</code>
            </section>
          </aside>
        </section>

        <section class="wui-card publication-provenance" aria-label={zh() ? "出版 provenance" : "Publication provenance"}>
          <div class="publication-provenance-head"><div><small>PROVENANCE</small><h2>{zh() ? "每个派生物都能回答：它从哪份正文来的？" : "Every derivative should answer: which exact manuscript did it come from?"}</h2></div><span class="wui-badge wui-badge--soft">deterministic pipeline</span></div>
          <div class="publication-pipeline">
            <div class="publication-pipeline-node" data-kind="source"><span>✓</span><div><small>{zh() ? "输入" : "INPUT"}</small><strong>{zh() ? "接受正文" : "Accepted manuscript"}</strong><code>sha256 · exact</code></div></div>
            <span class="publication-pipeline-arrow">→</span>
            <div class="publication-pipeline-node" data-kind="ir"><span>IR</span><div><small>{zh() ? "中间表示" : "INTERMEDIATE"}</small><strong>novelforge_publication_ir_v1</strong><code>schema-bound</code></div></div>
            <span class="publication-pipeline-arrow">→</span>
            <div class="publication-pipeline-node" data-kind="renderer"><span>⌘</span><div><small>{zh() ? "渲染器" : "RENDERER"}</small><strong>publication/compiler.py</strong><code>deterministic</code></div></div>
            <span class="publication-pipeline-arrow">→</span>
            <div class="publication-pipeline-node" data-kind="artifact"><span>{current().icon}</span><div><small>{zh() ? "派生物" : "DERIVATIVE"}</small><strong>{zh() ? current().pipelineLabelZh : current().pipelineLabel}</strong><code>authority=false</code></div></div>
          </div>
          <div class="publication-contract-strip"><span>single manuscript truth</span><span>exact accepted text</span><span>replaceable presentation</span><span>provenance retained</span></div>
        </section>
      </main>

      <footer class="publication-footer page-width">
        <span>NovelForge · Publication Workbench</span>
        <span>{zh() ? "展示派生物，不伪造权威。" : "Preview derivatives without manufacturing authority."}</span>
      </footer>
    </div>
  );
}

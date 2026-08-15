import { For, createEffect, createSignal } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import type { Locale } from "./content";

type Props = { initialLocale: Locale };

type StartPath = {
  id: string;
  icon: string;
  eyebrowZh: string;
  eyebrowEn: string;
  titleZh: string;
  titleEn: string;
  bodyZh: string;
  bodyEn: string;
  href: string;
  external?: boolean;
  lane: "project" | "runtime" | "editorial" | "evidence";
};

const studioStartUrl = "https://studio.novelforge.wei-dev.com/start";

const paths: StartPath[] = [
  {
    id: "start-novel",
    icon: "✦",
    eyebrowZh: "从零开始",
    eyebrowEn: "START FRESH",
    titleZh: "开始一本小说",
    titleEn: "Start a novel",
    bodyZh: "进入 Studio 的新项目引导。先建立项目边界，再开始写，而不是把第一条消息直接当成世界观。",
    bodyEn: "Open Studio's new-project onboarding. Establish the project boundary first instead of turning the first prompt into accidental canon.",
    href: studioStartUrl,
    external: true,
    lane: "project",
  },
  {
    id: "open-project",
    icon: "⌂",
    eyebrowZh: "已有项目",
    eyebrowEn: "EXISTING PROJECT",
    titleZh: "打开现有项目",
    titleEn: "Open an existing project",
    bodyZh: "先在浏览器本地检查 manifest、Framework lock、attestation 与结构证据；文件不会上传。",
    bodyEn: "Inspect the manifest, exact Framework lock, attestation, and structural evidence locally in the browser. Files stay on your device.",
    href: "/inspect",
    lane: "runtime",
  },
  {
    id: "connect-agent",
    icon: "◈",
    eyebrowZh: "已有 Coding Agent",
    eyebrowEn: "BRING AN AGENT",
    titleZh: "接入我的 Agent",
    titleEn: "Use with my coding agent",
    bodyZh: "用 portable Agent Skill + versioned Host Bridge 接入 Claude Code、Codex、Cursor、OpenCode 或自定义宿主。",
    bodyEn: "Connect Claude Code, Codex, Cursor, OpenCode, or a custom host through the portable Agent Skill and versioned Host Bridge.",
    href: "/agents",
    lane: "editorial",
  },
  {
    id: "explore",
    icon: "▷",
    eyebrowZh: "先体验边界",
    eyebrowEn: "EXPLORE FIRST",
    titleZh: "先看看 NovelForge 怎么工作",
    titleEn: "Explore how NovelForge works",
    bodyZh: "用不调用模型、没有写权限的 Local Playground 看 Context、contracts、evidence 与结果如何串起来。",
    bodyEn: "Use the deterministic Local Playground to see Context, contracts, evidence, and results without model calls or write authority.",
    href: "/playground",
    lane: "evidence",
  },
];

function initialDark() {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export default function StartHubEntry(props: Props) {
  const [locale, setLocale] = createSignal<Locale>(props.initialLocale);
  const [dark, setDark] = createSignal(initialDark());
  const zh = () => locale() === "zh-CN";

  createEffect(() => {
    document.documentElement.lang = zh() ? "zh-CN" : "en";
    document.documentElement.dataset.locale = locale();
    document.documentElement.classList.toggle("dark", dark());
    localStorage.setItem("novelforge.locale", locale());
    localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
  });

  return (
    <div class="site-shell product-entry start-hub-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <a href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </a>
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "开始导航" : "Start navigation"}>
          <a class="wui-app-bar__link active" href="/start" aria-current="page">{zh() ? "开始" : "Start"}</a>
          <a class="wui-app-bar__link" href="/inspect">{zh() ? "检查项目" : "Inspect"}</a>
          <a class="wui-app-bar__link" href="/playground">Playground</a>
          <a class="wui-app-bar__link" href="/agents">{zh() ? "Agent 集成" : "Agents"}</a>
          <a class="wui-app-bar__link" href="/docs">{zh() ? "知识库" : "Docs"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href={studioStartUrl} target="_blank" rel="noreferrer">✦ {zh() ? "打开 Studio" : "Open Studio"}</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact start-hub-main">
        <section class="start-hub-hero" aria-labelledby="start-hub-title">
          <div class="start-hub-ribbon"><span aria-hidden="true">🎀</span><strong>{zh() ? "从这里开始" : "START HERE"}</strong></div>
          <div class="start-hub-hero-grid">
            <div class="start-hub-copy">
              <div class="start-hub-badges">
                <span class="wui-badge wui-badge--soft">product-first</span>
                <span class="wui-badge wui-badge--outline">local-first</span>
                <span class="wui-badge wui-badge--outline">authority-aware</span>
              </div>
              <h1 id="start-hub-title">{zh() ? "你今天想让 NovelForge 做什么？" : "What do you want to do with NovelForge?"}</h1>
              <p>{zh() ? "不需要先读完整个框架，也不需要先理解所有术语。选一个目标，NovelForge 会把你带到当前真实可用的最短路径。" : "You do not need to read the whole framework or learn every term first. Pick an outcome and NovelForge will route you to the shortest path that actually exists today."}</p>
              <div class="start-hub-trust">
                <span><b>✓</b>{zh() ? "不伪装未实现能力" : "No fake capabilities"}</span>
                <span><b>♡</b>{zh() ? "项目权威保持显式" : "Explicit project authority"}</span>
                <span><b>⌂</b>{zh() ? "本地项目不上传" : "Local projects stay local"}</span>
              </div>
            </div>
            <div class="start-hub-preview" aria-hidden="true">
              <div class="start-hub-cloud cloud-one">☁</div>
              <div class="start-hub-cloud cloud-two">☁</div>
              <div class="start-hub-thread">✦ · · · ♡ · · · ✧</div>
              <div class="start-hub-book">
                <span class="book-tab">PROJECT</span>
                <div class="book-page"><i>01</i><b>Project</b><small>manifest · lock</small></div>
                <div class="book-page"><i>02</i><b>Context</b><small>selected contracts</small></div>
                <div class="book-page"><i>03</i><b>Work</b><small>evidence · result</small></div>
                <span class="book-charm">🐰</span>
              </div>
            </div>
          </div>
        </section>

        <section class="start-paths" aria-labelledby="start-paths-title">
          <div class="start-section-heading">
            <div><small>{zh() ? "选择一条路径" : "CHOOSE A PATH"}</small><h2 id="start-paths-title">{zh() ? "目标先于工具。" : "Outcome first. Tool second."}</h2></div>
            <span class="start-kawaii" aria-hidden="true">(｡•̀ᴗ-)✧</span>
          </div>
          <div class="start-path-grid">
            <For each={paths}>{(path, index) => (
              <a
                class="start-path-card"
                data-lane={path.lane}
                data-intent={path.id}
                href={path.href}
                target={path.external ? "_blank" : undefined}
                rel={path.external ? "noreferrer" : undefined}
              >
                <div class="start-path-top"><span class="start-path-number">0{index() + 1}</span><span class="start-path-icon">{path.icon}</span></div>
                <small>{zh() ? path.eyebrowZh : path.eyebrowEn}</small>
                <h3>{zh() ? path.titleZh : path.titleEn}</h3>
                <p>{zh() ? path.bodyZh : path.bodyEn}</p>
                <span class="start-path-action">{path.external ? (zh() ? "打开 Studio ↗" : "Open Studio ↗") : (zh() ? "继续 →" : "Continue →")}</span>
              </a>
            )}</For>
          </div>
        </section>

        <section class="start-hub-flow" aria-label={zh() ? "产品路径" : "Product path"}>
          <div class="start-flow-title"><span>🧵</span><div><small>{zh() ? "共同的产品边界" : "SHARED PRODUCT BOUNDARY"}</small><strong>{zh() ? "不管从哪里进入，权威与状态都不会偷偷换主人。" : "Whichever path you choose, authority and state do not silently change owners."}</strong></div></div>
          <div class="start-flow-track">
            <div><span>01</span><strong>{zh() ? "选择目标" : "Choose outcome"}</strong><small>{zh() ? "新建 / 检查 / Agent / 体验" : "new · inspect · agent · explore"}</small></div>
            <b>→</b>
            <div><span>02</span><strong>{zh() ? "发现能力" : "Discover capability"}</strong><small>manifest · lock · describe</small></div>
            <b>→</b>
            <div><span>03</span><strong>{zh() ? "执行工作" : "Do the work"}</strong><small>context · contract · evidence</small></div>
            <b>→</b>
            <div><span>04</span><strong>{zh() ? "明确写入" : "Explicit write"}</strong><small>authority ≠ capability</small></div>
          </div>
        </section>

        <section class="start-hub-footer-callout">
          <div><span aria-hidden="true">♡</span><div><small>{zh() ? "还不确定？" : "NOT SURE YET?"}</small><h2>{zh() ? "先在 Playground 看一次完整流程，再决定要不要接入项目。" : "Run one complete Playground flow before deciding how deeply to integrate."}</h2></div></div>
          <div class="start-hub-footer-actions"><a class="wui-button wui-button--soft" href="/playground">▷ Playground</a><a class="wui-button wui-button--ghost" href="/docs/why-novelforge">📚 {zh() ? "为什么是 NovelForge" : "Why NovelForge"}</a></div>
        </section>
      </main>

      <footer class="site-footer start-hub-footer">
        <div class="page-width footer-grid">
          <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{zh() ? "先选你要完成的事，再进入需要的复杂度。" : "Choose the outcome first, then enter only the complexity you need."}</p></div>
          <div class="footer-links"><a href="/inspect">{zh() ? "检查项目" : "Project Inspector"}</a><a href="/playground">Local Playground</a><a href="/agents">{zh() ? "Agent 集成" : "Agent Integration"}</a></div>
          <div class="footer-links"><a href="/docs">{zh() ? "知识库" : "Docs"}</a><a href="/">{zh() ? "返回产品首页" : "Product home"}</a></div>
        </div>
      </footer>
    </div>
  );
}

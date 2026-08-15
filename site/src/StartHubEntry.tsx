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
    bodyZh: "进入 Studio 的新项目引导，先建立项目边界，再开始创作。",
    bodyEn: "Open Studio onboarding, establish the project boundary, then start creating.",
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
    bodyZh: "在浏览器本地检查 manifest、Framework lock、attestation 与项目结构。",
    bodyEn: "Inspect the manifest, Framework lock, attestation, and project structure locally in your browser.",
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
    bodyZh: "通过 portable Agent Skill 与 Host Bridge 接入现有 coding agent。",
    bodyEn: "Connect an existing coding agent through the portable Agent Skill and Host Bridge.",
    href: "/agents",
    lane: "editorial",
  },
  {
    id: "explore",
    icon: "▷",
    eyebrowZh: "先体验",
    eyebrowEn: "EXPLORE FIRST",
    titleZh: "看看 NovelForge 怎么工作",
    titleEn: "Explore how NovelForge works",
    bodyZh: "用 Local Playground 看 Context、contracts、evidence 与结果如何串起来。",
    bodyEn: "Use the Local Playground to see how Context, contracts, evidence, and results connect.",
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
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "产品导航" : "Product navigation"}>
          <a class="wui-app-bar__link" href="/">{zh() ? "产品" : "Product"}</a>
          <a class="wui-app-bar__link" href="/architecture">{zh() ? "架构" : "Architecture"}</a>
          <a class="wui-app-bar__link" href="/publication">{zh() ? "出版" : "Publication"}</a>
          <a class="wui-app-bar__link" href="/docs">{zh() ? "知识库" : "Knowledge"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href={studioStartUrl} target="_blank" rel="noreferrer">✦ {zh() ? "打开 Studio" : "Open Studio"}</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact start-hub-main">
        <section class="start-hub-hero" aria-labelledby="start-hub-title">
          <p class="eyebrow">{zh() ? "从这里开始" : "START HERE"}</p>
          <h1 id="start-hub-title">{zh() ? "你想先做什么？" : "What do you want to do first?"}</h1>
          <p>{zh() ? "不用先理解整套框架。选一个目标，直接进入当前真正可用的路径。" : "You do not need to learn the whole framework first. Pick an outcome and go straight to the path that actually exists today."}</p>
        </section>

        <section class="start-paths" aria-labelledby="start-paths-title">
          <div class="start-section-heading">
            <div>
              <small>{zh() ? "四个入口" : "FOUR STARTING POINTS"}</small>
              <h2 id="start-paths-title">{zh() ? "目标先于工具。" : "Outcome first. Tool second."}</h2>
            </div>
          </div>
          <div class="start-path-grid">
            <For each={paths}>{(path) => (
              <a
                class="start-path-card"
                data-lane={path.lane}
                data-intent={path.id}
                href={path.href}
                target={path.external ? "_blank" : undefined}
                rel={path.external ? "noreferrer" : undefined}
              >
                <div class="start-path-top">
                  <span class="start-path-icon" aria-hidden="true">{path.icon}</span>
                  <small>{zh() ? path.eyebrowZh : path.eyebrowEn}</small>
                  <span class="start-path-arrow" aria-hidden="true">{path.external ? "↗" : "→"}</span>
                </div>
                <h3>{zh() ? path.titleZh : path.titleEn}</h3>
                <p>{zh() ? path.bodyZh : path.bodyEn}</p>
              </a>
            )}</For>
          </div>
        </section>

        <section class="start-hub-boundary" aria-label={zh() ? "产品边界" : "Product boundary"}>
          <span>✓ {zh() ? "不伪装未实现能力" : "No fake capabilities"}</span>
          <span>⌂ {zh() ? "本地项目不上传" : "Local projects stay local"}</span>
          <span>◇ authority ≠ capability</span>
          <a href="/docs/why-novelforge">{zh() ? "为什么是 NovelForge →" : "Why NovelForge →"}</a>
        </section>
      </main>

      <footer class="site-footer start-hub-footer">
        <div class="page-width footer-grid">
          <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{zh() ? "先选目标，再进入需要的复杂度。" : "Choose the outcome first, then enter only the complexity you need."}</p></div>
          <div class="footer-links"><a href="/inspect">{zh() ? "检查项目" : "Project Inspector"}</a><a href="/playground">Local Playground</a><a href="/agents">{zh() ? "Agent 集成" : "Agent Integration"}</a></div>
          <div class="footer-links"><a href="/docs">{zh() ? "知识库" : "Docs"}</a><a href="/">{zh() ? "返回产品首页" : "Product home"}</a></div>
        </div>
      </footer>
    </div>
  );
}

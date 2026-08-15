import { createEffect, createSignal } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import type { Locale } from "./content";
import LocalPlayground from "./LocalPlayground";

type Props = { initialLocale: Locale };

function initialDark() {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export default function LocalPlaygroundEntry(props: Props) {
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
    <div class="site-shell product-entry playground-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <a href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </a>
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "Playground 导航" : "Playground navigation"}>
          <a class="wui-app-bar__link" href="/">{zh() ? "产品" : "Product"}</a>
          <a class="wui-app-bar__link" href="/inspect">{zh() ? "检查项目" : "Inspect"}</a>
          <a class="wui-app-bar__link active" href="/playground" aria-current="page">Playground</a>
          <a class="wui-app-bar__link" href={zh() ? "/docs/production-pipeline" : "/docs/en/production-pipeline"}>{zh() ? "生产流水线" : "Pipeline"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href="https://studio.novelforge.wei-dev.com" target="_blank" rel="noreferrer">✦ Studio</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact playground-main">
        <LocalPlayground locale={locale()} />
      </main>

      <footer class="site-footer playground-footer">
        <div class="page-width footer-grid">
          <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{zh() ? "本页是 deterministic preview，不调用模型。" : "This surface is a deterministic preview and makes no model calls."}</p></div>
          <div class="footer-links"><a href={zh() ? "/docs/production-pipeline" : "/docs/en/production-pipeline"}>{zh() ? "生产流水线" : "Production pipeline"}</a><a href={zh() ? "/docs/framework-skill" : "/docs/en/framework-skill"}>Skill Contract</a></div>
          <div class="footer-links"><a href="/inspect">{zh() ? "检查项目" : "Inspect project"}</a><a href="/">{zh() ? "返回产品站" : "Back to product"}</a></div>
        </div>
      </footer>
    </div>
  );
}

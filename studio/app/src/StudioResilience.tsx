import { ErrorBoundary, type JSX } from "solid-js";

function zh() {
  const locale = document.documentElement.dataset.locale;
  if (locale === "zh-CN") return true;
  if (locale === "en-US") return false;
  return navigator.language.toLowerCase().startsWith("zh");
}

export function StudioSkipLink() {
  return <a class="nf-studio-skip-link" href="#main-content">{zh() ? "跳到主要内容" : "Skip to main content"}</a>;
}

export function StudioFailureBoundary(props: { children: JSX.Element }) {
  return (
    <ErrorBoundary fallback={(error, reset) => (
      <main id="main-content" class="nf-studio-resilience" role="alert">
        <section class="nf-studio-resilience-card">
          <span aria-hidden="true">♡</span>
          <small>Quillframe Studio · UI recovery</small>
          <h1>{zh() ? "Studio 没有完成这次渲染。" : "Studio did not finish this render."}</h1>
          <p>{zh() ? "这只是界面故障，不会自动产生 Canon、Settlement 或 Framework 写入。可以重试，或返回 Studio 起点。" : "This is a UI failure only; it does not create Canon, Settlement, or Framework writes. Retry or return to the Studio start."}</p>
          <details>
            <summary>{zh() ? "技术信息" : "Technical details"}</summary>
            <code>{error instanceof Error ? error.message : String(error)}</code>
          </details>
          <div>
            <button class="wui-button wui-button--solid" type="button" onClick={reset}>{zh() ? "重新尝试" : "Try again"}</button>
            <a class="wui-button wui-button--soft" href="/">{zh() ? "返回 Studio" : "Return to Studio"}</a>
          </div>
        </section>
      </main>
    )}>
      {props.children}
    </ErrorBoundary>
  );
}

export function StudioRouteLoading() {
  return <div class="nf-studio-route-loading" role="status" aria-live="polite"><span aria-hidden="true">✦</span>{zh() ? "正在打开工作区…" : "Opening workspace…"}</div>;
}

export function StudioNotFound() {
  return (
    <section class="nf-page nf-studio-not-found" aria-labelledby="studio-not-found-title">
      <div class="nf-page-intro">
        <div>
          <span class="nf-eyebrow">404 · Studio route</span>
          <h1 id="studio-not-found-title">{zh() ? "这个 Studio 页面不存在。" : "This Studio page does not exist."}</h1>
          <p>{zh() ? "地址没有匹配当前 Studio 的任何工作区。你可以回到创作桌面或项目入口。" : "The address does not match a current Studio workspace. Return to the desk or project entry."}</p>
        </div>
        <div class="nf-resilience-actions">
          <a class="wui-button wui-button--solid" href="/">{zh() ? "回到创作桌面" : "Back to desk"}</a>
          <a class="wui-button wui-button--soft" href="/project">{zh() ? "打开项目" : "Open project"}</a>
        </div>
      </div>
    </section>
  );
}

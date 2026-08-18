import { ErrorBoundary, type JSX } from "solid-js";

function prefersChinese() {
  const locale = document.documentElement.dataset.locale;
  if (locale === "zh-CN") return true;
  if (locale === "en-US") return false;
  return navigator.language.toLowerCase().startsWith("zh");
}

export function ProductFailureBoundary(props: { children: JSX.Element }) {
  return (
    <ErrorBoundary fallback={(error, reset) => (
      <main id="main-content" class="nf-resilience-page page-width" role="alert">
        <section class="nf-resilience-card">
          <span class="nf-resilience-mark" aria-hidden="true">♡</span>
          <p class="nf-resilience-eyebrow">Quillframe · UI recovery</p>
          <h1>{prefersChinese() ? "这个界面没有正常完成渲染。" : "This surface did not finish rendering."}</h1>
          <p>{prefersChinese() ? "你的项目和正典状态没有因此被修改。可以重新尝试渲染，或返回产品首页。" : "No Project or Canon state was changed by this UI failure. Retry the render or return to the product home."}</p>
          <details>
            <summary>{prefersChinese() ? "技术信息" : "Technical details"}</summary>
            <code>{error instanceof Error ? error.message : String(error)}</code>
          </details>
          <div class="nf-resilience-actions">
            <button class="wui-button wui-button--solid" type="button" onClick={reset}>{prefersChinese() ? "重新尝试" : "Try again"}</button>
            <a class="wui-button wui-button--soft" href="/">{prefersChinese() ? "返回首页" : "Return home"}</a>
          </div>
        </section>
      </main>
    )}>
      {props.children}
    </ErrorBoundary>
  );
}

export function ProductNotFound() {
  const zh = prefersChinese();
  return (
    <main id="main-content" class="nf-resilience-page page-width">
      <section class="nf-resilience-card nf-not-found">
        <span class="nf-resilience-mark" aria-hidden="true">404</span>
        <p class="nf-resilience-eyebrow">Quillframe · route</p>
        <h1>{zh ? "这里没有这个页面。" : "There is no page here."}</h1>
        <p>{zh ? "这个地址不属于当前 Product Site。可以返回产品首页，或继续查看架构与知识库。" : "This address is not part of the current Product Site. Return home or continue with Architecture and Knowledge."}</p>
        <div class="nf-resilience-actions">
          <a class="wui-button wui-button--solid" href="/">{zh ? "返回首页" : "Home"}</a>
          <a class="wui-button wui-button--soft" href="/architecture">{zh ? "查看架构" : "Architecture"}</a>
          <a class="wui-button wui-button--ghost" href={zh ? "/docs" : "/docs/en"}>{zh ? "知识库" : "Knowledge"}</a>
        </div>
      </section>
    </main>
  );
}

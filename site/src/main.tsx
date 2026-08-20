import { render } from "solid-js/web";
import ProductApp from "./ProductApp";
import { ProductFailureBoundary, ProductNotFound } from "./ProductResilience";
import "./styles/index.css";

const root = document.getElementById("root");
const weiUiUrl = "https://ui.wei-dev.com/";

document.documentElement.dataset.experience = "story-loom-kawaii-atelier-v5";

if (!root) {
  throw new Error("Quillframe Product Site root element is missing");
}

const productRoutes = new Set([
  "/",
  "/product",
  "/studio",
  "/architecture",
  "/publication",
  "/inspect",
  "/playground",
  "/agents",
  "/changelog",
]);

function normalizedPath() {
  const path = window.location.pathname.replace(/\/+$/, "");
  return path || "/";
}

function installCrossAppNavigationGuard() {
  document.addEventListener("click", (event) => {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.altKey ||
      event.ctrlKey ||
      event.shiftKey
    ) {
      return;
    }

    const target = event.target;
    const anchor = target instanceof Element ? target.closest("a[href]") : null;
    if (!(anchor instanceof HTMLAnchorElement) || anchor.target || anchor.hasAttribute("download")) {
      return;
    }

    const url = new URL(anchor.href, window.location.href);
    const isDocsApp = url.origin === window.location.origin && /^\/docs(?:\/|$)/.test(url.pathname);
    if (!isDocsApp) {
      return;
    }

    // @solidjs/router intercepts same-origin anchors by default. Docs are a
    // separate Astro/Starlight application, so crossing this boundary must be
    // a real document navigation instead of an in-SPA history.pushState().
    event.preventDefault();
    event.stopImmediatePropagation();
    window.location.assign(url.href);
  }, true);
}

function installWeiUiCredit() {
  const footerColumns = document.querySelectorAll(".site-footer .footer-links");
  const creditHost = footerColumns.item(footerColumns.length - 1);
  if (!(creditHost instanceof HTMLElement) || creditHost.querySelector("[data-weiui-credit]")) {
    return;
  }

  const credit = document.createElement("a");
  credit.href = weiUiUrl;
  credit.target = "_blank";
  credit.rel = "noopener noreferrer";
  credit.dataset.weiuiCredit = "true";
  credit.textContent = "Powered by WeiUI ↗";
  creditHost.append(credit);
}

installCrossAppNavigationGuard();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => undefined);
  }, { once: true });
}

render(() => (
  <ProductFailureBoundary>
    {productRoutes.has(normalizedPath()) ? <ProductApp /> : <ProductNotFound />}
  </ProductFailureBoundary>
), root);

installWeiUiCredit();

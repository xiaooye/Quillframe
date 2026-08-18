import "./appearance-v5";
import { render } from "solid-js/web";
import ProductApp from "./ProductApp";
import { ProductFailureBoundary, ProductNotFound } from "./ProductResilience";
import "./styles/index.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Quillframe Product Site root element is missing");
}

const productRoutes = new Set([
  "/",
  "/start",
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

installCrossAppNavigationGuard();

render(() => (
  <ProductFailureBoundary>
    {productRoutes.has(normalizedPath()) ? <ProductApp /> : <ProductNotFound />}
  </ProductFailureBoundary>
), root);

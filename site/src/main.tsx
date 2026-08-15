import "./appearance-v5";
import { render } from "solid-js/web";
import App from "./App";
import LocalPlaygroundEntry from "./LocalPlaygroundEntry";
import ProjectInspectorEntry from "./ProjectInspectorEntry";
import "./styles/site.css";
import "./styles/product-contract.css";
import "./styles/showcase.css";
import "./styles/atelier.css";
import "./styles/atelier-photos.css";
import "./styles/atelier-clean-canvas.css";
import "./styles/project-inspector.css";
import "./styles/local-playground.css";

// The launcher emits a synthetic Ctrl+K event on document. Real keyboard events
// already bubble to window; only bridge the synthetic event into the AppShell
// listener so every search entry opens the same WeiUI command palette.
document.addEventListener("keydown", (event) => {
  if (!event.isTrusted && (event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase() === "k") {
    window.dispatchEvent(new KeyboardEvent("keydown", {
      key: "k",
      ctrlKey: event.ctrlKey,
      metaKey: event.metaKey,
    }));
  }
});

function preferredLocale(): "zh-CN" | "en-US" {
  const datasetLocale = document.documentElement.dataset.locale;
  if (datasetLocale === "zh-CN" || datasetLocale === "en-US") return datasetLocale;
  const saved = localStorage.getItem("novelforge.locale");
  if (saved === "zh-CN" || saved === "en-US") return saved;
  return navigator.language.toLocaleLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function localizedDocsTarget(url: string | URL | null | undefined): URL | undefined {
  if (url == null) return undefined;

  const target = new URL(url instanceof URL ? url.href : url, window.location.href);
  if (target.origin !== window.location.origin) return undefined;
  if (target.pathname !== "/docs" && !target.pathname.startsWith("/docs/")) return undefined;

  const alreadyEnglish = target.pathname === "/docs/en" || target.pathname.startsWith("/docs/en/");
  if (preferredLocale() === "en-US" && !alreadyEnglish) {
    const suffix = target.pathname.slice("/docs".length);
    target.pathname = `/docs/en${suffix || "/"}`;
  }

  return target;
}

function handOffToDocs(target: URL) {
  window.location.assign(target.href);
}

// @solidjs/router owns product-site navigation. Documentation is a separate,
// static-first Starlight application under /docs, so any SPA attempt to enter
// that namespace must become a real document navigation instead of mounting a
// second documentation renderer inside the product app.
document.addEventListener("click", (event) => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const origin = event.target;
  if (!(origin instanceof Element)) return;
  const anchor = origin.closest("a[href]");
  if (!(anchor instanceof HTMLAnchorElement) || anchor.target === "_blank" || anchor.hasAttribute("download")) return;

  const target = localizedDocsTarget(anchor.href);
  if (!target) return;

  event.preventDefault();
  event.stopPropagation();
  handOffToDocs(target);
}, true);

const historyMarker = "__novelforgeDocsHandoff";
const markedHistory = window.history as History & { [historyMarker]?: boolean };

if (!markedHistory[historyMarker]) {
  markedHistory[historyMarker] = true;

  const originalPushState = window.history.pushState.bind(window.history);
  window.history.pushState = ((data: unknown, unused: string, url?: string | URL | null) => {
    const docsTarget = localizedDocsTarget(url);
    if (docsTarget) {
      handOffToDocs(docsTarget);
      return;
    }
    originalPushState(data, unused, url);
  }) as History["pushState"];

  const originalReplaceState = window.history.replaceState.bind(window.history);
  window.history.replaceState = ((data: unknown, unused: string, url?: string | URL | null) => {
    const docsTarget = localizedDocsTarget(url);
    if (docsTarget) {
      handOffToDocs(docsTarget);
      return;
    }
    originalReplaceState(data, unused, url);
  }) as History["replaceState"];
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

const path = window.location.pathname.replace(/\/+$/, "") || "/";
render(
  () => path === "/inspect"
    ? <ProjectInspectorEntry initialLocale={preferredLocale()} />
    : path === "/playground"
      ? <LocalPlaygroundEntry initialLocale={preferredLocale()} />
      : <App />,
  root,
);

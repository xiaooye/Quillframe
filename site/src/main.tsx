import "./appearance-v5";
import { render } from "solid-js/web";
import App from "./App";
import AgentIntegrationEntry from "./AgentIntegrationEntry";
import ArchitectureExplorerEntry from "./ArchitectureExplorerEntry";
import PublicationWorkbenchEntry from "./PublicationWorkbenchEntry";
import LocalPlaygroundEntry from "./LocalPlaygroundEntry";
import ProjectInspectorEntry from "./ProjectInspectorEntry";
import StartHubEntry from "./StartHubEntry";
import "./styles/site.css";
import "./styles/product-contract.css";
import "./styles/showcase.css";
import "./styles/atelier.css";
import "./styles/atelier-photos.css";
import "./styles/atelier-clean-canvas.css";
import "./styles/project-inspector.css";
import "./styles/local-playground.css";
import "./styles/architecture-explorer.css";
import "./styles/publication-workbench.css";
import "./styles/agent-integration.css";
import "./styles/agent-host-profiles.css";
import "./styles/start-hub.css";
import "./styles/kawaii-surfaces.css";
import "./styles/start-hub-kawaii.css";

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

const standaloneProductPaths = new Set(["/start", "/inspect", "/playground", "/agents", "/architecture", "/publication"]);

function standaloneProductTarget(url: string | URL | null | undefined): URL | undefined {
  if (url == null) return undefined;
  const target = new URL(url instanceof URL ? url.href : url, window.location.href);
  if (target.origin !== window.location.origin) return undefined;
  const normalized = target.pathname.replace(/\/+$/, "") || "/";
  return standaloneProductPaths.has(normalized) ? target : undefined;
}

function handoffTarget(url: string | URL | null | undefined): URL | undefined {
  return localizedDocsTarget(url) ?? standaloneProductTarget(url);
}

function handOff(target: URL) {
  window.location.assign(target.href);
}

// @solidjs/router owns the main product SPA. Documentation and the heavier
// browser-native product tools are separate static entry surfaces, so any SPA
// attempt to enter one of those namespaces becomes a real document navigation.
document.addEventListener("click", (event) => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const origin = event.target;
  if (!(origin instanceof Element)) return;
  const anchor = origin.closest("a[href]");
  if (!(anchor instanceof HTMLAnchorElement) || anchor.target === "_blank" || anchor.hasAttribute("download")) return;

  const target = handoffTarget(anchor.href);
  if (!target) return;

  event.preventDefault();
  event.stopPropagation();
  handOff(target);
}, true);

const historyMarker = "__novelforgeSurfaceHandoff";
const markedHistory = window.history as History & { [historyMarker]?: boolean };

if (!markedHistory[historyMarker]) {
  markedHistory[historyMarker] = true;

  const originalPushState = window.history.pushState.bind(window.history);
  window.history.pushState = ((data: unknown, unused: string, url?: string | URL | null) => {
    const target = handoffTarget(url);
    if (target) {
      handOff(target);
      return;
    }
    originalPushState(data, unused, url);
  }) as History["pushState"];

  const originalReplaceState = window.history.replaceState.bind(window.history);
  window.history.replaceState = ((data: unknown, unused: string, url?: string | URL | null) => {
    const target = handoffTarget(url);
    if (target) {
      handOff(target);
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
  () => path === "/start"
    ? <StartHubEntry initialLocale={preferredLocale()} />
    : path === "/inspect"
      ? <ProjectInspectorEntry initialLocale={preferredLocale()} />
      : path === "/playground"
        ? <LocalPlaygroundEntry initialLocale={preferredLocale()} />
        : path === "/agents"
          ? <AgentIntegrationEntry initialLocale={preferredLocale()} />
          : path === "/architecture"
            ? <ArchitectureExplorerEntry initialLocale={preferredLocale()} />
            : path === "/publication"
              ? <PublicationWorkbenchEntry initialLocale={preferredLocale()} />
              : <App />,
  root,
);

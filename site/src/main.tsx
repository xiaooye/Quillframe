import "./appearance-v5";
import { Show, createEffect, createSignal, onCleanup, onMount } from "solid-js";
import { Portal, render } from "solid-js/web";
import App from "./App";
import { KnowledgeDocumentPage, KnowledgeExplorer } from "./KnowledgeExperience";
import type { KnowledgeLocale } from "./knowledge";
import "./styles/site.css";
import "./styles/product-contract.css";
import "./styles/showcase.css";
import "./styles/atelier.css";
import "./styles/atelier-photos.css";
import "./styles/atelier-clean-canvas.css";
import "./styles/knowledge-experience.css";

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

const locationEvent = "novelforge:locationchange";
const historyMarker = "__novelforgeHistoryWrapped";
const markedHistory = window.history as History & { [historyMarker]?: boolean };

if (!markedHistory[historyMarker]) {
  markedHistory[historyMarker] = true;
  for (const methodName of ["pushState", "replaceState"] as const) {
    const original = window.history[methodName].bind(window.history);
    window.history[methodName] = ((...args: Parameters<History[typeof methodName]>) => {
      const result = original(...args);
      window.dispatchEvent(new Event(locationEvent));
      return result;
    }) as History[typeof methodName];
  }
}

function currentLocale(): KnowledgeLocale {
  const datasetLocale = document.documentElement.dataset.locale;
  if (datasetLocale === "zh-CN" || datasetLocale === "en-US") return datasetLocale;
  const saved = localStorage.getItem("novelforge.locale");
  if (saved === "zh-CN" || saved === "en-US") return saved;
  return navigator.language.toLocaleLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function KnowledgePortal() {
  const [mount, setMount] = createSignal<HTMLElement>();
  const [path, setPath] = createSignal(window.location.pathname);
  const [locale, setLocale] = createSignal<KnowledgeLocale>(currentLocale());

  const syncPath = () => setPath(window.location.pathname);

  onMount(() => {
    setMount(document.getElementById("main-content") ?? undefined);
    window.addEventListener("popstate", syncPath);
    window.addEventListener(locationEvent, syncPath);

    const observer = new MutationObserver(() => setLocale(currentLocale()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-locale", "lang"] });

    onCleanup(() => {
      observer.disconnect();
      window.removeEventListener("popstate", syncPath);
      window.removeEventListener(locationEvent, syncPath);
    });
  });

  const docsActive = () => path() === "/docs" || path().startsWith("/docs/");
  const docId = () => {
    if (!path().startsWith("/docs/")) return undefined;
    const value = path().slice("/docs/".length).split("/")[0];
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  };

  createEffect(() => {
    if (docsActive()) document.documentElement.dataset.knowledgeExperience = "journey-v1";
    else delete document.documentElement.dataset.knowledgeExperience;
  });

  onCleanup(() => {
    delete document.documentElement.dataset.knowledgeExperience;
  });

  return (
    <Show when={docsActive() && mount()}>
      <Portal mount={mount()!}>
        <div class="knowledge-v2-portal">
          <Show when={docId()} fallback={<KnowledgeExplorer locale={locale()} />}>
            {(id) => <KnowledgeDocumentPage locale={locale()} docId={id()} />}
          </Show>
        </div>
      </Portal>
    </Show>
  );
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

render(() => <><App /><KnowledgePortal /></>, root);

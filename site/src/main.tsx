import { render } from "solid-js/web";
import App from "./App";
import "./styles/site.css";
import "./styles/showcase.css";

const appearanceMigrationKey = "novelforge.product-entry.v4.appearance-migrated";
if (!localStorage.getItem(appearanceMigrationKey)) {
  localStorage.setItem("novelforge.appearance", "light");
  localStorage.setItem(appearanceMigrationKey, "true");
}

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

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

render(() => <App />, root);

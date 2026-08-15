import "./appearance-v5";
import { render } from "solid-js/web";
import App from "./App";
import "./styles/site.css";
import "./styles/product-contract.css";
import "./styles/showcase.css";
import "./styles/atelier.css";
import "./styles/atelier-photos.css";

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
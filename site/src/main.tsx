import "./appearance-v5";
import { render } from "solid-js/web";
import ProductApp from "./ProductApp";
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
import "./styles/kawaii-surfaces.css";
import "./styles/tool-workbench-kawaii.css";
import "./styles/product-surface.css";
import "./styles/unified-product-app.css";
import "./styles/surface-audit.css";
import "./styles/embedded-features.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

render(() => <ProductApp />, root);

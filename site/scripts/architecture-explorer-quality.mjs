#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const surface = read("src/ProductSurface.tsx");
const index = read("src/styles/index.css");
const architectureCss = read("src/styles/architecture-explorer.css");
const sharedRouteCss = read("src/styles/unified-product-app.css");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const semanticOrder = ["project", "manager", "context", "worker", "gate", "settlement", "publication"];
let previousIndex = -1;
for (const node of semanticOrder) {
  const marker = `id: "${node}"`;
  const currentIndex = app.indexOf(marker);
  check(currentIndex >= 0, `architecture explorer missing ${node} node`);
  check(currentIndex > previousIndex, `architecture semantic order drifted at ${node}`);
  previousIndex = currentIndex;
}

for (const contract of ["quillframe_project_v1_0", "quillframe_project_context_v1_0", "manifest_fingerprint", ".quillframe/data", "scope=novel", "quillframe_host_capabilities_v1", "quillframe_context_inspector_v2", "quillframe_run_receipt_v1", "quillframe_production_readiness_v1", "quillframe_publication_manifest_v1"]) {
  check(app.includes(contract), `architecture explorer missing public contract ${contract}`);
}
const legacyMarkers = [["quillframe", "project", "resolution", "v1"].join("_"), ["quillframe", "lock", "json"].join("."), ["framework", "attestation", "json"].join("."), ["project", "schema", "version"].join("_")];
for (const legacy of legacyMarkers) {
  check(!app.includes(legacy), `architecture explorer retains legacy contract ${legacy}`);
}

check(app.includes('<Route path="/architecture" component={ArchitecturePage}'), "shared ProductApp must expose /architecture");
check(app.includes("function ProductShell") && app.includes("<Router root={ProductShell}>"), "architecture must live inside the shared Router shell");
check(app.includes("ProductSurfaceHero") && app.includes("architecture-hero-path"), "architecture must use the shared hero frame with an architecture-specific visual slot");
check(app.includes("architectureNodes.map") && app.includes("<For each={architectureNodes}>"), "hero path and execution path must consume the same architectureNodes semantic source");
check(app.includes("Project → Manager → Context → Worker → Gate → Settlement → Publication"), "architecture hero must preserve the canonical seven-step semantic sequence");
check(app.includes("authority=false"), "architecture preview must state its non-authoritative boundary");
check(app.includes("This is not a real Core execution") && app.includes("不调用模型"), "architecture simulation must be explicitly identified as a deterministic preview");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(app), "product app must not add idle timers or frame loops");
check(main.includes('import ProductApp from "./ProductApp"') && !main.includes("standaloneProductPaths"), "main must mount one shared ProductApp without standalone architecture handoff");
check(main.includes('import "./styles/index.css"'), "main must load the single Product stylesheet entrypoint");
check(index.includes('@import "./architecture-explorer.css"') && index.includes('@import "./unified-product-app.css"'), "architecture shared and feature styles must load through the Product CSS entrypoint");
check(index.indexOf('architecture-explorer.css') < index.indexOf('readability.css'), "architecture route styling must precede cross-cutting readability hardening");
check(surface.includes("product-surface-hero"), "shared ProductSurfaceHero primitive must remain present");

check(architectureCss.includes(".architecture-flow") && architectureCss.includes(".architecture-detail-grid") && architectureCss.includes(".architecture-trace-list"), "architecture explorer must retain flow, inspector, and trace surfaces");
check(architectureCss.includes("grid-template-columns: repeat(7, minmax(0, 1fr))"), "desktop execution path must use seven stable equal step columns");
check(architectureCss.includes("grid-template-columns: repeat(4, minmax(0, 1fr))"), "tablet execution path must provide a 4+3 semantic reflow");
check(architectureCss.includes("grid-template-columns: minmax(0, 1fr)"), "phone execution path must collapse to one semantic column");
check(architectureCss.includes("grid-template-columns: minmax(0, 1fr) var(--architecture-connector)"), "each architecture step must own a content column and connector column");
check(architectureCss.includes(".architecture-node::after") && architectureCss.includes("grid-column: 2") && architectureCss.includes("place-self: center"), "connectors must participate in the node grid and remain vertically centered");
check(architectureCss.includes(".architecture-node:last-child::after { content: none; }"), "the final Publication step must not render a trailing connector");
check(architectureCss.includes("word-break: normal") && architectureCss.includes("hyphens: none"), "architecture copy must prefer natural words instead of destructive narrow-column breaks");
check(!architectureCss.includes(".architecture-node + .architecture-node"), "architecture layout must not use per-card sibling margin hacks");
check(!architectureCss.includes("overflow-x: auto") && !architectureCss.includes("scrollbar-width"), "architecture execution path must not depend on horizontal scrolling");
check(!architectureCss.includes("right: -15px") && !architectureCss.includes("translateY(-50%)"), "architecture connectors must not use absolute-position drift compensation");
check(!architectureCss.includes('data-run-state="current"] { transform'), "current run state must not translate individual nodes out of alignment");
check(!architectureCss.includes("-webkit-line-clamp"), "architecture node copy must not be line-clamped to fit narrow cards");
check(!architectureCss.includes("!important"), "architecture route owner must not use specificity escape hatches");
check(!sharedRouteCss.includes(".architecture-entry .architecture-flow") && !sharedRouteCss.includes(".architecture-entry .architecture-node"), "shared route composition must not retain a competing architecture rail owner");
check(architectureCss.includes("@media (max-width: 1120px)") && architectureCss.includes("@media (max-width: 760px)"), "architecture explorer must retain explicit tablet and phone responsive contracts");

if (failures.length) {
  for (const failure of failures) console.error(`architecture-explorer-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_architecture_explorer_quality_v4",
    status: "pass",
    shell: "shared_product_app",
    css_entrypoint: "index.css",
    shared_surface_hero: true,
    semantic_order: semanticOrder,
    nodes: 7,
    connector_layout: "grid-owned",
    desktop_columns: 7,
    tablet_columns: 4,
    phone_columns: 1,
    horizontal_scroll: false,
    deterministic_preview: true,
    model_execution: false,
    authority: false,
    public_contract_grounded: true,
    responsive: true,
  }, null, 2));
}

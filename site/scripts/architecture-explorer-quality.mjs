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
const css = `${read("src/styles/architecture-explorer.css")}\n${read("src/styles/unified-product-app.css")}`;
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

for (const node of ["project", "manager", "context", "worker", "gate", "settlement", "publication"]) {
  check(app.includes(`id: "${node}"`), `architecture explorer missing ${node} node`);
}

for (const contract of ["quillframe_project_adapter_resolution_v1", "quillframe_host_capabilities_v1", "quillframe_context_inspector_v2", "quillframe_run_receipt_v1", "quillframe_production_readiness_v1", "quillframe_publication_ir_v1"]) {
  check(app.includes(contract), `architecture explorer missing public contract ${contract}`);
}

check(app.includes('<Route path="/architecture" component={ArchitecturePage}'), "shared ProductApp must expose /architecture");
check(app.includes("function ProductShell") && app.includes("<Router root={ProductShell}>"), "architecture must live inside the shared Router shell");
check(app.includes("ProductSurfaceHero") && app.includes("architecture-hero-path"), "architecture must use the shared hero frame with an architecture-specific visual slot");
check(app.includes("authority=false"), "architecture preview must state its non-authoritative boundary");
check(app.includes("This is not a real Core execution") && app.includes("不调用模型"), "architecture simulation must be explicitly identified as a deterministic preview");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(app), "product app must not add idle timers or frame loops");
check(main.includes('import ProductApp from "./ProductApp"') && !main.includes("standaloneProductPaths"), "main must mount one shared ProductApp without standalone architecture handoff");
check(main.includes('import "./styles/index.css"'), "main must load the single Product stylesheet entrypoint");
check(index.includes('@import "./architecture-explorer.css"') && index.includes('@import "./unified-product-app.css"'), "architecture shared and feature styles must load through the Product CSS entrypoint");
check(index.indexOf('architecture-explorer.css') < index.indexOf('readability.css'), "architecture route styling must precede cross-cutting readability hardening");
check(surface.includes("product-surface-hero"), "shared ProductSurfaceHero primitive must remain present");
check(css.includes(".architecture-flow") && css.includes(".architecture-detail-grid") && css.includes(".architecture-trace-list"), "architecture explorer must retain flow, inspector, and trace surfaces");
check(css.includes("minmax(174px, 1fr)") && css.includes("overflow-x: auto"), "architecture node rail must preserve readable card width instead of crushing typography");
check(css.includes("@media (max-width: 760px)"), "architecture explorer must retain a mobile responsive contract");

if (failures.length) {
  for (const failure of failures) console.error(`architecture-explorer-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "quillframe_architecture_explorer_quality_v3", status: "pass", shell: "shared_product_app", css_entrypoint: "index.css", shared_surface_hero: true, nodes: 7, deterministic_preview: true, model_execution: false, authority: false, public_contract_grounded: true, responsive: true }, null, 2));
}

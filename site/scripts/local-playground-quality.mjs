#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const playground = read("src/LocalPlayground.tsx");
const quickDemo = read("src/QuickDemo.tsx");
const quickDemoWorker = read("src/quickDemo.worker.ts");
const app = read("src/ProductApp.tsx");
const main = read("src/main.tsx");
const index = read("src/styles/index.css");
const css = read("src/styles/local-playground.css");
const failures = [];
const requireCheck = (condition, message) => { if (!condition) failures.push(message); };

requireCheck(main.includes('import ProductApp from "./ProductApp"') && main.includes("<ProductApp />"), "main entry must mount the shared ProductApp");
requireCheck(main.includes('import "./styles/index.css"'), "main entry must load the single Product stylesheet entrypoint");
requireCheck(app.includes('<Route path="/playground" component={PlaygroundPage}'), "shared ProductApp must expose /playground");
requireCheck(app.includes("<LocalPlayground locale={locale()} />"), "PlaygroundPage must render LocalPlayground with shared locale state");
requireCheck(app.includes("<QuickDemo"), "Product home must render the CH001 QuickDemo");
requireCheck(app.includes("ProductSurfaceHero") && app.includes("LOCAL PLAYGROUND"), "PlaygroundPage must use the shared product surface hero");
requireCheck(index.includes('@import "./local-playground.css"'), "local playground styles must load through the Product CSS entrypoint");
requireCheck(index.indexOf('local-playground.css') < index.indexOf('readability.css'), "playground route styling must precede cross-cutting readability hardening");
requireCheck(!main.includes("LocalPlaygroundEntry") && !main.includes("standaloneProductPaths"), "playground must not retain a standalone shell/handoff path");

requireCheck(playground.includes('type PlaygroundMode = "DRAFT" | "REVISE" | "AUDIT" | "PLAN-CHAPTER"'), "Playground modes must use real Quillframe task modes");
requireCheck(!playground.includes('"REVIEW"') && !playground.includes('"PLAN" |'), "Playground must not invent REVIEW or generic PLAN primary task modes");

for (const marker of ["Context Manifest", "Contract candidates", "Execution", "Evidence", "Result", "context.select", "revision.diagnose", "quality.production_review", "plan.reconcile", "0 model calls", "no semantic routing", "deterministic semantic router", "No automatic settlement"]) {
  requireCheck(playground.includes(marker), `Local Playground contract marker missing: ${marker}`);
}

requireCheck(!/\bfetch\s*\(|XMLHttpRequest|navigator\.sendBeacon|WebSocket\s*\(/.test(playground), "Local Playground must not make network calls");
requireCheck(!/openai|anthropic|model\.generate|chat\.completions/i.test(playground), "Local Playground must not hide a live model provider call");
requireCheck(playground.includes("not the output of a deterministic semantic router"), "Playground must not misrepresent illustrative contract candidates as deterministic semantic routing");
requireCheck(playground.includes("no Canon-write, publication, settlement, or durable-state authority"), "Playground result must explicitly carry no consequential write authority");

for (const marker of ["Deterministic Core", "Recorded semantic evidence", "0 uploads", "CH001"]) {
  requireCheck(quickDemo.includes(marker), `Quick Demo truth marker missing: ${marker}`);
}
requireCheck(quickDemo.includes("Worker(new URL"), "Quick Demo must execute outside the UI thread");
requireCheck(quickDemoWorker.includes("loadPyodide"), "Quick Demo worker must load Pyodide");
requireCheck(quickDemoWorker.includes("production_runtime/workflow.py") && quickDemoWorker.includes("production_runtime/types.py"), "Quick Demo must load the canonical Core sources");
requireCheck(quickDemoWorker.includes("recorded_fixture") && quickDemoWorker.includes("live_model_called"), "Quick Demo receipt must distinguish recorded semantic evidence from live execution");

for (const selector of [".playground-shell", ".playground-workspace", ".playground-mode-tabs", ".playground-trace-flow", ".playground-contract-boundary", ".playground-authority-boundary"]) {
  requireCheck(css.includes(selector), `Local Playground visual contract missing ${selector}`);
}
requireCheck(css.includes("@media (max-width: 620px)"), "Local Playground must retain a compact mobile layout");

if (failures.length > 0) {
  for (const failure of failures) console.error(`local-playground-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "quillframe_local_playground_quality_v3", status: "pass", route: "/playground", shell: "shared_product_app", css_entrypoint: "index.css", execution: "deterministic_preview", model_calls: 0, semantic_routing: false, authority: false, modes: ["DRAFT", "REVISE", "AUDIT", "PLAN-CHAPTER"] }, null, 2));
}

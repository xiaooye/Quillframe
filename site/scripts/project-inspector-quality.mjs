#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const inspector = read("src/ProjectInspector.tsx");
const app = read("src/ProductApp.tsx");
const main = read("src/main.tsx");
const css = read("src/styles/project-inspector.css");
const failures = [];
const requireCheck = (condition, message) => { if (!condition) failures.push(message); };

requireCheck(main.includes('import ProductApp from "./ProductApp"') && main.includes("<ProductApp />"), "main entry must mount the shared ProductApp");
requireCheck(app.includes('<Route path="/inspect" component={InspectorPage}'), "shared ProductApp must expose /inspect");
requireCheck(app.includes("<ProjectInspector locale={locale()} />"), "InspectorPage must render the browser-native inspector with shared locale state");
requireCheck(app.includes("ProductSurfaceHero") && app.includes("PROJECT INSPECTOR"), "InspectorPage must use the shared product surface hero");
requireCheck(main.includes('import "./styles/project-inspector.css"'), "project inspector styles must be loaded by the product entry");
requireCheck(!main.includes("ProjectInspectorEntry") && !main.includes("standaloneProductPaths"), "inspector must not retain a standalone shell/handoff path");

for (const marker of [
  "novelforge.toml",
  "novelforge.lock.json",
  "framework.attestation.json",
  "webkitdirectory",
  "FileList",
  "bundle_fingerprint",
  "production-readiness approval",
  "production readiness approval",
  "python project_sdk.py init",
]) {
  requireCheck(inspector.includes(marker), `Project Inspector contract marker missing: ${marker}`);
}

requireCheck(inspector.includes("file.text()"), "Project Inspector must parse selected files locally with the browser File API");
requireCheck(!/\bfetch\s*\(|XMLHttpRequest|navigator\.sendBeacon|WebSocket\s*\(/.test(inspector), "Project Inspector must not upload or transmit selected project content");
requireCheck(!/FormData\s*\(/.test(inspector), "Project Inspector must not prepare selected project content for upload");
requireCheck(inspector.includes('type InspectionStatus = "coherent" | "scaffold" | "incomplete" | "conflict"'), "Project Inspector must distinguish coherent, scaffold, incomplete, and conflicting states");
requireCheck(inspector.includes("Mapped adapters may intentionally use a different physical layout"), "structural inspection must not treat the standard folder layout as universal semantic authority");

for (const selector of [".project-inspector-shell", ".inspector-dropzone", ".inspector-dashboard-grid", ".inspector-status-badge", ".inspector-disclaimer"]) {
  requireCheck(css.includes(selector), `Project Inspector visual contract missing ${selector}`);
}
requireCheck(css.includes("@media (max-width: 560px)"), "Project Inspector must retain a compact mobile layout");

if (failures.length > 0) {
  for (const failure of failures) console.error(`project-inspector-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "novelforge_project_inspector_quality_v2", status: "pass", route: "/inspect", shell: "shared_product_app", execution: "browser-native", upload: false, authority: false }, null, 2));
}

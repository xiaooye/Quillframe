#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const inspector = read("src/ProjectInspector.tsx");
const inspectorContract = read("src/project-inspector-contract.ts");
const app = read("src/ProductApp.tsx");
const main = read("src/main.tsx");
const index = read("src/styles/index.css");
const css = read("src/styles/project-inspector.css");
const failures = [];
const requireCheck = (condition, message) => { if (!condition) failures.push(message); };

requireCheck(main.includes('import ProductApp from "./ProductApp"') && main.includes("<ProductApp />"), "main entry must mount the shared ProductApp");
requireCheck(main.includes('import "./styles/index.css"'), "main entry must load the single Product stylesheet entrypoint");
requireCheck(app.includes('<Route path="/inspect" component={InspectorPage}'), "shared ProductApp must expose /inspect");
requireCheck(app.includes("<ProjectInspector locale={locale()} />"), "InspectorPage must render the browser-native inspector with shared locale state");
requireCheck(app.includes("ProductSurfaceHero") && app.includes("PROJECT INSPECTOR"), "InspectorPage must use the shared product surface hero");
requireCheck(index.includes('@import "./project-inspector.css"'), "project inspector styles must load through the Product CSS entrypoint");
requireCheck(index.indexOf('project-inspector.css') < index.indexOf('readability.css'), "inspector route styling must precede cross-cutting readability hardening");
requireCheck(!main.includes("ProjectInspectorEntry") && !main.includes("standaloneProductPaths"), "inspector must not retain a standalone shell/handoff path");

for (const marker of [
  "quillframe.toml",
  "quillframe_project_v1_0",
  "quillframe_project_context_v1_0",
  "webkitdirectory",
  "FileList",
  "manifest_fingerprint",
  ".quillframe/data",
  'scope: "novel"',
  "legacy_metadata_rejected",
]) {
  requireCheck(`${inspector}\n${inspectorContract}`.includes(marker), `Project Inspector contract marker missing: ${marker}`);
}

requireCheck(inspectorContract.includes("file.text()"), "Project Inspector must parse selected files locally with the browser File API");
requireCheck(!/\bfetch\s*\(|XMLHttpRequest|navigator\.sendBeacon|WebSocket\s*\(/.test(inspector), "Project Inspector must not upload or transmit selected project content");
requireCheck(!/FormData\s*\(/.test(inspector), "Project Inspector must not prepare selected project content for upload");
requireCheck(inspectorContract.includes('type InspectionStatus = "coherent" | "scaffold" | "incomplete" | "conflict"'), "Project Inspector must distinguish coherent, scaffold, incomplete, and conflicting states");
requireCheck(inspectorContract.includes(".quillframe/data"), "structural inspection must expose the exact native data boundary");
requireCheck(inspectorContract.includes('Object.keys(values).length !== 4') && !inspectorContract.includes("chapter_scope"), "Project Inspector must enforce the four-key novel manifest without a chapter scope alias");
const legacyMarkers = [["quillframe", "lock", "json"].join("."), ["framework", "attestation", "json"].join("."), ["project", "sdk", "py"].join(".")];
for (const legacy of legacyMarkers) {
  requireCheck(!`${inspector}\n${inspectorContract}`.includes(legacy), `Project Inspector retains legacy marker: ${legacy}`);
}

for (const selector of [".project-inspector-shell", ".inspector-dropzone", ".inspector-dashboard-grid", ".inspector-status-badge", ".inspector-disclaimer"]) {
  requireCheck(css.includes(selector), `Project Inspector visual contract missing ${selector}`);
}
requireCheck(css.includes("@media (max-width: 560px)"), "Project Inspector must retain a compact mobile layout");

if (failures.length > 0) {
  for (const failure of failures) console.error(`project-inspector-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "quillframe_project_inspector_quality_v3", status: "pass", route: "/inspect", shell: "shared_product_app", css_entrypoint: "index.css", execution: "browser-native", upload: false, authority: false }, null, 2));
}

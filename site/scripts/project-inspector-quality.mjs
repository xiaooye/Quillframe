#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const inspector = read("src/ProjectInspector.tsx");
const entry = read("src/ProjectInspectorEntry.tsx");
const main = read("src/main.tsx");
const css = read("src/styles/project-inspector.css");
const failures = [];
const requireCheck = (condition, message) => {
  if (!condition) failures.push(message);
};

requireCheck(main.includes('path === "/inspect"'), "Product Entry must expose the /inspect browser-native product surface");
requireCheck(main.includes("ProjectInspectorEntry"), "main entry must route /inspect to ProjectInspectorEntry");
requireCheck(main.includes('import "./styles/project-inspector.css"'), "project inspector styles must be loaded by the product entry");

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
requireCheck(inspector.includes('status: "coherent" | "scaffold" | "incomplete" | "conflict"'), "Project Inspector must distinguish coherent, scaffold, incomplete, and conflicting states");
requireCheck(inspector.includes("Mapped adapters may intentionally use a different physical layout"), "structural inspection must not treat the standard folder layout as universal semantic authority");
requireCheck(entry.includes("ProjectInspector locale={locale()}"), "standalone inspector entry must preserve bilingual product rendering");
requireCheck(entry.includes("Your project content stays in your browser"), "inspector shell must expose the local-only privacy boundary");

for (const selector of [
  ".project-inspector-shell",
  ".inspector-dropzone",
  ".inspector-dashboard-grid",
  ".inspector-status-badge",
  ".inspector-disclaimer",
]) {
  requireCheck(css.includes(selector), `Project Inspector visual contract missing ${selector}`);
}
requireCheck(css.includes("@media (max-width: 560px)"), "Project Inspector must retain a compact mobile layout");

if (failures.length > 0) {
  for (const failure of failures) console.error(`project-inspector-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_project_inspector_quality_v1",
    status: "pass",
    route: "/inspect",
    execution: "browser-native",
    upload: false,
    authority: false,
    checks: ["manifest", "lock", "exact-revision", "bundle-fingerprint", "attestation", "logical-structure", "quality-evidence"],
  }, null, 2));
}

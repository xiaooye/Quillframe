#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const css = read("src/styles/tool-workbench-kawaii.css");
const main = read("src/main.tsx");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(main.includes('import "./styles/tool-workbench-kawaii.css"'), "standalone workbench polish must load after the shared surface layer");
check(main.indexOf('surface-consistency.css') < main.indexOf('tool-workbench-kawaii.css'), "tool polish must refine, not precede, shared surface consistency");

for (const selector of [
  ".project-inspector-intro",
  ".inspector-dropzone",
  ".inspector-stat-grid",
  ".playground-intro",
  ".playground-input-panel textarea",
  ".playground-stage",
  ".agent-integration-hero",
  ".agent-path-card",
  ".agent-host-workbench",
  ".agent-host-tabs button",
]) {
  check(css.includes(selector), `workbench design marker missing: ${selector}`);
}

for (const designToken of [
  "--tool-paper",
  "--tool-stitch",
  "border: 1px dashed",
  "repeating-linear-gradient",
  "color-mix(in oklab",
]) {
  check(css.includes(designToken), `stationery design token/technique missing: ${designToken}`);
}

check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(css), "standalone workbench polish must not add infinite idle animation");
check(!/requestAnimationFrame\s*\(|setInterval\s*\(/.test(css), "standalone workbench stylesheet must stay declarative and idle-safe");
check(css.includes("@media (max-width: 620px)"), "standalone workbench polish must preserve compact mobile behavior");

if (failures.length) {
  for (const failure of failures) console.error(`tool-workbench-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_tool_workbench_quality_v1",
    status: "pass",
    inspector: true,
    playground: true,
    agent_integration: true,
    publication_design_language: true,
    stationery_surface_grammar: true,
    responsive: true,
    infinite_idle_animation: false,
  }, null, 2));
}

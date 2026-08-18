#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const css = read("src/styles/tool-workbench-kawaii.css");
const embedded = read("src/styles/embedded-features.css");
const readability = read("src/styles/readability.css");
const index = read("src/styles/index.css");
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(main.includes('import "./styles/index.css"'), "Product main must load the single CSS entrypoint");
for (const style of ["project-inspector.css", "local-playground.css", "agent-integration.css", "tool-workbench-kawaii.css", "embedded-features.css", "readability.css"]) {
  check(index.includes(`@import "./${style}"`), `Product CSS entrypoint missing ${style}`);
}
check(index.indexOf('local-playground.css') < index.indexOf('tool-workbench-kawaii.css'), "workbench composition must load after route defaults");
check(index.indexOf('tool-workbench-kawaii.css') < index.indexOf('embedded-features.css'), "embedded feature ownership must refine workbench composition");
check(index.indexOf('embedded-features.css') < index.indexOf('readability.css'), "readability hardening must remain the final cross-cutting layer");
check(!index.includes("surface-consistency.css") && !index.includes("surface-audit.css") && !index.includes("editorial-composition.css"), "rejected flattening layers must stay out of the Product cascade");

for (const route of ["/product", "/studio", "/inspect", "/playground", "/agents"]) {
  check(app.includes(`path="${route}"`), `shared ProductApp must retain ${route}`);
}
for (const page of ["ProductPage", "StudioPage", "InspectorPage", "PlaygroundPage", "AgentsPage"]) {
  check(app.includes(`function ${page}`), `shared ProductApp missing ${page}`);
}

for (const selector of [
  ".inspector-dropzone",
  ".inspector-summary-card",
  ".playground-workspace",
  ".playground-input-panel textarea",
  ".playground-stage",
  ".agent-host-workbench",
  ".agent-path-card",
  ":has(.unified-stack-visual)",
  ":has(.unified-studio-terminal)",
]) {
  check(css.includes(selector), `Story Loom workstation marker missing: ${selector}`);
}

for (const marker of [
  "Story Loom workstation language",
  "repeating-linear-gradient",
  "border: 1px dashed",
  "border-radius: 28px 28px 18px 28px",
  "box-shadow:",
  "color-mix(in oklab",
  "@media (max-width: 620px)",
]) {
  check(css.includes(marker), `Story Loom workstation technique missing: ${marker}`);
}

check(embedded.includes(".project-inspector-intro") && embedded.includes(".playground-intro") && embedded.includes("display: none"), "embedded Inspector and Playground must suppress their duplicate internal page heroes");
check(embedded.includes(".unified-route-page.inspector-entry") && embedded.includes(".unified-route-page.playground-entry"), "embedded overrides must be scoped to routed product pages");
check(css.includes('content: "PROJECT FILES"'), "Inspector must preserve the project-folder/stationery object cue");
check(css.includes("open notebook + execution sheet") && css.includes("linear-gradient(90deg"), "Playground must preserve the two-page notebook/workbench composition");
check(css.includes("host rail + wiring desk"), "Agent integration must preserve its host-workbench composition");
check(css.includes("Product / Studio: keep the same brand grammar"), "Product and Studio must participate in the shared Story Loom visual language");
check(readability.includes("--qf-copy-size: 14px") && readability.includes("--qf-micro-size: 11px"), "workbench readability floor must stay active");
check(!css.includes("!important"), "Story Loom workstation composition must not rely on specificity escalation");
check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(`${css}\n${embedded}\n${readability}`), "tool workbench layers must not add infinite idle animation");

if (failures.length) {
  for (const failure of failures) console.error(`tool-workbench-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_tool_workbench_quality_v5",
    status: "pass",
    shell: "shared_product_app",
    css_entrypoint: "index.css",
    inspector: "project_folder_evidence_desk",
    playground: "open_notebook_execution_sheet",
    agent_integration: "host_rail_wiring_desk",
    product_and_studio_story_loom: true,
    duplicate_page_heroes: false,
    story_loom_workstation_language: true,
    pastel_object_surfaces: true,
    generic_saas_flattening: false,
    readability_hardening: true,
    responsive: true,
    infinite_idle_animation: false,
  }, null, 2));
}

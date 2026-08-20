#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(process.env.QUILLFRAME_TOOL_WORKBENCH_SITE_ROOT || path.resolve(here, ".."));
const repoRoot = path.resolve(process.env.QUILLFRAME_TOOL_WORKBENCH_REPO_ROOT || path.resolve(siteRoot, ".."));
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const readRepo = (relative) => fs.readFileSync(path.join(repoRoot, relative), "utf8");

const css = read("src/styles/tool-workbench-kawaii.css");
const agentIntegration = read("src/styles/agent-integration.css");
const agentHostProfiles = read("src/styles/agent-host-profiles.css");
const embedded = read("src/styles/embedded-features.css");
const readability = read("src/styles/readability.css");
const index = read("src/styles/index.css");
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const studioIndex = readRepo("studio/app/src/styles/index.css");
const studioMain = readRepo("studio/app/src/main.tsx");
const sharedProductLanguage = readRepo("assets/brand/quillframe-product-language.css");
const sharedStoryLoom = readRepo("assets/brand/story-loom.weiui.css");
const workstationCss = `${css}\n${agentIntegration}\n${agentHostProfiles}`;
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

function hasAsymmetricObjectRadius(source) {
  return Array.from(source.matchAll(/border-radius:\s*([^;]+);/g)).some((match) => {
    const values = match[1].trim().split(/\s+/);
    return values.length === 4
      && values.every((value) => /^\d+(?:\.\d+)?px$/.test(value))
      && new Set(values).size > 1;
  });
}

check(main.includes('import "./styles/index.css"'), "Product main must load the single CSS entrypoint");
for (const style of ["project-inspector.css", "local-playground.css", "agent-integration.css", "agent-host-profiles.css", "tool-workbench-kawaii.css", "embedded-features.css", "readability.css"]) {
  check(index.includes(`@import "./${style}"`), `Product CSS entrypoint missing ${style}`);
}
check(index.indexOf('local-playground.css') < index.indexOf('tool-workbench-kawaii.css'), "workbench composition must load after route defaults");
check(index.indexOf('tool-workbench-kawaii.css') < index.indexOf('embedded-features.css'), "embedded feature ownership must refine workbench composition");
check(index.indexOf('embedded-features.css') < index.indexOf('readability.css'), "readability hardening must remain the final cross-cutting layer");
check(!index.includes("surface-consistency.css") && !index.includes("surface-audit.css"), "rejected audit layers must stay out of the Product cascade");

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
  check(workstationCss.includes(selector), `Story Loom workstation marker missing: ${selector}`);
}

for (const marker of [
  "Story Loom workstation language",
  "repeating-linear-gradient",
  "border: 1px dashed",
  "box-shadow:",
  "color-mix(in oklab",
  "@media (max-width: 620px)",
]) {
  check(workstationCss.includes(marker), `Story Loom workstation technique missing: ${marker}`);
}
check(hasAsymmetricObjectRadius(workstationCss), "Story Loom workstation technique missing: asymmetric object radius");

check(embedded.includes(".project-inspector-intro") && embedded.includes(".playground-intro") && embedded.includes("display: none"), "embedded Inspector and Playground must suppress their duplicate internal page heroes");
check(embedded.includes(".unified-route-page.inspector-entry") && embedded.includes(".unified-route-page.playground-entry"), "embedded overrides must be scoped to routed product pages");
check(css.includes('content: "PROJECT FILES"'), "Inspector must preserve the project-folder/stationery object cue");
check(css.includes("open notebook + execution sheet") && css.includes("linear-gradient(90deg"), "Playground must preserve the two-page notebook/workbench composition");
check(css.includes("host rail + wiring desk"), "Agent integration must preserve its host-workbench composition");
const sharedLanguageContract = index.includes('@import "../../../assets/brand/quillframe-product-language.css";')
  && studioIndex.includes('@import "../../../../assets/brand/story-loom.weiui.css";')
  && studioIndex.includes('@import "../../../../assets/brand/quillframe-product-language.css";')
  && studioMain.includes('document.documentElement.dataset.productLanguage = "quillframe-kawaii-v1"')
  && sharedProductLanguage.includes("--qf-product-canvas")
  && sharedProductLanguage.includes("--qf-product-focus")
  && sharedStoryLoom.includes("@layer wui-theme")
  && index.indexOf('agent-integration.css') < index.indexOf('tool-workbench-kawaii.css')
  && studioIndex.indexOf('product-language.css') < studioIndex.indexOf('hardening.css');
check(sharedLanguageContract, "Product and Studio must retain the shared Story Loom product language contract");
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

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
check(!index.includes("surface-consistency.css") && !index.includes("surface-audit.css"), "retired catch-all visual override layers must stay out of the Product cascade");

for (const route of ["/inspect", "/playground", "/agents"]) {
  check(app.includes(`path="${route}"`), `shared ProductApp must retain ${route}`);
}
for (const page of ["InspectorPage", "PlaygroundPage", "AgentsPage"]) {
  check(app.includes(`function ${page}`), `shared ProductApp missing ${page}`);
}

for (const selector of [
  ".project-inspector-intro",
  ".inspector-dropzone",
  ".inspector-summary-card",
  ".playground-intro",
  ".playground-input-panel textarea",
  ".playground-stage",
  ".agent-host-workbench",
]) {
  check(css.includes(selector), `workbench clean-surface marker missing: ${selector}`);
}

for (const marker of ["border: 0", "background: transparent", "box-shadow: none", "color-mix(in oklab", "@media (max-width: 620px)"]) {
  check(css.includes(marker), `home-like surface technique missing: ${marker}`);
}

check(embedded.includes(".project-inspector-intro") && embedded.includes(".playground-intro") && embedded.includes("display: none"), "embedded Inspector and Playground must suppress their legacy internal page heroes");
check(embedded.includes(".unified-route-page.inspector-entry") && embedded.includes(".unified-route-page.playground-entry"), "embedded overrides must be scoped to routed product pages");
check(css.includes(".inspector-summary-card") && css.includes("border-radius: 0"), "inspector result sections must not return to rounded card stacks");
check(css.includes(".playground-stage") && css.includes("border-top: 1px solid"), "playground stages should use hairline separation instead of cards");
check(readability.includes("--nf-copy-size: 14px") && readability.includes("--nf-micro-size: 11px"), "workbench readability floor must stay active");
check(!css.includes("--tool-stitch"), "stitched stationery framing must stay removed from tool workbenches");
check(!css.includes("rotate(.25deg)") && !css.includes("rotate(-1.8deg)"), "decorative card rotation must stay removed from tool workbenches");
check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(`${css}\n${embedded}\n${readability}`), "tool workbench layers must not add infinite idle animation");

if (failures.length) {
  for (const failure of failures) console.error(`tool-workbench-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_tool_workbench_quality_v4",
    status: "pass",
    shell: "shared_product_app",
    css_entrypoint: "index.css",
    inspector: "embedded_feature_body",
    playground: "embedded_feature_body",
    agent_integration: "shared_route",
    duplicate_page_heroes: false,
    near_borderless: true,
    restrained_kawaii_palette: true,
    readability_hardening: true,
    responsive: true,
    infinite_idle_animation: false,
  }, null, 2));
}

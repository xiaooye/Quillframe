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
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(main.includes('import "./styles/tool-workbench-kawaii.css"'), "tool workbench refinement must be loaded");
check(main.includes('import "./styles/product-surface.css"') && main.includes('import "./styles/unified-product-app.css"'), "tool pages must inherit the shared product surface layers");
check(main.includes('import "./styles/surface-audit.css"') && main.includes('import "./styles/embedded-features.css"'), "final shared surface and embedded-feature layers must be loaded");
check(!main.includes("surface-consistency.css"), "legacy per-page surface consistency layer must stay retired");
check(main.indexOf('tool-workbench-kawaii.css') < main.indexOf('product-surface.css'), "feature refinement must load before the shared surface composition");
check(main.indexOf('surface-audit.css') < main.indexOf('embedded-features.css'), "embedded-feature overrides must be the final ownership layer");

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
check(!css.includes("--tool-stitch"), "stitched stationery framing must stay removed from tool workbenches");
check(!css.includes("rotate(.25deg)") && !css.includes("rotate(-1.8deg)"), "decorative card rotation must stay removed from tool workbenches");
check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(`${css}\n${embedded}`), "tool workbench layers must not add infinite idle animation");

if (failures.length) {
  for (const failure of failures) console.error(`tool-workbench-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_tool_workbench_quality_v3",
    status: "pass",
    shell: "shared_product_app",
    inspector: "embedded_feature_body",
    playground: "embedded_feature_body",
    agent_integration: "shared_route",
    duplicate_page_heroes: false,
    near_borderless: true,
    restrained_kawaii_palette: true,
    responsive: true,
    infinite_idle_animation: false,
  }, null, 2));
}

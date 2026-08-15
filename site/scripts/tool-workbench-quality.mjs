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

check(main.includes('import "./styles/tool-workbench-kawaii.css"'), "standalone workbench refinement must be loaded");
check(main.indexOf('surface-consistency.css') < main.indexOf('tool-workbench-kawaii.css'), "tool refinement must override the shared framed defaults");

for (const selector of [
  ".project-inspector-intro",
  ".inspector-dropzone",
  ".inspector-summary-card",
  ".playground-intro",
  ".playground-input-panel textarea",
  ".playground-stage",
  ".agent-integration-hero",
  ".agent-path-card",
  ".agent-host-workbench",
  ".agent-host-tabs button",
]) {
  check(css.includes(selector), `workbench clean-surface marker missing: ${selector}`);
}

for (const marker of [
  "border: 0",
  "background: transparent",
  "box-shadow: none",
  "color-mix(in oklab",
  "@media (max-width: 620px)",
]) {
  check(css.includes(marker), `home-like surface technique missing: ${marker}`);
}

check(css.includes(".project-inspector-intro::before") && css.includes("display: none"), "tool heroes must remove the shared inset frame");
check(css.includes(".inspector-summary-card") && css.includes("border-radius: 0"), "inspector result sections must not return to rounded card stacks");
check(css.includes(".playground-stage") && css.includes("border-top: 1px solid"), "playground stages should use hairline separation instead of cards");
check(css.includes(".agent-path-card") && css.includes("border-top: 2px solid"), "agent paths should read as editorial columns instead of cards");
check(!css.includes("--tool-stitch"), "stitched stationery framing must stay removed from the product tools");
check(!css.includes("rotate(.25deg)") && !css.includes("rotate(-1.8deg)"), "decorative card rotation must stay removed");
check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(css), "standalone workbench refinement must not add infinite idle animation");
check(!/requestAnimationFrame\s*\(|setInterval\s*\(/.test(css), "standalone workbench stylesheet must stay declarative and idle-safe");

if (failures.length) {
  for (const failure of failures) console.error(`tool-workbench-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_tool_workbench_quality_v2",
    status: "pass",
    inspector: true,
    playground: true,
    agent_integration: true,
    home_like_visual_density: true,
    near_borderless: true,
    nested_card_grammar: false,
    restrained_kawaii_palette: true,
    responsive: true,
    infinite_idle_animation: false,
  }, null, 2));
}

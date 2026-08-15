#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const fail = (message) => {
  console.error(`atelier-quality: FAIL: ${message}`);
  process.exitCode = 1;
};
const check = (condition, message) => {
  if (!condition) fail(message);
};

const main = read("src/main.tsx");
const appearance = read("src/appearance-v5.ts");
const app = read("src/App.tsx");
const atelier = read("src/styles/atelier.css");
const site = read("src/styles/site.css");
const packageJson = JSON.parse(read("package.json"));

const showcaseIndex = main.indexOf('import "./styles/showcase.css"');
const atelierIndex = main.indexOf('import "./styles/atelier.css"');
check(main.startsWith('import "./appearance-v5"'), "v5 appearance bootstrap must evaluate before App");
check(showcaseIndex >= 0 && atelierIndex > showcaseIndex, "Atelier composition must load after the v4 progressive-enhancement fallback");
check(appearance.includes('novelforge.product-entry.v5.appearance-migrated'), "v5 appearance migration key is missing");
check(appearance.includes('localStorage.setItem("novelforge.appearance", "light")'), "v5 first-load migration must restore warm light presentation");
check(appearance.includes('story-loom-kawaii-atelier-v5'), "v5 experience identity must be stamped on the document root");

for (const lane of ["project", "runtime", "editorial", "evidence", "validated", "rejected"]) {
  check(atelier.includes(`--nf-lane-${lane}-`), `Atelier must consume Story Loom ${lane} lane tokens`);
}

for (const marker of [
  "--atelier-paper",
  ".entry-hero",
  ".hero-launcher",
  ".capability-ribbon",
  ".product-lab",
  ".lab-grid",
  ".portal-grid",
  ".studio-portal",
  ".knowledge-preview",
  ".interactive-route",
  ".knowledge-explorer",
  ".product-document",
]) {
  check(atelier.includes(marker), `Atelier composition marker missing: ${marker}`);
}

for (const technique of [
  "@property --atelier-angle",
  ":has(",
  "@container",
  "@scope",
  "@starting-style",
  "allow-discrete",
  "animation-timeline: view(",
  "animation-timeline: scroll(",
  "::view-transition-old(root)",
  "@supports (anchor-name:",
  "@supports (corner-shape: squircle)",
  "mask-image:",
  "color-mix(in oklab",
  "@media (prefers-reduced-motion: reduce)",
]) {
  check(atelier.includes(technique), `Atelier progressive-enhancement contract missing: ${technique}`);
}

check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(atelier), "Atelier must not introduce infinite idle animation");
check(!/requestAnimationFrame\s*\(|setInterval\s*\(/.test(`${app}\n${appearance}`), "Atelier Product Entry must not add decorative frame loops or polling");
check(atelier.includes("var(--nf-touch-target-min, 44px)"), "Atelier controls must derive touch targets from Story Loom");
check(site.includes('@import "../generated/weiui.generated.css"') && site.includes('@import "../../../assets/brand/story-loom.weiui.css"'), "Atelier must remain layered over the real WeiUI → Story Loom foundation");

for (const primitive of ["wui-app-bar", "wui-button", "wui-card", "wui-command", "wui-input-group", "wui-badge", "wui-bottom-nav", "wui-tabs"]) {
  check(app.includes(primitive), `v5 must retain WeiUI primitive .${primitive}`);
}

check(app.includes("loadKnowledgeIndex") && app.includes("loadProductDocument"), "v5 must retain the real build-time Knowledge runtime");
check(app.includes("https://studio.novelforge.wei-dev.com"), "v5 must retain the real Hosted Studio entry point");
check(app.includes("Context budget lab") || app.includes("上下文预算实验"), "v5 must retain the interactive context lab");
check(app.includes("Candidate readiness lab") || app.includes("候选稿就绪实验"), "v5 must retain the interactive readiness lab");

const qualityScript = packageJson.scripts?.quality ?? "";
check(qualityScript.includes("atelier-quality.mjs"), "Product Site quality script must include the v5 Atelier gate");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_product_atelier_quality_v1",
    status: "pass",
    identity: "story_loom_kawaii_atelier_v5",
    weiui_foundation: true,
    story_loom_lane_authority: true,
    knowledge_runtime_preserved: true,
    hosted_studio_preserved: true,
    premium_kawaii_composition: true,
    warm_first_load: true,
    progressive_css: true,
    infinite_idle_animation: false,
    authority: false,
  }, null, 2));
}

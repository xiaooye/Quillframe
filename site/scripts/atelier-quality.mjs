#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const main = read("src/main.tsx");
const index = read("src/styles/index.css");
const appearance = read("src/appearance-v5.ts");
const app = read("src/ProductApp.tsx");
const surface = read("src/ProductSurface.tsx");
const atelier = read("src/styles/atelier.css");
const site = read("src/styles/site.css");
const unified = read("src/styles/unified-product-app.css");
const surfaceCss = read("src/styles/product-surface.css");
const packageJson = JSON.parse(read("package.json"));

const showcaseIndex = index.indexOf('@import "./showcase.css"');
const atelierIndex = index.indexOf('@import "./atelier.css"');
const surfaceIndex = index.indexOf('@import "./product-surface.css"');
const unifiedIndex = index.indexOf('@import "./unified-product-app.css"');
const compositionIndex = index.indexOf('@import "./tool-workbench-kawaii.css"');
const routeIdentityIndex = index.indexOf('@import "./route-identities.css"');
const readabilityIndex = index.indexOf('@import "./readability.css"');
check(main.startsWith('import "./appearance-v5"'), "v5 appearance bootstrap must evaluate before ProductApp");
check(main.includes('import "./styles/index.css"'), "v5 Product entry must use the single stylesheet entrypoint");
check(surfaceIndex >= 0 && unifiedIndex > surfaceIndex && showcaseIndex > unifiedIndex, "stable shared product primitives must load before route-owned feature styles");
check(atelierIndex > showcaseIndex, "Atelier composition must load after the progressive-enhancement route fallback");
check(compositionIndex > atelierIndex, "shared workstation composition must refine Atelier route defaults");
check(routeIdentityIndex > compositionIndex, "route identity must follow shared workstation composition");
check(readabilityIndex > routeIdentityIndex, "cross-cutting readability hardening must remain after route composition");
check(!index.includes('@import "./kawaii-surfaces.css"'), "retired route-wallpaper layer must not participate in the active Atelier cascade");
check(appearance.includes('quillframe.product-entry.v5.appearance-migrated'), "v5 appearance migration key is missing");
check(appearance.includes('localStorage.setItem("quillframe.appearance", "light")'), "v5 first-load migration must restore warm light presentation");
check(appearance.includes('story-loom-kawaii-atelier-v5'), "v5 experience identity must be stamped on the document root");

for (const lane of ["project", "runtime", "editorial", "evidence", "validated"]) {
  check(atelier.includes(`--qf-lane-${lane}-`), `Atelier must consume Story Loom ${lane} lane tokens`);
}
check(site.includes("--qf-lane-rejected-stroke") || site.includes("--pe-reject"), "Rejected state must remain represented by the Story Loom-backed lower product layer");

for (const technique of ["@property --atelier-angle", ":has(", "@container", "@scope", "@starting-style", "allow-discrete", "animation-timeline: view(", "animation-timeline: scroll(", "::view-transition-old(root)", "@supports (anchor-name:", "@supports (corner-shape: squircle)", "mask-image:", "color-mix(in oklab", "@media (prefers-reduced-motion: reduce)"]) {
  check(atelier.includes(technique), `Atelier progressive-enhancement contract missing: ${technique}`);
}
check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(`${atelier}\n${unified}\n${surfaceCss}`), "Product presentation must not introduce infinite idle animation");
check(!/requestAnimationFrame\s*\(|setInterval\s*\(/.test(`${app}\n${appearance}`), "unified Product Entry must not add decorative frame loops or polling");
check(atelier.includes("var(--qf-touch-target-min, 44px)"), "Atelier controls must derive touch targets from Story Loom");
check(site.includes('@import "../generated/weiui.generated.css"') && site.includes('@import "../../../assets/brand/story-loom.weiui.css"'), "Atelier must remain layered over the WeiUI → Story Loom foundation");

for (const primitive of ["wui-app-bar", "wui-button", "wui-card", "wui-command", "wui-badge"]) {
  check(app.includes(primitive), `unified v5 app must retain WeiUI primitive .${primitive}`);
}
check(app.includes("loadKnowledgeIndex") && app.includes("searchKnowledge"), "unified shell must retain build-time Knowledge search for command palette");
check(app.includes("https://studio.quillframe.wei-dev.com"), "unified shell must retain the real Hosted Studio entry point");
check(app.includes("<Router root={ProductShell}>") && surface.includes("ProductSurfaceHero"), "v5 must now compose through one shared shell and shared surface hero");
check(unified.includes(".unified-publication-gallery") && unified.includes(".architecture-hero-path"), "product composition must retain page-specific visual objects inside the shared canvas");
check(unified.includes(".unified-card-grid") && unified.includes("border-block-start"), "secondary product explanation must use editorial sequence rather than card soup");

const qualityScript = packageJson.scripts?.quality ?? "";
const baselineQualityScript = packageJson.scripts?.["baseline:quality"] ?? "";
check(qualityScript.includes("baseline:quality"), "Product Site aggregate quality must execute the golden-baseline quality chain");
check(
  baselineQualityScript.includes("atelier-quality.mjs") &&
    baselineQualityScript.includes("product-shell-quality.mjs") &&
    baselineQualityScript.includes("css-architecture-quality.mjs"),
  "Golden baseline quality chain must gate Atelier, shared shell, and CSS architecture",
);

if (failures.length) {
  for (const failure of failures) console.error(`atelier-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "quillframe_product_atelier_quality_v4", status: "pass", identity: "story_loom_kawaii_atelier_v5", unified_shell: true, css_entrypoint: "index.css", css_cascade: "primitives_routes_shared_composition_readability", weiui_foundation: true, story_loom_lane_authority: true, route_wallpaper_layer_active: false, hosted_studio_preserved: true, canvas_first_composition: true, warm_first_load: true, progressive_css: true, infinite_idle_animation: false, authority: false }, null, 2));
}

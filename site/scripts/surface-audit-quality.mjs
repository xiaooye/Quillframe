#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(siteRoot, relative));
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const main = read("src/main.tsx");
const productApp = read("src/ProductApp.tsx");
const productIndex = read("src/styles/index.css");
const productSurface = read("src/styles/product-surface.css");
const atelier = read("src/styles/atelier.css");
const workbench = read("src/styles/tool-workbench-kawaii.css");
const routeScenes = read("src/styles/story-loom-route-refinements.css");
const docsConfig = read("docs-site/astro.config.mjs");
const docsAudit = read("docs-site/src/styles/surface-audit.css");
const docsIdentity = read("docs-site/src/styles/story-loom-docs.css");
const docsReadability = read("docs-site/src/styles/readability-audit.css");

check(main.includes('import "./styles/index.css"'), "product site must load the single CSS entrypoint");
check(!productIndex.includes("surface-audit.css"), "product site must not use a final audit override layer");
check(!exists("src/styles/surface-audit.css"), "retired product surface-audit.css must stay deleted");
check(productIndex.includes("kawaii-surfaces.css") && productIndex.includes("atelier.css"), "Story Loom product composition layers must remain explicit");
check(productIndex.includes("tool-workbench-kawaii.css") && productIndex.includes("story-loom-route-refinements.css"), "Story Loom workstation and route-language layers must stay active");
check(!productIndex.includes("editorial-composition.css"), "global editorial flattening must remain retired from the active product cascade");
check(!productIndex.includes("home-identity.css"), "temporary simplified-home rewrite must remain retired from the active product cascade");
check(productIndex.indexOf("architecture-explorer.css") < productIndex.indexOf("kawaii-surfaces.css"), "feature defaults must precede Story Loom product-language composition");
check(productIndex.indexOf("route-identities.css") < productIndex.indexOf("story-loom-route-refinements.css"), "route-specific Story Loom scenes must refine route identity defaults");
check(productIndex.indexOf("story-loom-route-refinements.css") < productIndex.indexOf("publication-gallery.css"), "non-publication route scenes must not replace the Publication-owned refinement");

/* PAGE == CANVAS: shared route hero owns composition, never a giant card. */
for (const marker of ["border: 0", "border-radius: 0", "background: transparent", "box-shadow: none", "content: none"]) {
  check(productSurface.includes(marker), `shared ProductSurfaceHero canvas contract missing ${marker}`);
}
check(!productSurface.includes("border-radius: 28px"), "shared ProductSurfaceHero must not restore the old 28px giant-card frame");
check(!productSurface.includes("border: 1px dashed"), "shared ProductSurfaceHero must not restore the old dashed inset frame");
check(!productSurface.includes("box-shadow: var(--pe-shadow-2)"), "shared ProductSurfaceHero root must not restore card shadow");
check(productSurface.includes('.product-surface-hero[data-tone="project"]') && productSurface.includes('.product-surface-hero[data-tone="publication"]'), "route semantic accents must remain explicit without becoming wallpaper");
check(productSurface.includes("--product-hero-accent"), "shared hero tones must resolve through a restrained semantic accent token");

for (const marker of ["entry-hero", "hero-launcher wui-card material-panel", "capability-ribbon", "capability-focus page-width section-compact", "product-lab section-pad-soft", "product-world page-width section-compact", "knowledge-preview section-pad-soft"]) {
  check(productApp.includes(marker), `restored screenshot-era HomePage missing ${marker}`);
}
for (const marker of [".entry-hero", ".hero-launcher.material-panel", ".launcher-tile", ".capability-ribbon", ".capability-chip", ".capability-focus-grid", ".lab-grid", ".portal-grid", ".knowledge-preview-grid"]) {
  check(atelier.includes(marker), `Story Loom Atelier source missing restored HomePage marker ${marker}`);
}
check(productApp.includes("让故事越写越长，系统仍然知道自己在做什么。") && productApp.includes("六条真实产品能力"), "restored HomePage must keep the screenshot-era visual/copy anchor points");
check(productApp.includes('href: "/inspect"') && productApp.includes('href: "/playground"') && productApp.includes('href: "/agents"'), "new Product capabilities must remain reachable while HomePage layout is restored");

for (const marker of ["Story Loom workstation language", "PROJECT FILES", "open notebook + execution sheet", "host rail + wiring desk"]) {
  check(workbench.includes(marker), `workbench Story Loom identity missing ${marker}`);
}
for (const marker of ["Route-specific Story Loom scenes", "♡ STORY STATE", "LOCAL ONLY", "AGENT PATCH BAY"]) {
  check(routeScenes.includes(marker), `route Story Loom scene missing ${marker}`);
}
check(!routeScenes.includes(".architecture-entry") && !routeScenes.includes(".publication-workbench-entry"), "new route-scene layer must not take ownership of Architecture or Publication");

/* Docs remain reading-first, but their chrome and landing share Story Loom identity. */
check(docsConfig.includes('"./src/styles/surface-audit.css"'), "Starlight must keep its docs-specific reading-surface audit");
check(docsConfig.includes('"./src/styles/story-loom-docs.css"'), "Starlight must load the restrained Story Loom identity layer");
check(docsConfig.includes('"./src/styles/readability-audit.css"'), "Starlight must load the docs readability pass");
check(docsConfig.indexOf('surface-audit.css') < docsConfig.indexOf('story-loom-docs.css'), "docs Story Loom identity must refine the neutral reading surface");
check(docsConfig.indexOf('story-loom-docs.css') < docsConfig.indexOf('readability-audit.css'), "docs readability must remain final after identity styling");
for (const marker of ["header.header", ".sidebar-pane", "body:has([data-nf-docs-home]) .hero", ".nf-article-title", ".sl-markdown-content blockquote", ".sl-markdown-content table", ".pagination-links a"]) {
  check(docsAudit.includes(marker), `docs reading-surface audit missing ${marker}`);
}
for (const marker of ["Story Loom identity for Starlight", "♡ Quillframe Docs", ".nf-link-card", ".nf-tier-card", ".nf-article-title"] ) {
  check(docsIdentity.includes(marker), `docs Story Loom identity missing ${marker}`);
}
check(docsAudit.includes(".nf-article-title") && docsAudit.includes("border-bottom: 1px solid"), "article hierarchy must retain a restrained divider");
check(docsReadability.includes(":lang(zh-CN) body:has(.nf-article-title) .sl-markdown-content") && docsReadability.includes("line-height: 1.9"), "Chinese long-form reading rhythm must remain explicit");
check(docsReadability.includes(".sl-markdown-content li > p") && docsReadability.includes("margin-block: .18rem"), "tight Markdown lists must not inherit full paragraph spacing");
check(docsReadability.includes("max-width: 68ch") && docsReadability.includes("max-width: 42em"), "docs reading measure must remain bounded for Latin and CJK copy");
check(!workbench.includes("!important") && !routeScenes.includes("!important") && !docsIdentity.includes("!important"), "Story Loom identity layers must not depend on specificity escalation");

if (failures.length) {
  for (const failure of failures) console.error(`surface-audit-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_surface_identity_quality_v8",
    status: "pass",
    product_final_override: false,
    product_editorial_flattening: false,
    canvas_first_route_hero: true,
    giant_hero_card: false,
    screenshot_era_home_dom: true,
    screenshot_era_home_sections: true,
    home_style_owner: "showcase.css+atelier.css",
    story_loom_workstations: true,
    story_loom_route_scenes: true,
    architecture_publication_ownership_preserved: true,
    new_product_code_preserved: true,
    docs_reading_surface: true,
    docs_story_loom_identity: true,
    docs_readability_audit: true,
    tight_markdown_lists: true,
    cjk_reading_rhythm: true,
  }, null, 2));
}

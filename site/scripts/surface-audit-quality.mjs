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
const routeIdentity = read("src/styles/route-identities.css");
const routeScenes = read("src/styles/story-loom-route-refinements.css");
const docsConfig = read("docs-site/astro.config.mjs");
const docsAudit = read("docs-site/src/styles/surface-audit.css");
const docsIdentity = read("docs-site/src/styles/story-loom-docs.css");
const docsReadability = read("docs-site/src/styles/readability-audit.css");
const docsHeader = read("docs-site/src/styles/product-header-parity.css");
const docsActions = read("docs-site/src/components/QuillframeActions.astro");

check(main.includes('import "./styles/index.css"'), "product site must load the single CSS entrypoint");
check(!productIndex.includes("surface-audit.css"), "product site must not use a final audit override layer");
check(!exists("src/styles/surface-audit.css"), "retired product surface-audit.css must stay deleted");
check(productIndex.includes("atelier.css"), "Homepage Atelier composition must remain explicit");
check(productIndex.includes("tool-workbench-kawaii.css") && productIndex.includes("story-loom-route-refinements.css"), "Story Loom workstation and route-language layers must stay active");
check(productIndex.indexOf("architecture-explorer.css") < productIndex.indexOf("embedded-features.css"), "route defaults must precede shared product-language composition");
check(productIndex.indexOf("embedded-features.css") < productIndex.indexOf("route-identities.css"), "route identity must refine shared workbench composition");
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
check(routeIdentity.includes("never becomes a second hero card or route wallpaper"), "route visual slots must preserve the page-canvas boundary");
check(!routeIdentity.includes("radial-gradient"), "route visual-slot owner must not reintroduce route-level radial wallpaper");

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
check(!workbench.includes("radial-gradient"), "Inspector/Playground/Agent workstation layer must not paint route-level radial wallpaper");
for (const marker of ["Route-specific Story Loom scenes", "♡ STORY STATE", "LOCAL ONLY", "AGENT PATCH BAY"]) {
  check(routeScenes.includes(marker), `route Story Loom scene missing ${marker}`);
}
check(!routeScenes.includes(".architecture-entry") && !routeScenes.includes(".publication-workbench-entry"), "new route-scene layer must not take ownership of Architecture or Publication");
check(!routeScenes.includes("radial-gradient"), "late route-scene refinement must not reintroduce hero/card wallpaper");

/* Docs remain reading-first while their product chrome stays synchronized with
 * the current Quillframe Product Site shell. */
check(docsConfig.includes('"./src/styles/surface-audit.css"'), "Starlight must keep its docs-specific reading-surface audit");
check(docsConfig.includes('"./src/styles/story-loom-docs.css"'), "Starlight must load the restrained Story Loom identity layer");
check(docsConfig.includes('"./src/styles/readability-audit.css"'), "Starlight must load the docs readability pass");
check(docsConfig.includes('"./src/styles/product-header-parity.css"'), "Starlight must load the dedicated shared-shell header owner");
check(docsConfig.indexOf('surface-audit.css') < docsConfig.indexOf('story-loom-docs.css'), "docs Story Loom identity must refine the neutral reading surface");
check(docsConfig.indexOf('story-loom-docs.css') < docsConfig.indexOf('readability-audit.css'), "docs readability must remain after identity styling");
check(docsConfig.indexOf('readability-audit.css') < docsConfig.indexOf('product-header-parity.css'), "docs shell owner may load last but must remain scoped to chrome");
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

check(docsHeader.includes("Quillframe Docs product-shell owner"), "Docs final header layer must document its shared-shell ownership");
check(docsHeader.includes("background: color-mix(in oklab, var(--qf-surface-solid) 94%, transparent)") && docsHeader.includes("box-shadow: none"), "Docs top chrome must use the same quiet canvas language as ProductShell");
check(!docsHeader.includes("radial-gradient") && !docsHeader.includes("!important"), "Docs shell owner must not use route wallpaper or specificity escape hatches");
for (const route of ["/product", "/studio", "/architecture", "/publication"]) {
  check(docsActions.includes(`href=\"${route}\"`), `Docs primary product navigation missing ${route}`);
}
check(docsActions.includes('class="nf-product-link nf-docs-nav-link"'), "Docs primary navigation must include the Docs entry");
check(docsActions.includes('class="nf-product-link nf-github-link"') && docsActions.includes("https://github.com/xiaooye/Quillframe"), "Docs primary navigation must include the canonical GitHub repository");
check(docsActions.includes("https://studio.quillframe.wei-dev.com"), "Docs Hosted Studio action must use the current Quillframe Studio domain");
check(docsActions.includes('rel="noopener noreferrer"'), "Docs external product-shell links must use safe new-window semantics");

check(!workbench.includes("!important") && !routeIdentity.includes("!important") && !routeScenes.includes("!important") && !docsIdentity.includes("!important"), "Story Loom identity layers must not depend on specificity escalation");

if (failures.length) {
  for (const failure of failures) console.error(`surface-audit-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_surface_identity_quality_v12",
    status: "pass",
    product_final_override: false,
    product_editorial_flattening: false,
    route_wallpaper_layer_active: false,
    route_scene_wallpaper: false,
    workbench_wallpaper: false,
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
    docs_shell_synced: true,
    docs_github_entry: true,
    docs_current_quillframe_identity: true,
    tight_markdown_lists: true,
    cjk_reading_rhythm: true,
  }, null, 2));
}

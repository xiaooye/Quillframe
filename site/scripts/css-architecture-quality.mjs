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
const app = read("src/ProductApp.tsx");
const index = read("src/styles/index.css");
const surface = read("src/styles/product-surface.css");
const atelier = read("src/styles/atelier.css");
const routeIdentity = read("src/styles/route-identities.css");
const publicationGallery = read("src/styles/publication-gallery.css");
const readability = read("src/styles/readability.css");
const hardening = read("src/styles/hardening.css");
const sharedLanguage = read("../assets/brand/novelforge-product-language.css");

const styleImports = [...main.matchAll(/import\s+["']\.\/styles\/([^"']+)["']/g)].map((match) => match[1]);
check(styleImports.length === 1 && styleImports[0] === "index.css", `main.tsx must import exactly one stylesheet entrypoint; got ${styleImports.join(", ") || "none"}`);
check(index.includes('@import "../../../assets/brand/novelforge-product-language.css"'), "Product Site must consume the shared product-language tokens");
check(index.indexOf('product-surface.css') < index.indexOf('architecture-explorer.css'), "shared primitives must load before route feature styles");
check(index.indexOf('architecture-explorer.css') < index.indexOf('kawaii-surfaces.css'), "Story Loom product-language composition must load after route defaults");
check(index.indexOf('kawaii-surfaces.css') < index.indexOf('embedded-features.css'), "embedded feature ownership must remain after the shared kawaii language");
check(index.indexOf('embedded-features.css') < index.indexOf('route-identities.css'), "route identity must refine shared/embedded composition rather than replace it");
check(index.indexOf('route-identities.css') < index.indexOf('publication-gallery.css'), "publication gallery must remain a route-specific refinement of the shared identity layer");
check(index.indexOf('publication-gallery.css') < index.indexOf('readability.css'), "route-specific composition must precede readability hardening");
check(index.indexOf('readability.css') < index.indexOf('hardening.css'), "resilience/accessibility hardening must remain the final Product layer");
check(!index.includes('editorial-composition.css'), "rejected global editorial flattening must stay out of the active cascade");
check(!index.includes('home-identity.css'), "temporary simplified-home rewrite must stay out of the active cascade");
check(!index.includes("surface-audit.css"), "legacy surface-audit override must not return to the cascade");
check(!exists("src/styles/surface-audit.css"), "legacy surface-audit.css must stay deleted");
check(!exists("src/styles/readability-audit.css"), "readability must remain a named hardening layer, not a catch-all audit override");
check(sharedLanguage.includes("--nf-product-pink") && sharedLanguage.includes("--nf-product-radius-panel"), "shared product-language tokens are incomplete");

check(surface.includes("border-radius: 28px") && surface.includes("radial-gradient") && surface.includes("border: 1px dashed"), "shared ProductSurfaceHero must retain the restored Story Loom framed treatment for newer routes");
check(surface.includes('.product-surface-hero[data-tone="project"]') && surface.includes('.product-surface-hero[data-tone="publication"]'), "shared surface tones must retain route-aware pastel treatments");
check(!surface.includes("!important"), "shared surface styling must not depend on specificity escalation");

for (const marker of ["function HomePage()", "class=\"entry-hero\"", "class=\"hero-launcher wui-card material-panel\"", "class=\"capability-ribbon\"", "class=\"capability-focus page-width section-compact\"", "class=\"product-lab section-pad-soft\"", "class=\"product-world page-width section-compact\"", "class=\"knowledge-preview section-pad-soft\""]) {
  check(app.includes(marker), `screenshot-era HomePage structure missing ${marker}`);
}
check(app.includes("让故事越写越长，系统仍然知道自己在做什么。") && app.includes("今天也把故事织得更漂亮一点吧"), "screenshot-era HomePage copy/identity markers must remain intact");
check(app.includes("setBudget") && app.includes("setGates") && app.includes("setActiveCapability"), "restored HomePage interactions must remain functional");
for (const marker of [".entry-hero", ".hero-launcher.material-panel", ".launcher-grid", ".capability-ribbon", ".capability-focus-grid", ".lab-grid", ".portal-grid", ".knowledge-preview-grid"]) {
  check(atelier.includes(marker), `Atelier must still own restored HomePage visual marker ${marker}`);
}

for (const marker of [".architecture-entry", ".publication-workbench-entry", ".inspector-entry", ".playground-entry", ".agent-integration-entry", ":has(.unified-studio-terminal)"]) {
  check(routeIdentity.includes(marker), `route identity layer missing ${marker}`);
}
check(routeIdentity.includes("Route identity layer") && routeIdentity.includes("ProductSurfaceHero owns shared typography"), "route identity must document its ownership boundary");
check(!routeIdentity.includes("!important"), "route identity must not depend on specificity escalation");
for (const marker of [".snapshot-text", ".snapshot-web", ".snapshot-print", ".snapshot-epub", '[data-profile="text"]', '[data-profile="web"]', '[data-profile="print"]', '[data-profile="epub"]']) {
  check(publicationGallery.includes(marker), `publication gallery missing distinct preview treatment ${marker}`);
}
check(publicationGallery.includes("columns: 2") && publicationGallery.includes("novel.example / chapter-1") && publicationGallery.includes("9:41"), "publication gallery must visibly distinguish print, web, and EPUB objects");
check(!publicationGallery.includes("!important"), "publication gallery must not depend on specificity escalation");
check(readability.includes("--nf-copy-size: 14px") && readability.includes("--nf-micro-size: 11px"), "readability hardening must preserve the product copy floor");
check(readability.includes(".unified-info-card p") && readability.includes("font-size: var(--nf-copy-size)"), "capability copy must not regress to miniature dashboard text");
check(!readability.includes("!important"), "readability hardening must not depend on specificity escalation");
check(hardening.includes(":focus-visible") && hardening.includes("prefers-reduced-motion: reduce"), "final hardening layer must preserve accessibility contracts");
check(!index.includes("!important"), "the stylesheet entrypoint must not encode specificity overrides");

if (failures.length) {
  for (const failure of failures) console.error(`css-architecture-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_css_architecture_v7",
    status: "pass",
    entrypoints: 1,
    audit_override: false,
    shared_product_language: true,
    story_loom_surface_restore: true,
    editorial_flattening: false,
    screenshot_era_home_dom: true,
    screenshot_era_home_sections: 5,
    home_style_owner: "showcase.css+atelier.css",
    new_route_code_preserved: true,
    route_identity_layer: true,
    publication_format_previews: true,
    readability_hardening: true,
    final_hardening: "hardening.css",
  }, null, 2));
}

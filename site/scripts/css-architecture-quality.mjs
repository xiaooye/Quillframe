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
const index = read("src/styles/index.css");
const editorial = read("src/styles/editorial-composition.css");
const routeIdentity = read("src/styles/route-identities.css");
const publicationGallery = read("src/styles/publication-gallery.css");
const interaction = read("src/styles/interaction-contract.css");
const readability = read("src/styles/readability.css");
const hardening = read("src/styles/hardening.css");
const sharedLanguage = read("../assets/brand/novelforge-product-language.css");

const styleImports = [...main.matchAll(/import\s+["']\.\/styles\/([^"']+)["']/g)].map((match) => match[1]);
check(styleImports.length === 1 && styleImports[0] === "index.css", `main.tsx must import exactly one stylesheet entrypoint; got ${styleImports.join(", ") || "none"}`);
check(index.includes('@import "../../../assets/brand/novelforge-product-language.css"'), "Product Site must consume the shared product-language tokens");
check(index.indexOf('product-surface.css') < index.indexOf('architecture-explorer.css'), "shared primitives must load before route feature styles");
check(index.indexOf('architecture-explorer.css') < index.indexOf('kawaii-surfaces.css'), "product-language composition must load after route defaults");
check(index.indexOf('tool-workbench-kawaii.css') < index.indexOf('editorial-composition.css'), "clean editorial composition must refine the kawaii route language");
check(index.indexOf('editorial-composition.css') < index.indexOf('embedded-features.css'), "embedded feature ownership must remain after shared editorial composition");
check(index.indexOf('embedded-features.css') < index.indexOf('route-identities.css'), "route identity must refine shared/embedded composition rather than replace it");
check(index.indexOf('route-identities.css') < index.indexOf('publication-gallery.css'), "publication gallery must remain a route-specific refinement of the shared identity layer");
check(index.indexOf('publication-gallery.css') < index.indexOf('interaction-contract.css'), "shared interaction contract must remain later than visual route identity layers");
check(index.indexOf('interaction-contract.css') < index.indexOf('readability.css'), "interaction composition must precede readability hardening");
check(index.indexOf('readability.css') < index.indexOf('hardening.css'), "resilience/accessibility hardening must remain the final Product layer");
check(!index.includes("surface-audit.css"), "legacy surface-audit override must not return to the cascade");
check(!exists("src/styles/surface-audit.css"), "legacy surface-audit.css must stay deleted");
check(!exists("src/styles/readability-audit.css"), "readability must remain a named hardening layer, not a catch-all audit override");
check(sharedLanguage.includes("--nf-product-pink") && sharedLanguage.includes("--nf-product-radius-panel"), "shared product-language tokens are incomplete");
check(editorial.includes("Kawaii is identity, not container chrome") && editorial.includes(".product-surface-hero") && editorial.includes(".publication-workbench-entry"), "editorial composition must explicitly encode the clean-kawaii surface policy");
check(editorial.includes("background: transparent") && editorial.includes("border-bottom: 1px solid"), "editorial composition must use neutral surfaces and hairline hierarchy");
check(!editorial.includes("!important"), "editorial composition must not depend on specificity escalation");
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
for (const marker of [".product-appbar", ".mobile-nav", ".command-surface", ".footer-grid", ":root.dark", "@media (max-width: 980px)"]) {
  check(interaction.includes(marker), `shared interaction contract missing ${marker}`);
}
check(interaction.includes("backdrop-filter: none") && interaction.includes("overscroll-behavior: contain"), "interaction contract must avoid gratuitous shell blur and keep mobile navigation contained");
check(interaction.includes("--pe-header-h: 60px") && interaction.includes("min-block-size: 44px"), "interaction contract must retain compact shell density without losing touch ergonomics");
check(!interaction.includes("!important"), "interaction contract must not depend on specificity escalation");
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
    schema: "novelforge_css_architecture_v5",
    status: "pass",
    entrypoints: 1,
    audit_override: false,
    shared_product_language: true,
    editorial_composition: true,
    kawaii_as_accent_not_container: true,
    route_identity_layer: true,
    publication_format_previews: true,
    interaction_contract: true,
    compact_shell_density: true,
    responsive_navigation_contract: true,
    dark_interaction_contract: true,
    readability_hardening: true,
    final_hardening: "hardening.css",
  }, null, 2));
}

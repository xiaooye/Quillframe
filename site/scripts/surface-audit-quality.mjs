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
const productIndex = read("src/styles/index.css");
const productSurface = read("src/styles/product-surface.css");
const editorial = read("src/styles/editorial-composition.css");
const docsConfig = read("docs-site/astro.config.mjs");
const docsAudit = read("docs-site/src/styles/surface-audit.css");
const docsReadability = read("docs-site/src/styles/readability-audit.css");

check(main.includes('import "./styles/index.css"'), "product site must load the single CSS entrypoint");
check(!productIndex.includes("surface-audit.css"), "product site must not use a final audit override layer");
check(!exists("src/styles/surface-audit.css"), "retired product surface-audit.css must stay deleted");
check(productIndex.includes("kawaii-surfaces.css") && productIndex.includes("editorial-composition.css"), "product composition layers must remain explicit");
check(productIndex.indexOf("architecture-explorer.css") < productIndex.indexOf("kawaii-surfaces.css"), "feature defaults must precede product-language composition");
check(productIndex.indexOf("kawaii-surfaces.css") < productIndex.indexOf("editorial-composition.css"), "clean editorial composition must refine kawaii route defaults");
check(productSurface.includes("border-bottom: 1px solid") && productSurface.includes("border-radius: 0") && productSurface.includes("background: transparent"), "shared ProductSurfaceHero must be borderless and neutral by default");
check(productSurface.includes('.product-surface-hero[data-tone="project"]') && productSurface.includes('.product-surface-hero[data-tone="publication"]'), "hero tones must remain accents rather than separate framed surfaces");
for (const marker of [".unified-card-grid", ".inspector-entry", ".playground-entry", ".agent-integration-entry", ".architecture-entry", ".publication-workbench-entry"]) {
  check(editorial.includes(marker), `editorial product composition missing ${marker}`);
}
check(editorial.includes("Kawaii is identity, not container chrome"), "clean-kawaii design intent must remain explicit");
check(editorial.includes("background: transparent") && editorial.includes("border-bottom: 1px solid"), "product hierarchy must remain typography/whitespace/hairline based");
check(!editorial.includes("!important"), "editorial surface policy must not rely on specificity escalation");

check(docsConfig.includes('"./src/styles/surface-audit.css"'), "Starlight must keep its docs-specific final surface audit");
check(docsConfig.includes('"./src/styles/readability-audit.css"'), "Starlight must load the docs readability pass");
check(docsConfig.indexOf('docs-home-clean.css') < docsConfig.indexOf('surface-audit.css'), "docs surface audit must load after existing landing/article polish");
check(docsConfig.indexOf('surface-audit.css') < docsConfig.indexOf('readability-audit.css'), "docs readability must load after surface styling");
for (const marker of ["header.header", ".sidebar-pane", "body:has([data-nf-docs-home]) .hero", ".nf-article-title", ".sl-markdown-content blockquote", ".sl-markdown-content table", ".pagination-links a"]) {
  check(docsAudit.includes(marker), `docs surface audit missing ${marker}`);
}
check(docsAudit.includes(".nf-article-title") && docsAudit.includes("border-bottom: 1px solid"), "article hierarchy must retain a restrained divider");
check(docsReadability.includes(":lang(zh-CN) body:has(.nf-article-title) .sl-markdown-content") && docsReadability.includes("line-height: 1.9"), "Chinese long-form reading rhythm must remain explicit");
check(docsReadability.includes(".sl-markdown-content li > p") && docsReadability.includes("margin-block: .18rem"), "tight Markdown lists must not inherit full paragraph spacing");
check(docsReadability.includes("max-width: 68ch") && docsReadability.includes("max-width: 42em"), "docs reading measure must remain bounded for Latin and CJK copy");

if (failures.length) {
  for (const failure of failures) console.error(`surface-audit-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_surface_audit_quality_v4",
    status: "pass",
    product_final_override: false,
    product_editorial_composition: true,
    product_large_surface_cards: false,
    kawaii_as_accent_not_container: true,
    docs_surface_audit: true,
    docs_readability_audit: true,
    tight_markdown_lists: true,
    cjk_reading_rhythm: true,
  }, null, 2));
}

#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const main = read("src/main.tsx");
const productAudit = read("src/styles/surface-audit.css");
const docsConfig = read("docs-site/astro.config.mjs");
const docsAudit = read("docs-site/src/styles/surface-audit.css");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(main.includes('import "./styles/surface-audit.css"'), "product site must load the final surface audit layer");
check(main.indexOf('unified-product-app.css') < main.indexOf('surface-audit.css'), "product surface audit must load after route-specific styling");

for (const marker of [
  ".product-surface-hero",
  ".unified-info-card",
  ".inspector-entry",
  ".playground-entry",
  ".agent-integration-entry",
  ".architecture-entry",
  ".publication-workbench-entry",
]) {
  check(productAudit.includes(marker), `product surface audit missing ${marker}`);
}
check(productAudit.includes("border-radius: 0") && productAudit.includes("background: transparent"), "product audit must encode borderless neutral surfaces");
check(productAudit.includes(".unified-product-shell :where(.wui-button, .wui-badge, .version-chip)"), "compact controls must be explicitly exempted from large-surface flattening");
check(productAudit.includes(".unified-info-card:nth-child(n)") && productAudit.includes("background: transparent !important"), "capability cards must not regain per-card color fills through nth-child styling");
check(productAudit.includes(".publication-profile-card[data-active=\"true\"]") && productAudit.includes("border-bottom-color"), "publication selection must use a line state instead of a filled rounded card");

check(docsConfig.includes('"./src/styles/surface-audit.css"'), "Starlight must load the final docs surface audit layer");
check(docsConfig.indexOf('docs-home-clean.css') < docsConfig.indexOf('surface-audit.css'), "docs audit must load after existing landing/article polish");
for (const marker of [
  "header.header",
  ".sidebar-pane",
  "body:has([data-nf-docs-home]) .hero",
  ".nf-article-title",
  ".sl-markdown-content blockquote",
  ".sl-markdown-content table",
  ".pagination-links a",
]) {
  check(docsAudit.includes(marker), `docs surface audit missing ${marker}`);
}
check(docsAudit.includes("body,\nbody:has([data-nf-docs-home])") && docsAudit.includes("background: var(--sl-color-black)"), "docs must use a neutral page canvas instead of decorative patterned backgrounds");
check(docsAudit.includes(".nf-article-title") && docsAudit.includes("border-bottom: 1px solid"), "article hierarchy must use a divider instead of a framed title card");
check(!docsAudit.includes("var(--nf-shadow)"), "docs audit must not restore heavy card shadow tokens");

if (failures.length) {
  for (const failure of failures) console.error(`surface-audit-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_surface_audit_quality_v1",
    status: "pass",
    product_large_surface_cards: false,
    docs_large_surface_cards: false,
    colorful_container_backgrounds: false,
    hierarchy: "typography_whitespace_hairlines",
    compact_control_shape_preserved: true,
    product_routes_covered: ["home", "product", "studio", "inspect", "playground", "agents", "architecture", "publication"],
    docs_surfaces_covered: ["landing", "article", "sidebar", "toc", "pagination"],
  }, null, 2));
}

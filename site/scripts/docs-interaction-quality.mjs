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

const config = read("docs-site/astro.config.mjs");
const actions = read("docs-site/src/components/NovelForgeActions.astro");
const interaction = read("docs-site/src/styles/interaction-contract.css");

check(config.includes('"./src/styles/interaction-contract.css"'), "Starlight must load the documentation interaction contract");
check(config.indexOf('readability-audit.css') < config.indexOf('interaction-contract.css'), "docs interaction contract must refine the established readability layer");
check(actions.includes('<details class="nf-product-menu">') && actions.includes('class="nf-product-menu__panel"'), "docs must preserve product navigation through an accessible mobile disclosure");
check(actions.includes('productMenu: "产品"') && actions.includes('productMenu: "Product"'), "mobile product navigation must be natively localized");
for (const href of ["/product", "/studio", "/architecture", "/publication", "https://studio.novelforge.wei-dev.com"]) {
  const occurrences = actions.split(`href="${href}"`).length - 1;
  check(occurrences >= 2, `desktop and mobile docs product navigation must both expose ${href}`);
}
for (const marker of [
  "--sl-nav-height: 3.75rem",
  "header.header",
  ".nf-product-menu",
  ".nf-product-menu__panel",
  "overscroll-behavior: contain",
  "backdrop-filter: none",
  ':root[data-theme="dark"]',
  "@media (max-width: 68rem)",
  "@media (max-width: 50rem)",
  "@media (pointer: coarse)",
  "@media (prefers-contrast: more)",
  "@media (forced-colors: active)",
  "@media (prefers-reduced-motion: reduce)",
]) {
  check(interaction.includes(marker), `docs interaction contract missing ${marker}`);
}
check(interaction.includes(".sidebar-content li > a[aria-current=\"page\"]") && interaction.includes(".right-sidebar a[aria-current=\"true\"]"), "docs interaction contract must preserve explicit sidebar and TOC active states");
check(interaction.includes("min-height: 2.75rem") && interaction.includes("pointer: coarse"), "coarse-pointer docs navigation must retain 44px-class touch targets");
check(!interaction.includes("!important"), "docs interaction contract must not depend on specificity escape hatches");

if (failures.length) {
  for (const failure of failures) console.error(`docs-interaction-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_docs_interaction_quality_v1",
    status: "pass",
    engine: "Astro Starlight",
    compact_header: true,
    mobile_product_handoff: true,
    mobile_product_routes: 5,
    sidebar_active_state: true,
    toc_active_state: true,
    dark_interaction_contract: true,
    coarse_pointer_targets: true,
    increased_contrast: true,
    forced_colors: true,
    reduced_motion: true,
    gratuitous_header_blur: false,
  }, null, 2));
}

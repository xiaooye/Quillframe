#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const main = read("src/main.tsx");
const resilience = read("src/ProductResilience.tsx");
const indexHtml = read("index.html");
const index = read("src/styles/index.css");
const interaction = read("src/styles/interaction-contract.css");
const hardening = read("src/styles/hardening.css");

check(main.includes('from "./ProductResilience"'), "main must import the product resilience boundary");
for (const marker of ["ProductFailureBoundary", "ProductNotFound", "productRoutes", "normalizedPath"]) check(main.includes(marker), `main missing hardening marker ${marker}`);
for (const route of ["/", "/start", "/product", "/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) check(main.includes(`"${route}"`), `direct-route allowlist missing ${route}`);
check(resilience.includes("ErrorBoundary"), "product failure UI must use Solid ErrorBoundary");
check(indexHtml.includes('class="skip-link nf-skip-link"') && indexHtml.includes('href="#main-content"'), "document shell must own exactly one skip link to main content");
check(resilience.includes('role="alert"'), "render failure must be announced as an alert");
check(resilience.includes("404"), "direct unknown routes must render a 404 surface");
check(index.includes('@import "./interaction-contract.css";'), "shared interaction contract must ship in the Product cascade");
check(index.trim().endsWith('@import "./hardening.css";'), "hardening.css must be the final Product Site stylesheet layer");
for (const marker of [":focus-visible", "prefers-reduced-motion: reduce", "prefers-contrast: more", "forced-colors: active", "pointer: coarse", "overflow-wrap: anywhere", "touch-action: manipulation"]) check(hardening.includes(marker), `hardening CSS missing ${marker}`);
check(hardening.includes('body:has(.unified-product-shell .command-dialog[open])') && hardening.includes("overflow: hidden"), "open command palette must lock background scrolling");
check(hardening.includes("overscroll-behavior-inline: contain"), "horizontal code/table overflow must stay contained");
check(interaction.includes("overscroll-behavior: contain") && interaction.includes("backdrop-filter: none"), "mobile/transient shell interaction must avoid scroll leakage and gratuitous blur");
check(!hardening.includes("!important") && !interaction.includes("!important"), "interaction hardening must not use specificity escape hatches");

if (failures.length) {
  for (const failure of failures) console.error(`product-hardening-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_product_hardening_v2",
    status: "pass",
    error_boundary: true,
    direct_404: true,
    skip_link_owner: "document",
    focus_visible: true,
    reduced_motion: true,
    increased_contrast: true,
    forced_colors: true,
    coarse_pointer_targets: true,
    modal_scroll_lock: true,
    overscroll_containment: true,
    gratuitous_shell_blur: false,
  }, null, 2));
}

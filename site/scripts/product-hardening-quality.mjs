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
const index = read("src/styles/index.css");
const hardening = read("src/styles/hardening.css");

check(main.includes('from "./ProductResilience"'), "main must import the product resilience boundary");
for (const marker of ["ProductFailureBoundary", "ProductSkipLink", "ProductNotFound", "productRoutes", "normalizedPath"]) check(main.includes(marker), `main missing hardening marker ${marker}`);
for (const route of ["/", "/start", "/product", "/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) check(main.includes(`"${route}"`), `direct-route allowlist missing ${route}`);
check(resilience.includes("ErrorBoundary"), "product failure UI must use Solid ErrorBoundary");
check(resilience.includes('href="#main-content"'), "product site must provide a skip link to main content");
check(resilience.includes('role="alert"'), "render failure must be announced as an alert");
check(resilience.includes("404"), "direct unknown routes must render a 404 surface");
check(index.trim().endsWith('@import "./hardening.css";'), "hardening.css must be the final Product Site stylesheet layer");
for (const marker of [":focus-visible", "prefers-reduced-motion: reduce", "forced-colors: active", "pointer: coarse", "overflow-wrap: anywhere"]) check(hardening.includes(marker), `hardening CSS missing ${marker}`);
check(!hardening.includes("!important"), "hardening CSS must not use specificity escape hatches");

if (failures.length) {
  for (const failure of failures) console.error(`product-hardening-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "novelforge_product_hardening_v1", status: "pass", error_boundary: true, direct_404: true, skip_link: true, focus_visible: true, reduced_motion: true, forced_colors: true, coarse_pointer_targets: true }, null, 2));
}

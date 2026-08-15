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
const sharedLanguage = read("../assets/brand/novelforge-product-language.css");

const styleImports = [...main.matchAll(/import\s+["']\.\/styles\/([^"']+)["']/g)].map((match) => match[1]);
check(styleImports.length === 1 && styleImports[0] === "index.css", `main.tsx must import exactly one stylesheet entrypoint; got ${styleImports.join(", ") || "none"}`);
check(index.includes('@import "../../../assets/brand/novelforge-product-language.css"'), "Product Site must consume the shared product-language tokens");
check(index.indexOf('product-surface.css') < index.indexOf('architecture-explorer.css'), "shared primitives must load before route feature styles");
check(index.indexOf('architecture-explorer.css') < index.indexOf('kawaii-surfaces.css'), "product-language composition must load after route defaults");
check(!index.includes("surface-audit.css"), "legacy surface-audit override must not return to the cascade");
check(!exists("src/styles/surface-audit.css"), "legacy surface-audit.css must stay deleted");
check(sharedLanguage.includes("--nf-product-pink") && sharedLanguage.includes("--nf-product-radius-panel"), "shared product-language tokens are incomplete");
check(!index.includes("!important"), "the stylesheet entrypoint must not encode specificity overrides");

if (failures.length) {
  for (const failure of failures) console.error(`css-architecture-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "novelforge_css_architecture_v1", status: "pass", entrypoints: 1, audit_override: false, shared_product_language: true }, null, 2));
}

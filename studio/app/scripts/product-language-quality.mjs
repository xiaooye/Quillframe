#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const repoRoot = path.resolve(root, "../..");
const read = (base, relative) => fs.readFileSync(path.join(base, relative), "utf8");
const exists = (base, relative) => fs.existsSync(path.join(base, relative));
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const main = read(root, "src/main.tsx");
const index = read(root, "src/styles/index.css");
const studioLanguage = read(root, "src/styles/product-language.css");
const sharedLanguage = read(repoRoot, "assets/brand/novelforge-product-language.css");
const i18n = read(root, "src/i18n.tsx");
const styleImports = [...main.matchAll(/import\s+["']\.\/styles\/([^"']+)["']/g)].map((match) => match[1]);

check(styleImports.length === 1 && styleImports[0] === "index.css", "Studio main.tsx must import exactly one stylesheet entrypoint");
check(index.includes('../../../../assets/brand/novelforge-product-language.css'), "Studio must consume the repo-level product-language tokens");
check(index.trim().endsWith('@import "./product-language.css";'), "Studio product-language mapping must load last");
check(!index.includes("visual-fixes.css") && !exists(root,"src/styles/visual-fixes.css"), "retired visual-fixes layer must stay deleted");
check(main.includes('dataset.productLanguage = "novelforge-kawaii-v1"'), "Studio must identify the shared product language in the document contract");
for (const token of ["--nf-product-pink","--nf-product-lilac","--nf-product-mint","--nf-product-radius-panel"]) check(sharedLanguage.includes(token), `shared product language missing ${token}`);
for (const marker of [".nf-sidebar",".nf-topbar",".nf-page-intro",".nf-command",".nf-bottom-nav-item"]) check(studioLanguage.includes(marker), `Studio product-language mapping missing ${marker}`);
check(i18n.includes("document.documentElement.dataset.locale = next"), "Studio locale changes must expose the same data-locale selector contract as the Product Site");
check(!studioLanguage.includes("!important"), "Studio product-language layer must not depend on specificity escape hatches");

if(failures.length){for(const failure of failures) console.error(`product-language-quality: FAIL: ${failure}`);process.exitCode=1}else console.log(JSON.stringify({schema:"novelforge_studio_product_language_v2",status:"pass",shared_tokens:true,single_css_entrypoint:true,retired_visual_fixes:true,product_language:"novelforge-kawaii-v1"},null,2));

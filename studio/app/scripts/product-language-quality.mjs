#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const repoRoot = path.resolve(root, "../..");
const read = (base, relative) => fs.readFileSync(path.join(base, relative), "utf8");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const main = read(root, "src/main.tsx");
const index = read(root, "src/styles/index.css");
const studioLanguage = read(root, "src/styles/product-language.css");
const experience = read(root, "src/styles/experience-polish.css");
const sharedLanguage = read(repoRoot, "assets/brand/quillframe-product-language.css");
const i18n = read(root, "src/i18n.tsx");
const styleImports = [...main.matchAll(/import\s+["']\.\/styles\/([^"']+)["']/g)].map((match) => match[1]);

check(styleImports.length === 1 && styleImports[0] === "index.css", "Studio main.tsx must import exactly one stylesheet entrypoint");
check(index.includes('../../../../assets/brand/quillframe-product-language.css'), "Studio must consume the repo-level product-language tokens");
check(index.indexOf('@import "./product-language.css";') < index.indexOf('@import "./experience-polish.css";'), "Studio workstation composition must refine the semantic product-language mapping");
check(index.indexOf('@import "./experience-polish.css";') < index.indexOf('@import "./hardening.css";'), "Studio workstation composition must load before final hardening");
check(index.trim().endsWith('@import "./hardening.css";'), "Studio hardening must be the final CSS layer");
check(!index.includes("visual-fixes.css"), "legacy visual-fixes path must not participate in the active cascade");
check(main.includes('dataset.productLanguage = "quillframe-kawaii-v1"'), "Studio must identify the shared product language in the document contract");
for (const token of ["--qf-product-pink","--qf-product-lilac","--qf-product-mint","--qf-product-radius-panel"]) check(sharedLanguage.includes(token), `shared product language missing ${token}`);
for (const marker of [".nf-sidebar",".nf-topbar",".nf-page-intro",".nf-command",".nf-bottom-nav"]) check(studioLanguage.includes(marker), `Studio product-language mapping missing ${marker}`);
for (const marker of [".nf-main-column", ".nf-nav-section", ".nf-page-intro", ".nf-workspace-stage", ".nf-command", ":root.dark", "@media (max-width: 719px)"]) check(experience.includes(marker), `Studio workstation composition missing ${marker}`);
check(experience.includes("Studio parity pass") && experience.includes("same soft Quillframe atmosphere"), "Studio parity layer must document its workstation-only ownership");
check(experience.includes("var(--qf-product-pink-soft)") && experience.includes("var(--qf-product-lilac-soft)") && experience.includes("var(--qf-product-mint-soft)"), "Studio parity layer must consume shared Quillframe color language rather than inventing local colors");
check(i18n.includes("document.documentElement.dataset.locale = next"), "Studio locale changes must expose the same data-locale selector contract as the Product Site");
check(!studioLanguage.includes("!important"), "Studio product-language layer must not depend on specificity escape hatches");
check(!experience.includes("!important"), "Studio workstation composition must not depend on specificity escape hatches");
check(!studioLanguage.includes('.nf-bottom-nav-item[data-active'), "WeiUI must retain generic bottom-nav active chrome ownership");

if(failures.length){
  for(const failure of failures) console.error(`product-language-quality: FAIL: ${failure}`);
  process.exitCode=1;
}else{
  console.log(JSON.stringify({schema:"quillframe_studio_product_language_v5",status:"pass",shared_tokens:true,single_css_entrypoint:true,legacy_visual_fixes_in_cascade:false,workstation_parity:true,hardening_layer:"final",product_language:"quillframe-kawaii-v1"},null,2));
}

#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const readJson = (relative) => JSON.parse(read(relative));

const pkg = readJson("package.json");
const main = read("src/main.tsx");
const config = read("docs-site/astro.config.mjs");
const contentConfig = read("docs-site/src/content.config.ts");
const customCss = read("docs-site/src/styles/custom.css");
const manifest = JSON.parse(fs.readFileSync(path.resolve(siteRoot, "../docs/documentation_manifest.json"), "utf8"));
const stagedRoot = path.join(siteRoot, "docs-site", "src", "content", "docs");

const failures = [];
const requireCheck = (condition, message) => {
  if (!condition) failures.push(message);
};

function markdownCount(directory) {
  if (!fs.existsSync(directory)) return 0;
  let count = 0;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) count += markdownCount(absolute);
    else if (entry.isFile() && entry.name.endsWith(".md")) count += 1;
  }
  return count;
}

requireCheck(pkg.devDependencies?.astro === "7.1.6", "Astro must remain exact-pinned at 7.1.6");
requireCheck(pkg.devDependencies?.["@astrojs/starlight"] === "0.41.5", "Starlight must remain exact-pinned at 0.41.5");
requireCheck(pkg.scripts?.["docs:build"]?.includes("astro build docs-site"), "docs:build must build the Starlight app");
requireCheck(pkg.scripts?.build?.includes("docs:build"), "production build must include Starlight output");

requireCheck(config.includes('base: "/docs"'), "Starlight must own the /docs surface");
requireCheck(config.includes('lang: "zh-CN"') && config.includes('lang: "en"'), "Starlight must keep zh-CN and English locales");
requireCheck(config.includes("starlight({"), "docs app must remain powered by Starlight");
requireCheck(contentConfig.includes("docsLoader()") && contentConfig.includes("docsSchema()"), "Starlight content collection must use official loader and schema");
requireCheck(customCss.includes("--sl-content-width: 50rem"), "documentation reading width must stay bounded");
requireCheck(customCss.includes(':lang(zh-CN) .sl-markdown-content'), "Chinese typography override must remain explicit");

requireCheck(!main.includes("KnowledgePortal"), "legacy Knowledge Portal must not mount beside the product router");
requireCheck(!main.includes("KnowledgeExperience"), "product entry must not import the retired custom docs renderer");
requireCheck(main.includes("localizedDocsTarget"), "product SPA must hand /docs navigation to Starlight with locale preservation");

const expectedPages = manifest.documents.length * 2;
requireCheck(markdownCount(stagedRoot) === expectedPages, `Starlight staging must contain ${expectedPages} localized Markdown pages`);
requireCheck(fs.existsSync(path.join(stagedRoot, "why-novelforge.md")), "zh-CN why-novelforge route must be staged at the docs root");
requireCheck(fs.existsSync(path.join(stagedRoot, "en", "why-novelforge.md")), "English why-novelforge route must be staged under /en");

if (failures.length > 0) {
  for (const failure of failures) console.error(`docs-platform-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_docs_platform_quality_v1",
    status: "pass",
    engine: "Astro Starlight",
    astro: pkg.devDependencies.astro,
    starlight: pkg.devDependencies["@astrojs/starlight"],
    localized_pages: expectedPages,
    root_locale: "zh-CN",
    spa_docs_renderer: false,
  }, null, 2));
}

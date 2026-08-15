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
const siteTitle = read("docs-site/src/components/NovelForgeSiteTitle.astro");
const actions = read("docs-site/src/components/NovelForgeActions.astro");
const landing = read("docs-site/src/components/DocsLanding.astro");
const zhLandingRoute = read("docs-site/src/pages/index.astro");
const enLandingRoute = read("docs-site/src/pages/en/index.astro");
const stagingCompiler = read("scripts/build-starlight-content.mjs");
const verifier = read("scripts/verify-starlight-build.mjs");
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
requireCheck(pkg.scripts?.["docs:build"]?.includes("astro build --root docs-site"), "docs:build must execute Astro with docs-site as the real project root");
requireCheck(pkg.scripts?.["dev:docs"]?.includes("astro dev --root docs-site"), "dev:docs must execute Astro with docs-site as the real project root");
requireCheck(pkg.scripts?.["docs:build"]?.includes("verify-starlight-build.mjs"), "docs:build must verify emitted Starlight pages");
requireCheck(pkg.scripts?.build?.includes("docs:build"), "production build must include Starlight output");

requireCheck(config.includes('base: "/docs"'), "Starlight must own the /docs surface");
requireCheck(config.includes('outDir: "../dist/docs"'), "Starlight output must compose into site/dist/docs");
requireCheck(config.includes('lang: "zh-CN"') && config.includes('lang: "en"'), "Starlight must keep zh-CN and English locales");
requireCheck(config.includes("starlight({"), "docs app must remain powered by Starlight");
requireCheck(config.includes('SiteTitle: "./src/components/NovelForgeSiteTitle.astro"'), "docs header must override SiteTitle so product and docs homes remain distinct");
requireCheck(contentConfig.includes("docsLoader()") && contentConfig.includes("docsSchema()"), "Starlight content collection must use official loader and schema");
requireCheck(customCss.includes("--sl-content-width: 52rem"), "documentation reading width must stay deliberately bounded");
requireCheck(customCss.includes(':lang(zh-CN) .sl-markdown-content'), "Chinese typography override must remain explicit");
requireCheck(customCss.includes('a[aria-current="page"]'), "documentation navigation must retain a strong current-page state");
requireCheck(customCss.includes(".nf-link-grid") && customCss.includes(".nf-link-card"), "curated docs landing must retain stable task-path card styling");
requireCheck(customCss.includes(".nf-tier-grid") && customCss.includes(".nf-reference-callout"), "curated docs landing must retain its layered reference hierarchy");
requireCheck(siteTitle.includes('class="nf-brand-home" href="/"'), "NovelForge docs brand must navigate to the main product home");
requireCheck(siteTitle.includes('english ? "/docs/en/" : "/docs/"'), "docs header must retain a locale-aware documentation-home link");
requireCheck(siteTitle.includes('english ? "Docs" : "文档"'), "docs header must label the documentation namespace natively");
requireCheck(actions.includes('english ? "Product" : "产品"'), "Product header action must remain locale-aware");

requireCheck(!main.includes("KnowledgePortal"), "legacy Knowledge Portal must not mount beside the product router");
requireCheck(!main.includes("KnowledgeExperience"), "product entry must not import the retired custom docs renderer");
requireCheck(main.includes("localizedDocsTarget"), "product SPA must hand /docs navigation to Starlight with locale preservation");
requireCheck(stagingCompiler.includes("rewriteHtmlAttributes"), "Starlight staging must rewrite raw HTML document attributes");
requireCheck(stagingCompiler.includes("copyRelativeAsset"), "Starlight staging must copy repository-local documentation assets");
requireCheck(stagingCompiler.includes('if (doc.id === "docs-home") continue;'), "docs home must be reserved for the curated Starlight landing routes");

const expectedLocalizedPages = manifest.documents.length * 2;
const expectedStagedMarkdownPages = (manifest.documents.length - 1) * 2;
requireCheck(markdownCount(stagedRoot) === expectedStagedMarkdownPages, `Starlight staging must contain ${expectedStagedMarkdownPages} localized Markdown reference pages`);
requireCheck(!fs.existsSync(path.join(stagedRoot, "index.md")), "zh-CN docs root must not conflict with the curated Astro landing route");
requireCheck(!fs.existsSync(path.join(stagedRoot, "en", "index.md")), "English docs root must not conflict with the curated Astro landing route");
requireCheck(fs.existsSync(path.join(stagedRoot, "why-novelforge.md")), "zh-CN why-novelforge route must be staged at the docs root");
requireCheck(fs.existsSync(path.join(stagedRoot, "en", "why-novelforge.md")), "English why-novelforge route must be staged under /en");

requireCheck(landing.includes('template: "splash"'), "docs home must use Starlight's splash landing template");
requireCheck(landing.includes("StarlightPage"), "docs home must remain inside the official Starlight page shell");
requireCheck(landing.includes('class="nf-link-grid"') && landing.includes('class="nf-link-card"'), "docs home must use stable semantic task-path cards instead of private Starlight component imports");
requireCheck(landing.includes('link: "/inspect"') && landing.includes('"/inspect"'), "docs home must connect product-first onboarding to the live project inspector");
requireCheck(landing.includes("data-nf-docs-home"), "docs home must expose a stable verification marker");
requireCheck(landing.includes("按目标开始") && landing.includes("Choose a path"), "docs landing copy must remain natively localized");
requireCheck(zhLandingRoute.includes('<DocsLanding locale="zh-CN" />'), "zh-CN docs root must render the curated Chinese landing");
requireCheck(enLandingRoute.includes('<DocsLanding locale="en" />'), "English docs root must render the curated English landing");

requireCheck(verifier.includes('path.join(outputRoot, "why-novelforge", "index.html")'), "post-build verifier must assert a concrete zh-CN deep route");
requireCheck(verifier.includes('path.join(outputRoot, "en", "why-novelforge", "index.html")'), "post-build verifier must assert a concrete English deep route");
requireCheck(verifier.includes("data-nf-docs-home"), "post-build verifier must assert the curated landing page marker");

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
    localized_pages: expectedLocalizedPages,
    staged_markdown_pages: expectedStagedMarkdownPages,
    custom_landing_pages: 2,
    root_locale: "zh-CN",
    spa_docs_renderer: false,
    astro_project_root: "site/docs-site",
    emitted_page_verification: true,
    raw_html_asset_rewrite: true,
    localized_header_actions: true,
    curated_landing: true,
    product_first_inspector_handoff: true,
    product_home_brand_handoff: true,
  }, null, 2));
}

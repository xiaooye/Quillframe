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
const articleCss = read("docs-site/src/styles/article-polish.css");
const navigationCss = read("docs-site/src/styles/navigation-polish.css");
const docsHomeCss = read("docs-site/src/styles/docs-home-clean.css");
const siteTitle = read("docs-site/src/components/NovelForgeSiteTitle.astro");
const pageTitle = read("docs-site/src/components/NovelForgePageTitle.astro");
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
requireCheck(config.includes('PageTitle: "./src/components/NovelForgePageTitle.astro"'), "deep docs must use the NovelForge article title surface");
requireCheck(config.includes('"./src/styles/article-polish.css"'), "deep docs article polish stylesheet must stay wired into Starlight");
requireCheck(config.includes('"./src/styles/navigation-polish.css"'), "final navigation polish stylesheet must stay wired into Starlight");
requireCheck(config.includes('"./src/styles/docs-home-clean.css"'), "docs landing clean-surface override must load after the shared Starlight polish");
requireCheck(config.indexOf('navigation-polish.css') < config.indexOf('docs-home-clean.css'), "docs landing clean layer must refine the shared navigation/theme layers");
requireCheck(config.includes('label: "入门"') && config.includes('en: "Getting started"'), "sidebar information architecture must keep concise native group labels");
requireCheck(config.includes('label: "创作与质量"') && config.includes('label: "架构与发布"'), "sidebar must retain product-oriented Chinese grouping");
requireCheck(contentConfig.includes("docsLoader()") && contentConfig.includes("docsSchema()"), "Starlight content collection must use official loader and schema");

requireCheck(customCss.includes("--sl-content-width: 52rem"), "documentation reading width must stay deliberately bounded");
requireCheck(customCss.includes(':lang(zh-CN) .sl-markdown-content'), "Chinese typography override must remain explicit");
requireCheck(customCss.includes('a[aria-current="page"]'), "documentation navigation must retain a strong current-page state");
requireCheck(customCss.includes(".nf-link-grid") && customCss.includes(".nf-link-card"), "curated docs landing must retain stable semantic task-path structure");
requireCheck(customCss.includes(".nf-tier-grid") && customCss.includes(".nf-reference-callout"), "curated docs landing must retain its layered reference hierarchy");

requireCheck(docsHomeCss.includes('body:has([data-nf-docs-home]) .hero'), "clean docs layer must scope the splash hero to the landing page");
requireCheck(docsHomeCss.includes("border: 0") && docsHomeCss.includes("box-shadow: none"), "docs landing must remove framed-card chrome");
requireCheck(docsHomeCss.includes(".nf-link-card") && docsHomeCss.includes("border-bottom: 1px solid"), "task paths must use hairline rows instead of rounded cards");
requireCheck(docsHomeCss.includes(".nf-tier-card") && docsHomeCss.includes("border-radius: 0"), "documentation tiers must read as editorial columns rather than cards");
requireCheck(docsHomeCss.includes(".nf-reference-callout") && docsHomeCss.includes("border-top: 1px solid"), "reference CTA must use a section divider instead of a framed callout card");
requireCheck(docsHomeCss.includes("@media (max-width: 50rem)"), "clean docs landing must retain explicit mobile behavior");
requireCheck(!docsHomeCss.includes("var(--nf-shadow)"), "docs landing clean layer must not restore heavy surface shadowing");

requireCheck(pageTitle.includes('class="nf-article-title"') && pageTitle.includes('id="_top"'), "custom PageTitle must keep the product surface and Starlight top anchor");
requireCheck(pageTitle.includes('english ? "NovelForge Docs" : "NovelForge 知识库"'), "custom PageTitle must keep native bilingual labeling");
requireCheck(pageTitle.includes('zh: "入门"') && pageTitle.includes('zh: "创作与质量"') && pageTitle.includes('zh: "架构与发布"'), "article titles must expose route-aware section context");
requireCheck(articleCss.includes(".nf-article-title") && articleCss.includes(".sl-markdown-content h2"), "deep article polish must style both title and reading hierarchy");
requireCheck(articleCss.includes(".right-sidebar") && articleCss.includes(".pagination-links"), "deep article polish must cover TOC and footer navigation");
requireCheck(articleCss.includes("@media (max-width: 50rem)"), "deep article polish must keep an explicit mobile treatment");

requireCheck(navigationCss.includes(".nf-product-nav") && navigationCss.includes(".sidebar-content summary::before"), "final navigation polish must cover product header and sidebar hierarchy");
requireCheck(navigationCss.includes('.right-sidebar a[aria-current="true"]'), "final navigation polish must retain a visible active TOC state");
requireCheck(navigationCss.includes("@media (max-width: 68rem)") && navigationCss.includes("@media (max-width: 50rem)"), "final navigation polish must deliberately collapse at tablet and mobile widths");

requireCheck(siteTitle.includes('class="nf-brand-home" href="/"'), "NovelForge docs brand must navigate to the main product home");
requireCheck(siteTitle.includes('english ? "/docs/en/" : "/docs/"'), "docs header must retain a locale-aware documentation-home link");
requireCheck(siteTitle.includes('english ? "Docs" : "知识库"'), "docs header must use the same knowledge namespace as the product navigation");
requireCheck(siteTitle.includes('aria-current="page"'), "docs namespace must expose an explicit active navigation state");

for (const [href, marker] of [
  ['/product', 'product: "产品"'],
  ['/studio', 'studio: "Studio"'],
  ['/architecture', 'architecture: "架构"'],
  ['/publication', 'publication: "出版"'],
]) {
  requireCheck(actions.includes(`href="${href}"`) && actions.includes(marker), `Docs header product navigation missing ${href}`);
}
requireCheck(actions.includes('openStudio: "打开 Studio"') && actions.includes('class="nf-studio-link"'), "Docs header must retain the localized primary Studio CTA");
requireCheck(actions.includes('class="nf-product-nav"'), "Docs header product links must be grouped as semantic navigation");
requireCheck(!actions.includes('href="/start"'), "Docs header must not reintroduce the retired standalone start surface");

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
requireCheck(landing.includes('class="nf-link-grid"') && landing.includes('class="nf-link-card"'), "docs home must keep stable semantic task-path markup without private Starlight component imports");
requireCheck(!landing.includes('"/start"'), "docs home must not route users through the retired standalone start page");
requireCheck(landing.includes('secondaryAction: "进入产品首页"') && landing.includes('secondaryAction: "Explore the product"'), "docs hero must hand onboarding directly to the main product entry");
requireCheck(landing.includes('["产品首页"') && landing.includes('["Product home"'), "docs runtime paths must expose the consolidated product home in both locales");
requireCheck(landing.includes('"/inspect"'), "docs home must retain a direct path to the live Project Inspector");
requireCheck(landing.includes('"/playground"') && landing.includes('"/agents"'), "docs home must connect to the live Playground and Agent integration workbench");
requireCheck(landing.includes("data-nf-docs-home"), "docs home must expose a stable verification marker");
requireCheck(landing.includes("按目标开始") && landing.includes("Choose a path"), "docs landing copy must remain natively localized");
requireCheck(landing.includes('tierLabel: (tier: string) => `第 ${tier} 层`') && landing.includes('referenceEyebrow: "参考"'), "Chinese landing chrome must not leak English Tier or Reference labels");
requireCheck(landing.includes("编程智能体") && landing.includes("真正负责的子系统"), "Chinese landing explanations must prefer native product language over untranslated implementation jargon");
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
    schema: "novelforge_docs_platform_quality_v5",
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
    native_landing_copy: true,
    product_home_primary_entry: true,
    product_header_navigation_parity: true,
    knowledge_namespace_active: true,
    concise_sidebar_information_architecture: true,
    route_aware_article_sections: true,
    curated_landing: true,
    borderless_landing_hierarchy: true,
    nested_landing_cards: false,
    product_style_article_title: true,
    polished_reading_hierarchy: true,
    polished_article_toc: true,
    polished_article_pagination: true,
    responsive_navigation: true,
    product_first_inspector_handoff: true,
    product_tool_handoff: true,
    product_home_brand_handoff: true,
  }, null, 2));
}

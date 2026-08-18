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
const productApp = read("src/ProductApp.tsx");
const content = read("src/content.ts");
const config = read("docs-site/astro.config.mjs");
const contentConfig = read("docs-site/src/content.config.ts");
const customCss = read("docs-site/src/styles/custom.css");
const articleCss = read("docs-site/src/styles/article-polish.css");
const navigationCss = read("docs-site/src/styles/navigation-polish.css");
const docsHomeCss = read("docs-site/src/styles/docs-home-clean.css");
const shellCss = read("docs-site/src/styles/product-header-parity.css");
const siteTitle = read("docs-site/src/components/QuillframeSiteTitle.astro");
const pageTitle = read("docs-site/src/components/QuillframePageTitle.astro");
const actions = read("docs-site/src/components/QuillframeActions.astro");
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

/* Platform contracts --------------------------------------------------- */
requireCheck(pkg.scripts?.["docs:build"]?.includes("astro build --root docs-site"), "docs:build must execute Astro with docs-site as the real project root");
requireCheck(pkg.scripts?.["dev:docs"]?.includes("astro dev --root docs-site"), "dev:docs must execute Astro with docs-site as the real project root");
requireCheck(pkg.scripts?.["docs:build"]?.includes("verify-starlight-build.mjs"), "docs:build must verify emitted Starlight pages");
requireCheck(pkg.scripts?.build?.includes("docs:build"), "production build must include Starlight output");

requireCheck(config.includes('base: "/docs"'), "Starlight must own the /docs surface");
requireCheck(config.includes('outDir: "../dist/docs"'), "Starlight output must compose into site/dist/docs");
requireCheck(config.includes('lang: "zh-CN"') && config.includes('lang: "en"'), "Starlight must keep zh-CN and English locales");
requireCheck(config.includes("starlight({"), "docs app must remain powered by Starlight");
requireCheck(config.includes('SiteTitle: "./src/components/QuillframeSiteTitle.astro"'), "docs header must override SiteTitle so product and docs homes remain distinct");
requireCheck(config.includes('PageTitle: "./src/components/QuillframePageTitle.astro"'), "deep docs must use the Quillframe article title surface");
for (const stylesheet of ["article-polish.css", "navigation-polish.css", "docs-home-clean.css", "product-header-parity.css"]) {
  requireCheck(config.includes(`"./src/styles/${stylesheet}"`), `Starlight custom CSS must include ${stylesheet}`);
}
requireCheck(config.indexOf('navigation-polish.css') < config.indexOf('docs-home-clean.css'), "docs landing clean layer must refine the shared navigation/theme layers");
requireCheck(config.indexOf('docs-home-clean.css') < config.indexOf('product-header-parity.css'), "dedicated Docs product-shell owner must load after landing/article styling");
requireCheck(config.includes('label: "入门"') && config.includes('en: "Getting started"'), "sidebar information architecture must keep concise native group labels");
requireCheck(config.includes('label: "创作与质量"') && config.includes('label: "架构与发布"'), "sidebar must retain product-oriented Chinese grouping");
requireCheck(contentConfig.includes("docsLoader()") && contentConfig.includes("docsSchema()"), "Starlight content collection must use official loader and schema");

/* Reading-first composition ------------------------------------------- */
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
requireCheck(!docsHomeCss.includes("var(--qf-shadow)"), "docs landing clean layer must not restore heavy surface shadowing");

requireCheck(pageTitle.includes('class="nf-article-title"') && pageTitle.includes('id="_top"'), "custom PageTitle must keep the product surface and Starlight top anchor");
requireCheck(pageTitle.includes('english ? "Quillframe Docs" : "Quillframe 知识库"'), "custom PageTitle must keep native bilingual labeling");
requireCheck(pageTitle.includes('zh: "入门"') && pageTitle.includes('zh: "创作与质量"') && pageTitle.includes('zh: "架构与发布"'), "article titles must expose route-aware section context");
requireCheck(articleCss.includes(".nf-article-title") && articleCss.includes(".sl-markdown-content h2"), "deep article polish must style both title and reading hierarchy");
requireCheck(articleCss.includes(".right-sidebar") && articleCss.includes(".pagination-links"), "deep article polish must cover TOC and footer navigation");
requireCheck(articleCss.includes("@media (max-width: 50rem)"), "deep article polish must keep an explicit mobile treatment");
requireCheck(navigationCss.includes(".nf-product-nav") && navigationCss.includes(".sidebar-content summary::before"), "navigation polish must cover product header and sidebar hierarchy");
requireCheck(navigationCss.includes('.right-sidebar a[aria-current="true"]'), "navigation polish must retain a visible active TOC state");
requireCheck(navigationCss.includes("@media (max-width: 68rem)") && navigationCss.includes("@media (max-width: 50rem)"), "navigation polish must deliberately collapse at tablet and mobile widths");

/* Shared Quillframe shell --------------------------------------------- */
requireCheck(siteTitle.includes('class="nf-brand-home" href="/"'), "Quillframe docs brand must navigate to the main product home");
requireCheck(siteTitle.includes('english ? "/docs/en/" : "/docs/"'), "docs title component must retain locale-aware docs identity markers");
requireCheck(siteTitle.includes('english ? "Docs" : "知识库"'), "docs title component must retain the current knowledge namespace markers");
requireCheck(siteTitle.includes('aria-label="Quillframe 0.9.x"') && siteTitle.includes('>0.9.x</span>'), "Docs visible version identity must track the Quillframe 0.9.x development line");
requireCheck(!siteTitle.includes("0.8.x") && !siteTitle.includes(">0.9.0</span>"), "Docs title must not regress to stale shell-version copy");

const primaryDocsRoutes = [
  ['/product', 'product: "产品"'],
  ['/studio', 'studio: "Studio"'],
  ['/architecture', 'architecture: "架构"'],
  ['/publication', 'publication: "出版"'],
];
for (const [href, marker] of primaryDocsRoutes) {
  requireCheck(actions.includes(`href="${href}"`) && actions.includes(marker), `Docs header product navigation missing ${href}`);
}
requireCheck(actions.includes('class="nf-product-link nf-docs-nav-link"') && actions.includes('aria-current="page"'), "Docs item must own the active product-navigation state");
requireCheck(actions.includes('class="nf-product-link nf-github-link"'), "Docs primary navigation must expose GitHub");
requireCheck(actions.includes('https://github.com/xiaooye/Quillframe'), "Docs GitHub entry must use the canonical repository root");
requireCheck(actions.includes('openStudio: "打开 Studio"') && actions.includes('class="nf-studio-link"'), "Docs header must retain the localized Hosted Studio CTA");
requireCheck(actions.includes('https://studio.quillframe.wei-dev.com'), "Docs Hosted Studio entry must use the current Quillframe domain");
requireCheck(actions.includes('rel="noopener noreferrer"'), "Docs external product links must use safe new-window semantics");
requireCheck(!actions.includes('href="/start"'), "Docs header must not reintroduce the retired standalone start surface");

requireCheck(shellCss.includes("Quillframe Docs product-shell owner"), "Docs final header stylesheet must explicitly own shared shell parity");
requireCheck(shellCss.includes("border-bottom: 1px solid") && shellCss.includes("box-shadow: none"), "Docs top chrome must use a quiet divider rather than floating banner chrome");
requireCheck(shellCss.includes("background: color-mix(in oklab, var(--qf-surface-solid) 94%, transparent)"), "Docs header must use the shared near-white canvas");
requireCheck(!shellCss.includes("radial-gradient") && !shellCss.includes("!important"), "Docs shell owner must not use route wallpaper or specificity hacks");
requireCheck(shellCss.includes("@media (max-width: 50rem)") && shellCss.includes(".sidebar-pane"), "Docs shared shell must preserve deliberate mobile navigation behavior");

/* Product → Docs handoff ---------------------------------------------- */
requireCheck(!main.includes("KnowledgePortal"), "legacy Knowledge Portal must not mount beside the product router");
requireCheck(!main.includes("KnowledgeExperience"), "product entry must not import the retired custom docs renderer");
requireCheck(main.includes('import ProductApp from "./ProductApp"') && main.includes("<ProductApp />") && main.includes("ProductFailureBoundary"), "product entry must route through the resilient shared ProductApp shell");
requireCheck(productApp.includes('kind: "document", href: zh() ? "/docs" : "/docs/en"'), "shared primary navigation model must hand off to the locale-aware Starlight docs root");
requireCheck(productApp.includes('<For each={primaryNav()}>{(item) => navLink(item, "wui-app-bar__link")}</For>'), "desktop Product header must render the shared primary navigation source");
requireCheck(productApp.includes('<div class="footer-links"><For each={primaryNav()}>{(item) => navLink(item, "footer-link")}</For></div>'), "Product footer primary section must render the same primary navigation source");
requireCheck(content.includes('export const githubRoot = "https://github.com/xiaooye/Quillframe"'), "Product content authority must retain the canonical repository root");
requireCheck(productApp.includes('kind: "external", href: githubRoot, label: copy().nav.github'), "Product shared primary navigation must include GitHub");
requireCheck(productApp.includes('if (result.href.startsWith("/docs")) window.location.assign(result.href);'), "product command search must use a real document navigation for Starlight results");
requireCheck(productApp.includes('`/docs/${encodeURIComponent(doc.id)}`') && productApp.includes('`/docs/en/${encodeURIComponent(doc.id)}`'), "product knowledge search must keep localized deep-document URLs");

/* Staging + emitted pages --------------------------------------------- */
requireCheck(stagingCompiler.includes("rewriteHtmlAttributes"), "Starlight staging must rewrite raw HTML document attributes");
requireCheck(stagingCompiler.includes("copyRelativeAsset"), "Starlight staging must copy repository-local documentation assets");
requireCheck(stagingCompiler.includes('if (doc.id === "docs-home") continue;'), "docs home must be reserved for the curated Starlight landing routes");

const expectedLocalizedPages = manifest.documents.length * 2;
const expectedStagedMarkdownPages = (manifest.documents.length - 1) * 2;
requireCheck(markdownCount(stagedRoot) === expectedStagedMarkdownPages, `Starlight staging must contain ${expectedStagedMarkdownPages} localized Markdown reference pages`);
requireCheck(!fs.existsSync(path.join(stagedRoot, "index.md")), "zh-CN docs root must not conflict with the curated Astro landing route");
requireCheck(!fs.existsSync(path.join(stagedRoot, "en", "index.md")), "English docs root must not conflict with the curated Astro landing route");
requireCheck(fs.existsSync(path.join(stagedRoot, "why-quillframe.md")), "zh-CN why-quillframe route must be staged at the docs root");
requireCheck(fs.existsSync(path.join(stagedRoot, "en", "why-quillframe.md")), "English why-quillframe route must be staged under /en");

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

requireCheck(verifier.includes('path.join(outputRoot, "why-quillframe", "index.html")'), "post-build verifier must assert a concrete zh-CN deep route");
requireCheck(verifier.includes('path.join(outputRoot, "en", "why-quillframe", "index.html")'), "post-build verifier must assert a concrete English deep route");
requireCheck(verifier.includes("data-nf-docs-home"), "post-build verifier must assert the curated landing page marker");

if (failures.length > 0) {
  for (const failure of failures) console.error(`docs-platform-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_docs_platform_quality_v9",
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
    unified_product_shell_handoff: true,
    shared_primary_navigation: true,
    github_entry: true,
    quillframe_studio_domain: true,
    product_version: "0.9.x",
    current_identity: "Quillframe",
    resilience_boundary: true,
    product_header_navigation_parity: true,
    quiet_product_shell: true,
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

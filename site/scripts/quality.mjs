#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const repoRoot = path.resolve(siteRoot, "..");

const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const readJson = (relative) => JSON.parse(read(relative));
const readRepo = (relative) => fs.readFileSync(path.join(repoRoot, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(siteRoot, relative));
const fail = (message) => {
  console.error(`product-site-quality: FAIL: ${message}`);
  process.exitCode = 1;
};
const requireCheck = (condition, message) => {
  if (!condition) fail(message);
};

const packageJson = readJson("package.json");
const appSource = read("src/App.tsx");
const knowledgeSource = read("src/knowledge.ts");
const rendererSource = read("src/DocumentRenderer.tsx");
const contentTypesSource = read("src/content.ts");
const enSource = read("src/content.en-US.ts");
const zhSource = read("src/content.zh-CN.ts");
const siteCss = read("src/styles/site.css");
const showcaseCss = read("src/styles/showcase.css");
const mainSource = read("src/main.tsx");
const indexHtml = read("index.html");
const contentCompiler = read("scripts/build-content.mjs");
const foundationSync = read("scripts/sync-weiui.mjs");
const tokens = JSON.parse(readRepo("assets/brand/tokens.json"));
const weiuiIntegration = JSON.parse(readRepo("assets/brand/weiui.integration.json"));
const storyLoomTheme = readRepo("assets/brand/story-loom.weiui.css");
const allCopy = `${enSource}\n${zhSource}\n${appSource}`;
const productRuntimeSource = `${appSource}\n${knowledgeSource}\n${rendererSource}\n${contentTypesSource}\n${enSource}\n${zhSource}`;

const exactVersions = {
  "solid-js": "1.9.14",
  "@solidjs/router": "0.16.2",
  marked: "18.0.7",
  typescript: "7.0.2",
  vite: "8.1.5",
  "vite-plugin-solid": "2.11.14",
};

for (const [name, version] of Object.entries(exactVersions)) {
  const actual = packageJson.dependencies?.[name] ?? packageJson.devDependencies?.[name];
  requireCheck(actual === version, `${name} must remain exactly pinned to ${version}; got ${actual ?? "missing"}`);
  requireCheck(typeof actual === "string" && !actual.startsWith("^") && !actual.startsWith("~"), `${name} must not use a version range`);
}

for (const forbidden of ["@weiui/react", "@weiui/headless", "react", "react-dom"]) {
  requireCheck(!(forbidden in (packageJson.dependencies ?? {})), `forbidden runtime dependency ${forbidden}`);
  requireCheck(!(forbidden in (packageJson.devDependencies ?? {})), `forbidden development dependency ${forbidden}`);
}

requireCheck(tokens.schema === "novelforge_brand_tokens_v2", "Story Loom token authority must be novelforge_brand_tokens_v2");
requireCheck(weiuiIntegration.schema === "novelforge_weiui_integration_v2", "WeiUI integration contract schema drifted");
requireCheck(weiuiIntegration.consumption?.phase_2c_framework === "SolidJS", "Product stack must remain SolidJS");
requireCheck(weiuiIntegration.consumption?.runtime_javascript_from_weiui === false, "WeiUI runtime JavaScript must remain disabled");
requireCheck(JSON.stringify(weiuiIntegration.consumption?.allowed_packages) === JSON.stringify(["@weiui/tokens", "@weiui/css"]), "WeiUI allowed package surface drifted");
requireCheck(weiuiIntegration.consumption?.css_delivery?.mode === "config_generated_checked_in", "Product Entry requires generated WeiUI CSS foundation");
requireCheck(weiuiIntegration.consumption?.css_delivery?.regeneration_requires_exact_pin === true, "WeiUI generated bundle must remain exact-pin reproducible");
requireCheck(storyLoomTheme.includes("@layer wui-theme"), "Story Loom application theme must retain wui-theme layer");

requireCheck(exists("src/generated/weiui.tokens.generated.css"), "Product Entry must generate WeiUI token foundation before QA");
requireCheck(exists("src/generated/weiui.generated.css"), "Product Entry must generate WeiUI CSS primitives before QA");
requireCheck(exists("src/generated/weiui.foundation.json"), "Product Entry must generate WeiUI provenance before QA");
const foundationMeta = readJson("src/generated/weiui.foundation.json");
requireCheck(foundationMeta.schema === "novelforge_product_weiui_foundation_v1", "Product Entry WeiUI foundation schema drifted");
requireCheck(foundationMeta.authority === false, "Product Entry generated WeiUI copy must not claim authority");
requireCheck(foundationMeta.sourceCommit === weiuiIntegration.source.commit, "Product Entry WeiUI foundation must follow current integration exact pin");
requireCheck(foundationSync.includes("delivery.generated_tokens") && foundationSync.includes("delivery.generated_css"), "WeiUI sync must derive source paths from integration contract");

const tokenImport = '@import "../generated/weiui.tokens.generated.css"';
const cssImport = '@import "../generated/weiui.generated.css"';
const storyImport = '@import "../../../assets/brand/story-loom.weiui.css"';
const tokenIndex = siteCss.indexOf(tokenImport);
const cssIndex = siteCss.indexOf(cssImport);
const storyIndex = siteCss.indexOf(storyImport);
requireCheck(tokenIndex >= 0 && cssIndex > tokenIndex && storyIndex > cssIndex, "Product Entry CSS import order must be WeiUI tokens → WeiUI CSS → Story Loom theme");

for (const primitive of [
  "wui-app-bar",
  "wui-button",
  "wui-card",
  "wui-command",
  "wui-input-group",
  "wui-badge",
  "wui-bottom-nav",
  "wui-tabs",
]) {
  requireCheck(appSource.includes(primitive), `Product Entry must consume WeiUI primitive .${primitive}`);
}

requireCheck(packageJson.scripts?.content?.includes("sync-weiui.mjs") || packageJson.scripts?.content?.includes("foundation"), "content build must sync WeiUI foundation");
requireCheck(packageJson.scripts?.build?.includes("npm run content"), "production build must compile Product Entry content first");
requireCheck(contentCompiler.includes("marked.lexer"), "documentation compiler must use parser tokens, not raw HTML injection");
requireCheck(!contentCompiler.includes("marked.parse("), "documentation compiler must not inject parser-generated HTML");
requireCheck(contentCompiler.includes('authority: false'), "generated documentation must remain authority=false");
requireCheck(rendererSource.includes("DocumentBlock") && rendererSource.includes("InlineNode"), "Product Entry must render structured documentation AST");
requireCheck(!rendererSource.includes("innerHTML") && !rendererSource.includes("innerHTML="), "Product Entry document renderer must not use innerHTML");
requireCheck(!appSource.includes("api.github.com") && !knowledgeSource.includes("api.github.com"), "Product Entry runtime must not depend on GitHub API");

requireCheck(exists("public/generated/docs-index.json"), "documentation compiler must generate docs-index.json");
requireCheck(exists("public/generated/build-meta.json"), "documentation compiler must generate build-meta.json");
const docsIndex = readJson("public/generated/docs-index.json");
const buildMeta = readJson("public/generated/build-meta.json");
requireCheck(docsIndex.schema === "novelforge_product_document_index_v1", "generated documentation index schema drifted");
requireCheck(docsIndex.authority === false, "generated documentation index must remain authority=false");
requireCheck(buildMeta.schema === "novelforge_product_content_build_v1" && buildMeta.authority === false, "generated content build metadata contract drifted");
requireCheck(buildMeta.parser === "marked@18.0.7", "generated content must record exact Markdown parser identity");
requireCheck(Number(docsIndex.documentCount) >= 20, `expected substantial repository documentation corpus; got ${docsIndex.documentCount}`);
requireCheck(docsIndex.documents.some((doc) => doc.locale === "en-US"), "generated documentation must include en-US");
requireCheck(docsIndex.documents.some((doc) => doc.locale === "zh-CN"), "generated documentation must include zh-CN");
requireCheck(docsIndex.documents.every((doc) => typeof doc.sourceFingerprint === "string" && doc.sourceFingerprint.length === 64), "every generated document index entry must carry source SHA-256");
const representative = docsIndex.documents.find((doc) => doc.locale === "zh-CN" && doc.id === "architecture-atlas") ?? docsIndex.documents[0];
requireCheck(Boolean(representative), "generated documentation index must contain at least one document");
if (representative) {
  const generatedPath = `public/generated/docs/${representative.locale}/${representative.id}.json`;
  requireCheck(exists(generatedPath), `representative generated document missing: ${generatedPath}`);
  if (exists(generatedPath)) {
    const generatedDoc = readJson(generatedPath);
    requireCheck(generatedDoc.schema === "novelforge_product_document_v1", "generated document schema drifted");
    requireCheck(generatedDoc.authority === false, "generated document must remain authority=false");
    requireCheck(Array.isArray(generatedDoc.blocks) && generatedDoc.blocks.length > 0, "generated document must contain structured blocks");
    requireCheck(Array.isArray(generatedDoc.toc), "generated document must contain TOC structure");
  }
}

for (const route of ["/", "/product", "/studio", "/architecture", "/publication", "/docs", "/docs/:docId", "/changelog"]) {
  const needle = route === "/" ? 'path="/"' : `path="${route}"`;
  requireCheck(appSource.includes(needle), `missing required Product Entry route ${route}`);
}

requireCheck(appSource.includes("https://studio.novelforge.wei-dev.com"), "Product Entry must expose real hosted Studio entry point");
requireCheck(appSource.includes("loadKnowledgeIndex") && appSource.includes("loadProductDocument"), "Product Entry must expose build-time Knowledge Explorer at runtime");
requireCheck(appSource.includes("metaKey || event.ctrlKey") && appSource.includes('key.toLocaleLowerCase() === "k"'), "Product Entry must expose Ctrl/Cmd+K command palette shortcut");
requireCheck(appSource.includes("command-dialog") && appSource.includes("showModal"), "Product Entry must expose accessible command dialog");
requireCheck(appSource.includes("Context budget lab") || appSource.includes("上下文预算实验"), "Home must expose interactive context lab");
requireCheck(appSource.includes("Candidate readiness lab") || appSource.includes("候选稿就绪实验"), "Home must expose interactive readiness lab");
requireCheck(appSource.includes("ฅ^•ﻌ•^ฅ") || appSource.includes("(｡•̀ᴗ-)✧"), "Product Entry must retain restrained kawaii state language");

const fakeMarketingPatterns = [
  /10K\+/i,
  /99\.9%\s*(uptime|sla)/i,
  /start free trial/i,
  /trusted by (?:industry|leading|thousands|teams)/i,
  /loved by teams/i,
  /customer logos?/i,
  /limited seats?/i,
  /five[- ]star rating/i,
  /\b\d{1,3}(?:,\d{3})+\s+(?:users|creators|customers|teams)\b/i,
];
for (const pattern of fakeMarketingPatterns) {
  requireCheck(!pattern.test(allCopy), `fabricated or placeholder marketing claim matched ${pattern}`);
}

const chineseLeakagePatterns = [
  /所有产品\s*claim/i,
  /了解\s*Product model/i,
  /维护中的\s*Source of Truth/i,
  /latest main 是/i,
  /Prompt Wrapper/i,
  /current gaps/i,
  /active pre-1\.0 development/i,
  /read-oriented/i,
  /product proof/i,
  /Runtime Inspector/i,
  /Context、Reader、Continuity/i,
];
for (const pattern of chineseLeakagePatterns) {
  requireCheck(!pattern.test(`${zhSource}\n${appSource}`), `zh-CN user-facing copy regressed into internal English phrasing: ${pattern}`);
}

for (const required of [
  "var(--nf-touch-target-min, 44px)",
  "overflow-wrap: break-word",
]) {
  const inFoundation = read("src/generated/weiui.generated.css").includes(required) || read("src/generated/weiui.tokens.generated.css").includes(required);
  const inSite = siteCss.includes(required);
  requireCheck(inFoundation || inSite, `WeiUI/Product Entry foundation missing UX contract: ${required}`);
}
requireCheck(siteCss.includes("@media (max-width: 760px)"), "Product Entry must preserve mobile layout contract");

for (const requiredShowcase of [
  "@property --pe-angle",
  ":has(",
  "color-mix(in oklab",
  "@starting-style",
  "allow-discrete",
  "animation-timeline: view(",
  "animation-timeline: scroll(root block)",
  "::view-transition-old(root)",
  "@container",
  "@scope",
  "offset-path",
  "@supports (anchor-name:",
  "@media (prefers-reduced-motion: reduce)",
]) {
  requireCheck(showcaseCss.includes(requiredShowcase), `Product Entry modern CSS layer missing progressive enhancement: ${requiredShowcase}`);
}

requireCheck(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(showcaseCss), "Product Entry must not introduce idle infinite animation");
requireCheck(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(productRuntimeSource), "Product Entry must not add default polling or decorative frame loops");
requireCheck(appSource.includes("startViewTransition"), "Product Entry route/theme changes should progressively enhance with View Transitions");
requireCheck(appSource.includes('document.documentElement.dataset.locale = lang'), "locale-specific typography must remain document-state driven");

for (const forbiddenRuntimePattern of [/\.novelforge\/runtime\.db/, /sqlite/i]) {
  requireCheck(!forbiddenRuntimePattern.test(productRuntimeSource), `Product Entry must not couple to private runtime storage: ${forbiddenRuntimePattern}`);
}

for (const privateCorePath of ["harness/", "quality/", "core/", "publication/compiler.py", "control_plane"]) {
  const importPattern = new RegExp(`(?:from|import\\s*\\()\\s*[\"'][^\"']*${privateCorePath.replace("/", "\\/")}`, "i");
  requireCheck(!importPattern.test(productRuntimeSource), `Product Entry must not import private Core implementation path ${privateCorePath}`);
}

requireCheck(indexHtml.includes('name="viewport"'), "index.html must declare responsive viewport");
requireCheck(indexHtml.includes('class="skip-link"'), "index.html must provide a skip link");
requireCheck(appSource.includes('id="main-content"'), "Product Entry must provide a main-content skip target");
requireCheck(appSource.includes('aria-expanded={menuOpen()}'), "mobile navigation disclosure must expose aria-expanded");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_product_site_quality_v2",
    status: "pass",
    identity: "product_entry_spa",
    stack: "SolidJS + TypeScript + Vite",
    weiui_foundation: foundationMeta.sourceCommit,
    routes: 8,
    locales: ["en-US", "zh-CN"],
    generated_documents: docsIndex.documentCount,
    knowledge_runtime_github_api: false,
    generated_content_authority: false,
    native_chinese_copy_gate: true,
    premium_cute_state_language: true,
    modern_css_progressive_enhancement: true,
    idle_animation: false,
    weiui_runtime_javascript: false,
    weiui_integration: weiuiIntegration.schema,
    story_loom_tokens: tokens.schema,
  }, null, 2));
}

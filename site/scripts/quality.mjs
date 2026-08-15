#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const repoRoot = path.resolve(siteRoot, "..");

const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const readRepo = (relative) => fs.readFileSync(path.join(repoRoot, relative), "utf8");
const fail = (message) => {
  console.error(`product-site-quality: FAIL: ${message}`);
  process.exitCode = 1;
};
const requireCheck = (condition, message) => {
  if (!condition) fail(message);
};

const packageJson = JSON.parse(read("package.json"));
const appSource = read("src/App.tsx");
const contentTypesSource = read("src/content.ts");
const enSource = read("src/content.en-US.ts");
const zhSource = read("src/content.zh-CN.ts");
const siteCss = read("src/styles/site.css");
const showcaseCss = read("src/styles/showcase.css");
const mainSource = read("src/main.tsx");
const indexHtml = read("index.html");
const tokens = JSON.parse(readRepo("assets/brand/tokens.json"));
const weiuiIntegration = JSON.parse(readRepo("assets/brand/weiui.integration.json"));
const storyLoomTheme = readRepo("assets/brand/story-loom.weiui.css");
const allCopy = `${enSource}\n${zhSource}`;
const productRuntimeSource = `${appSource}\n${contentTypesSource}\n${allCopy}`;

const exactVersions = {
  "solid-js": "1.9.14",
  "@solidjs/router": "0.16.2",
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
requireCheck(weiuiIntegration.consumption?.phase_2c_framework === "SolidJS", "Phase 2C framework must remain SolidJS");
requireCheck(weiuiIntegration.consumption?.runtime_javascript_from_weiui === false, "WeiUI runtime JavaScript must remain disabled");
requireCheck(JSON.stringify(weiuiIntegration.consumption?.allowed_packages) === JSON.stringify(["@weiui/tokens", "@weiui/css"]), "WeiUI allowed package surface drifted");
requireCheck(weiuiIntegration.consumption?.css_delivery?.config_schema === "weiui_css_config_v1", "WeiUI config contract must remain weiui_css_config_v1");
requireCheck(weiuiIntegration.consumption?.css_delivery?.manifest_schema === "weiui_css_bundle_manifest_v1", "WeiUI bundle manifest contract drifted");
requireCheck(weiuiIntegration.consumption?.css_delivery?.regeneration_requires_exact_pin === true, "WeiUI generated bundle must remain exact-pin reproducible");
requireCheck(storyLoomTheme.includes("@layer wui-theme"), "Story Loom application theme must retain wui-theme layer");
requireCheck(siteCss.includes('@import "../../../assets/brand/story-loom.weiui.css"'), "site must consume the maintained Story Loom application theme directly");
requireCheck(mainSource.includes('import "./styles/showcase.css"'), "site must load the Product Site visual-showcase layer after base styles");

for (const route of ["/", "/product", "/studio", "/architecture", "/publication", "/docs", "/changelog"]) {
  const needle = route === "/" ? 'path="/"' : `path="${route}"`;
  requireCheck(appSource.includes(needle), `missing required SPA route ${route}`);
}

requireCheck(enSource.includes('proofLabel: "Proof, not promises"'), "home must retain evidence-first product framing");
requireCheck(zhSource.includes('proofLabel: "不是承诺，是证据"'), "Chinese home must retain native evidence-first product framing");
requireCheck(zhSource.includes('title: "让长篇创作有记忆，也有边界。"'), "Chinese hero must retain concise native headline geometry");
requireCheck(zhSource.includes('title: "真实 SolidJS 产品壳"'), "Chinese Studio route must describe merged Phase 2C truth");
requireCheck(enSource.includes('title: "Real SolidJS product shell"'), "English Studio route must describe merged Phase 2C truth");

const fakeMarketingPatterns = [
  /10K\+/i,
  /99\.9%\s*(uptime|sla)/i,
  /start free trial/i,
  /trusted by (?:industry|leading|thousands|teams)/i,
  /loved by teams/i,
  /customer logos?/i,
  /limited seats?/i,
  /five[- ]star rating/i,
];

for (const pattern of fakeMarketingPatterns) {
  requireCheck(!pattern.test(allCopy), `fabricated or placeholder marketing claim matched ${pattern}`);
}

const chineseCopyLeakagePatterns = [
  /所有产品\s*claim/i,
  /了解\s*Product model/i,
  /维护中的\s*Source of Truth/i,
  /latest main 是/i,
  /Agent Framework/i,
  /Prompt Wrapper/i,
  /current gaps/i,
  /active pre-1\.0 development/i,
  /read-oriented/i,
  /product proof/i,
  /Runtime Inspector/i,
  /Context、Reader、Continuity/i,
];

for (const pattern of chineseCopyLeakagePatterns) {
  requireCheck(!pattern.test(zhSource), `zh-CN copy regressed into internal English phrasing: ${pattern}`);
}

const sharedComponentZhLeakagePatterns = [
  /\?\s*"所有产品\s*claim/i,
  /\?\s*"了解\s*Product model/i,
  /\?\s*"Canonical sources/i,
  /\?\s*"维护中的\s*Source of Truth/i,
  /\?\s*"latest main 是/i,
  /\?\s*"Context、Reader、Continuity/i,
  /\?\s*"可见 evidence/i,
  /\?\s*"候选稿绑定 fingerprint/i,
  /\?\s*"可以进入 Review/i,
];

for (const pattern of sharedComponentZhLeakagePatterns) {
  requireCheck(!pattern.test(appSource), `shared component restored a known zh-CN hybrid phrase: ${pattern}`);
}

for (const required of [
  ":focus-visible",
  "var(--nf-touch-target-min, 44px)",
  "@media (prefers-reduced-motion: reduce)",
  "overflow-wrap: anywhere",
]) {
  requireCheck(siteCss.includes(required), `site CSS missing required UX contract: ${required}`);
}

for (const requiredShowcase of [
  "color-mix(in oklab",
  "backdrop-filter: blur",
  "animation-timeline: view()",
  "animation-timeline: scroll(root block)",
  "::view-transition-old(root)",
  '[data-locale="zh-CN"] .hero-copy h1',
  "@media (prefers-reduced-motion: reduce)",
]) {
  requireCheck(showcaseCss.includes(requiredShowcase), `visual showcase missing modern progressive-enhancement contract: ${requiredShowcase}`);
}

requireCheck(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(showcaseCss), "Product Site showcase must not introduce idle infinite animation");
requireCheck(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(appSource), "Product Site must not add polling or frame loops for decorative effects");
requireCheck(appSource.includes("startViewTransition"), "locale/theme changes should progressively enhance with same-document View Transitions");
requireCheck(appSource.includes('document.documentElement.dataset.locale = lang'), "locale-specific typography must be driven by a document locale attribute");

for (const forbiddenRuntimePattern of [/setInterval\s*\(/, /requestAnimationFrame\s*\(/, /\.novelforge\/runtime\.db/, /sqlite/i]) {
  requireCheck(!forbiddenRuntimePattern.test(productRuntimeSource), `site must not add polling/private-runtime coupling: ${forbiddenRuntimePattern}`);
}

for (const privateCorePath of ["harness/", "quality/", "core/", "publication/compiler.py", "control_plane"]) {
  const importPattern = new RegExp(`(?:from|import\\s*\\()\\s*[\"'][^\"']*${privateCorePath.replace("/", "\\/")}`, "i");
  requireCheck(!importPattern.test(appSource), `site must not import private Core implementation path ${privateCorePath}`);
}

requireCheck(indexHtml.includes('name="viewport"'), "index.html must declare responsive viewport");
requireCheck(indexHtml.includes('class="skip-link"'), "index.html must provide a skip link");
requireCheck(appSource.includes('id="main-content"'), "site must provide a main-content skip target");
requireCheck(appSource.includes('aria-expanded={menuOpen()}'), "mobile navigation disclosure must expose aria-expanded");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_product_site_quality_v1",
    status: "pass",
    stack: "SolidJS + TypeScript + Vite",
    routes: 7,
    locales: ["en-US", "zh-CN"],
    native_chinese_copy_gate: true,
    modern_css_progressive_enhancement: true,
    idle_animation: false,
    weiui_runtime_javascript: false,
    weiui_integration: weiuiIntegration.schema,
    story_loom_tokens: tokens.schema,
  }, null, 2));
}

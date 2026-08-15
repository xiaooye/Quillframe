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
const contentSource = read("src/content.ts");
const siteCss = read("src/styles/site.css");
const indexHtml = read("index.html");
const tokens = JSON.parse(readRepo("assets/brand/tokens.json"));
const weiuiIntegration = JSON.parse(readRepo("assets/brand/weiui.integration.json"));
const storyLoomTheme = readRepo("assets/brand/story-loom.weiui.css");

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
requireCheck(weiuiIntegration.schema === "novelforge_weiui_integration_v1", "WeiUI integration contract schema drifted");
requireCheck(weiuiIntegration.consumption?.phase_2c_framework === "SolidJS", "Phase 2C framework must remain SolidJS");
requireCheck(weiuiIntegration.consumption?.runtime_javascript_from_weiui === false, "WeiUI runtime JavaScript must remain disabled");
requireCheck(JSON.stringify(weiuiIntegration.consumption?.allowed_packages) === JSON.stringify(["@weiui/tokens", "@weiui/css"]), "WeiUI allowed package surface drifted");
requireCheck(storyLoomTheme.includes("@layer wui-theme"), "Story Loom application theme must retain wui-theme layer");
requireCheck(siteCss.includes('@import "../../../assets/brand/story-loom.weiui.css"'), "site must consume the maintained Story Loom application theme directly");

for (const route of ["/", "/product", "/studio", "/architecture", "/publication", "/docs", "/changelog"]) {
  const needle = route === "/" ? 'path="/"' : `path="${route}"`;
  requireCheck(appSource.includes(needle), `missing required SPA route ${route}`);
}

requireCheck(contentSource.includes('"en-US"'), "missing en-US locale content");
requireCheck(contentSource.includes('"zh-CN"'), "missing zh-CN locale content");
requireCheck(contentSource.includes("Proof, not promises"), "home must retain evidence-first product framing");
requireCheck(contentSource.includes("不是承诺，是证据"), "Chinese home must retain native evidence-first product framing");

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
  requireCheck(!pattern.test(contentSource), `fabricated or placeholder marketing claim matched ${pattern}`);
}

for (const required of [
  ":focus-visible",
  "var(--nf-touch-target-min, 44px)",
  "@media (prefers-reduced-motion: reduce)",
  "overflow-wrap: anywhere",
]) {
  requireCheck(siteCss.includes(required), `site CSS missing required UX contract: ${required}`);
}

for (const forbiddenRuntimePattern of [/setInterval\s*\(/, /requestAnimationFrame\s*\(/, /\.novelforge\/runtime\.db/, /sqlite/i]) {
  requireCheck(!forbiddenRuntimePattern.test(appSource + contentSource), `site must not add polling/private-runtime coupling: ${forbiddenRuntimePattern}`);
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
    weiui_runtime_javascript: false,
    story_loom_tokens: tokens.schema,
  }, null, 2));
}

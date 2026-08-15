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
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const packageJson = readJson("package.json");
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const surface = read("src/ProductSurface.tsx");
const inspector = read("src/ProjectInspector.tsx");
const playground = read("src/LocalPlayground.tsx");
const knowledge = read("src/knowledge.ts");
const renderer = read("src/DocumentRenderer.tsx");
const contentTypes = read("src/content.ts");
const en = read("src/content.en-US.ts");
const zh = read("src/content.zh-CN.ts");
const siteCss = read("src/styles/site.css");
const productContractCss = read("src/styles/product-contract.css");
const showcaseCss = read("src/styles/showcase.css");
const unifiedCss = read("src/styles/unified-product-app.css");
const surfaceCss = read("src/styles/product-surface.css");
const indexHtml = read("index.html");
const contentCompiler = read("scripts/build-content.mjs");
const foundationSync = read("scripts/sync-weiui.mjs");
const tokens = JSON.parse(readRepo("assets/brand/tokens.json"));
const weiuiIntegration = JSON.parse(readRepo("assets/brand/weiui.integration.json"));
const storyLoomTheme = readRepo("assets/brand/story-loom.weiui.css");
const runtime = `${app}\n${surface}\n${inspector}\n${playground}\n${knowledge}\n${renderer}\n${contentTypes}`;
const allCopy = `${en}\n${zh}\n${app}`;

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
  check(actual === version, `${name} must remain exactly pinned to ${version}; got ${actual ?? "missing"}`);
  check(typeof actual === "string" && !actual.startsWith("^") && !actual.startsWith("~"), `${name} must not use a version range`);
}
for (const forbidden of ["@weiui/react", "@weiui/headless", "react", "react-dom"]) {
  check(!(forbidden in (packageJson.dependencies ?? {})) && !(forbidden in (packageJson.devDependencies ?? {})), `forbidden dependency ${forbidden}`);
}

check(tokens.schema === "novelforge_brand_tokens_v2", "Story Loom token authority must remain v2");
check(weiuiIntegration.schema === "novelforge_weiui_integration_v2", "WeiUI integration contract schema drifted");
check(weiuiIntegration.consumption?.phase_2c_framework === "SolidJS", "Product stack must remain SolidJS");
check(weiuiIntegration.consumption?.runtime_javascript_from_weiui === false, "WeiUI runtime JavaScript must remain disabled");
check(JSON.stringify(weiuiIntegration.consumption?.allowed_packages) === JSON.stringify(["@weiui/tokens", "@weiui/css"]), "WeiUI allowed package surface drifted");
check(storyLoomTheme.includes("@layer wui-theme"), "Story Loom application theme must retain wui-theme layer");
check(storyLoomTheme.includes("--nf-touch-target-min: 44px"), "Story Loom minimum touch target token is missing");

check(exists("src/generated/weiui.tokens.generated.css"), "generated WeiUI token foundation missing");
check(exists("src/generated/weiui.generated.css"), "generated WeiUI CSS foundation missing");
check(exists("src/generated/weiui.foundation.json"), "generated WeiUI provenance missing");
const foundationMeta = readJson("src/generated/weiui.foundation.json");
check(foundationMeta.schema === "novelforge_product_weiui_foundation_v1", "WeiUI foundation schema drifted");
check(foundationMeta.authority === false, "generated WeiUI copy must remain authority=false");
check(foundationMeta.sourceCommit === weiuiIntegration.source.commit, "WeiUI foundation must follow current exact pin");
check(foundationSync.includes("delivery.generated_tokens") && foundationSync.includes("delivery.generated_css"), "WeiUI sync must derive paths from integration contract");

const tokenIndex = siteCss.indexOf('@import "../generated/weiui.tokens.generated.css"');
const cssIndex = siteCss.indexOf('@import "../generated/weiui.generated.css"');
const storyIndex = siteCss.indexOf('@import "../../../assets/brand/story-loom.weiui.css"');
check(tokenIndex >= 0 && cssIndex > tokenIndex && storyIndex > cssIndex, "CSS import order must be WeiUI tokens → WeiUI CSS → Story Loom");
check(main.includes('import "./styles/product-contract.css"'), "main must load the Product composition semantic bridge");
check(main.includes('import "./styles/product-surface.css"') && main.includes('import "./styles/unified-product-app.css"'), "main must load the shared product surface layers");
check(productContractCss.includes("--pe-touch-target: var(--nf-touch-target-min, 44px)"), "Product semantic bridge must derive touch targets from Story Loom");

check(main.includes('import ProductApp from "./ProductApp"') && main.includes("render(() => <ProductApp />, root)"), "main must mount one unified ProductApp");
check(!main.includes("standaloneProductPaths") && !main.includes("Entry initialLocale"), "main must not retain standalone product surfaces");
check(app.includes("<Router root={ProductShell}>"), "ProductApp must have one shared Router root shell");
check(app.includes("const UiContext = createContext"), "ProductApp must share locale/appearance state through one context");
check(surface.includes("export function ProductSurfaceHero"), "shared ProductSurfaceHero primitive missing");
check((app.match(/<ProductSurfaceHero/g) ?? []).length >= 8, "product pages must consistently consume ProductSurfaceHero");

for (const route of ["/", "/product", "/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) {
  check(app.includes(`path="${route}"`), `missing required shared Product route ${route}`);
}
check(app.includes('path="/start"') && app.includes('<Navigate href="/"'), "legacy /start must resolve inside the shared router");
check(app.includes('href={zh() ? "/docs" : "/docs/en"}'), "Knowledge must remain a deliberate separate docs boundary");
check(app.includes("https://studio.novelforge.wei-dev.com"), "shared shell must expose the real Hosted Studio entry point");
check(app.includes("metaKey || event.ctrlKey") && app.includes('event.key.toLowerCase() === "k"'), "shared shell must expose Ctrl/Cmd+K command palette shortcut");
check(app.includes("command-dialog") && app.includes("showModal"), "shared shell must expose an accessible command dialog");
check(app.includes('id="main-content"') && app.includes('aria-expanded={menuOpen()}'), "shared shell must expose skip target and accessible mobile disclosure");

for (const primitive of ["wui-app-bar", "wui-button", "wui-card", "wui-command", "wui-badge"]) {
  check(runtime.includes(primitive), `unified Product runtime must consume WeiUI primitive .${primitive}`);
}
check(runtime.includes("wui-input-group") || runtime.includes("wui-tabs"), "feature surfaces must retain WeiUI form/navigation primitives");

check(packageJson.scripts?.content?.includes("sync-weiui.mjs") || packageJson.scripts?.content?.includes("foundation"), "content build must sync WeiUI foundation");
check(packageJson.scripts?.build?.includes("npm run content"), "production build must compile Product Entry content first");
check(contentCompiler.includes("marked.lexer") && !contentCompiler.includes("marked.parse("), "documentation compiler must use structured parser tokens");
check(contentCompiler.includes('authority: false'), "generated documentation must remain authority=false");
check(renderer.includes("DocumentBlock") && renderer.includes("InlineNode") && !renderer.includes("innerHTML"), "document renderer must consume structured AST without innerHTML");
check(!runtime.includes("api.github.com"), "Product runtime must not depend on GitHub API");

check(exists("public/generated/docs-index.json") && exists("public/generated/build-meta.json"), "generated documentation build artifacts missing");
const docsIndex = readJson("public/generated/docs-index.json");
const buildMeta = readJson("public/generated/build-meta.json");
check(docsIndex.schema === "novelforge_product_document_index_v1" && docsIndex.authority === false, "generated documentation index contract drifted");
check(buildMeta.schema === "novelforge_product_content_build_v1" && buildMeta.authority === false, "generated content build metadata contract drifted");
check(buildMeta.parser === "marked@18.0.7", "generated content must record exact Markdown parser identity");
check(Number(docsIndex.documentCount) >= 20, `expected substantial repository documentation corpus; got ${docsIndex.documentCount}`);
check(docsIndex.documents.some((doc) => doc.locale === "en-US") && docsIndex.documents.some((doc) => doc.locale === "zh-CN"), "generated docs must include both locales");
check(docsIndex.documents.every((doc) => typeof doc.sourceFingerprint === "string" && doc.sourceFingerprint.length === 64), "every generated document index entry must carry source SHA-256");

const fakeMarketingPatterns = [/10K\+/i, /99\.9%\s*(uptime|sla)/i, /start free trial/i, /trusted by (?:industry|leading|thousands|teams)/i, /customer logos?/i, /limited seats?/i, /five[- ]star rating/i];
for (const pattern of fakeMarketingPatterns) check(!pattern.test(allCopy), `fabricated or placeholder marketing claim matched ${pattern}`);

check(siteCss.includes("@media (max-width: 760px)") && unifiedCss.includes("@media (max-width: 760px)"), "Product Entry must preserve responsive layout contracts");
check(surfaceCss.includes("color-mix(in oklab") && unifiedCss.includes("color-mix(in oklab"), "shared product surfaces must remain Story Loom color-token driven");
for (const requiredShowcase of ["@property --pe-angle", ":has(", "color-mix(in oklab", "@starting-style", "allow-discrete", "animation-timeline: view(", "::view-transition-old(root)", "@container", "@scope", "@supports (anchor-name:", "@media (prefers-reduced-motion: reduce)"]) {
  check(showcaseCss.includes(requiredShowcase), `modern CSS progressive enhancement missing: ${requiredShowcase}`);
}
check(!/animation-iteration-count\s*:\s*infinite|animation\s*:[^;]*\binfinite\b/i.test(`${showcaseCss}\n${unifiedCss}`), "Product Entry must not introduce idle infinite animation");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(runtime), "Product runtime must not add default polling or decorative frame loops");
for (const forbidden of [/\.novelforge\/runtime\.db/, /sqlite/i]) check(!forbidden.test(runtime), `Product Entry must not couple to private runtime storage: ${forbidden}`);
check(indexHtml.includes('name="viewport"') && indexHtml.includes('class="skip-link"'), "index.html must retain viewport and skip link contracts");

if (failures.length) {
  for (const failure of failures) console.error(`product-site-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "novelforge_product_site_quality_v3", status: "pass", identity: "unified_product_spa", stack: "SolidJS + TypeScript + Vite", shared_shell: true, shared_locale_state: true, shared_appearance_state: true, shared_command_palette: true, docs_boundary: "starlight", authority: false }, null, 2));
}

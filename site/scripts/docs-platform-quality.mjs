#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const pkg = JSON.parse(read("package.json"));
const config = read("docs-site/astro.config.mjs");
const contentConfig = read("docs-site/src/content.config.ts");
const siteTitle = read("docs-site/src/components/NovelForgeSiteTitle.astro");
const actions = read("docs-site/src/components/NovelForgeActions.astro");
const landing = read("docs-site/src/components/DocsLanding.astro");
const stagingCompiler = read("scripts/build-starlight-content.mjs");
const verifier = read("scripts/verify-starlight-build.mjs");
const distPrep = read("scripts/prepare-dist.mjs");
const staticServer = read("scripts/serve-dist.mjs");
const redirects = read("public/_redirects");
const manifest = JSON.parse(fs.readFileSync(path.resolve(siteRoot, "../docs/documentation_manifest.json"), "utf8"));
const stagedRoot = path.join(siteRoot, "docs-site", "src", "content", "docs");

const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

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

check(pkg.version === "0.9.0", "Godot replacement package milestone must be 0.9.0");
check(pkg.devDependencies?.astro === "7.1.6", "Astro must remain exact-pinned at 7.1.6");
check(pkg.devDependencies?.["@astrojs/starlight"] === "0.41.5", "Starlight must remain exact-pinned at 0.41.5");
check(Object.keys(pkg.dependencies ?? {}).length === 0, "Product root must not retain browser-framework runtime dependencies");
for (const dependency of ["solid-js", "@solidjs/router", "vite", "vite-plugin-solid", "typescript", "marked"]) {
  check(!pkg.dependencies?.[dependency] && !pkg.devDependencies?.[dependency], `legacy Product dependency must be removed: ${dependency}`);
}
check(!fs.existsSync(path.join(siteRoot, "src")), "legacy Solid Product source tree must be removed");
check(!fs.existsSync(path.join(siteRoot, "index.html")), "legacy Vite Product host must be removed");
check(!fs.existsSync(path.join(siteRoot, "vite.config.ts")), "legacy Vite configuration must be removed");
check(!fs.existsSync(path.join(siteRoot, "tsconfig.json")), "legacy Product TypeScript configuration must be removed");
check(!Object.values(pkg.scripts ?? {}).some((value) => /\b(?:vite|tsc)\b/.test(String(value))), "Product scripts must not invoke Vite or tsc");
check(pkg.scripts?.build === "npm run prepare:dist && npm run docs:build", "pre-Godot production build must own only static host files and Starlight Docs");
check(pkg.scripts?.preview === "node scripts/serve-dist.mjs", "browser QA must preview the exported dist without a Vite SPA server");
check(pkg.scripts?.["godot:build"]?.includes("build-godot-web.sh"), "Godot export must remain the Product runtime build");
check(pkg.scripts?.quality?.includes("godot-web-quality.mjs"), "quality gate must include the Godot Product contract");

check(config.includes('base: "/docs"'), "Starlight must exclusively own /docs/**");
check(config.includes('outDir: "../dist/docs"'), "Starlight output must compose into site/dist/docs");
check(config.includes('lang: "zh-CN"') && config.includes('lang: "en"'), "Docs must remain bilingual");
check(config.includes("starlight({"), "Docs must remain powered by Starlight");
check(contentConfig.includes("docsLoader()") && contentConfig.includes("docsSchema()"), "Starlight content collection must use official loader and schema");
check(siteTitle.includes('class="nf-brand-home" href="/"'), "Docs brand must return to the Godot Product home");
for (const href of ["/product", "/studio", "/architecture", "/publication"]) {
  check(actions.includes(`href="${href}"`), `Docs header must retain Godot Product handoff ${href}`);
}
check(landing.includes('"/inspect"') && landing.includes('"/playground"') && landing.includes('"/agents"'), "Docs landing must retain direct handoffs to live Godot tool routes");
check(stagingCompiler.includes("rewriteHtmlAttributes") && stagingCompiler.includes("copyRelativeAsset"), "Docs staging must preserve repository-local links and assets");
check(verifier.includes("data-nf-docs-home"), "Docs build must verify the curated landing marker");

const expectedStaged = (manifest.documents.length - 1) * 2;
check(markdownCount(stagedRoot) === expectedStaged, `Starlight staging must contain ${expectedStaged} localized Markdown pages`);
check(!fs.existsSync(path.join(stagedRoot, "index.md")), "curated zh-CN Docs landing must not be shadowed by staged Markdown");
check(!fs.existsSync(path.join(stagedRoot, "en", "index.md")), "curated English Docs landing must not be shadowed by staged Markdown");

check(distPrep.includes("fs.rmSync(distRoot") && distPrep.includes("fs.cpSync"), "dist preparation must clean stale Product artifacts and preserve root public host files");
check(staticServer.includes('application/wasm') && staticServer.includes('application/octet-stream'), "static preview must serve Godot WASM and PCK with explicit MIME types");
check(staticServer.includes('/^\\/docs(?:\\/|$)/') && staticServer.includes("Documentation page not found"), "local preview must never fall missing Docs paths into the Product canvas");
check(staticServer.includes('path.join(distRoot, "index.html")'), "local preview must fallback Product routes to the Godot host document");
check(redirects.includes("/docs /docs/ 301") && redirects.includes("/docs/en /docs/en/ 301"), "Cloudflare canonical Docs redirects must be retained");

if (failures.length) {
  for (const failure of failures) console.error(`docs-platform-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_docs_platform_quality_v8",
    status: "pass",
    product_runtime: "godot_web",
    legacy_product_spa: false,
    docs_runtime: "astro_starlight",
    docs_base: "/docs/**",
    localized_docs: true,
    product_route_preview: "godot_host_fallback",
    authority: false
  }, null, 2));
}

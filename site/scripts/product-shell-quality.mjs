#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(siteRoot, relative));
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const publication = read("src/PublicationWorkbench.tsx");
const content = read("src/content.ts");
const surface = read("src/ProductSurface.tsx");
const styleIndex = read("src/styles/index.css");
const shellCss = read("src/styles/product-shell.css");
const embedded = read("src/styles/embedded-features.css");
const routeSurfaces = `${app}\n${publication}`;
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(main.includes('import ProductApp from "./ProductApp"'), "main must import ProductApp");
check(main.includes("<ProductApp />"), "main must retain the single shared ProductApp runtime");
check(main.includes("ProductFailureBoundary"), "main must wrap ProductApp in the shared resilience boundary");
check(main.includes("installCrossAppNavigationGuard"), "main must preserve an explicit cross-app navigation boundary");
check(main.includes("/^\\/docs(?:\\/|$)/"), "docs cross-app boundary must match /docs and all nested docs routes");
check(main.includes("window.location.assign(url.href)"), "docs cross-app boundary must perform a real document navigation");
for (const forbidden of ["standaloneProductPaths", "ProjectInspectorEntry", "LocalPlaygroundEntry", "ArchitectureExplorerEntry", "PublicationWorkbenchEntry", "AgentIntegrationEntry", "history.pushState =", "history.replaceState ="]) {
  check(!main.includes(forbidden), `main must not retain legacy standalone shell logic: ${forbidden}`);
}

for (const retiredFile of [
  "src/App.tsx",
  "src/ArchitectureExplorerEntry.tsx",
  "src/PublicationWorkbenchEntry.tsx",
  "src/ProjectInspectorEntry.tsx",
  "src/LocalPlaygroundEntry.tsx",
  "src/AgentIntegrationEntry.tsx",
  "src/styles/surface-consistency.css",
]) {
  check(!exists(retiredFile), `retired duplicate surface must stay deleted: ${retiredFile}`);
}

check(app.includes("<Router root={ProductShell}>"), "all product pages must share one Router root shell");
check(app.includes("const UiContext = createContext"), "locale/theme state must be owned by one shared UI context");
check(app.includes("function ProductShell"), "shared ProductShell component is missing");
check(app.includes("createEffect(syncDocumentState)"), "shared shell must own document locale/theme synchronization");
check(app.includes("function ProductSurfaceHero") === false, "shared hero implementation must live outside ProductApp");
check(surface.includes("export function ProductSurfaceHero"), "shared ProductSurfaceHero component is missing");
check((app.match(/<header class="wui-app-bar product-appbar"/g) ?? []).length === 1, "ProductApp must have exactly one product header owner");
check((app.match(/<footer class="site-footer unified-product-footer"/g) ?? []).length === 1, "ProductApp must have exactly one product footer owner");

for (const route of ["/", "/product", "/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) {
  check(app.includes(`path="${route}"`), `shared ProductApp missing route ${route}`);
}

check(app.includes("const primaryNav = (): ShellNavItem[]"), "shared shell must own one primary navigation model");
check(app.includes("const utilityNav = (): ShellNavItem[]"), "shared shell must own one utility navigation model");
for (const nav of ["/product", "/studio", "/architecture", "/publication"]) {
  check(app.includes(`href: "${nav}"`), `canonical primary navigation missing ${nav}`);
}
check(app.includes('kind: "document", href: zh() ? "/docs" : "/docs/en"'), "Knowledge must remain an explicit documentation boundary in primary navigation");
check(content.includes('export const githubRoot = "https://github.com/xiaooye/Quillframe"'), "content source must own canonical GitHub repository root");
check(app.includes('import { githubRoot, type Locale } from "./content"'), "ProductApp must consume the canonical GitHub repository root");
check(app.includes('kind: "external", href: githubRoot, label: copy().nav.github'), "GitHub must be a primary external navigation entry");
check(app.includes('<For each={primaryNav()}>{(item) => navLink(item, "wui-app-bar__link")}</For>'), "desktop header must render the shared primary navigation model");
check(app.includes('<For each={primaryNav()}>{(item) => navLink(item, "wui-sidebar__item")}</For>'), "mobile navigation must render the shared primary navigation model");
check(app.includes('<div class="footer-links"><For each={primaryNav()}>{(item) => navLink(item, "footer-link")}</For></div>'), "footer primary section must render the same primary navigation model");
check(app.includes('href: "/changelog", label: copy().nav.changelog'), "utility navigation must expose Changelog");
check(app.includes("noopener noreferrer"), "external shell links must use safe new-window semantics");
check(app.includes('const productVersion = "1.0.0-dev.0"'), "visible product shell identity must track the 1.0 development release");
check(!app.includes("0.8.x"), "stale 0.8.x shell identity must not remain in ProductApp");

check(app.includes("header-search") && app.includes("command-dialog") && app.includes("showModal"), "shared shell must own one command palette");
check(app.includes('label: copy().nav.github') && app.includes('label: copy().nav.changelog') && app.includes('description: copy().routes.studio.lede'), "command palette must expose GitHub, Changelog, and Studio landing");
check(app.includes("aria-expanded={menuOpen()}"), "shared shell must own accessible mobile navigation state");
check(app.includes("const [locale, setLocale] = createSignal") && app.includes("const [dark, setDark] = createSignal"), "shared ProductApp must own one locale and one appearance state");

/* Header and footer share a dedicated style owner instead of drifting through
 * route CSS or late overrides. */
check(styleIndex.includes('@import "./product-shell.css"'), "Product stylesheet entrypoint must load the shared ProductShell style owner");
check(styleIndex.indexOf('product-contract.css') < styleIndex.indexOf('product-shell.css') && styleIndex.indexOf('product-shell.css') < styleIndex.indexOf('product-surface.css'), "ProductShell style owner must sit with shared primitives before route styling");
for (const marker of [".unified-product-shell .product-appbar", ".unified-product-footer", ".unified-product-footer .footer-link"]) {
  check(shellCss.includes(marker), `shared ProductShell CSS missing ${marker}`);
}
check(shellCss.includes("background: transparent") && shellCss.includes("border-block-start"), "footer must use the same quiet canvas language as the top shell");
check(!shellCss.includes("radial-gradient"), "shared ProductShell chrome must not use route-level radial wallpaper");
check(!shellCss.includes("!important"), "shared ProductShell styling must not depend on specificity escape hatches");

for (const pageMarker of ["function HomePage", "function ProductPage", "function StudioPage", "function ArchitecturePage", "function PublicationPage", "function InspectorPage", "function PlaygroundPage", "function AgentsPage", "function ChangelogPage"]) {
  check(app.includes(pageMarker), `shared ProductApp missing ${pageMarker}`);
}
const heroUses = (routeSurfaces.match(/<ProductSurfaceHero/g) ?? []).length;
check(heroUses >= 8, `expected shared ProductSurfaceHero across product pages; got ${heroUses}`);
check(embedded.includes(".project-inspector-intro") && embedded.includes(".playground-intro"), "embedded feature bodies must suppress duplicate internal page heroes");

if (failures.length) {
  for (const failure of failures) console.error(`product-shell-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_product_shell_quality_v5",
    status: "pass",
    shared_router: true,
    shared_header: true,
    shared_footer: true,
    shared_shell_style_owner: "product-shell.css",
    shared_primary_navigation: true,
    shared_mobile_navigation: true,
    github_entry: true,
    changelog_entry: true,
    product_version: "1.0.0-dev.0",
    shared_locale_state: true,
    shared_appearance_state: true,
    shared_command_palette: true,
    shared_surface_hero: true,
    resilience_boundary: true,
    standalone_product_shells: 0,
    duplicate_runtime_sources: 0,
    docs_boundary: "hard-navigation",
  }, null, 2));
}

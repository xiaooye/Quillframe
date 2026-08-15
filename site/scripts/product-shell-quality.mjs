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
const surface = read("src/ProductSurface.tsx");
const embedded = read("src/styles/embedded-features.css");
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
for (const nav of ["/product", "/studio", "/architecture", "/publication"]) {
  check(app.includes(`["${nav}"`), `canonical product navigation missing ${nav}`);
}
check(app.includes('href={zh() ? "/docs" : "/docs/en"}'), "Knowledge must remain an explicit documentation boundary");
check(app.includes("header-search") && app.includes("command-dialog") && app.includes("showModal"), "shared shell must own one command palette");
check(app.includes("aria-expanded={menuOpen()}"), "shared shell must own accessible mobile navigation state");
check(app.includes("const [locale, setLocale] = createSignal") && app.includes("const [dark, setDark] = createSignal"), "shared ProductApp must own one locale and one appearance state");

for (const pageMarker of ["function HomePage", "function ProductPage", "function StudioPage", "function ArchitecturePage", "function PublicationPage", "function InspectorPage", "function PlaygroundPage", "function AgentsPage", "function ChangelogPage"]) {
  check(app.includes(pageMarker), `shared ProductApp missing ${pageMarker}`);
}
const heroUses = (app.match(/<ProductSurfaceHero/g) ?? []).length;
check(heroUses >= 8, `expected shared ProductSurfaceHero across product pages; got ${heroUses}`);
check(embedded.includes(".project-inspector-intro") && embedded.includes(".playground-intro"), "embedded feature bodies must suppress duplicate internal page heroes");

if (failures.length) {
  for (const failure of failures) console.error(`product-shell-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "novelforge_product_shell_quality_v3", status: "pass", shared_router: true, shared_header: true, shared_footer: true, shared_locale_state: true, shared_appearance_state: true, shared_command_palette: true, shared_surface_hero: true, resilience_boundary: true, standalone_product_shells: 0, duplicate_runtime_sources: 0, docs_boundary: "hard-navigation" }, null, 2));
}

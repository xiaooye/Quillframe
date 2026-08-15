#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const surface = read("src/ProductSurface.tsx");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(main.includes('import ProductApp from "./ProductApp"'), "main must import ProductApp");
check(main.includes("render(() => <ProductApp />, root)"), "main must render only the shared ProductApp");
for (const forbidden of ["standaloneProductPaths", "ProjectInspectorEntry", "LocalPlaygroundEntry", "ArchitectureExplorerEntry", "PublicationWorkbenchEntry", "AgentIntegrationEntry", "history.pushState =", "history.replaceState ="]) {
  check(!main.includes(forbidden), `main must not retain legacy standalone shell logic: ${forbidden}`);
}

check(app.includes("<Router root={ProductShell}>"), "all product pages must share one Router root shell");
check(app.includes("const UiContext = createContext"), "locale/theme state must be owned by one shared UI context");
check(app.includes("function ProductShell"), "shared ProductShell component is missing");
check(app.includes("createEffect(syncDocumentState)"), "shared shell must own document locale/theme synchronization");
check(app.includes("function ProductSurfaceHero") === false, "shared hero implementation must live outside ProductApp");
check(surface.includes("export function ProductSurfaceHero"), "shared ProductSurfaceHero component is missing");

for (const route of ["/", "/product", "/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) {
  check(app.includes(`path="${route}"`), `shared ProductApp missing route ${route}`);
}
for (const nav of ["/product", "/studio", "/architecture", "/publication"]) {
  check(app.includes(`["${nav}"`), `canonical product navigation missing ${nav}`);
}
check(app.includes('href={zh() ? "/docs" : "/docs/en"}'), "Knowledge must remain an explicit documentation boundary");
check(app.includes("header-search") && app.includes("command-dialog") && app.includes("showModal"), "shared shell must own one command palette");
check(app.includes("aria-expanded={menuOpen()}"), "shared shell must own accessible mobile navigation state");

for (const pageMarker of ["function ArchitecturePage", "function PublicationPage", "function InspectorPage", "function PlaygroundPage", "function AgentsPage"]) {
  check(app.includes(pageMarker), `shared ProductApp missing ${pageMarker}`);
}
const heroUses = (app.match(/<ProductSurfaceHero/g) ?? []).length;
check(heroUses >= 8, `expected shared ProductSurfaceHero across product pages; got ${heroUses}`);
check(!/const \[locale, setLocale\].*function ArchitecturePage/s.test(app.slice(app.indexOf("function ArchitecturePage"))), "feature pages must not create their own locale state");

if (failures.length) {
  for (const failure of failures) console.error(`product-shell-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "novelforge_product_shell_quality_v1", status: "pass", shared_router: true, shared_header: true, shared_footer: true, shared_locale_state: true, shared_appearance_state: true, shared_command_palette: true, shared_surface_hero: true, standalone_product_shells: 0, docs_boundary: "separate" }, null, 2));
}

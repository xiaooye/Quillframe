#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const failures = [];
const check = (ok, message) => { if (!ok) failures.push(message); };

const project = read("godot/project.godot");
const scene = read("godot/Main.tscn");
const main = read("godot/scripts/main.gd");
const parity = read("godot/scripts/main_parity.gd");
const routes = read("godot/scripts/route_surfaces.gd");
const catalog = read("godot/scripts/route_catalog.gd");
const systems = read("godot/scripts/system_surfaces.gd");
const editorial = read("godot/scripts/editorial_surfaces.gd");
const typography = read("godot/scripts/typography_parity.gd");
const mobileGeometry = read("godot/scripts/mobile_geometry_parity.gd");
const shell = read("godot/web/novelforge.html");
const fontFetch = read("scripts/fetch-godot-fonts.sh");

check(project.includes('run/main_scene="res://Main.tscn"'), "Godot main scene must remain explicit");
check(project.includes('renderer/rendering_method="gl_compatibility"'), "Web migration must use Compatibility renderer");
check(scene.includes('path="res://scripts/mobile_geometry_parity.gd"'), "shadow scene must enter through the final mobile geometry parity layer");
check(mobileGeometry.includes('extends "res://scripts/typography_parity.gd"'), "mobile geometry parity must remain a thin layer above deterministic typography");
check(scene.includes("offset_right = -15.0"), "web page scrollbar gutter must remain reserved in the Godot layout viewport");
check(!/Node3D|Camera3D|MeshInstance3D/.test(scene + main + parity + routes + catalog + systems + editorial + typography + mobileGeometry), "migration is capped at 2.5D; 3D scene nodes are forbidden");

check(typography.includes('INTER_FONT_PATH := "res://generated/Inter-opsz-wght.ttf"'), "WeiUI Latin typography must be pinned to Inter");
check(typography.includes("_contains_cjk"), "Latin/CJK font selection must remain text-aware");
check(typography.includes("_cjk_font") && typography.includes("_latin_base_font"), "Latin and CJK typography metrics must stay isolated");
check(typography.includes("fallbacks.append(_base_font)"), "decorative mixed font must retain CJK fallback");
check(typography.includes("_reset_label_scale"), "legacy Noto width compensation must be neutralized under Inter");

check(main.includes('FONT_PATH := "res://generated/NotoSansSC-wght.ttf"'), "deterministic bundled CJK font is required");
check(main.includes('SYMBOL_FONT_PATH := "res://generated/NotoSansSymbols2-Regular.ttf"'), "deterministic symbol fallback is required");
check(main.includes('THAI_FONT_PATH := "res://generated/NotoSansThai-wdth-wght.ttf"'), "deterministic Thai fallback is required for baseline kaomoji");
check(main.includes('ARABIC_FONT_PATH := "res://generated/NotoSansArabic-wdth-wght.ttf"'), "deterministic Arabic fallback is required for baseline kaomoji");
for (const fingerprint of [
  "047c92f6e2212473dc436020afed689527076d44",
  "fb0637bafbcd804fe32152370a1225990745b4bc",
  "caf89dd0e60e23ac39ce18da823095959d409437",
  "34b48ab6f74867dbfce19410a2f452abef34e3ff",
  "f1d01edce4ebaedcbe9a06fc75fec07b304ec3df",
]) check(fontFetch.includes(fingerprint), `pinned font fingerprint missing: ${fingerprint}`);

check(main.includes("ฅ^•ﻌ•^ฅ"), "baseline kawaii status copy must remain exact");
check(main.includes('BOOKS_ICON_PATH := "res://assets/books-stack.svg"'), "Knowledge icon must use deterministic local vector art");
check(main.includes("Let the story\\ngrow without\\nletting the\\nsystem lose\\nthe plot."), "desktop/mobile baseline headline geometry must stay explicit");
check(parity.includes("LAUNCHER_CONTENT_INSET := 36.0"), "Story Loom content inset must preserve the Solid material-panel content box");
check(parity.includes("MOBILE_LEDE_LINE_SPACING := 3"), "mobile hero lede rhythm must remain calibrated to the Solid baseline");
check(parity.includes("DESKTOP_LEDE_LINE_SPACING := 4"), "desktop hero lede rhythm must remain calibrated to the Solid baseline");
check(parity.includes('Color("b0a8da")'), "Godot scrollbar thumb must preserve the Atelier lavender scrollbar treatment");
check(parity.includes('route == "/product"'), "Product route must remain an explicit shadow surface");
check(routes.includes('title_size = 62 if not stacked else 39'), "Product typography must preserve route-specific desktop/mobile sizing");
check(routes.includes('stack_size.x - (130.0 if not phone else 68.0)'), "Product stack geometry must stay baseline-calibrated");
check(catalog.includes('"/studio"') && catalog.includes('"/changelog"'), "Studio and Changelog must remain explicit Godot shadow surfaces");
for (const route of ["/inspect", "/playground", "/agents"]) check(systems.includes(`"${route}"`), `${route} must remain an explicit Godot shadow surface`);
for (const route of ["/architecture", "/publication"]) check(editorial.includes(`"${route}"`), `${route} must remain an explicit Godot shadow surface`);
check(systems.includes("PROJECT INSPECTOR") && systems.includes("LOCAL PLAYGROUND") && systems.includes("AGENT PATCH BAY"), "system route identity surfaces must remain explicit");
check(editorial.includes("INTERACTIVE ARCHITECTURE") && editorial.includes("PUBLICATION WORKBENCH"), "editorial route identity surfaces must remain explicit");

check(mobileGeometry.includes("NovelForge is a\\nfiction production\\nsystem, not a\\nprompt wrapper."), "Product phone heading must preserve the four-line Solid wrap");
check(mobileGeometry.includes("with progressive\\ndisclosure instead\\nof dashboard\\noverload."), "Studio phone heading must preserve the seven-line Solid wrap");
check(mobileGeometry.includes('pink.text = "many"') && mobileGeometry.includes('"deterministic\\nderivatives."'), "Publication phone heading must keep inline pink continuation geometry");
check(mobileGeometry.includes("_fix_epub_card_position"), "Publication phone format cards must retain deterministic grid placement");

check(main.includes('"phone"') && main.includes('"compact"') && main.includes('"desktop"'), "three responsive layout modes are required");
check(main.includes("window.location.assign") && parity.includes("window.history.pushState"), "browser navigation boundary must stay explicit");
check(main.includes("novelforge:godot-ready"), "browser readiness marker is required");
check(shell.includes('$GODOT_URL') && shell.includes('$GODOT_CONFIG'), "custom Web shell must retain Godot placeholders");
check(shell.includes('data-novelforge-godot-shadow="loading"'), "shadow runtime marker missing");

if (failures.length) {
  failures.forEach((failure) => console.error(`godot-shadow-source-quality: FAIL: ${failure}`));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_godot_shadow_source_quality_v10",
    status: "pass",
    production_cutover: false,
    visual_baseline: "Solid/Vite Story Loom Kawaii Atelier",
    typography_authority: "WeiUI Inter + Noto Sans SC",
    renderer: "gl_compatibility",
    max_dimension: "2.5D",
    deterministic_latin_font: true,
    deterministic_cjk_font: true,
    deterministic_unicode_fallbacks: true,
    fallback_scope: "decorative_controls_only",
    page_grid_contract: true,
    route_surface_contract: true,
    route_catalog_contract: true,
    system_surface_contract: true,
    editorial_surface_contract: true,
    mobile_geometry_contract: true,
    authority: false,
  }, null, 2));
}

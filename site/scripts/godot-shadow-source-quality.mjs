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
const shell = read("godot/web/novelforge.html");
const fontFetch = read("scripts/fetch-godot-fonts.sh");

check(project.includes('run/main_scene="res://Main.tscn"'), "Godot main scene must remain explicit");
check(project.includes('renderer/rendering_method="gl_compatibility"'), "Web migration must use Compatibility renderer");
check(!/Node3D|Camera3D|MeshInstance3D/.test(scene + main), "migration is capped at 2.5D; 3D scene nodes are forbidden");
check(main.includes('FONT_PATH := "res://generated/NotoSansSC-wght.ttf"'), "deterministic bundled CJK font is required");
check(main.includes('SYMBOL_FONT_PATH := "res://generated/NotoSansSymbols2-Regular.ttf"'), "deterministic symbol fallback is required");
check(main.includes('THAI_FONT_PATH := "res://generated/NotoSansThai-wdth-wght.ttf"'), "deterministic Thai fallback is required for baseline kaomoji");
check(main.includes('ARABIC_FONT_PATH := "res://generated/NotoSansArabic-wdth-wght.ttf"'), "deterministic Arabic fallback is required for baseline kaomoji");
check(main.includes('text_server.name_to_tag("wght")'), "variable font weight must use a TextServer OpenType tag");
for (const fingerprint of [
  "fb0637bafbcd804fe32152370a1225990745b4bc",
  "caf89dd0e60e23ac39ce18da823095959d409437",
  "34b48ab6f74867dbfce19410a2f452abef34e3ff",
  "f1d01edce4ebaedcbe9a06fc75fec07b304ec3df",
]) check(fontFetch.includes(fingerprint), `pinned font fingerprint missing: ${fingerprint}`);
check(main.includes("ฅ^•ﻌ•^ฅ"), "baseline kawaii status copy must remain exact");
check(main.includes('BOOKS_ICON_PATH := "res://assets/books-stack.svg"'), "Knowledge icon must use deterministic local vector art");
check(main.includes("Let the story\\ngrow without\\nletting the\\nsystem lose\\nthe plot."), "desktop/mobile baseline headline geometry must stay explicit");
check(main.includes('"phone"') && main.includes('"compact"') && main.includes('"desktop"'), "three responsive layout modes are required");
check(main.includes("window.location.assign") && main.includes("window.history.pushState"), "browser navigation boundary must stay explicit");
check(main.includes("novelforge:godot-ready"), "browser readiness marker is required");
check(shell.includes('$GODOT_URL') && shell.includes('$GODOT_CONFIG'), "custom Web shell must retain Godot placeholders");
check(shell.includes('data-novelforge-godot-shadow="loading"'), "shadow runtime marker missing");

if (failures.length) {
  failures.forEach((failure) => console.error(`godot-shadow-source-quality: FAIL: ${failure}`));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_godot_shadow_source_quality_v2",
    status: "pass",
    production_cutover: false,
    visual_baseline: "Solid/Vite Story Loom Kawaii Atelier",
    renderer: "gl_compatibility",
    max_dimension: "2.5D",
    deterministic_cjk_font: true,
    deterministic_unicode_fallbacks: true,
    authority: false,
  }, null, 2));
}

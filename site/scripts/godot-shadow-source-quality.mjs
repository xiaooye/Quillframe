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
check(main.includes('FONT_PATH := "res://generated/NotoSansSC-wght.ttf"'), "deterministic bundled font is required");
check(fontFetch.includes("fb0637bafbcd804fe32152370a1225990745b4bc"), "Noto Sans SC binary must stay content-pinned");
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
    schema: "novelforge_godot_shadow_source_quality_v1",
    status: "pass",
    production_cutover: false,
    visual_baseline: "Solid/Vite Story Loom Kawaii Atelier",
    renderer: "gl_compatibility",
    max_dimension: "2.5D",
    deterministic_cjk_font: true,
    authority: false,
  }, null, 2));
}

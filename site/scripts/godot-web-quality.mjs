import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const check = (condition, message) => {
  if (!condition) {
    console.error(`godot-web-quality: ${message}`);
    process.exitCode = 1;
  }
};

const project = read("godot/project.godot");
const preset = read("godot/export_presets.cfg");
const scene = read("godot/Main.tscn");
const main = read("godot/scripts/main.gd");
const systemMap = read("godot/scripts/system_map.gd");
const shell = read("godot/web/novelforge.html");
const buildScript = read("scripts/build-godot-web.sh");

check(project.includes('run/main_scene="res://Main.tscn"'), "Godot runtime must boot Main.tscn");
check(project.includes('renderer/rendering_method="gl_compatibility"'), "Web runtime must use Compatibility rendering");
check(preset.includes('platform="Web"'), "Web export preset is required");
check(preset.includes('variant/thread_support=false'), "Web export must stay single-threaded unless hosting headers are deliberately changed");
check(preset.includes('html/custom_html_shell="res://web/novelforge.html"'), "Web export must use the branded NovelForge HTML shell");
check(scene.includes('type="Control"'), "root scene must remain a 2D Control surface");

for (const [name, source] of [["Main.tscn", scene], ["main.gd", main], ["system_map.gd", systemMap]]) {
  check(!/\b(Node3D|Camera3D|MeshInstance3D|CSGShape3D|PhysicsBody3D|WorldEnvironment)\b/.test(source), `${name} must not introduce 3D runtime nodes`);
}

for (const route of ["/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) {
  check(main.includes(`"${route}"`), `product runtime must preserve ${route}`);
}

check(main.includes("window.history.pushState"), "Godot navigation must synchronize browser history");
check(main.includes("addEventListener(\"popstate\""), "browser back/forward must drive the Godot scene");
check(main.includes("window.location.assign('/docs')"), "Docs must remain a hard cross-application navigation boundary");
check(main.includes("novelforgeRuntime='ready'"), "main scene must publish a browser-visible readiness marker");
check(main.includes("novelforge:ready"), "main scene must publish a runtime-ready browser event");
check(systemMap.includes("_parallax"), "system map must retain 2.5D parallax depth cues");
check(systemMap.includes("_draw_packet"), "system map must retain animated execution packets");

check(shell.includes('$GODOT_URL') && shell.includes('$GODOT_CONFIG'), "custom Web shell must preserve required Godot export placeholders");
check(shell.includes('data-novelforge-runtime="loading"'), "custom Web shell must expose the loading state to browser QA");
check(shell.includes('id="nf-loader"') && shell.includes('id="nf-progress"'), "custom Web shell must provide branded loading and progress UI");
check(!shell.includes("GODOT\n") && !shell.includes("Game engine"), "custom loader must not regress to Godot default splash branding");

check(buildScript.includes('--export-release Web'), "CI export script must produce a release Web artifact");
check(buildScript.includes('--quit-after 2'), "CI export script must instantiate the product scene before export");
check(buildScript.includes('test -d "${DIST_DIR}/docs"'), "Godot export must preserve the already-built Docs app");
check(buildScript.includes('data-novelforge-runtime="loading"'), "export verification must prove the branded shell was emitted");

if (!process.exitCode) {
  console.log("godot-web-quality: pass");
}

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
const browserProof = read("scripts/godot-browser-proof.mjs");

check(project.includes('run/main_scene="res://Main.tscn"'), "Godot runtime must boot Main.tscn");
check(project.includes('renderer/rendering_method="gl_compatibility"'), "Web runtime must use Compatibility rendering");
check(project.includes('window/stretch/mode="disabled"'), "non-game Product UI must keep one scene unit per browser pixel");
check(project.includes('window/size/viewport_width=390'), "base design width must cover the smallest supported phone surface");
check(!project.includes('window/size/window_width_override'), "Web Product UI must not pin a desktop window override");
check(preset.includes('platform="Web"'), "Web export preset is required");
check(preset.includes('html/canvas_resize_policy=2'), "Web canvas must use the adaptive resize policy");
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
check(main.includes("window.addEventListener('popstate'"), "browser back/forward must remain bound to product routing");
check(main.includes("window.location.reload()"), "popstate must rehydrate the current product route without a Godot-to-JS callback object");
check(!main.includes("JavaScriptBridge.create_callback"), "product boot must not depend on JavaScript callback-object construction");
check(main.includes("window.location.assign('/docs')"), "Docs must remain a hard cross-application navigation boundary");
check(main.includes("window.innerWidth") && main.includes("window.innerHeight"), "responsive layout must derive from the real browser viewport");
check(main.includes("novelforgeLayout"), "responsive layout mode must be browser-observable");
check(main.includes('"phone" if phone else ("compact" if compact else "desktop")'), "Product UI must preserve phone/compact/desktop layout states");
check(main.includes("novelforgeRuntime='ready'"), "main scene must publish a browser-visible readiness marker");
check(main.includes("novelforge:ready"), "main scene must publish a runtime-ready browser event");

check(systemMap.includes("_parallax"), "system map must retain 2.5D parallax depth cues");
check(systemMap.includes("_draw_packet"), "system map must retain animated execution packets");
check(systemMap.includes('"phone":'), "system map must provide a portrait topology instead of shrinking the desktop graph");
check(systemMap.includes("set_layout_mode"), "system map must respond to the shared responsive layout state");

check(shell.includes('$GODOT_URL') && shell.includes('$GODOT_CONFIG'), "custom Web shell must preserve required Godot export placeholders");
check(shell.includes('data-novelforge-runtime="loading"'), "custom Web shell must expose the scene loading state to browser QA");
check(shell.includes('data-novelforge-engine="loading"'), "custom Web shell must expose the engine startup state to browser QA");
check(shell.includes("novelforgeEngine = 'started'"), "startGame resolution must be browser-observable independently from scene readiness");
check(shell.includes('id="nf-loader"') && shell.includes('id="nf-progress"'), "custom Web shell must provide branded loading and progress UI");
check(!shell.includes("GODOT\n") && !shell.includes("Game engine"), "custom loader must not regress to Godot default splash branding");

check(buildScript.includes('--export-release Web'), "CI export script must produce a release Web artifact");
check(buildScript.includes('--quit-after 2'), "CI export script must instantiate the product scene before export");
check(buildScript.includes('test -d "${DIST_DIR}/docs"'), "Godot export must preserve the already-built Docs app");
check(buildScript.includes('data-novelforge-runtime="loading"'), "export verification must prove the branded shell was emitted");

check(browserProof.includes('const expectLayout = arg("expect-layout")'), "browser proof must support an expected responsive layout");
check(browserProof.includes("state?.layout !== expectLayout"), "browser proof must fail on responsive layout mismatch");
check(browserProof.includes("canvasWidth") && browserProof.includes("browser_viewport"), "browser proof must record canvas and browser dimensions");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_godot_web_quality_v2",
    status: "pass",
    renderer: "gl_compatibility",
    dimension: "2d_2_5d",
    adaptive_canvas: true,
    stretch_mode: "disabled",
    responsive_layouts: ["phone", "compact", "desktop"],
    docs_boundary: "hard-navigation",
    authority: false,
  }, null, 2));
}

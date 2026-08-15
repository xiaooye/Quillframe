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
const browserRouteBridge = read("godot/scripts/browser_route_bridge.gd");
const localeBridge = read("godot/scripts/locale_bridge.gd");
const accessibilityBridge = read("godot/scripts/accessibility_bridge.gd");
const systemMap = read("godot/scripts/system_map.gd");
const shell = read("godot/web/novelforge.html");
const buildScript = read("scripts/build-godot-web.sh");
const assetVerifier = read("scripts/verify-cloudflare-assets.sh");
const browserProof = read("scripts/godot-browser-proof.mjs");
const pkg = JSON.parse(read("package.json"));

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
check(scene.includes('path="res://scripts/browser_route_bridge.gd"'), "root scene must install the browser history bridge before parent readiness");
check(scene.includes('path="res://scripts/locale_bridge.gd"'), "root scene must install the bilingual locale bridge");
check(scene.includes('path="res://scripts/accessibility_bridge.gd"'), "root scene must install the accessibility bridge");
check(Object.keys(pkg.dependencies ?? {}).length === 0, "Godot Product runtime must not depend on a browser UI framework");

for (const [name, source] of [["Main.tscn", scene], ["main.gd", main], ["system_map.gd", systemMap]]) {
  check(!/\b(Node3D|Camera3D|MeshInstance3D|CSGShape3D|PhysicsBody3D|WorldEnvironment)\b/.test(source), `${name} must not introduce 3D runtime nodes`);
}

for (const route of ["/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) {
  check(main.includes(`"${route}"`), `product runtime must preserve ${route}`);
}

check(main.includes("window.history.pushState"), "Godot navigation must synchronize browser history");
check(main.includes("window.location.assign('/docs')"), "main scene must retain a defensive Docs hard-navigation fallback");
check(main.includes("window.innerWidth") && main.includes("window.innerHeight"), "responsive layout must derive from the real browser viewport");
check(main.includes("novelforgeLayout"), "responsive layout mode must be browser-observable");
check(main.includes('"phone" if phone else ("compact" if compact else "desktop")'), "Product UI must preserve phone/compact/desktop layout states");
check(main.includes("novelforgeRuntime='ready'"), "main scene must publish a browser-visible readiness marker");
check(main.includes("novelforge:ready"), "main scene must publish a runtime-ready browser event");

check(browserRouteBridge.includes("JavaScriptBridge.create_callback"), "browser back/forward must use a retained Godot callback instead of reloading the runtime");
check(browserRouteBridge.includes('addEventListener("popstate"'), "browser history bridge must listen for popstate");
check(browserRouteBridge.includes("__novelforgePopstateReloadInstalled = true"), "browser history bridge must preempt the defensive reload fallback before parent readiness");
check(browserRouteBridge.includes('host.call("_navigate", path, false)'), "browser history callback must navigate the live scene without pushing another history entry");
check(browserRouteBridge.includes('get_node_or_null("LocaleBridge")'), "browser history must re-apply locale after live scene navigation");
check(browserRouteBridge.includes("novelforgeHistory = \"live\""), "browser history bridge must publish an observable live-history marker");
check(browserRouteBridge.includes("novelforgeRoute = path"), "browser history bridge must publish the routed scene path for browser QA");
check(!browserRouteBridge.includes("func _process"), "browser history synchronization must be event-driven rather than polled every frame");

check(localeBridge.includes('LOCALE_EN := "en-US"') && localeBridge.includes('LOCALE_ZH := "zh-CN"'), "Product locale bridge must explicitly support en-US and zh-CN");
check(localeBridge.includes("localStorage.getItem") && localeBridge.includes("localStorage.setItem"), "Product locale must persist explicitly in browser storage");
check(localeBridge.includes("navigator.language") && localeBridge.includes('begins_with("zh")'), "first-run Product locale must honor the browser language");
check(localeBridge.includes("LocaleToggle") && localeBridge.includes("中文"), "Godot Product chrome must expose an explicit locale toggle");
check(localeBridge.includes('"/docs/en/" if _locale == LOCALE_EN else "/docs/"'), "Docs handoff must follow the active Product locale");
check(localeBridge.includes("JavaScriptBridge.create_callback(_set_locale_from_browser)"), "locale state must be browser-observable/testable without DOM ownership of Product UI");
check(localeBridge.includes("novelforgeLocaleApplied"), "locale bridge must publish application evidence to browser QA");
check(localeBridge.includes('has_meta("novelforge_locale_hooked")'), "locale bridge must guard dynamic signal hooks against duplicate connections");
check(!localeBridge.includes("func _process"), "locale synchronization must remain event-driven");

check(accessibilityBridge.includes("MIN_TARGET := 44.0"), "interactive Product targets must retain the 44px minimum contract");
check(accessibilityBridge.includes("Control.FOCUS_ALL") && accessibilityBridge.includes('add_theme_stylebox_override("focus"'), "Godot Product controls must expose keyboard focus with a visible focus style");
check(accessibilityBridge.includes("prefers-reduced-motion: reduce"), "Godot Product motion must honor the browser reduced-motion preference");
check(accessibilityBridge.includes("set_process(not _reduced_motion)"), "reduced motion must freeze decorative continuous animation while preserving the final scene");
check(accessibilityBridge.includes('novelforgeA11y = "ready"'), "accessibility bridge must publish a browser-observable readiness marker");
check(!accessibilityBridge.includes("func _process"), "accessibility bridge itself must not poll");

check(systemMap.includes("_parallax"), "system map must retain 2.5D parallax depth cues when motion is allowed");
check(systemMap.includes("_draw_packet"), "system map must retain animated execution packets when motion is allowed");
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
check(assetVerifier.includes("stat -c '%s'"), "Cloudflare asset verification must inspect file sizes without a pipefail-sensitive sort/head pipeline");
check(assetVerifier.includes("25 MiB"), "Cloudflare asset verification must explain the hosting ceiling when it fails");

check(browserProof.includes('const expectLayout = arg("expect-layout")'), "browser proof must support an expected responsive layout");
check(browserProof.includes('const verifyHistory = arg("verify-history") === "true"'), "browser proof must support live history verification");
check(browserProof.includes("history.pushState"), "browser proof must exercise a same-runtime route transition");
check(browserProof.includes("history.back()"), "browser proof must exercise browser back navigation");
check(browserProof.includes("proofToken"), "browser proof must prove popstate does not reload the document");
check(browserProof.includes("window.__novelforgeSetLocale('zh-CN')") && browserProof.includes("window.__novelforgeSetLocale('en-US')"), "browser proof must exercise both Product locales in the live Godot runtime");
check(browserProof.includes('state?.a11y !== "ready"') && browserProof.includes('state?.target !== "44"'), "browser proof must fail when the accessibility contract is absent");
check(browserProof.includes("locale_proof: localeProof"), "browser proof must emit explicit bilingual runtime evidence");
check(browserProof.includes("state?.layout !== expectLayout"), "browser proof must fail on responsive layout mismatch");
check(browserProof.includes("canvasWidth") && browserProof.includes("browser_viewport"), "browser proof must record canvas and browser dimensions");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_godot_web_quality_v4",
    status: "pass",
    renderer: "gl_compatibility",
    dimension: "2d_2_5d",
    adaptive_canvas: true,
    responsive_layouts: ["phone", "compact", "desktop"],
    locales: ["en-US", "zh-CN"],
    min_target_px: 44,
    reduced_motion: true,
    history: "event_driven_live_scene",
    docs_boundary: "locale_aware_hard_navigation",
    legacy_product_spa: false,
    authority: false
  }, null, 2));
}

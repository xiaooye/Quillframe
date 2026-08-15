import fs from "node:fs";
import path from "node:path";
const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const check = (condition, message) => { if (!condition) { console.error(`godot-web-quality: ${message}`); process.exitCode = 1; } };

const project = read("godot/project.godot");
const preset = read("godot/export_presets.cfg");
const scene = read("godot/Main.tscn");
const main = read("godot/scripts/main.gd");
const routeBridge = read("godot/scripts/browser_route_bridge.gd");
const themeBridge = read("godot/scripts/theme_bridge.gd");
const localeBridge = read("godot/scripts/locale_bridge.gd");
const a11yBridge = read("godot/scripts/accessibility_bridge.gd");
const systemMap = read("godot/scripts/system_map.gd");
const backdrop = read("godot/scripts/ambient_backdrop.gd");
const generatedTheme = read("godot/generated/story_loom_tokens.gd");
const themeGenerator = read("scripts/generate-godot-theme.mjs");
const shell = read("godot/web/novelforge.html");
const buildScript = read("scripts/build-godot-web.sh");
const assetVerifier = read("scripts/verify-cloudflare-assets.sh");
const browserProof = read("scripts/godot-browser-proof.mjs");
const pkg = JSON.parse(read("package.json"));

check(project.includes('run/main_scene="res://Main.tscn"'), "Godot runtime must boot Main.tscn");
check(project.includes('renderer/rendering_method="gl_compatibility"'), "Web runtime must use Compatibility rendering");
check(project.includes('window/stretch/mode="disabled"'), "Product UI must keep browser-pixel layout semantics");
check(project.includes('window/size/viewport_width=390'), "base design width must cover phone surfaces");
check(preset.includes('platform="Web"') && preset.includes('variant/thread_support=false'), "Web export must stay single-threaded");
check(preset.includes('html/custom_html_shell="res://web/novelforge.html"') && preset.includes('html/canvas_resize_policy=2'), "Web export must use branded adaptive shell");
check(scene.includes('type="Control"'), "root scene must remain 2D Control");
for (const bridge of ["browser_route_bridge.gd", "theme_bridge.gd", "locale_bridge.gd", "accessibility_bridge.gd"]) check(scene.includes(`path="res://scripts/${bridge}"`), `root scene must install ${bridge}`);
check(Object.keys(pkg.dependencies ?? {}).length === 0, "Godot Product runtime must not depend on browser UI frameworks");
check(pkg.scripts?.["tokens:godot:check"]?.includes("--check"), "package must verify generated Godot Story Loom tokens");
check(pkg.scripts?.["godot:build"]?.includes("tokens:godot:check"), "Godot export must refuse stale Story Loom token projection");

for (const [name, source] of [["Main.tscn", scene], ["main.gd", main], ["system_map.gd", systemMap], ["ambient_backdrop.gd", backdrop]]) check(!/\b(Node3D|Camera3D|MeshInstance3D|CSGShape3D|PhysicsBody3D|WorldEnvironment)\b/.test(source), `${name} must not introduce 3D runtime nodes`);
for (const route of ["/studio", "/architecture", "/publication", "/inspect", "/playground", "/agents", "/changelog"]) check(main.includes(`"${route}"`), `product runtime must preserve ${route}`);

check(generatedTheme.includes('TOKEN_SCHEMA := "novelforge_brand_tokens_v2"') && generatedTheme.includes('THEME_NAME := "Story Loom v2"'), "generated Godot theme must identify the canonical brand token schema");
for (const token of ["BACKGROUND", "PRIMARY", "PROJECT", "RUNTIME", "EDITORIAL", "EVIDENCE", "VALIDATED", "MIN_TOUCH_TARGET", "FOCUS_RING_WIDTH", "IDLE_ANIMATION_ALLOWED"]) check(generatedTheme.includes(`const ${token} :=`), `generated Godot theme must project ${token}`);
check(themeGenerator.includes('../assets/brand/tokens.json') && themeGenerator.includes('godot/generated/story_loom_tokens.gd'), "Godot theme generator must project repository brand tokens into the runtime");
check(themeGenerator.includes('process.argv.includes("--check")'), "Godot theme generator must support deterministic stale-file checking");
check(themeBridge.includes('preload("res://generated/story_loom_tokens.gd")'), "Product visual bridge must consume generated Story Loom tokens");
check(themeBridge.includes('novelforgeTheme = "story-loom-v2"') && themeBridge.includes("novelforgeTokenSchema"), "browser QA must observe applied Story Loom theme authority");
check(themeBridge.includes("_accent_for_route") && themeBridge.includes("Story.EDITORIAL") && themeBridge.includes("Story.RUNTIME"), "route accents must derive from Story Loom semantic colors");

check(systemMap.includes('preload("res://generated/story_loom_tokens.gd")'), "system map must consume Story Loom tokens");
check(systemMap.includes("_parallax") && systemMap.includes("_draw_packet"), "system map must retain controlled 2.5D depth cues");
check(systemMap.includes('"phone":') && systemMap.includes("set_layout_mode"), "system map must preserve dedicated phone topology");
check(systemMap.includes("_motion_remaining") && systemMap.includes("set_process(false)") && systemMap.includes("_kick_motion"), "system map motion must be bounded by interaction/route transitions rather than an idle loop");
check(backdrop.includes("set_process(false)") && !backdrop.includes("func _process"), "ambient backdrop must remain static/event-driven at idle");

check(main.includes("window.history.pushState") && main.includes("window.innerWidth") && main.includes("window.innerHeight"), "Godot scene must own browser-addressable responsive Product navigation");
check(main.includes("novelforgeRuntime='ready'") && main.includes("novelforge:ready"), "scene must publish browser readiness");
check(routeBridge.includes("JavaScriptBridge.create_callback") && routeBridge.includes('addEventListener("popstate"'), "history must use retained JS callback");
check(routeBridge.includes('host.call("_navigate", path, false)') && routeBridge.includes("ThemeBridge") && routeBridge.includes("LocaleBridge"), "browser back/forward must update the live themed localized scene");
check(!routeBridge.includes("func _process"), "history synchronization must be event-driven");

check(localeBridge.includes('LOCALE_EN := "en-US"') && localeBridge.includes('LOCALE_ZH := "zh-CN"'), "Product must support en-US and zh-CN");
check(localeBridge.includes("localStorage.getItem") && localeBridge.includes("localStorage.setItem") && localeBridge.includes("navigator.language"), "Product locale must persist and honor first-run browser language");
check(localeBridge.includes("LocaleToggle") && localeBridge.includes("中文"), "Godot chrome must expose locale toggle");
check(localeBridge.includes('"/docs/en/" if _locale == LOCALE_EN else "/docs/"'), "Docs handoff must follow Product locale");
check(localeBridge.includes("JavaScriptBridge.create_callback(_set_locale_from_browser)") && localeBridge.includes("novelforgeLocaleApplied"), "locale bridge must expose browser QA evidence");
check(!localeBridge.includes("func _process"), "locale synchronization must be event-driven");

check(a11yBridge.includes("Story.MIN_TOUCH_TARGET") && a11yBridge.includes("Control.FOCUS_ALL") && a11yBridge.includes("Story.FOCUS_RING_WIDTH"), "Godot controls must enforce canonical touch and keyboard focus contracts");
check(a11yBridge.includes("prefers-reduced-motion: reduce") && a11yBridge.includes("set_reduced_motion"), "Godot Product motion must honor reduced-motion without enabling idle processing");
check(a11yBridge.includes('novelforgeA11y = "ready"'), "accessibility bridge must publish browser evidence");
check(!a11yBridge.includes("func _process"), "accessibility bridge must not poll");

check(shell.includes('$GODOT_URL') && shell.includes('$GODOT_CONFIG') && shell.includes('data-novelforge-runtime="loading"'), "custom Web shell must preserve Godot placeholders and loading marker");
check(shell.includes("novelforgeEngine = 'started'") && shell.includes('id="nf-loader"') && shell.includes('id="nf-progress"'), "custom shell must expose branded engine startup state");
check(buildScript.includes('--export-release Web') && buildScript.includes('--quit-after 2') && buildScript.includes('test -d "${DIST_DIR}/docs"'), "CI export must instantiate Product and preserve Docs");
check(assetVerifier.includes("stat -c '%s'") && assetVerifier.includes("25 MiB"), "Cloudflare asset verification must be deterministic and explicit");

check(browserProof.includes('novelforge_godot_browser_proof_v5'), "browser proof schema must cover final Godot replacement contract");
check(browserProof.includes('state?.theme !== "story-loom-v2"') && browserProof.includes('novelforge_brand_tokens_v2'), "browser proof must fail if Story Loom theme projection is absent");
check(browserProof.includes("window.__novelforgeSetLocale('zh-CN')") && browserProof.includes("window.__novelforgeSetLocale('en-US')"), "browser proof must exercise both Product locales");
check(browserProof.includes('state?.a11y !== "ready"') && browserProof.includes('state?.target !== "44"'), "browser proof must exercise accessibility markers");
check(browserProof.includes("history.back()") && browserProof.includes("proofToken"), "browser proof must prove no-reload back navigation");
check(browserProof.includes("canvasWidth") && browserProof.includes("browser_viewport"), "browser proof must record canvas/browser dimensions");

if (!process.exitCode) console.log(JSON.stringify({ schema: "novelforge_godot_web_quality_v5", status: "pass", renderer: "gl_compatibility", dimension: "2d_2_5d", theme: "story-loom-v2", token_schema: "novelforge_brand_tokens_v2", adaptive_canvas: true, responsive_layouts: ["phone", "compact", "desktop"], locales: ["en-US", "zh-CN"], min_target_px: 44, motion: "bounded_event_driven", reduced_motion: true, history: "event_driven_live_scene", docs_boundary: "locale_aware_hard_navigation", legacy_product_spa: false, authority: false }, null, 2));

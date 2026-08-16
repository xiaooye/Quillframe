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
const geometry = read("godot/scripts/geometry_parity.gd");
const interaction = read("godot/scripts/interaction_parity.gd");
const completionCore = read("godot/scripts/visual_completion_core.gd");
const completion = read("godot/scripts/visual_completion.gd");
const wideCompact = read("godot/scripts/wide_compact_parity.gd");
const completionAll = `${completionCore}\n${completion}\n${wideCompact}`;
const shell = read("godot/web/novelforge.html");
const fontFetch = read("scripts/fetch-godot-fonts.sh");

check(project.includes('run/main_scene="res://Main.tscn"'), "Godot main scene must remain explicit");
check(project.includes('renderer/rendering_method="gl_compatibility"'), "Web runtime must use Compatibility renderer");
check(scene.includes('path="res://scripts/wide_compact_parity.gd"'), "Godot production scene must enter through the final wide-compact parity layer");
check(wideCompact.includes('extends "res://scripts/visual_completion.gd"'), "wide-compact parity must remain a thin layer above screenshot-driven visual completion");
check(wideCompact.includes("SOLID_HOME_STACK_MAX_WIDTH := 980.0"), "final route geometry must preserve Solid's independent 980px Home stack breakpoint");
check(wideCompact.includes("SOLID_HERO_STACK_MAX_WIDTH := 900.0"), "final route geometry must preserve Solid's 900px hero stack breakpoint");
check(wideCompact.includes("NARROW_COMPACT_H1_SIZE := 36"), "768px route headings must track the Solid clamp rather than desktop typography");
check(wideCompact.includes("custom_maximum_size") && wideCompact.includes("AUTOWRAP_WORD_SMART"), "compact copy must force wrap against the Solid column width");
check(wideCompact.includes("_build_product_hero") && wideCompact.includes("false"), "Product wide compact must preserve the Solid two-column hero topology");
check(completion.includes('extends "res://scripts/visual_completion_core.gd"'), "visual polish must remain a thin layer above complete product surfaces");
check(completionCore.includes('extends "res://scripts/interaction_parity.gd"'), "visual completion core must remain above validated browser interaction parity");
check(interaction.includes('extends "res://scripts/geometry_parity.gd"'), "interaction parity must remain a thin layer above geometry parity");
check(geometry.includes('extends "res://scripts/mobile_geometry_parity.gd"'), "cross-viewport geometry parity must remain a thin layer above mobile parity");
check(mobileGeometry.includes('extends "res://scripts/typography_parity.gd"'), "mobile geometry parity must remain a thin layer above deterministic typography");
check(scene.includes("offset_right = -15.0"), "web page scrollbar gutter must remain reserved in the Godot layout viewport");
check(!/Node3D|Camera3D|MeshInstance3D/.test(scene + main + parity + routes + catalog + systems + editorial + typography + mobileGeometry + geometry + interaction + completionAll), "Product runtime is capped at 2.5D; 3D scene nodes are forbidden");

check(typography.includes('INTER_FONT_PATH := "res://generated/Inter-opsz-wght.ttf"'), "WeiUI Latin typography must be pinned to Inter");
check(typography.includes("_contains_cjk"), "Latin/CJK font selection must remain text-aware");
check(typography.includes("_cjk_font") && typography.includes("_latin_base_font"), "Latin and CJK typography metrics must stay isolated");
check(typography.includes("fallbacks.append(_base_font)"), "decorative mixed font must retain CJK fallback");
check(typography.includes("_reset_label_scale"), "legacy Noto width compensation must be neutralized under Inter");
check(typography.includes("func _heading_font(glyph_spacing: int, optical_size: int = 62)"), "optical-size heading helper must remain backward compatible with calibrated geometry call sites");

check(main.includes('FONT_PATH := "res://generated/NotoSansSC-wght.ttf"'), "deterministic bundled CJK font is required");
check(main.includes('SYMBOL_FONT_PATH := "res://generated/NotoSansSymbols2-Regular.ttf"'), "deterministic symbol fallback is required");
check(main.includes('THAI_FONT_PATH := "res://generated/NotoSansThai-wdth-wght.ttf"'), "deterministic Thai fallback asset must remain pinned");
check(main.includes('ARABIC_FONT_PATH := "res://generated/NotoSansArabic-wdth-wght.ttf"'), "deterministic Arabic fallback asset must remain pinned");
for (const fingerprint of [
  "047c92f6e2212473dc436020afed689527076d44",
  "fb0637bafbcd804fe32152370a1225990745b4bc",
  "caf89dd0e60e23ac39ce18da823095959d409437",
  "34b48ab6f74867dbfce19410a2f452abef34e3ff",
  "f1d01edce4ebaedcbe9a06fc75fec07b304ec3df"
]) check(fontFetch.includes(fingerprint), `pinned font fingerprint missing: ${fingerprint}`);

check(completion.includes('cat.text = "♡ Loom"'), "browser-visible decorative status copy must avoid unstable mixed-script shaping");
check(completion.includes("Let’s weave something lovely today ♡") && completion.includes("今天也把故事织得更漂亮一点吧 ♡"), "launcher decorative copy must use deterministic glyph coverage");
check(main.includes('BOOKS_ICON_PATH := "res://assets/books-stack.svg"'), "Knowledge icon must use deterministic local vector art");
check(main.includes("Let the story\\ngrow without\\nletting the\\nsystem lose\\nthe plot."), "desktop/mobile baseline headline geometry must stay explicit");
check(parity.includes("LAUNCHER_CONTENT_INSET := 36.0"), "Story Loom content inset must preserve the Solid material-panel content box");
check(parity.includes("MOBILE_LEDE_LINE_SPACING := 3"), "mobile hero lede rhythm must remain calibrated to the Solid baseline");
check(parity.includes("DESKTOP_LEDE_LINE_SPACING := 4"), "desktop hero lede rhythm must remain calibrated to the Solid baseline");
check(parity.includes('Color("b0a8da")'), "Godot scrollbar thumb must preserve the Atelier lavender scrollbar treatment");
check(parity.includes('route == "/product"'), "Product route must remain an explicit Godot surface");
check(routes.includes('title_size = 62 if not stacked else 39'), "Product typography must preserve route-specific desktop/mobile sizing");
check(routes.includes('stack_size.x - (130.0 if not phone else 68.0)'), "Product stack geometry must stay baseline-calibrated");
check(catalog.includes('"/studio"') && catalog.includes('"/changelog"'), "Studio and Changelog must remain explicit Godot surfaces");
for (const route of ["/inspect", "/playground", "/agents"]) check(systems.includes(`"${route}"`), `${route} must remain an explicit Godot surface`);
for (const route of ["/architecture", "/publication"]) check(editorial.includes(`"${route}"`), `${route} must remain an explicit Godot surface`);
check(systems.includes("PROJECT INSPECTOR") && systems.includes("LOCAL PLAYGROUND") && systems.includes("AGENT PATCH BAY"), "system route identity surfaces must remain explicit");
check(editorial.includes("INTERACTIVE ARCHITECTURE") && editorial.includes("PUBLICATION WORKBENCH"), "editorial route identity surfaces must remain explicit");

check(mobileGeometry.includes("NovelForge is a\\nfiction production\\nsystem, not a\\nprompt wrapper."), "Product phone heading must preserve the four-line Solid wrap");
check(mobileGeometry.includes("with progressive\\ndisclosure instead\\nof dashboard\\noverload."), "Studio phone heading must preserve the seven-line Solid wrap");
check(mobileGeometry.includes('pink.text = "many"') && mobileGeometry.includes('"deterministic\\nderivatives."'), "Publication phone heading must keep inline pink continuation geometry");
check(mobileGeometry.includes("_fix_epub_card_position"), "Publication phone format cards must retain deterministic grid placement");

check(geometry.includes("NovelForge is a fiction\\nproduction system,\\nnot a prompt wrapper."), "Product desktop heading must preserve the three-line Solid wrap");
check(geometry.includes("disclosure instead of\\ndashboard overload."), "Studio desktop heading must preserve the six-line Solid wrap");
check(geometry.includes("See how one NovelForge run\\nmoves through the system."), "Architecture desktop heading must preserve the two-line Solid wrap");
check(geometry.includes("_home_heading_font") && geometry.includes('name_to_tag("wght"): 810'), "Home identity heading must preserve the Atelier 810 weight authority");
check(geometry.includes("_spaced_latin_font(420, -1)"), "Home mobile lede must preserve browser-like width and vertical rhythm");
check(geometry.includes("docs.text = \"Read architecture docs\""), "Architecture Docs CTA must not duplicate the books icon");
check(geometry.includes("_patch_inspect_phone") && geometry.includes("_patch_playground_phone"), "remaining phone flow parity corrections must remain explicit");
check(wideCompact.includes("WIDE_COMPACT_H1_SIZE_EN := 48"), "wide compact H1 must track the Solid clamp near 1024px rather than desktop 62px geometry");
check(wideCompact.includes("NARROW_COMPACT_H1_SIZE := 36"), "narrow compact H1 must track the Solid clamp near 768px");
check(wideCompact.includes("SOLID_HOME_STACK_MAX_WIDTH := 980.0"), "Home must keep its separate Solid 980px responsive breakpoint");
check(wideCompact.includes("_fit_wide_compact_lede") && wideCompact.includes("AUTOWRAP_WORD_SMART"), "wide compact copy must reflow without crossing the evidence column");

check(interaction.includes("JavaScriptBridge.create_callback"), "browser-originated interaction must use retained JavaScriptBridge callbacks");
check(interaction.includes('addEventListener("keydown"') && interaction.includes('addEventListener("popstate"'), "keyboard and browser history events must remain explicit");
check(interaction.includes('key.to_lower() == "k"'), "Ctrl/Cmd+K command palette shortcut is required");
check(interaction.includes("_toggle_mobile_menu"), "mobile navigation menu must remain functional");
check(interaction.includes("novelforge.appearance") && interaction.includes("novelforgeAppearance"), "appearance preference must persist and expose a browser QA marker");
check(interaction.includes('target = "/docs/en"'), "English Docs handoff must preserve the locale boundary");
check(interaction.includes("novelforgeInteraction"), "browser interaction readiness marker is required");
check(!interaction.includes("set_interval") && !interaction.includes("setInterval") && !interaction.includes("Timer.new"), "interaction parity must not introduce default polling");

check(completionCore.includes("func _build_lower_sections"), "Home must own a complete post-hero surface rather than a three-card placeholder");
check(completionCore.includes("_build_home_labs") && completionCore.includes("_build_home_portals") && completionCore.includes("_build_home_knowledge"), "Home capability, lab, portal, and knowledge sections are required");
check(completionCore.includes("func _repair_localized_control_fonts"), "localized controls must repair CJK font fallback after text mutation");
check(completionCore.includes("func _patch_architecture_copy_geometry"), "Architecture CJK heading/lede geometry repair is required");
check(completionCore.includes("func _append_architecture_inspector"), "Architecture must render the selected-node inspector below the execution path");
check(completionCore.includes("func _build_reading_preview"), "Publication must render a real reading preview body");
check(completionCore.includes("_build_publication_metadata") && completionCore.includes("_build_publication_provenance"), "Publication preview must include metadata and provenance surfaces");
check(completionCore.includes('novelforgeVisualCompletion", "ready"'), "browser QA visual-completion readiness marker is required");
check(completionCore.includes('novelforgeHomeSections", "complete"'), "Home completeness marker is required");
check(completionCore.includes('novelforgePublicationPreview", "ready"'), "Publication preview marker is required");
check(completion.includes('novelforgeVisualPolish", "ready"'), "screenshot-driven visual polish readiness marker is required");
check(completion.includes("看一次 NovelForge\\n如何穿过整个系统。"), "Architecture Chinese hero must use collision-free two-line geometry");
check(completion.includes("Every derivative resolves back\\nto the same accepted manuscript."), "Publication phone provenance title must use an explicit safe wrap");
check(!completionAll.includes("Timer.new") && !completionAll.includes("setInterval"), "visual completion must remain event-driven with no default polling");

check(main.includes('"phone"') && main.includes('"compact"') && main.includes('"desktop"'), "three responsive layout modes are required");
check(main.includes("window.location.assign") && parity.includes("window.history.pushState"), "browser navigation boundary must stay explicit");
check(main.includes("novelforge:godot-ready"), "browser readiness marker is required");
check(shell.includes('$GODOT_URL') && shell.includes('$GODOT_CONFIG'), "custom Web shell must retain Godot placeholders");
check(shell.includes('data-novelforge-godot-shadow="loading"'), "legacy parity compatibility marker missing");
check(shell.includes("prefers-color-scheme: dark") && shell.includes("novelforgeAppearance"), "Web shell must initialize persisted/system appearance before the scene is visible");
check(shell.includes("prefers-reduced-motion:reduce"), "Web shell must honor reduced motion");

if (failures.length) {
  failures.forEach((failure) => console.error(`godot-source-quality: FAIL: ${failure}`));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_godot_production_source_quality_v17",
    status: "pass",
    production_cutover: true,
    runtime_role: "production",
    visual_baseline: "Solid/Vite Story Loom Kawaii Atelier golden fixture",
    visual_completion_layer: true,
    final_wide_compact_parity: true,
    solid_home_stack_breakpoint: 980,
    solid_hero_stack_breakpoint: 900,
    narrow_compact_h1_px: 36,
    compact_wrap_contract: "godot_4_7_custom_maximum_size",
    screenshot_driven_polish: true,
    home_full_surface: true,
    architecture_inspector: true,
    publication_rendered_preview: true,
    cjk_localized_controls: true,
    stable_decorative_glyphs: true,
    typography_authority: "WeiUI Inter + Noto Sans SC",
    renderer: "gl_compatibility",
    max_dimension: "2.5D",
    deterministic_latin_font: true,
    deterministic_cjk_font: true,
    deterministic_unicode_fallbacks: true,
    page_grid_contract: true,
    route_surface_contract: true,
    interaction_contract: true,
    browser_event_callbacks: true,
    default_polling: false,
    authority: false
  }, null, 2));
}
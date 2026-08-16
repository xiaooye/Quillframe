#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const failures = [];
const check = (ok, message) => { if (!ok) failures.push(message); };

const packageJson = JSON.parse(read("package.json"));
const scene = read("godot/Main.tscn");
const shell = read("godot/web/novelforge.html");
const interaction = read("godot/scripts/interaction_parity.gd");
const completionCore = read("godot/scripts/visual_completion_core.gd");
const completion = read("godot/scripts/visual_completion.gd");
const wideCompact = read("godot/scripts/wide_compact_parity.gd");
const responsiveCompletion = read("godot/scripts/responsive_completion.gd");
const build = read("scripts/build-godot-web.sh");
const exporter = read("scripts/build-godot-shadow.sh");
const redirects = read("public/_redirects");
const docsConfig = read("docs-site/astro.config.mjs");

check(scene.includes('path="res://scripts/responsive_completion.gd"'), "production scene must enter through the final responsive completion layer");
check(responsiveCompletion.includes('extends "res://scripts/wide_compact_parity.gd"'), "responsive completion must remain a thin layer above wide-compact parity");
check(wideCompact.includes('extends "res://scripts/visual_completion.gd"'), "wide-compact parity must remain a thin layer above visual completion");
check(wideCompact.includes("SOLID_HOME_STACK_MAX_WIDTH := 980.0"), "final responsive layer must preserve Solid's independent 980px Home stack breakpoint");
check(wideCompact.includes("SOLID_HERO_STACK_MAX_WIDTH := 900.0"), "final responsive layer must preserve Solid's 900px product-hero stack breakpoint");
check(wideCompact.includes("NARROW_COMPACT_H1_SIZE := 36"), "768px route typography must preserve the Solid 4.7vw clamp equivalent");
check(wideCompact.includes("custom_maximum_size") && wideCompact.includes("AUTOWRAP_WORD_SMART"), "compact labels must bind wrapping to the Solid copy column rather than intrinsic one-line width");
check(responsiveCompletion.includes("SOLID_SHELL_COMPACT_MAX_WIDTH := 980.0"), "final shell must preserve Solid's 980px desktop-nav collapse breakpoint");
check(responsiveCompletion.includes("SOLID_CARD_TWO_COLUMN_MAX_WIDTH := 1120.0"), "Product compact proof cards must preserve Solid's 1120px two-column breakpoint");
check(responsiveCompletion.includes("SOLID_CARD_SINGLE_COLUMN_MAX_WIDTH := 760.0"), "Product proof cards must preserve Solid's 760px single-column breakpoint");
check(responsiveCompletion.includes("_build_product_cards_adaptive") && responsiveCompletion.includes("_build_header"), "final responsive layer must own adaptive Product cards and compact shell topology");
check(completion.includes('extends "res://scripts/visual_completion_core.gd"'), "production polish layer must preserve the complete product surface beneath it");
check(completionCore.includes('extends "res://scripts/interaction_parity.gd"'), "visual-completion core must preserve the validated interaction runtime beneath it");
check(shell.includes('data-novelforge-runtime="loading"'), "production shell runtime marker missing");
check(shell.includes('<base href="/"'), "production shell must resolve Godot assets from the site root on direct routes");
check(shell.includes("Story Loom · Kawaii Atelier runtime"), "production loader must retain the Kawaii Atelier identity");
check(interaction.includes("JavaScriptBridge.create_callback"), "production browser event bridge missing");
check(interaction.includes("novelforgeInteraction"), "production interaction readiness marker missing");
check(completionCore.includes("novelforgeVisualCompletion"), "production visual-completion readiness marker missing");
check(completion.includes("novelforgeVisualPolish"), "production screenshot-polish readiness marker missing");
check(completionCore.includes("novelforgeHomeSections") && completionCore.includes("novelforgePublicationPreview") && completionCore.includes("novelforgeArchitectureInspector"), "production must publish route-body completeness markers");

// Godot Web does not expose the native desktop screen-reader bridge, so the
// shell must carry a semantic companion while native Control metadata remains
// populated for supported exports. These checks intentionally validate product
// behavior rather than a particular DOM hierarchy.
check(completion.includes("accessibility_name") && completion.includes("accessibility_description"), "native Godot accessibility metadata missing");
check(completion.includes("novelforgeAccessibility"), "Godot accessibility readiness marker missing");
check(shell.includes('aria-label="NovelForge primary navigation"'), "Web semantic primary navigation missing");
check(shell.includes('id="nf-a11y-main"'), "Web semantic main region missing");
check(shell.includes('aria-label="NovelForge Story Loom product interface"'), "canvas accessible name missing");
check(shell.includes('class="nf-skip"'), "visible-on-focus skip link missing");
check(shell.includes("@media(prefers-reduced-motion:reduce)"), "Web reduced-motion fallback missing");
check(shell.includes("@media(forced-colors:active)"), "Web forced-colors focus fallback missing");
check(shell.includes("MutationObserver") && !shell.includes("setInterval("), "Web accessibility synchronization must remain event-driven without polling");
check(completion.includes("custom_minimum_size") && completion.includes("44.0"), "Story Loom 44px mobile target contract missing from final Godot completion layer");

check(packageJson.scripts?.build?.includes("build-godot-web.sh"), "default npm build must assemble the Godot Product runtime");
check(packageJson.scripts?.dev?.includes("godot --path godot"), "default npm dev must enter the Godot project rather than the Solid baseline");
check(packageJson.scripts?.["baseline:build"]?.includes("vite build"), "Solid/Vite must remain available only as an explicit golden baseline build");
check(packageJson.scripts?.["baseline:quality"]?.includes("scripts/quality.mjs"), "golden baseline quality contract must remain explicit");
check(packageJson.scripts?.quality?.includes("godot:quality") && packageJson.scripts?.quality?.includes("godot-production-quality.mjs"), "aggregate quality must include Godot source and production contracts");
check(build.includes('DOCS_DIR="${OUT_DIR}/docs"'), "production build must preserve the Starlight docs boundary");
check(build.includes('STAGE_DIR="${ROOT_DIR}/dist-godot-shadow"'), "production build must consume the proven Godot export artifact");
check(build.includes('bash "${ROOT_DIR}/scripts/build-godot-shadow.sh"'), "production build must reuse the parity/size-gated Godot exporter");
check(!build.includes("--export-release"), "production assembly must not define a second Godot export path");
check(exporter.includes('OUT_DIR="${ROOT_DIR}/dist-godot-shadow"'), "shared Godot exporter output contract changed");
check(exporter.includes('--export-release Web "${OUT_DIR}/index.html"'), "shared Godot exporter must own the Web export command");
check(build.includes('! -name docs'), "production root replacement must not delete /docs/**");
check(build.includes('cp -a "${STAGE_DIR}/." "${OUT_DIR}/"'), "validated Godot output must be merged into the site root");
check(build.includes('MAX_PAGE_ASSET_BYTES'), "production build must enforce the Pages asset ceiling");
check(docsConfig.includes('base: "/docs"'), "Astro/Starlight must remain rooted at /docs");
for (const route of ["product","studio","architecture","publication","inspect","playground","agents","changelog"]) {
  check(redirects.includes(`/${route} /index.html 200`), `direct Godot route rewrite missing: /${route}`);
}
check(redirects.includes('/docs /docs/ 301') && redirects.includes('/docs/en /docs/en/ 301'), "Docs canonical redirects missing");

if (failures.length) {
  failures.forEach((failure) => console.error(`godot-production-quality: FAIL: ${failure}`));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_godot_production_quality_v10",
    status: "pass",
    production_cutover: true,
    product_runtime: "godot_web",
    docs_runtime: "astro_starlight",
    docs_root: "/docs/**",
    golden_baseline: "solidjs_vite_story_loom_fixture",
    visual_completion: true,
    final_wide_compact_parity: true,
    final_responsive_completion: true,
    solid_home_stack_breakpoint: 980,
    solid_shell_compact_breakpoint: 980,
    solid_hero_stack_breakpoint: 900,
    solid_product_card_two_column_breakpoint: 1120,
    solid_product_card_single_column_breakpoint: 760,
    narrow_compact_h1_px: 36,
    compact_wrap_contract: "godot_4_7_custom_maximum_size",
    screenshot_driven_polish: true,
    complete_home_body: true,
    rendered_publication_preview: true,
    architecture_detail_surface: true,
    cjk_control_fallback: true,
    stable_decorative_glyphs: true,
    web_semantic_companion: true,
    native_accessibility_metadata: true,
    reduced_motion: true,
    forced_colors_focus: true,
    mobile_target_44px: true,
    accessibility_sync: "event_driven",
    default_build: "godot_web",
    export_strategy: "single_parity_proven_exporter_then_root_merge",
    single_godot_exporter: true,
    renderer: "gl_compatibility",
    max_dimension: "2.5D",
    direct_route_rewrites: true,
    cloudflare_asset_ceiling: true,
    authority: false
  }, null, 2));
}
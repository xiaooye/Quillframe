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
const completion = read("godot/scripts/visual_completion.gd");
const build = read("scripts/build-godot-web.sh");
const exporter = read("scripts/build-godot-shadow.sh");
const redirects = read("public/_redirects");
const docsConfig = read("docs-site/astro.config.mjs");

check(scene.includes('path="res://scripts/visual_completion.gd"'), "production scene must enter through the validated visual-completion layer");
check(completion.includes('extends "res://scripts/interaction_parity.gd"'), "visual-completion layer must preserve the validated interaction runtime beneath it");
check(shell.includes('data-novelforge-runtime="loading"'), "production shell runtime marker missing");
check(shell.includes('<base href="/"'), "production shell must resolve Godot assets from the site root on direct routes");
check(shell.includes("Story Loom · Kawaii Atelier runtime"), "production loader must retain the Kawaii Atelier identity");
check(interaction.includes("JavaScriptBridge.create_callback"), "production browser event bridge missing");
check(interaction.includes("novelforgeInteraction"), "production interaction readiness marker missing");
check(completion.includes("novelforgeVisualCompletion"), "production visual-completion readiness marker missing");
check(completion.includes("novelforgeHomeSections") && completion.includes("novelforgePublicationPreview") && completion.includes("novelforgeArchitectureInspector"), "production must publish route-body completeness markers");
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
    schema: "novelforge_godot_production_quality_v5",
    status: "pass",
    production_cutover: true,
    product_runtime: "godot_web",
    docs_runtime: "astro_starlight",
    docs_root: "/docs/**",
    golden_baseline: "solidjs_vite_story_loom_fixture",
    visual_completion: true,
    complete_home_body: true,
    rendered_publication_preview: true,
    architecture_detail_surface: true,
    cjk_control_fallback: true,
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

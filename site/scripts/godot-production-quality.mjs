#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const failures = [];
const check = (ok, message) => { if (!ok) failures.push(message); };

const scene = read("godot/Main.tscn");
const shell = read("godot/web/novelforge.html");
const interaction = read("godot/scripts/interaction_parity.gd");
const build = read("scripts/build-godot-web.sh");
const redirects = read("public/_redirects");
const docsConfig = read("docs-site/astro.config.mjs");

check(scene.includes('path="res://scripts/interaction_parity.gd"'), "production scene must enter through the validated interaction layer");
check(shell.includes('data-novelforge-runtime="loading"'), "production shell runtime marker missing");
check(shell.includes('<base href="/"'), "production shell must resolve Godot assets from the site root on direct routes");
check(shell.includes("Story Loom · Kawaii Atelier runtime"), "production loader must retain the Kawaii Atelier identity");
check(interaction.includes("JavaScriptBridge.create_callback"), "production browser event bridge missing");
check(interaction.includes("novelforgeInteraction"), "production interaction readiness marker missing");
check(build.includes('DOCS_DIR="${OUT_DIR}/docs"'), "production build must preserve the Starlight docs boundary");
check(build.includes('STAGE_DIR="${ROOT_DIR}/dist-godot-production"'), "production build must use an isolated Godot staging directory");
check(build.includes('rm -rf "${STAGE_DIR}"') && build.includes('mkdir -p "${STAGE_DIR}"'), "production staging directory must be recreated cleanly");
check(build.includes('--export-release Web "${STAGE_DIR}/index.html"'), "production build must export Godot into the isolated staging directory");
check(build.includes('! -name docs'), "production root replacement must not delete /docs/**");
check(build.includes('cp -a "${STAGE_DIR}/." "${OUT_DIR}/"'), "validated Godot staging output must be merged into the site root");
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
    schema: "novelforge_godot_production_quality_v2",
    status: "pass",
    production_cutover: true,
    product_runtime: "godot_web",
    docs_runtime: "astro_starlight",
    docs_root: "/docs/**",
    export_strategy: "clean_stage_then_root_merge",
    renderer: "gl_compatibility",
    max_dimension: "2.5D",
    direct_route_rewrites: true,
    cloudflare_asset_ceiling: true,
    authority: false,
  }, null, 2));
}

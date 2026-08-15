#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const check = (condition, message) => {
  if (!condition) {
    console.error(`atelier-godot-quality: ${message}`);
    process.exitCode = 1;
  }
};

const atelier = read("godot/scripts/atelier_theme.gd");
const themeBridge = read("godot/scripts/theme_bridge.gd");
const backdrop = read("godot/scripts/ambient_backdrop.gd");
const map = read("godot/scripts/system_map.gd");
const shell = read("godot/web/novelforge.html");
const docsParity = read("docs-site/src/styles/product-header-parity.css");

check(atelier.includes('EXPERIENCE := "story-loom-kawaii-atelier-v5"'), "Godot must identify the established Kawaii Atelier v5 experience");
check(atelier.includes('preload("res://generated/story_loom_tokens.gd")'), "Atelier must derive from canonical generated Story Loom tokens");
for (const lane of ["PROJECT_FILL", "RUNTIME_FILL", "EDITORIAL_FILL", "EVIDENCE_FILL", "VALIDATED_FILL", "REJECTED_FILL"]) {
  check(atelier.includes(`Story.${lane}`), `Atelier projection must retain ${lane}`);
}
for (const primitive of ["paper_warm", "paper_pink", "paper_blue", "paper_violet", "paper_mint", "stitch", "shadow"]) {
  check(atelier.includes(`func ${primitive}`), `Atelier primitive missing: ${primitive}`);
}

check(themeBridge.includes('preload("res://scripts/atelier_theme.gd")'), "Theme bridge must apply the Atelier projection");
check(themeBridge.includes("novelforgeExperience = Atelier.EXPERIENCE"), "browser state must expose the Kawaii Atelier experience");
check(themeBridge.includes('novelforgeTheme = "story-loom-v2"'), "canonical Story Loom token theme identity must remain intact");
check(backdrop.includes("Atelier.paper()") && backdrop.includes("Story.EDITORIAL_FILL") && backdrop.includes("_draw_confetti"), "product backdrop must retain warm paper and restrained kawaii lane decoration");
check(map.includes("Atelier.fill_for") && map.includes("✦  FLOW FIELD") && map.includes("♡"), "spatial topology must use the Atelier surface language");

check(shell.includes('content="#fffdfc"') && shell.includes("--paper-pink") && shell.includes("--paper-violet"), "Godot loader must boot into the warm Atelier palette");
check(shell.includes("STORY LOOM KAWAII ATELIER V5") && shell.includes("♡  Story Loom"), "Godot loader must preserve the established product identity");
check(!shell.includes("#060911"), "dark control-room loader must not replace the default Kawaii Atelier surface");

check(docsParity.includes("--nf-atelier-paper") && docsParity.includes("--nf-atelier-pink") && docsParity.includes("--nf-atelier-violet"), "Docs chrome must share the Atelier palette");
check(docsParity.includes("transform: rotate(-2deg)") && docsParity.includes("border: 1px dashed"), "Docs chrome must retain tactile kawaii shape/stitch language");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_atelier_godot_quality_v1",
    status: "pass",
    experience: "story-loom-kawaii-atelier-v5",
    canonical_theme: "story-loom-v2",
    default_surface: "warm_paper",
    kawaii_balance: "restrained",
    godot_runtime: true,
    docs_parity: true,
    authority: false
  }, null, 2));
}

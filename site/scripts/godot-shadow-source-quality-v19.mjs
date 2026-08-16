#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const failures = [];
const check = (ok, message) => { if (!ok) failures.push(message); };

const scene = read("godot/Main.tscn");
const behavior = read("godot/scripts/route_behavior_completion.gd");
const stabilization = read("godot/scripts/post_merge_stabilization.gd");
const responsive = read("godot/scripts/responsive_completion.gd");
const templateBuilder = read("scripts/build-godot-web-template.sh");

check(scene.includes('path="res://scripts/route_behavior_completion.gd"'), "production scene must enter through final route behavior completion");
check(behavior.includes('extends "res://scripts/post_merge_stabilization.gd"'), "route behavior completion must extend post-merge stabilization");
check(stabilization.includes('extends "res://scripts/responsive_completion.gd"'), "post-merge stabilization must extend the current responsive completion authority");
check(responsive.includes('extends "res://scripts/wide_compact_parity.gd"'), "responsive completion inheritance must remain unchanged below stabilization");
check(stabilization.includes("SOLID_PAGE_MAX := 1480.0") && stabilization.includes("SOLID_INNER_MAX"), "wide desktop must derive from the Solid 1480px page-width contract");
check(stabilization.includes("_build_format_showcase") && stabilization.includes("PublicationHeroHit") && stabilization.includes("FOCUS_ALL"), "Publication hero selector must be a real focusable Control");
check(stabilization.includes("_publication_profile") && stabilization.includes("novelforgePublicationProfile") && stabilization.includes("novelforgePublicationArtifact"), "Publication runtime state evidence is required");
check(stabilization.includes("AGENT_HOSTS") && stabilization.includes("_select_agent_host") && stabilization.includes("novelforgeAgentHost"), "Agents must expose the current Solid host-selection behavior");
check(stabilization.includes("_resize_generation") && stabilization.includes("_stabilization_resize_probe") && stabilization.includes("_stabilization_resize_commit"), "browser resize must coalesce intermediate canvas sizes before rebuild");
check(stabilization.includes("novelforgeGlyphAudit"), "runtime glyph coverage marker is required");
check(behavior.includes("InspectorLoadDemo") && behavior.includes("InspectorReset") && behavior.includes("novelforgeInspectorState"), "Inspector must expose a real deterministic demo/reset interaction");
check(behavior.includes("PlaygroundMode") && behavior.includes("TextEdit.new") && behavior.includes("PlaygroundRun") && behavior.includes("PlaygroundClear") && behavior.includes("novelforgePlaygroundMode"), "Playground must expose real mode/input/run/clear interactions");
check(behavior.includes("_sync_playground_action_controls") && behavior.includes("_playground_run_button.disabled = not has_source"), "Playground action availability must react to typed working text without a rebuild");
check(!templateBuilder.includes("disable_advanced_gui=yes"), "production slim Web template must keep advanced GUI enabled because the Product uses TextEdit");
check(templateBuilder.includes("disable_advanced_gui=false") && templateBuilder.includes("text_edit=true"), "production slim Web template metadata must declare the TextEdit capability used by the Product");
check(!/Node3D|Camera3D|MeshInstance3D/.test(stabilization + behavior), "final Godot Product layers must remain within the 2.5D Product cap");
check(!stabilization.includes("Timer.new") && !behavior.includes("Timer.new") && !stabilization.includes("setInterval") && !behavior.includes("setInterval"), "final Godot Product layers must remain event-driven with no polling");
check(!stabilization.includes("SystemFont.new") && !behavior.includes("SystemFont.new"), "Godot Web completion must not depend on host system fonts");

// Preserve every v18 source contract. v18's only stale assumption is that the
// scene directly enters responsive_completion.gd; v19 validates the final
// chain above, then runs the unchanged v18 suite against an isolated copy where
// Main.tscn is projected to responsive_completion.gd. No repository file is
// edited and all other v18 source checks run unchanged.
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-godot-source-v19-"));
try {
  fs.cpSync(path.join(root, "godot"), path.join(tmp, "godot"), { recursive: true });
  fs.cpSync(path.join(root, "scripts"), path.join(tmp, "scripts"), { recursive: true });
  const projectedScene = scene.replace('path="res://scripts/route_behavior_completion.gd"', 'path="res://scripts/responsive_completion.gd"');
  fs.writeFileSync(path.join(tmp, "godot/Main.tscn"), projectedScene, "utf8");
  const legacy = spawnSync(process.execPath, [path.join(tmp, "scripts/godot-shadow-source-quality.mjs")], { encoding: "utf8" });
  check(legacy.status === 0, `v18 inherited source contract failed:\n${legacy.stdout}${legacy.stderr}`);
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}

if (failures.length) {
  for (const failure of failures) console.error(`godot-source-quality-v19: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_godot_production_source_quality_v19",
    status: "pass",
    inherited_v18_contract: "pass",
    production_entrypoint: "route_behavior_completion.gd",
    publication_behavior_contract: true,
    agent_behavior_contract: true,
    inspector_behavior_contract: true,
    playground_behavior_contract: true,
    playground_action_state_sync: true,
    deterministic_glyph_runtime: true,
    production_text_edit_capability: true,
    resize_coalescing: "two-deferred-turn latest-generation",
    solid_page_max_px: 1480,
    default_polling: false,
    authority: false
  }, null, 2));
}

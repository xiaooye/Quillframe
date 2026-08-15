#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const siteRoot = process.cwd();
const tokenPath = path.resolve(siteRoot, "../assets/brand/tokens.json");
const outputPath = path.resolve(siteRoot, "godot/generated/story_loom_tokens.gd");
const checkOnly = process.argv.includes("--check");
const tokens = JSON.parse(fs.readFileSync(tokenPath, "utf8"));
const light = tokens.app.theme.light;
const semantic = tokens.semantic;
const interaction = tokens.app.interaction;
const motion = tokens.app.motion;
const shape = tokens.shape;
const q = (value) => JSON.stringify(String(value));
const color = (name, value) => `const ${name} := Color(${q(value)})`;
const lines = [
  "# Generated from assets/brand/tokens.json. Do not hand-edit.", "extends RefCounted", "",
  `const TOKEN_SCHEMA := ${q(tokens.schema)}`, `const THEME_NAME := ${q(`${tokens.brand.concept} v2`)}`,
  color("BACKGROUND", light.background), color("FOREGROUND", light.foreground), color("MUTED", light.muted), color("MUTED_FOREGROUND", light.muted_foreground), color("CARD", light.card), color("CARD_FOREGROUND", light.card_foreground), color("BORDER", light.border), color("PRIMARY", light.primary), color("PRIMARY_FOREGROUND", light.primary_foreground), color("RING", light.ring), color("DESTRUCTIVE", light.destructive), color("SUCCESS", light.success), color("WARNING", light.warning), color("SURFACE_RAISED", light.surface_raised), color("SURFACE_OVERLAY", light.surface_overlay), color("SURFACE_SUNKEN", light.surface_sunken),
  color("PROJECT_FILL", semantic.project.fill), color("PROJECT", semantic.project.stroke), color("RUNTIME_FILL", semantic.runtime.fill), color("RUNTIME", semantic.runtime.stroke), color("EDITORIAL_FILL", semantic.editorial.fill), color("EDITORIAL", semantic.editorial.stroke), color("EVIDENCE_FILL", semantic.evidence.fill), color("EVIDENCE", semantic.evidence.stroke), color("VALIDATED_FILL", semantic.validated.fill), color("VALIDATED", semantic.validated.stroke), color("REJECTED_FILL", semantic.rejected.fill), color("REJECTED", semantic.rejected.stroke), color("NEUTRAL_FILL", semantic.neutral.fill), color("NEUTRAL", semantic.neutral.stroke),
  `const MIN_TOUCH_TARGET := ${Number(interaction.minimum_touch_target_px).toFixed(1)}`, `const FOCUS_RING_WIDTH := ${Number(interaction.focus_ring_width_px).toFixed(1)}`, `const FOCUS_RING_OFFSET := ${Number(interaction.focus_ring_offset_px).toFixed(1)}`, `const RADIUS_SM := ${Number(shape.radius_sm_px).toFixed(1)}`, `const RADIUS_MD := ${Number(shape.radius_md_px).toFixed(1)}`, `const RADIUS_LG := ${Number(shape.radius_lg_px).toFixed(1)}`, `const MOTION_FAST_MS := ${Number(motion.fast_ms)}`, `const MOTION_BASE_MS := ${Number(motion.base_ms)}`, `const MOTION_SLOW_MS := ${Number(motion.slow_ms)}`, `const IDLE_ANIMATION_ALLOWED := ${motion.idle_animation_allowed ? "true" : "false"}`, `const REDUCED_MOTION_REQUIRED := ${motion.reduced_motion_required ? "true" : "false"}`, "",
];
const generated = `${lines.join("\n")}\n`;
if (checkOnly) {
  if (!fs.existsSync(outputPath) || fs.readFileSync(outputPath, "utf8") !== generated) {
    console.error("Godot Story Loom token projection is missing or stale. Run: npm run tokens:godot"); process.exit(1);
  }
  console.log(JSON.stringify({ schema: "novelforge_godot_theme_projection_v1", status: "pass", token_schema: tokens.schema, mode: "check" }));
} else {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true }); fs.writeFileSync(outputPath, generated);
  console.log(JSON.stringify({ schema: "novelforge_godot_theme_projection_v1", status: "pass", token_schema: tokens.schema, output: path.relative(siteRoot, outputPath) }));
}

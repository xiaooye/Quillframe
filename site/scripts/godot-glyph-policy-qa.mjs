#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const policy = JSON.parse(fs.readFileSync(path.join(root, "godot/glyph-policy.json"), "utf8"));
const stabilization = fs.readFileSync(path.join(root, "godot/scripts/post_merge_stabilization.gd"), "utf8");
const main = fs.readFileSync(path.join(root, "godot/scripts/main.gd"), "utf8");
const failures = [];
const check = (ok, message) => { if (!ok) failures.push(message); };

const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
  const full = path.join(dir, entry.name);
  return entry.isDirectory() ? walk(full) : [full];
});

const sourceFiles = [
  ...walk(path.join(root, "godot/scripts")).filter((file) => file.endsWith(".gd")),
  path.join(root, "godot/Main.tscn"),
];
const textSymbols = new Set(policy.text_symbols ?? []);
const assetBacked = policy.asset_backed_source_emoji ?? {};
const symbolSanitized = policy.symbol_sanitized_source_emoji ?? {};
const approvedPictographs = new Set([...textSymbols, ...Object.keys(assetBacked), ...Object.keys(symbolSanitized)]);
const pictographic = /\p{Extended_Pictographic}/u;
const encountered = new Map();

for (const file of sourceFiles) {
  const text = fs.readFileSync(file, "utf8");
  for (const char of text) {
    if (!pictographic.test(char)) continue;
    if (!encountered.has(char)) encountered.set(char, new Set());
    encountered.get(char).add(path.relative(root, file));
    check(approvedPictographs.has(char), `unclassified pictographic glyph ${JSON.stringify(char)} in ${path.relative(root, file)}`);
  }
}

for (const [glyph, asset] of Object.entries(assetBacked)) {
  const relativeAsset = asset.replace(/^res:\/\//, "godot/");
  check(fs.existsSync(path.join(root, relativeAsset)), `asset-backed glyph ${glyph} is missing ${asset}`);
  check(stabilization.includes(glyph), `stabilization layer does not sanitize asset-backed glyph ${glyph}`);
  const loadedByStabilization = stabilization.includes(asset);
  const inheritedBooksAsset = asset === "res://assets/books-stack.svg"
    && stabilization.includes("_books_icon")
    && main.includes('BOOKS_ICON_PATH := "res://assets/books-stack.svg"');
  check(loadedByStabilization || inheritedBooksAsset, `stabilization layer does not load or reuse declared glyph asset ${asset}`);
}
for (const [glyph, replacement] of Object.entries(symbolSanitized)) {
  check(stabilization.includes(glyph), `stabilization layer does not sanitize source emoji ${glyph}`);
  check(stabilization.includes(replacement), `stabilization layer is missing deterministic replacement ${replacement} for ${glyph}`);
}

check(policy.web_system_emoji_fallback === false, "Godot Web glyph policy must forbid host OS emoji fallback");
check(stabilization.includes('novelforgeGlyphAudit'), "runtime glyph audit marker is required");
check(!stabilization.includes("SystemFont.new"), "stabilization must not depend on SystemFont for Web emoji");

if (failures.length) {
  for (const failure of failures) console.error(`godot-glyph-policy: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: policy.schema,
    status: "pass",
    source_files: sourceFiles.length,
    classified_pictographs: [...encountered.entries()].map(([glyph, files]) => ({ glyph, files: [...files].sort() })),
    web_system_emoji_fallback: false,
    runtime_marker: policy.runtime_marker,
  }, null, 2));
}

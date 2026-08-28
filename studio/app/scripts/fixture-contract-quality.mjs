#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixturePath = process.env.QUILLFRAME_SCENE_FIXTURE || path.resolve(appRoot, "../fixtures/scene-workspace.synthetic.json");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

let source = "";
let fixture;
try {
  source = fs.readFileSync(fixturePath, "utf8");
  fixture = JSON.parse(source);
} catch (error) {
  console.error(`fixture-contract-quality: FAIL: fixture is not readable JSON (${error instanceof Error ? error.message : "parse failure"})`);
  process.exit(1);
}

const identity = (value) => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value);
check(fixture.schema === "quillframe_studio_scene_workspace_fixture_v1", "fixture schema must be the current scene workspace contract");
check(fixture.synthetic === true && fixture.authority === false, "fixture must remain synthetic and non-authoritative");
check(identity(fixture.chapter?.id), "fixture chapter must have an explicit valid identity");
check(identity(fixture.scene?.id), "fixture scene must have an explicit valid identity");
check(identity(fixture.runtime?.latest_run_id), "fixture runtime must have an explicit valid run identity");
check(fixture.scene?.accepted_canon === false && fixture.runtime?.execution_evidence_is_canon === false, "synthetic fixture must not claim Canon authority");

if (failures.length) {
  for (const failure of failures) console.error(`fixture-contract-quality: FAIL: ${failure}`);
  process.exit(1);
}

console.log(JSON.stringify({
  schema: "quillframe_studio_scene_fixture_quality_v1",
  status: "pass",
  scope: "novel",
  chapter_id: fixture.chapter.id,
  scene_id: fixture.scene.id,
  authority: false,
}, null, 2));

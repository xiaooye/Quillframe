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

for (const marker of ["CH-012", "SCN-012", "RUN-SYNTHETIC-012"]) {
  check(!source.includes(marker), `historical scene marker is forbidden: ${marker}`);
}
check(fixture.schema === "quillframe_studio_scene_workspace_fixture_v1", "fixture schema must be the current scene workspace contract");
check(fixture.synthetic === true && fixture.authority === false, "fixture must remain synthetic and non-authoritative");
check(fixture.chapter?.id === "CH001", "fixture chapter must be exactly CH001");
check(typeof fixture.scene?.id === "string" && /^SCN-001-[0-9]{2}$/.test(fixture.scene.id), "fixture scene must use the current CH001 scene identity");
check(fixture.runtime?.latest_run_id === "RUN-SYNTHETIC-001", "fixture runtime run must be bound to CH001");

if (failures.length) {
  for (const failure of failures) console.error(`fixture-contract-quality: FAIL: ${failure}`);
  process.exit(1);
}

console.log(JSON.stringify({
  schema: "quillframe_studio_scene_fixture_quality_v1",
  status: "pass",
  chapter_scope: "CH001",
  scene_id: fixture.scene.id,
  authority: false,
}, null, 2));

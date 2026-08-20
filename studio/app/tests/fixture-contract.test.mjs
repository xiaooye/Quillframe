import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const appRoot = path.resolve(new URL("..", import.meta.url).pathname);
const fixturePath = path.resolve(appRoot, "../fixtures/scene-workspace.synthetic.json");
const qualityPath = path.resolve(appRoot, "scripts/fixture-contract-quality.mjs");

test("synthetic scene fixture is bound to the current CH001 scene identity", () => {
  const source = fs.readFileSync(fixturePath, "utf8");
  const fixture = JSON.parse(source);
  assert.equal(fixture.chapter.id, "CH001");
  assert.match(fixture.scene.id, /^SCN-001-[0-9]{2}$/);
  assert.match(fixture.runtime.latest_run_id, /^RUN-SYNTHETIC-001$/);
  assert.doesNotMatch(source, /CH-012|SCN-012|RUN-SYNTHETIC-012/);
});

test("fixture scanner rejects a reintroduced historical CH-012 marker", () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe-fixture-contract-"));
  try {
    const tempFixture = path.join(tempRoot, "scene-workspace.synthetic.json");
    fs.copyFileSync(fixturePath, tempFixture);
    const mutated = fs.readFileSync(tempFixture, "utf8").replace('"CH001"', '"CH-012"');
    fs.writeFileSync(tempFixture, mutated);
    const result = spawnSync(process.execPath, [qualityPath], {
      cwd: tempRoot,
      env: { ...process.env, QUILLFRAME_SCENE_FIXTURE: tempFixture },
      encoding: "utf8",
    });
    assert.notEqual(result.status, 0);
    assert.match(`${result.stdout}\n${result.stderr}`, /CH-012/);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});

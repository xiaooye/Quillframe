import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const appRoot = fileURLToPath(new URL("..", import.meta.url));
const fixturePath = path.resolve(appRoot, "../fixtures/scene-workspace.synthetic.json");
const qualityPath = path.resolve(appRoot, "scripts/fixture-contract-quality.mjs");

test("synthetic scene fixture has explicit identities without claiming production authority", () => {
  const source = fs.readFileSync(fixturePath, "utf8");
  const fixture = JSON.parse(source);
  assert.equal(fixture.synthetic, true);
  assert.equal(fixture.authority, false);
  assert.match(fixture.chapter.id, /^[A-Za-z0-9][A-Za-z0-9._-]+$/);
  assert.match(fixture.scene.id, /^[A-Za-z0-9][A-Za-z0-9._-]+$/);
  assert.equal(fixture.scene.accepted_canon, false);
  assert.equal(fixture.runtime.execution_evidence_is_canon, false);
});

test("fixture scanner accepts later chapter identities and rejects missing identity or false authority", () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe-fixture-contract-"));
  try {
    const tempFixture = path.join(tempRoot, "scene-workspace.synthetic.json");
    const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
    for (const [update, valid] of [
      [{ chapter: { ...fixture.chapter, id: "CH012" }, scene: { ...fixture.scene, id: "SCN-012-03" }, runtime: { ...fixture.runtime, latest_run_id: "RUN-SYNTHETIC-012" } }, true],
      [{ chapter: { ...fixture.chapter, id: "" } }, false],
      [{ authority: true }, false],
      [{ scene: { ...fixture.scene, accepted_canon: true } }, false],
    ]) {
      fs.writeFileSync(tempFixture, JSON.stringify({ ...fixture, ...update }));
      const result = spawnSync(process.execPath, [qualityPath], {
        cwd: tempRoot,
        env: { ...process.env, QUILLFRAME_SCENE_FIXTURE: tempFixture },
        encoding: "utf8",
      });
      assert.equal(result.status === 0, valid, `${result.stdout}\n${result.stderr}`);
    }
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});

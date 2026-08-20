import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { BROWSER_CORE_SOURCES, syncBrowserCore } from "./browser-core-sync.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../..");

test("browser Core sync is hermetic and binds exact CH001 source bytes", () => {
  const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe-browser-core-"));
  const browserRuntimeRoot = path.join(temporaryRoot, "runtime");
  try {
    const manifest = syncBrowserCore({ repoRoot, browserRuntimeRoot });

    assert.deepEqual(BROWSER_CORE_SOURCES, [
      "production_runtime/workflow.py",
      "production_runtime/types.py",
    ]);
    assert.equal(manifest.schema, "quillframe_browser_core_manifest_v1");
    assert.equal(manifest.chapter_scope, "CH001");
    assert.equal(manifest.authority, false);

    for (const relative of BROWSER_CORE_SOURCES) {
      assert.deepEqual(
        fs.readFileSync(path.join(browserRuntimeRoot, relative)),
        fs.readFileSync(path.join(repoRoot, relative)),
      );
      assert.match(manifest.files[relative], /^[0-9a-f]{64}$/);
    }
    assert.deepEqual(
      fs.readFileSync(path.join(browserRuntimeRoot, "ch001_quick_demo.json")),
      fs.readFileSync(path.join(repoRoot, "demo/fixtures/ch001_quick_demo.json")),
    );
    assert.deepEqual(
      JSON.parse(fs.readFileSync(path.join(browserRuntimeRoot, "manifest.json"), "utf8")),
      manifest,
    );
  } finally {
    fs.rmSync(temporaryRoot, { recursive: true, force: true });
  }
});

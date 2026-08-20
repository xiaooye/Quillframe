import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export const BROWSER_CORE_SOURCES = Object.freeze([
  "production_runtime/workflow.py",
  "production_runtime/types.py",
]);

const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex");

export function syncBrowserCore({ repoRoot, browserRuntimeRoot }) {
  if (!path.isAbsolute(repoRoot) || !path.isAbsolute(browserRuntimeRoot)) {
    throw new TypeError("browser Core sync roots must be absolute paths");
  }

  const files = {};
  for (const relative of BROWSER_CORE_SOURCES) {
    const source = path.join(repoRoot, relative);
    const destination = path.join(browserRuntimeRoot, relative);
    if (!fs.existsSync(source)) throw new Error(`Browser Core source is missing: ${relative}`);
    const bytes = fs.readFileSync(source);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, bytes);
    files[relative] = sha256(bytes);
  }

  const fixtureName = "ch001_quick_demo.json";
  const fixtureSource = path.join(repoRoot, "demo", "fixtures", fixtureName);
  if (!fs.existsSync(fixtureSource)) throw new Error("CH001 quick-demo fixture is missing");
  fs.copyFileSync(fixtureSource, path.join(browserRuntimeRoot, fixtureName));

  const manifest = {
    schema: "quillframe_browser_core_manifest_v1",
    chapter_scope: "CH001",
    files,
    demo_fixture: fixtureName,
    authority: false,
  };
  fs.writeFileSync(
    path.join(browserRuntimeRoot, "manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8",
  );
  return manifest;
}

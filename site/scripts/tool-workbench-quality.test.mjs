import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(new URL("./tool-workbench-quality.mjs", import.meta.url));
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");
const requiredFiles = [
  "site/src/styles/tool-workbench-kawaii.css",
  "site/src/styles/agent-integration.css",
  "site/src/styles/agent-host-profiles.css",
  "site/src/styles/embedded-features.css",
  "site/src/styles/readability.css",
  "site/src/styles/index.css",
  "site/src/main.tsx",
  "site/src/ProductApp.tsx",
  "studio/app/src/styles/index.css",
  "studio/app/src/main.tsx",
  "assets/brand/quillframe-product-language.css",
  "assets/brand/story-loom.weiui.css",
];

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe-tool-workbench-"));
  for (const relative of requiredFiles) {
    const target = path.join(root, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(path.join(repoRoot, relative), target);
  }
  return root;
}

function mutate(root, relative, transform) {
  const target = path.join(root, relative);
  fs.writeFileSync(target, transform(fs.readFileSync(target, "utf8")));
}

function run(root) {
  return spawnSync(process.execPath, [scriptPath], {
    cwd: root,
    env: {
      ...process.env,
      QUILLFRAME_TOOL_WORKBENCH_REPO_ROOT: root,
      QUILLFRAME_TOOL_WORKBENCH_SITE_ROOT: path.join(root, "site"),
    },
    encoding: "utf8",
  });
}

test("tool workbench quality follows every active CSS and shared-language owner", () => {
  const root = fixture();
  try {
    const result = run(root);
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("tool workbench quality rejects a missing live agent card owner", () => {
  const root = fixture();
  try {
    mutate(root, "site/src/styles/agent-integration.css", (source) => source.replaceAll(".agent-path-card", ".removed-agent-path-card"));
    const result = run(root);
    assert.notEqual(result.status, 0);
    assert.match(`${result.stdout}\n${result.stderr}`, /\.agent-path-card/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("tool workbench quality owns asymmetric object radii semantically", () => {
  const changed = fixture();
  const flattened = fixture();
  try {
    mutate(changed, "site/src/styles/agent-integration.css", (source) => source.replace("26px 26px 14px 26px", "30px 30px 15px 30px"));
    const changedResult = run(changed);
    assert.equal(changedResult.status, 0, `${changedResult.stdout}\n${changedResult.stderr}`);

    for (const relative of ["site/src/styles/agent-integration.css", "site/src/styles/agent-host-profiles.css"]) {
      mutate(flattened, relative, (source) => source.replace(/border-radius:\s*\d+px\s+\d+px\s+\d+px\s+\d+px;/g, "border-radius: 24px;"));
    }
    const flattenedResult = run(flattened);
    assert.notEqual(flattenedResult.status, 0);
    assert.match(`${flattenedResult.stdout}\n${flattenedResult.stderr}`, /asymmetric object radius/);
  } finally {
    fs.rmSync(changed, { recursive: true, force: true });
    fs.rmSync(flattened, { recursive: true, force: true });
  }
});

for (const [name, relative, transform] of [
  ["Product shared token import", "site/src/styles/index.css", (source) => source.replace('@import "../../../assets/brand/quillframe-product-language.css";', "")],
  ["Studio shared token import", "studio/app/src/styles/index.css", (source) => source.replace('@import "../../../../assets/brand/quillframe-product-language.css";', "")],
  ["Studio product language identity", "studio/app/src/main.tsx", (source) => source.replace('dataset.productLanguage = "quillframe-kawaii-v1"', 'dataset.productLanguage = "drift"')],
]) {
  test(`tool workbench quality rejects drift in ${name}`, () => {
    const root = fixture();
    try {
      mutate(root, relative, transform);
      const result = run(root);
      assert.notEqual(result.status, 0);
      assert.match(`${result.stdout}\n${result.stderr}`, /shared Story Loom product language/);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });
}

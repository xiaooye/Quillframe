import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const generator = fs.readFileSync(new URL("../scripts/write-offline-shell.mjs", import.meta.url), "utf8");

test("Studio offline shell matches same-origin precache paths independently of Vary headers", () => {
  assert.match(generator, /caches\.match\(url\.pathname,\{ignoreVary:true\}\)/);
  assert.doesNotMatch(generator, /caches\.match\(request\)/);
  assert.match(generator, /url\.origin!==self\.location\.origin\|\|url\.pathname\.startsWith\(API_PREFIX\)/);
});

test("Studio navigation fallback stays limited to the generated index shell", () => {
  assert.match(generator, /request\.mode==="navigate"/);
  assert.match(generator, /fetch\(request\)\.catch\(\(\)=>caches\.match\("\/index\.html",\{ignoreVary:true\}\)\)/);
  assert.match(generator, /if\(url\.pathname\.startsWith\("\/assets\/"\)\|\|PRECACHE\.includes\(url\.pathname\)\)/);
});

test("Studio build finalizers decode file URLs in paths with spaces and Unicode", () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe finalize 数据 "));
  const appRoot = path.join(tempRoot, "studio", "app");
  const scriptsRoot = path.join(appRoot, "scripts");
  const distRoot = path.join(appRoot, "dist");
  const assetsRoot = path.join(distRoot, "assets");
  const brandRoot = path.join(tempRoot, "assets", "brand");
  try {
    fs.mkdirSync(scriptsRoot, { recursive: true });
    fs.mkdirSync(assetsRoot, { recursive: true });
    fs.mkdirSync(brandRoot, { recursive: true });
    const javascript = "console.log('test asset');\n";
    const css = "body{color:inherit}\n";
    fs.writeFileSync(path.join(assetsRoot, "index.js"), javascript);
    fs.writeFileSync(path.join(assetsRoot, "index.css"), css);
    fs.copyFileSync(
      new URL("../../../assets/brand/weiui.integration.json", import.meta.url),
      path.join(brandRoot, "weiui.integration.json"),
    );
    for (const script of ["write-offline-shell.mjs", "write-footprint.mjs"]) {
      const target = path.join(scriptsRoot, script);
      fs.copyFileSync(new URL(`../scripts/${script}`, import.meta.url), target);
      const run = spawnSync(process.execPath, [target], { cwd: tempRoot, encoding: "utf8" });
      assert.equal(run.status, 0, run.error?.message ?? run.stderr);
    }
    const serviceWorker = fs.readFileSync(path.join(distRoot, "sw.js"), "utf8");
    assert.match(serviceWorker, /"\/assets\/index\.js"/);
    assert.match(serviceWorker, /"\/assets\/index\.css"/);
    const footprint = JSON.parse(fs.readFileSync(
      path.join(distRoot, ".well-known", "quillframe-studio-footprint.json"),
      "utf8",
    ));
    assert.equal(footprint.assets.javascript.bytes, Buffer.byteLength(javascript));
    assert.equal(footprint.assets.css.bytes, Buffer.byteLength(css));
  } finally {
    assert.equal(path.dirname(tempRoot), path.resolve(os.tmpdir()));
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
});

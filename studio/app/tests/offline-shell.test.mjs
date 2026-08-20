import assert from "node:assert/strict";
import fs from "node:fs";
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

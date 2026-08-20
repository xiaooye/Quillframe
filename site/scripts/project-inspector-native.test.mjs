import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = fs.readFileSync(new URL("../src/project-inspector-contract.ts", import.meta.url), "utf8");
const qualitySource = fs.readFileSync(new URL("./project-inspector-quality.mjs", import.meta.url), "utf8");
const output = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const contract = await import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
const manifest = 'schema = "quillframe_project_v1_0"\nid = "P"\ntitle = "Novel"\nlanguage = "en-US"\nchapter_scope = "CH001"\n';
const file = (path, body = manifest) => { const value = new File([body], path.split("/").at(-1)); Object.defineProperty(value, "webkitRelativePath", { value: path }); return value; };

test("production inspector accepts only one selected-root manifest", async () => {
  const result = await contract.inspectProjectFiles([file("root/quillframe.toml"), file("root/.quillframe/data/state.json", "{}")]);
  assert.equal(result.status, "coherent");
  assert.equal(result.project.id, "P");
});

test("production inspector rejects nested and duplicate manifests", async () => {
  for (const files of [[file("root/nested/quillframe.toml")], [file("root/quillframe.toml"), file("root/quillframe.toml")]]) {
    const result = await contract.inspectProjectFiles(files);
    assert.notEqual(result.status, "coherent");
  }
});

test("production inspector rejects malformed CH002, legacy, and private manifests", async () => {
  const ch2 = manifest.replace("CH001", "CH002");
  for (const files of [[file("root/quillframe.toml", ch2)], [file("root/quillframe.lock.json", "{}")], [file("root/quillframe.toml", manifest + 'private = "/tmp/x"\n')]]) {
    const result = await contract.inspectProjectFiles(files);
    assert.notEqual(result.status, "coherent");
  }
});

test("production inspector rejects absolute, drive, UNC, NUL, and traversal paths before root stripping", async () => {
  for (const path of ["/tmp/quillframe.toml", "C:\\quillframe.toml", "C:drive/quillframe.toml", "\\\\server\\share\\quillframe.toml", "root/../quillframe.toml", "root/./quillframe.toml", "root/\0quillframe.toml"]) {
    await assert.rejects(() => contract.inspectProjectFiles([file(path)]), undefined, path);
  }
});

test("production inspector normalizes title and language before fingerprint while preserving id grammar", async () => {
  const padded = manifest.replace('title = "Novel"', 'title = " Novel "').replace('language = "en-US"', 'language = " en-US "');
  const result = await contract.inspectProjectFiles([file("root/quillframe.toml", padded)]);
  assert.equal(result.status, "coherent");
  assert.equal(result.project.title, "Novel");
  assert.equal(result.project.language, "en-US");
  const badId = await contract.inspectProjectFiles([file("root/quillframe.toml", padded.replace('id = "P"', 'id = " P"'))]);
  assert.notEqual(badId.status, "coherent");
});

test("production inspector applies Python text semantics to schema and chapter scope", async () => {
  const padded = manifest.replace('schema = "quillframe_project_v1_0"', 'schema = " quillframe_project_v1_0 "').replace('chapter_scope = "CH001"', 'chapter_scope = " CH001 "');
  const result = await contract.inspectProjectFiles([file("root/quillframe.toml", padded)]);
  assert.equal(result.status, "coherent");
  assert.equal(result.project.schema, "quillframe_project_v1_0");
  assert.equal(result.project.chapter_scope, "CH001");
  for (const field of ["title", "language", "schema", "chapter_scope"]) {
    const blank = manifest.replace(new RegExp(`${field} = "[^"]*"`), `${field} = "   "`);
    assert.notEqual((await contract.inspectProjectFiles([file("root/quillframe.toml", blank)])).status, "coherent", field);
  }
});

test("Project Inspector quality gate follows the parser contract owner", () => {
  assert.match(qualitySource, /src\/project-inspector-contract\.ts/);
  assert.match(qualitySource, /inspectorContract\.includes\("file\.text\(\)"\)/);
  assert.match(qualitySource, /inspectorContract\.includes\('type InspectionStatus/);
});

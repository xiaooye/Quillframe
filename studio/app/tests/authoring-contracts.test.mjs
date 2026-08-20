import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

async function loadContracts() {
  const source = fs.readFileSync(new URL("../src/authoring/contracts.ts", import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, importsNotUsedAsValues: ts.ImportsNotUsedAsValues.Remove },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

const contracts = await loadContracts();

test("authoring intents map to exactly one Core task_mode", () => {
  assert.deepEqual(contracts.AUTHORING_INTENT_TASK_MODE, {
    write: "DRAFT",
    revise: "REVISE",
    review: "AUDIT",
    continuity: "AUDIT",
    research: "RESEARCH",
  });
});

test("loaded Context is never conflated with considered/selected Context", () => {
  const projection = {
    items: [
      { state: "loaded", source_object_id: "Martin" },
      { state: "selected", source_object_id: "周叙" },
      { state: "considered", source_object_id: "CH002-ending" },
      { state: "dropped_due_budget", source_object_id: "research-note" },
      { state: "visibility_excluded", source_object_id: "hidden" },
    ],
  };
  assert.deepEqual(contracts.loadedContextItems(projection).map((item) => item.source_object_id), ["Martin"]);
  assert.deepEqual(contracts.consideredNotLoaded(projection).map((item) => item.source_object_id), ["周叙", "CH002-ending", "research-note"]);
});

test("Studio consumer requirements use exact Host Bridge v11 primitives", () => {
  const names = new Set(contracts.CORE_CONSUMER_REQUIREMENTS.map((item) => item.operation));
  for (const required of [
    "project.list",
    "document.list",
    "document.open",
    "model.service.add",
    "model.service.list",
    "author.run.execute",
    "author.run.status",
    "candidate.review.get",
    "candidate.visible.get",
    "candidate.reject",
    "candidate.revision.request",
    "settlement.preflight",
  ]) assert.equal(names.has(required), true, required);
  for (const obsolete of ["document.get", "model.connect", "model.services.list", "run.events.list"]) assert.equal(names.has(obsolete), false, obsolete);
});

test("Request Revision contract is explicit and never auto-chains REVISE", () => {
  const request = contracts.CORE_CONSUMER_REQUIREMENTS.find((item) => item.operation === "candidate.revision.request");
  assert.ok(request);
  assert.match(request.authorityExpectation, /does not auto-run REVISE/);
});

test("Project contracts expose only the native five-key manifest context", () => {
  const source = fs.readFileSync(new URL("../src/authoring/contracts.ts", import.meta.url), "utf8");
  assert.match(source, /quillframe_project_v1_0/);
  assert.match(source, /quillframe_project_inspection_v1_0/);
  assert.match(source, /manifest_fingerprint/);
  assert.match(source, /data_boundary/);
  assert.doesNotMatch(source, /project_schema_version/);
  assert.doesNotMatch(source, /quillframe_project_projection_v1/);
});

test("project response parsers reject legacy, extra, nested, and CH002 shapes", async () => {
  const valid = {
    schema: "quillframe_project_inspection_v1_0",
    manifest: { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US", chapter_scope: "CH001" },
    manifest_fingerprint: "",
    chapter_scope: "CH001", data_boundary: ".quillframe/data", authority: false,
    counts: { documents: 0 },
  };
  const bytes = new TextEncoder().encode(JSON.stringify({ chapter_scope: "CH001", id: "P", language: "en-US", schema: "quillframe_project_v1_0", title: "Novel" }));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  valid.manifest_fingerprint = `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
  assert.deepEqual((await contracts.parseProjectProjection(valid)).manifest.id, "P");
  for (const bad of [
    { ...valid, project: valid.manifest },
    { ...valid, manifest: { ...valid.manifest, chapter_scope: "CH002" } },
    { ...valid, project_schema_version: 3 },
    { ...valid, data_boundary: "/private/project/.quillframe/data" },
  ]) await assert.rejects(() => contracts.parseProjectProjection(bad));
});

test("project response parsers recompute canonical manifest fingerprints", async () => {
  const valid = {
    schema: "quillframe_project_inspection_v1_0",
    manifest: { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US", chapter_scope: "CH001" },
    manifest_fingerprint: `sha256:${"a".repeat(64)}`,
    chapter_scope: "CH001", data_boundary: ".quillframe/data", authority: false, counts: { documents: 0 },
  };
  await assert.rejects(() => contracts.parseProjectProjection(valid));
  await assert.rejects(() => contracts.parseProjectCreateResult({
    schema: "quillframe_project_create_result_v1_0", manifest: valid.manifest, manifest_fingerprint: valid.manifest_fingerprint,
    chapter_scope: "CH001", data_boundary: ".quillframe/data", created: true, authority: false,
  }));
  await assert.rejects(() => contracts.parseProjectListProjection({
    schema: "quillframe_project_list_v1_0", authority: false, items: [{ schema: "quillframe_project_registry_item_v1_0", ...valid.manifest, manifest_fingerprint: valid.manifest_fingerprint, data_boundary: ".quillframe/data", last_opened_at: null }],
  }));
  const originalCrypto = globalThis.crypto;
  try {
    Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
    await assert.rejects(() => contracts.parseProjectProjection(valid));
  } finally {
    Object.defineProperty(globalThis, "crypto", { value: originalCrypto, configurable: true });
  }
});

test("project parsers reject whitespace-only native text and missing WebCrypto for every response", async () => {
  const manifest = { schema: "quillframe_project_v1_0", id: "P", title: " ", language: "en-US", chapter_scope: "CH001" };
  const invalidProjection = { schema: "quillframe_project_inspection_v1_0", manifest, manifest_fingerprint: `sha256:${"a".repeat(64)}`, chapter_scope: "CH001", data_boundary: ".quillframe/data", authority: false, counts: {} };
  await assert.rejects(() => contracts.parseProjectProjection(invalidProjection));
  const originalCrypto = globalThis.crypto;
  try {
    const goodManifest = { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US", chapter_scope: "CH001" };
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify({ chapter_scope: "CH001", id: "P", language: "en-US", schema: "quillframe_project_v1_0", title: "Novel" })));
    const fp = `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
    Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
    await assert.rejects(() => contracts.parseProjectProjection({ ...invalidProjection, manifest: goodManifest, manifest_fingerprint: fp }));
    await assert.rejects(() => contracts.parseProjectCreateResult({ schema: "quillframe_project_create_result_v1_0", manifest: goodManifest, manifest_fingerprint: fp, chapter_scope: "CH001", data_boundary: ".quillframe/data", created: true, authority: false }));
    await assert.rejects(() => contracts.parseProjectListProjection({ schema: "quillframe_project_list_v1_0", authority: false, items: [{ schema: "quillframe_project_registry_item_v1_0", ...goodManifest, manifest_fingerprint: fp, data_boundary: ".quillframe/data", last_opened_at: null }] }));
  } finally {
    Object.defineProperty(globalThis, "crypto", { value: originalCrypto, configurable: true });
  }
});

test("wire response parsers reject padded title and language instead of normalizing", async () => {
  const manifest = { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US", chapter_scope: "CH001" };
  const bytes = new TextEncoder().encode(JSON.stringify({ chapter_scope: "CH001", id: "P", language: "en-US", schema: "quillframe_project_v1_0", title: "Novel" }));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const fp = `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
  for (const field of ["title", "language"]) {
    const padded = { ...manifest, [field]: ` ${manifest[field]} ` };
    await assert.rejects(() => contracts.parseProjectProjection({ schema: "quillframe_project_inspection_v1_0", manifest: padded, manifest_fingerprint: fp, chapter_scope: "CH001", data_boundary: ".quillframe/data", authority: false, counts: {} }));
    await assert.rejects(() => contracts.parseProjectCreateResult({ schema: "quillframe_project_create_result_v1_0", manifest: padded, manifest_fingerprint: fp, chapter_scope: "CH001", data_boundary: ".quillframe/data", created: true, authority: false }));
    await assert.rejects(() => contracts.parseProjectListProjection({ schema: "quillframe_project_list_v1_0", authority: false, items: [{ schema: "quillframe_project_registry_item_v1_0", ...padded, manifest_fingerprint: fp, data_boundary: ".quillframe/data", last_opened_at: null }] }));
  }
});

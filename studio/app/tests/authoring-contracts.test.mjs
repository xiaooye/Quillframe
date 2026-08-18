import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import * as ts from "typescript";

async function loadContracts() {
  const source = fs.readFileSync(new URL("../src/authoring/contracts.ts", import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
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

test("Studio consumer requirements use exact Host Bridge v8 primitives", () => {
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

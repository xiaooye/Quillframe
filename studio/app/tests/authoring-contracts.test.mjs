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
      { object_type: "story_node", object_key: "CH-001", decision: "loaded", authority_class: "active_plan" },
      { object_type: "character", object_key: "CHAR-001", decision: "not_selected", authority_class: "locked" },
    ],
  };
  const summary = contracts.contextSelectionSummary(projection);
  assert.equal(summary.loaded, 1);
  assert.equal(summary.considered, 2);
  assert.equal(summary.items[1].loaded, false);
});

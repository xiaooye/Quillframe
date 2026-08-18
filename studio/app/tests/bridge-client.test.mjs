import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

async function loadBridge() {
  const source = fs.readFileSync(new URL("../src/bridge.ts", import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

const bridge = await loadBridge();

test("normalizes current Core bridge.describe shape without inventing operations", () => {
  const normalized = bridge.normalizeBridgeDescription({
    schema: "quillframe_host_bridge_description_v1",
    framework_version: "0.9.0",
    contract_version: "5",
    surface: "local_app",
    operations: ["project.inspect", "author.run.start", "project.inspect"],
    authority: false,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  });
  assert.deepEqual(normalized.operations, ["author.run.start", "project.inspect"]);
  assert.equal(normalized.frameworkVersion, "0.9.0");
  assert.equal(normalized.authority, false);
});

test("BridgeClient forwards one authority=false request envelope through its transport", async () => {
  let observed;
  const transport = {
    name: "hosted-http",
    requestSurface: "hosted_web",
    available: () => true,
    invoke: async (request) => {
      observed = request;
      return {
        schema: "quillframe_studio_host_bridge_result_v1",
        request_id: request.request_id,
        operation: request.operation,
        surface: request.surface,
        status: "ok",
        request_fingerprint: "sha256:request",
        result_fingerprint: "sha256:result",
        data: { project_id: "novel" },
        error: null,
        authority: false,
        canon_authority: false,
        framework_write_authority: false,
        settlement_authority: false,
      };
    },
  };
  const client = new bridge.BridgeClient(transport);
  const result = await client.invoke("project.inspect", { project_id: "novel" });
  assert.equal(result.status, "ok");
  assert.equal(observed.schema, "quillframe_studio_host_bridge_request_v1");
  assert.equal(observed.operation, "project.inspect");
  assert.equal(observed.surface, "hosted_web");
  assert.equal(observed.authority, false);
  assert.deepEqual(observed.args, { project_id: "novel" });
});

test("bridge description with elevated authority fails closed", () => {
  assert.throws(() => bridge.normalizeBridgeDescription({
    schema: "bad",
    operations: [],
    authority: true,
    canon_authority: false,
    framework_write_authority: false,
    settlement_authority: false,
    direct_core_store_access: false,
  }), /authority invariant/);
});

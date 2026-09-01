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
const research = fs.readFileSync(new URL("../src/routes/Research.tsx", import.meta.url), "utf8");
const learning = fs.readFileSync(new URL("../src/routes/Learning.tsx", import.meta.url), "utf8");
const contract = JSON.parse(fs.readFileSync(new URL("../../host_bridge_contract.json", import.meta.url), "utf8"));

test("hosted Bridge client refuses Corpus path arguments before transport", async () => {
  let invoked = false;
  const transport = {
    name: "hosted-http",
    requestSurface: "hosted_web",
    available: () => true,
    invoke: async () => { invoked = true; throw new Error("must not invoke"); },
  };
  const client = new bridge.BridgeClient(transport);
  await assert.rejects(
    () => client.invoke("corpus.collection.scan", { collection_path: "C:\\books" }),
    /cannot access a local corpus path/,
  );
  await assert.rejects(
    () => client.invoke("corpus.selection.propose", { collection_id: "COL-1", profile: "general", metadata: { source_path: "C:\\books\\one.epub" } }),
    /cannot access a local corpus path/,
  );
  await assert.rejects(
    () => client.invoke("corpus.public.validate", { bundle: { location: "C:\\books\\preview.json" } }),
    /cannot access a local corpus path/,
  );
  assert.equal(invoked, false);
});

test("local Bridge transport may carry the explicit collection path", async () => {
  let request;
  const transport = {
    name: "local-http",
    requestSurface: "local_app",
    available: () => true,
    invoke: async (value) => { request = value; return { status: "ok", data: {}, error: null }; },
  };
  await new bridge.BridgeClient(transport).invoke("corpus.collection.scan", { collection_path: "C:\\books" });
  assert.equal(request.args.collection_path, "C:\\books");
});

test("Bridge contract exposes the complete typed Corpus and user-taste surface", () => {
  for (const operation of [
    "corpus.collection.scan", "corpus.selection.propose", "corpus.selection.confirm",
    "corpus.study.start", "corpus.study.status", "corpus.study.resume", "corpus.study.cancel",
    "corpus.public.preview", "corpus.public.validate", "corpus.public.release", "corpus.public.list", "corpus.public.get",
    "learning.auto_activation_policy.get", "learning.auto_activation_policy.set",
    "learning.user_taste.list", "learning.user_taste.get", "learning.user_taste.pause", "learning.user_taste.withdraw",
  ]) assert.ok(contract.operations[operation], operation);
  assert.deepEqual(contract.operations["corpus.collection.scan"].allowed_surfaces, ["cli", "local_app"]);
  assert.deepEqual(contract.operations["corpus.selection.propose"].required_args, ["profile"]);
  assert.deepEqual(contract.operations["corpus.selection.confirm"].required_args, ["study_id", "work_ids", "proposal_fingerprint", "profile"]);
  assert.deepEqual(contract.invariants.corpus_selection_profiles, ["general", "adult_explicit"]);
  assert.equal(contract.invariants.corpus_selection_propose_requires_one_of_collection_or_study, true);
  assert.equal(contract.invariants.corpus_eligibility_details_private_aggregate_counts_only, true);
  assert.equal(contract.invariants.corpus_private_labels_local_only, true);
  assert.equal(contract.invariants.corpus_selection_limit_maximum, 120);
  assert.equal(contract.invariants.corpus_style_publication_requires_explicit_protocol, true);
  assert.equal(contract.invariants.corpus_style_preview_never_implies_release, true);
  assert.equal(contract.invariants.corpus_style_release_requires_trusted_receipts, true);
  assert.equal(contract.invariants.corpus_style_registry_path_host_owned, true);
});

test("Research and Learning consume only typed Host Bridge operations for the new flows", () => {
  for (const operation of ["corpus.collection.scan", "corpus.selection.propose", "corpus.selection.confirm", "corpus.study.status", "corpus.public.preview", "corpus.public.validate", "corpus.public.list", "corpus.public.get"]) {
    assert.match(research, new RegExp(operation.replaceAll(".", "\\.")));
  }
  assert.doesNotMatch(research, /corpus\.public\.release/);
  assert.match(research, /quillframe_corpus_style_learning_v1/);
  assert.match(research, /stylePreviewToken/);
  assert.match(research, /Preview token \(manual review only\)/);
  assert.match(research, /Studio never manufactures PASS/);
  assert.match(research, /studio\.surface\(\) === "local_app"/);
  assert.match(research, /profile: requestedProfile/);
  assert.match(research, /profile: proposal\.profile/);
  assert.match(research, /study_id: requestedStudyId/);
  assert.match(research, /studio\.surface\(\) !== "local_app"/);
  assert.match(research, /proposal\.status !== "proposed"/);
  assert.match(research, /proposal\.proposal_fingerprint/);
  assert.match(research, /rightsScopeAcknowledged/);
  assert.match(research, /!rightsScopeAcknowledged\(\)/);
  assert.match(research, /available source pool/);
  assert.match(research, /AI is not required to use every work/);
  assert.match(research, /args\.max_jobs = 8/);
  assert.match(research, /not reported by Core/);
  assert.match(research, /Target: adaptive/);
  assert.match(research, /AI prose-style research/);
  assert.doesNotMatch(research, /AI-adaptive prose research|Start AI-adaptive research/);
  assert.match(research, /runner\(\)\.axis_reconciliation/);
  assert.match(research, /runner\(\)\.axis_reconciliation_execution/);
  assert.match(research, /runner\(\)\.cohort_states/);
  assert.doesNotMatch(research, /runner\(\)\.(?:convergence_state|evidence_scope_routes|next_evidence_requests)/);
  assert.match(research, /compatibility_work_count/);
  assert.doesNotMatch(research, /evidence_items_completed/);
  assert.doesNotMatch(research, /item-by-item rights and quality review/);
  assert.doesNotMatch(research, /I reviewed rights, language, completeness and source quality item by item/);
  assert.doesNotMatch(research, /<progress/);
  assert.match(research, /action === "start" && !selectionConfirmed\(\)/);
  assert.match(research, /!selectionConfirmed\(\).*corpus\.study\.start/);
  assert.match(research, /excluded/);
  assert.match(research, /quarantined/);
  assert.match(research, /adult_explicit/);
  assert.doesNotMatch(research, /relative_locator/);
  assert.doesNotMatch(research, /localStorage|sessionStorage|indexedDB/);
  assert.match(research, /Studio never displays or publishes full novel text/);
  for (const operation of ["learning.auto_activation_policy.get", "learning.auto_activation_policy.set", "learning.user_taste.list", "learning.user_taste.pause", "learning.user_taste.withdraw"]) {
    assert.match(learning, new RegExp(operation.replaceAll(".", "\\.")));
  }
  assert.match(learning, /current explicit request always wins/i);
});

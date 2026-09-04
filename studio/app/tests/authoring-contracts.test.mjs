import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

async function loadContracts(file = "contracts") {
  const source = fs.readFileSync(new URL(`../src/authoring/${file}.ts`, import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, importsNotUsedAsValues: ts.ImportsNotUsedAsValues.Remove },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

const contracts = await loadContracts();
const { createManuscriptBuffer } = await loadContracts("manuscriptBuffer");

const bytesFingerprint = async (content) => `sha256:${Buffer.from(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content))).toString("hex")}`;
const deferred = () => { let resolve; let reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

test("autosave serializes edits made during a save against the returned Core parent, without replacing newer text", async () => {
  const first = deferred(); const second = deferred(); const requests = [];
  const editor = createManuscriptBuffer({ changed() {}, save: (request) => { requests.push(request); return requests.length === 1 ? first.promise : second.promise; } });
  editor.bind({ project_id: "P", document_id: "DOC-A", content: "original", parent_revision_id: "R0" });
  editor.edit("first edit"); const saving = editor.flush();
  editor.edit("second edit");
  assert.equal(editor.flush(), saving, "concurrent flush must not duplicate the POST");
  first.resolve({ revision_id: "R1", content_fingerprint: await bytesFingerprint("first edit"), deduplicated: false });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(editor.current().content, "second edit");
  assert.equal(editor.current().dirty, true);
  // The digest is asynchronous; observe the next queued save before resolving it.
  while (requests.length < 2) await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(requests[1], { project_id: "P", document_id: "DOC-A", content: "second edit", expected_parent_revision_id: "R1" });
  second.resolve({ revision_id: "R2", content_fingerprint: await bytesFingerprint("second edit"), deduplicated: false });
  assert.equal(await saving, true);
  assert.equal(editor.current().content, "second edit");
  assert.equal(editor.current().parent_revision_id, "R2");
  assert.equal(editor.current().state, "saved");
});

test("a late save receipt cannot alter a newly opened document or a disposed editor", async () => {
  for (const dispose of [false, true]) {
    const pending = deferred(); let notifications = 0;
    const editor = createManuscriptBuffer({ changed() { notifications += 1; }, save: () => pending.promise });
    editor.bind({ project_id: "P", document_id: "DOC-A", content: "old", parent_revision_id: "R0" });
    editor.edit("edited"); const saving = editor.flush();
    if (dispose) editor.dispose(); else editor.bind({ project_id: "OTHER", document_id: "DOC-B", content: "new document", parent_revision_id: "RB" });
    const before = notifications;
    pending.resolve({ revision_id: "R1", content_fingerprint: await bytesFingerprint("edited"), deduplicated: false });
    assert.equal(await saving, false);
    assert.equal(notifications, before);
    if (!dispose) assert.equal(editor.current().content, "new document");
  }
});

test("save-and-refresh waits for edits entered during metadata refresh before a chapter switch or leave", async () => {
  const metadata = deferred(); const enteredRefresh = deferred(); const requests = [];
  let refreshes = 0;
  const editor = createManuscriptBuffer({ changed() {}, save: async (request) => {
    requests.push(request);
    return { revision_id: `R${requests.length}`, content_fingerprint: await bytesFingerprint(request.content), deduplicated: false };
  } });
  editor.bind({ project_id: "P", document_id: "DOC-A", content: "base", parent_revision_id: "R0" });
  editor.edit("saved first");
  const leaving = editor.flushAndRefresh(async () => {
    refreshes += 1;
    if (refreshes === 1) { enteredRefresh.resolve(); await metadata.promise; }
  });
  await enteredRefresh.promise;
  editor.edit("typed while metadata loaded");
  metadata.resolve();
  assert.equal(await leaving, true);
  assert.equal(refreshes, 2);
  assert.deepEqual(requests[1], { project_id: "P", document_id: "DOC-A", content: "typed while metadata loaded", expected_parent_revision_id: "R1" });
  assert.equal(editor.current().content, "typed while metadata loaded");
  assert.equal(editor.current().dirty, false);
  assert.equal(editor.current().parent_revision_id, "R2");
});

test("metadata refresh from an earlier editor generation cannot authorize replacing a rebound buffer", async () => {
  for (const sameDocument of [false, true]) {
    const metadata = deferred(); const enteredRefresh = deferred();
    const editor = createManuscriptBuffer({ changed() {}, save: async (request) => ({ revision_id: "R1", content_fingerprint: await bytesFingerprint(request.content), deduplicated: false }) });
    editor.bind({ project_id: "P", document_id: "DOC-A", content: "base", parent_revision_id: "R0" });
    editor.edit("saved");
    const leaving = editor.flushAndRefresh(async () => { enteredRefresh.resolve(); await metadata.promise; });
    await enteredRefresh.promise;
    editor.bind({ project_id: "P", document_id: sameDocument ? "DOC-A" : "DOC-B", content: "new buffer", parent_revision_id: "RX" });
    editor.edit("keep this local change");
    metadata.resolve();
    assert.equal(await leaving, false);
    assert.equal(editor.current().content, "keep this local change");
    assert.equal(editor.current().dirty, true);
    assert.equal(editor.current().parent_revision_id, "RX");
  }
});

test("a conflict after a metadata refresh keeps new edits and blocks navigation", async () => {
  let saves = 0;
  const editor = createManuscriptBuffer({ changed() {}, save: async (request) => {
    if (++saves > 1) throw new Error("revision conflict");
    return { revision_id: "R1", content_fingerprint: await bytesFingerprint(request.content), deduplicated: false };
  } });
  editor.bind({ project_id: "P", document_id: "DOC-A", content: "base", parent_revision_id: "R0" });
  editor.edit("first");
  assert.equal(await editor.flushAndRefresh(async () => { editor.edit("newer"); }), false);
  assert.equal(editor.current().content, "newer");
  assert.equal(editor.current().state, "conflict");
});

test("save conflict and mismatched content receipts preserve edits without replay or guessed parent", async () => {
  for (const conflict of [true, false]) {
    let calls = 0;
    const editor = createManuscriptBuffer({ changed() {}, save: async () => { calls += 1; if (conflict) throw new Error("revision conflict"); return { revision_id: "wrong", content_fingerprint: await bytesFingerprint("other bytes"), deduplicated: false }; } });
    editor.bind({ project_id: "P", document_id: "DOC-A", content: "base", parent_revision_id: "R0" });
    editor.edit("keep my edits");
    assert.equal(await editor.flush(), false);
    assert.equal(editor.current().content, "keep my edits");
    assert.equal(editor.current().parent_revision_id, "R0");
    assert.equal(editor.current().state, conflict ? "conflict" : "failed");
    if (conflict) { editor.edit("more edits"); await editor.flush(); assert.equal(calls, 1); }
  }
});

function reviewFixture() {
  return {
    schema: "quillframe_candidate_review_projection_v1", project_id: "P",
    candidate: { candidate_id: "C", candidate_fingerprint: `sha256:${"a".repeat(64)}`, document_id: "DOC-CH001", persisted_status: "accepted", effective_status: "accepted", user_visible_gate: "PASS" },
    candidate_revision: { revision_id: "REV-C", content_fingerprint: `sha256:${"a".repeat(64)}`, content: "fixture", authority_class: "accepted" },
    incumbent_revision: null, diff: null, evidence: {}, private_reasoning_exposed: false,
    authority: false, canon_authority: false, settlement_authority: false,
  };
}

function acceptanceFixture(review = reviewFixture()) {
  return {
    schema: "quillframe_candidate_acceptance_result_v1", acceptance_id: "accept_exact",
    candidate_id: review.candidate.candidate_id, candidate_fingerprint: review.candidate.candidate_fingerprint,
    authorized_by: "fixture_user", authorization: { source: "fixture" }, request_fingerprint: `sha256:${"b".repeat(64)}`,
    accepted: true, settled: false, canon_mutated: false,
  };
}

function settlementFixture(review = reviewFixture(), acceptance = acceptanceFixture(review)) {
  return {
    schema: "quillframe_settlement_result_v1", settlement_id: "settle_exact", status: "settled", target_ref: "chapter:CH001",
    before_fingerprint: "absent", after_fingerprint: `sha256:${"c".repeat(64)}`, canon_mutated: true,
    state_delta: { before: null, after: { acceptance_id: acceptance.acceptance_id, candidate_id: review.candidate.candidate_id, document_id: review.candidate.document_id, revision_id: review.candidate_revision.revision_id, content_fingerprint: review.candidate.candidate_fingerprint } },
  };
}

function receiptProjection(...payloads) {
  return {
    schema: "quillframe_inspector_projection_v1", kind: "receipts", project_id: "P", authority: false,
    items: payloads.map((payload, index) => ({ receipt_id: `R-${index}`, receipt_kind: payload.schema === "quillframe_candidate_acceptance_result_v1" ? "candidate_accept" : "settlement", payload_json: JSON.stringify(payload) })),
  };
}

test("Review settlement targets come from the exact manuscript's Core chapter association", () => {
  const review = reviewFixture();
  const document = { document_id: "DOC-CH001", story_node_id: "CH001", document_kind: "manuscript", title: "Fixture" };
  const projection = { schema: "quillframe_document_list_projection_v1", project_id: "P", items: [document], authority: false, canon_authority: false };
  const chapters = { schema: "quillframe_chapter_list_v1", project_id: "P", authority: false,
    items: [{ chapter_id: "CH001", document_id: document.document_id, title: "Fixture", ordinal: 1, parent_id: null }] };
  assert.equal(contracts.resolveReviewSettlementTarget(projection, review, chapters), "chapter:CH001");
  assert.equal(contracts.resolveReviewSettlementTarget(projection, review), undefined, "the document relation alone does not prove a chapter exists");
  for (const item of [
    { ...document, story_node_id: null }, { ...document, story_node_id: undefined },
    { ...document, story_node_id: "CH002" }, { ...document, story_node_id: "SCN-001-03" },
    { ...document, document_kind: "outline" }, { ...document, document_id: "OTHER" },
  ]) assert.equal(contracts.resolveReviewSettlementTarget({ ...projection, items: [item] }, review, chapters), undefined);
  assert.equal(contracts.resolveReviewSettlementTarget({ ...projection, items: [{ ...document, story_node_id: "CH012" }] }, review,
    { ...chapters, items: [{ ...chapters.items[0], chapter_id: "CH012", ordinal: 12 }] }), "chapter:CH012", "later chapters use the actual registry association");
  const chapterNamedDocument = { ...review, candidate: { ...review.candidate, document_id: "CH001" } };
  assert.equal(contracts.resolveReviewSettlementTarget({ ...projection, items: [{ ...document, document_id: "CH001", story_node_id: null }] }, chapterNamedDocument), undefined, "a chapter-like document name is not chapter evidence");
  assert.throws(() => contracts.resolveReviewSettlementTarget({ ...projection, project_id: "OTHER" }, review), /review_document/);
  assert.throws(() => contracts.resolveReviewSettlementTarget({ ...projection, items: [document, document] }, review), /review_document/);
});

test("Review recovers persisted acceptance and successful settlement only through exact receipt bindings", () => {
  const review = reviewFixture();
  const acceptance = acceptanceFixture(review);
  const settlement = settlementFixture(review, acceptance);
  const unrelated = { ...acceptance, candidate_id: "OTHER", acceptance_id: "accept_other" };
  const recovered = contracts.recoverReviewLifecycleReceipts(receiptProjection(unrelated, settlement, acceptance), review, "chapter:CH001");
  assert.deepEqual(recovered.acceptance, acceptance);
  assert.deepEqual(recovered.settlement, settlement);
  assert.equal(recovered.receipt_window_full, false);
  assert.throws(() => contracts.recoverReviewLifecycleReceipts({ ...receiptProjection(acceptance), project_id: "OTHER" }, review, "chapter:CH001"), /review_receipts/);
  assert.throws(() => contracts.recoverReviewLifecycleReceipts(receiptProjection(acceptance, { ...acceptance, acceptance_id: "accept_second" }), review, "chapter:CH001"), /review_acceptance/);
});

test("Review never infers acceptance from a status flag or settlement from an unbound receipt", () => {
  const review = reviewFixture();
  const acceptance = acceptanceFixture(review);
  const settlement = settlementFixture(review, acceptance);
  assert.equal(contracts.recoverReviewLifecycleReceipts(receiptProjection(), review, "chapter:CH001").acceptance, undefined);
  for (const candidate of [
    { ...review.candidate, candidate_fingerprint: `sha256:${"d".repeat(64)}` },
    { ...review.candidate, persisted_status: "review_draft", effective_status: "review_draft" },
  ]) {
    const current = { ...review, candidate, candidate_revision: { ...review.candidate_revision, content_fingerprint: candidate.candidate_fingerprint } };
    assert.equal(contracts.recoverReviewLifecycleReceipts(receiptProjection(acceptance, settlement), current, "chapter:CH001").acceptance, undefined);
  }
  for (const field of ["acceptance_id", "candidate_id", "document_id", "revision_id", "content_fingerprint"]) {
    const mismatched = { ...settlement, state_delta: { ...settlement.state_delta, after: { ...settlement.state_delta.after, [field]: "mismatch" } } };
    assert.equal(contracts.recoverReviewLifecycleReceipts(receiptProjection(acceptance, mismatched), review, "chapter:CH001").settlement, undefined, field);
  }
  for (const unbound of [
    { ...settlement, target_ref: "chapter:DOC-CH001" },
    { ...settlement, canon_mutated: false },
    { ...settlement, state_delta: undefined },
    { schema: "quillframe_settlement_result_v1", settlement_id: "settle_incomplete", status: "settlement_incomplete", target_ref: "chapter:CH001", expected_before_fingerprint: "absent", actual_before_fingerprint: `sha256:${"d".repeat(64)}`, canon_mutated: false },
  ]) assert.equal(contracts.recoverReviewLifecycleReceipts(receiptProjection(acceptance, unbound), review, "chapter:CH001").settlement, undefined);
  assert.equal(contracts.recoverReviewLifecycleReceipts(receiptProjection(acceptance, settlement), review, undefined).settlement, undefined, "a prior receipt cannot invent a missing canonical chapter association");
});

test("Review preserves unknown lifecycle state when the bounded receipt window has no exact evidence", () => {
  const window = receiptProjection();
  window.items = Array.from({ length: 500 }, (_, index) => ({ receipt_id: `R-${index}`, receipt_kind: "production_stage", payload_json: "{}" }));
  const result = contracts.recoverReviewLifecycleReceipts(window, reviewFixture(), "chapter:CH001");
  assert.equal(result.receipt_window_full, true);
  assert.equal(result.acceptance, undefined);
  assert.equal(result.settlement, undefined);
});

test("Review validates a direct acceptance receipt and the exact preflight before settlement", () => {
  const review = reviewFixture();
  const acceptance = acceptanceFixture(review);
  assert.deepEqual(contracts.parseReviewAcceptanceResult(acceptance, review), acceptance);
  assert.throws(() => contracts.parseReviewAcceptanceResult({ ...acceptance, candidate_fingerprint: `sha256:${"d".repeat(64)}` }, review), /review_acceptance/);
  const preflight = {
    schema: "quillframe_settlement_preflight_v1", project_id: "P", acceptance_id: acceptance.acceptance_id,
    candidate_id: review.candidate.candidate_id, candidate_fingerprint: review.candidate.candidate_fingerprint,
    document_id: review.candidate.document_id, revision_id: review.candidate_revision.revision_id,
    target_ref: "chapter:CH001", expected_before_fingerprint: "absent", current_before_fingerprint: "absent",
    settleable: true, mutation_performed: false, canon_mutated: false, authority: false,
  };
  assert.deepEqual(contracts.parseReviewSettlementPreflight(preflight, review, acceptance, "chapter:CH001"), preflight);
  const derived = { ...preflight, narrative_proposal: { changes: [{ evidence_quote: "Bounded evidence", field: "fixture_state" }] }, reader_observations: [{ observation_id: "OBS", updates: [] }], preflight_fingerprint: `sha256:${"f".repeat(64)}` };
  assert.deepEqual(contracts.parseReviewSettlementPreflight(derived, review, acceptance, "chapter:CH001"), derived);
  for (const changed of [{ preflight_fingerprint: undefined }, { preflight_fingerprint: "not-a-fingerprint" }, { reader_observations: ["not-an-observation"] }, { narrative_proposal: "not-a-proposal" }]) {
    assert.throws(() => contracts.parseReviewSettlementPreflight({ ...derived, ...changed }, review, acceptance, "chapter:CH001"), /review_settlement_preflight/);
  }
  for (const changed of [
    { project_id: "OTHER" }, { acceptance_id: "accept_other" }, { candidate_id: "OTHER" },
    { candidate_fingerprint: `sha256:${"d".repeat(64)}` }, { document_id: "OTHER" }, { revision_id: "OTHER" },
    { target_ref: "chapter:DOC-CH001" }, { current_before_fingerprint: `sha256:${"d".repeat(64)}` },
    { settleable: false }, { mutation_performed: true },
  ]) assert.throws(() => contracts.parseReviewSettlementPreflight({ ...preflight, ...changed }, review, acceptance, "chapter:CH001"), /review_settlement_preflight/);
});

test("Review treats a bound incomplete settlement as an unsuccessful attempt, never a recovered success", () => {
  const review = reviewFixture();
  const acceptance = acceptanceFixture(review);
  const incomplete = { schema: "quillframe_settlement_result_v1", settlement_id: null, status: "settlement_incomplete", target_ref: "chapter:CH001", expected_before_fingerprint: "absent", actual_before_fingerprint: `sha256:${"d".repeat(64)}`, canon_mutated: false };
  assert.deepEqual(contracts.parseReviewSettlementResult(incomplete, review, acceptance, "chapter:CH001", "absent"), incomplete);
  assert.throws(() => contracts.parseReviewSettlementResult(incomplete, review, acceptance, "chapter:CH001"), /review_settlement/);
  assert.throws(() => contracts.parseReviewSettlementResult({ ...incomplete, canon_mutated: true }, review, acceptance, "chapter:CH001", "absent"), /review_settlement/);
  assert.throws(() => contracts.parseReviewSettlementResult({ ...incomplete, expected_before_fingerprint: `sha256:${"e".repeat(64)}` }, review, acceptance, "chapter:CH001", "absent"), /review_settlement/);
});

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

test("Project contracts expose only the native four-key novel manifest context", () => {
  const source = fs.readFileSync(new URL("../src/authoring/contracts.ts", import.meta.url), "utf8");
  assert.match(source, /quillframe_project_v1_0/);
  assert.match(source, /quillframe_project_inspection_v1_0/);
  assert.match(source, /manifest_fingerprint/);
  assert.match(source, /data_boundary/);
  assert.match(source, /scope: "novel"/);
  assert.doesNotMatch(source, /project_schema_version/);
  assert.doesNotMatch(source, /quillframe_project_projection_v1/);
});

test("project response parsers reject legacy five-key, extra, and nested manifest shapes", async () => {
  const valid = {
    schema: "quillframe_project_inspection_v1_0",
    manifest: { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US" },
    manifest_fingerprint: "",
    scope: "novel", data_boundary: ".quillframe/data", authority: false,
    counts: { documents: 0 },
  };
  const bytes = new TextEncoder().encode(JSON.stringify({ id: "P", language: "en-US", schema: "quillframe_project_v1_0", title: "Novel" }));
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
    manifest: { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US" },
    manifest_fingerprint: `sha256:${"a".repeat(64)}`,
    scope: "novel", data_boundary: ".quillframe/data", authority: false, counts: { documents: 0 },
  };
  await assert.rejects(() => contracts.parseProjectProjection(valid));
  await assert.rejects(() => contracts.parseProjectCreateResult({
    schema: "quillframe_project_create_result_v1_0", manifest: valid.manifest, manifest_fingerprint: valid.manifest_fingerprint,
    scope: "novel", data_boundary: ".quillframe/data", created: true, authority: false,
  }));
  await assert.rejects(() => contracts.parseProjectListProjection({
    schema: "quillframe_project_list_v1_0", authority: false, items: [{ schema: "quillframe_project_registry_item_v1_0", ...valid.manifest, schema: "quillframe_project_registry_item_v1_0", scope: "novel", manifest_fingerprint: valid.manifest_fingerprint, data_boundary: ".quillframe/data", last_opened_at: null }],
  }));
  const originalCrypto = globalThis.crypto;
  try {
    Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
    await assert.rejects(() => contracts.parseProjectProjection(valid));
  } finally {
    Object.defineProperty(globalThis, "crypto", { value: originalCrypto, configurable: true });
  }
});

test("native whole-novel create, inspect and registry projections accept Chinese manifest bytes", async () => {
  const manifest = { schema: "quillframe_project_v1_0", id: "NOVEL-TEST", title: "中文测试项目", language: "zh-CN" };
  const manifest_fingerprint = await bytesFingerprint(JSON.stringify({ id: manifest.id, language: manifest.language, schema: manifest.schema, title: manifest.title }));
  const shared = { manifest, manifest_fingerprint, scope: "novel", data_boundary: ".quillframe/data", authority: false };
  assert.equal((await contracts.parseProjectCreateResult({ ...shared, schema: "quillframe_project_create_result_v1_0", created: true })).manifest.title, manifest.title);
  assert.equal((await contracts.parseProjectProjection({ ...shared, schema: "quillframe_project_inspection_v1_0", counts: { story_nodes: 12 } })).counts.story_nodes, 12);
  const registry = { id: manifest.id, title: manifest.title, language: manifest.language, schema: "quillframe_project_registry_item_v1_0", scope: "novel", manifest_fingerprint, data_boundary: ".quillframe/data", last_opened_at: null };
  assert.deepEqual((await contracts.parseProjectListProjection({ schema: "quillframe_project_list_v1_0", items: [registry], authority: false })).items, [registry]);
  await assert.rejects(() => contracts.parseProjectProjection({ ...shared, schema: "quillframe_project_inspection_v1_0", counts: {}, manifest: { ...manifest, chapter_scope: "CH001" } }));
});

test("chapter list validates real document bindings and current accepted heads across multiple chapters", () => {
  const value = { schema: "quillframe_chapter_list_v1", project_id: "P", authority: false,
    items: [{ chapter_id: "CH001", document_id: "DOC-A", ordinal: 1, title: "First", parent_id: null, current_acceptance_id: "ACCEPT-A" },
      { chapter_id: "CH012", document_id: "DOC-Z", ordinal: 12, title: "Later", parent_id: "VOL-2", current_acceptance_id: null, needs_review: true }] };
  assert.deepEqual(contracts.parseChapterList(value, "P"), value);
  for (const changed of [{ document_id: "DOC-A" }, { chapter_id: "CH001" }, { current_acceptance_id: true }, { ordinal: 1.5 }]) {
    assert.throws(() => contracts.parseChapterList({ ...value, items: [value.items[0], { ...value.items[1], ...changed }] }, "P"), /chapter_list/);
  }
  assert.throws(() => contracts.parseChapterList(value, "OTHER"), /chapter_list/);
});

test("plan save binds author intent, expected version and exact expectation references", () => {
  const expected = { project_id: "P", target_ref: "chapter:CH012", title: "测试章节计划", content: "作者的完整意图", expected_version: 3,
    reader_intent: { reader_question: "读者现在想知道什么", visible_reward: "本章兑现的信息" }, expectation_refs: ["EXP-A", "EXP-B"] };
  const result = { ...expected, schema: "quillframe_plan_save_result_v1", plan_id: "PLAN-A", version: 4, status: "active", authority: false, horizon: {} };
  assert.equal(contracts.parsePlanSave(result, expected).version, 4);
  for (const changed of [{ version: 3 }, { target_ref: "book" }, { content: "older text" }, { reader_intent: {} },
    { reader_intent: { ...expected.reader_intent, synthetic_score: "98" } }, { expectation_refs: ["EXP-B", "EXP-A"] }]) {
    assert.throws(() => contracts.parsePlanSave({ ...result, ...changed }, expected), /plan_/);
  }
  assert.throws(() => contracts.parsePlanInspection({ schema: "quillframe_plan_inspection_v1", project_id: "P", authority: false, items: [result] }, "P", "book"), /plan_/);
});

test("reader evidence is shown only for the exact released candidate and never becomes a numeric readership score", () => {
  const candidate = `sha256:${"a".repeat(64)}`;
  const value = { judgment: { artifact_fingerprint: candidate, status: "pass", summary: "Specific reader report", strongest_positive: "The choice matters", strongest_problem: "An unresolved cost", findings: ["paragraph:3", { private: "not a textual reference" }], retention_rate: 0.98 }, private_reasoning: "not projected" };
  assert.deepEqual(contracts.projectReaderEvidence(value, candidate), { bound: true, status: "pass", summary: "Specific reader report", strongest_positive: "The choice matters", strongest_problem: "An unresolved cost", evidence_refs: ["paragraph:3"] });
  assert.deepEqual(contracts.projectReaderEvidence(value, `sha256:${"b".repeat(64)}`), { bound: false, evidence_refs: [] });
  const released = { judgment: { ...value.judgment, report: "Released reader report", evidence_refs: ["candidate:paragraph:4"], strongest_problem: null } };
  assert.deepEqual(contracts.projectReaderEvidence(released, candidate), { bound: true, status: "pass", summary: "Released reader report", strongest_positive: "The choice matters", strongest_problem: undefined, evidence_refs: ["candidate:paragraph:4"] });
});

test("story source freshness stays distinct from historical acceptance authority", () => {
  const character = { character_id: "CHAR-A", name: "测试人物", state: {}, agenda: "保护同伴", voice_notes: "克制", authority_class: "accepted", source_state: "stale", source_chapter_id: "CH012" };
  const value = { schema: "quillframe_story_inspection_v1", project_id: "P", authority: false, characters: [character], relationships: [], timeline: [], world: [], canon: [], dependencies: [] };
  const parsed = contracts.parseStoryInspection(value, "P");
  assert.equal(parsed.characters[0].authority_class, "accepted");
  assert.equal(parsed.characters[0].source_state, "stale");
  for (const change of [{ source_state: "current" }, { source_state: "untracked", source_chapter_id: null }]) {
    assert.equal(contracts.parseStoryInspection({ ...value, characters: [{ ...character, ...change }] }, "P").characters[0].source_state, change.source_state);
  }
  for (const change of [{ source_state: "accepted" }, { source_state: undefined }, { source_chapter_id: null }, { source_chapter_id: " " }]) {
    assert.throws(() => contracts.parseStoryInspection({ ...value, characters: [{ ...character, ...change }] }, "P"), /story_inspection/);
  }
});

test("reader expectations preserve model provenance without asserting authority or measured retention", () => {
  const candidate = `sha256:${"a".repeat(64)}`;
  const value = { schema: "quillframe_reader_expectations_inspection_v1", project_id: "P", authority: false, measured_retention: false,
    items: [{ expectation_id: "EXP-A", kind: "question", scope: "book", description: "他会守住承诺吗", opened_order: 1, due_by_order: null, last_touched_order: 12, status: "partial", source_ref: "chapter:CH012", source_fingerprint: candidate, version: 2, authority: false }],
    observations: [{ observation_id: "OBS-A", run_id: "R", chapter_id: "CH012", document_id: "D", candidate_id: "C", candidate_fingerprint: candidate, reading_order: 12, state: "applied", updates: [], source_type: "model_proxy", authority: false }] };
  assert.equal(contracts.parseReaderExpectations(value, "P").items[0].status, "partial");
  for (const change of [{ authority: true }, { measured_retention: true }, { measured_retention: undefined }, { observations: [{ ...value.observations[0], source_type: "human_reader" }] }]) {
    assert.throws(() => contracts.parseReaderExpectations({ ...value, ...change }, "P"), /reader_expectations/);
  }
});

test("publication download verifies actual Unicode bytes, exact provenance and safe media", async () => {
  const content = "# 第十二章\n\n测试导出。";
  const bytes = new TextEncoder().encode(content);
  const expected = { project_id: "P", build_id: "BUILD-A", artifact_fingerprint: await bytesFingerprint(content), byte_size: bytes.length, source_acceptance_ids: ["A1", "A2"] };
  const value = { ...expected, schema: "quillframe_publication_artifact_v1", filename: "小说.md", media_type: "text/markdown; charset=utf-8", content_base64: Buffer.from(bytes).toString("base64"), authority: false };
  assert.deepEqual((await contracts.parsePublicationArtifact(value, expected)).bytes, bytes);
  for (const changed of [{ project_id: "OTHER" }, { build_id: "OTHER" }, { authority: true }, { source_acceptance_ids: ["A2", "A1"] }, { byte_size: bytes.length + 1 },
    { filename: "../novel.md" }, { filename: "C:\\novel.md" }, { media_type: "text/html" }, { content_base64: value.content_base64 + "\n" },
    { content_base64: Buffer.from("# 第十二章\n\n篡改导出。").toString("base64") }]) {
    await assert.rejects(() => contracts.parsePublicationArtifact({ ...value, ...changed }, expected), /publication_artifact/);
  }
  const empty = { ...expected, artifact_fingerprint: await bytesFingerprint(""), byte_size: 0, source_acceptance_ids: ["A1"] };
  assert.equal((await contracts.parsePublicationArtifact({ ...value, ...empty, content_base64: "" }, empty)).bytes.length, 0);
});

test("publication collection validates accepted source order and invalidates a changed selection", () => {
  const source = { project_id: "P", acceptance_ids: ["A1", "A2"], format: "txt" };
  const value = { schema: "quillframe_publication_collection_result_v1", project_id: "P", build_id: "B", source_acceptance_ids: ["A1", "A2"], format: "txt", artifact_fingerprint: `sha256:${"a".repeat(64)}`, byte_size: 10, output_ref: "exports/B.txt", persistent: true, authority: false };
  assert.deepEqual(contracts.parsePublicationCollection(value, source), value);
  assert.throws(() => contracts.parsePublicationCollection({ ...value, source_acceptance_ids: ["A2", "A1"] }, source), /publication_collection/);
  assert.throws(() => contracts.parsePublicationCollection(value, { ...source, acceptance_ids: ["A1", "A1"] }), /publication_collection/);
  const guard = contracts.createPublicationCollectionRequestGuard(() => source);
  const pending = guard.begin();
  source.acceptance_ids.reverse();
  assert.equal(pending.isCurrent(), false);
  assert.deepEqual(pending.source.acceptance_ids, ["A1", "A2"]);
  const latest = guard.begin(); guard.invalidate();
  assert.equal(latest.isCurrent(), false);
});

test("learning projections preserve feedback source, project scope and exact activation authority", () => {
  const noAuthority = { authority: false, canon_write: false, framework_write: false, durable_user_taste_write: false };
  const feedback = { ...noAuthority, schema: "quillframe_project_learning_v1", project_id: "P", event_id: "E", status: "advisory", advisory_only: true, run_id: "R", session_id: "S", candidate_id: "C", candidate_fingerprint: `sha256:${"a".repeat(64)}`, document_id: "D", evidence_kind: "comparison", source_type: "model_reader", source_id: "actual-model-source", feedback_text: "Bounded feedback", intake: null, semantic_call: null };
  assert.equal(contracts.parseProjectFeedback(feedback, "P", "E").source_type, "model_reader");
  assert.throws(() => contracts.parseProjectFeedback({ ...feedback, source_type: "human" }, "P"), /project_feedback/);
  assert.throws(() => contracts.parseProjectFeedback({ ...feedback, status: "awaiting_semantic" }, "P"), /project_feedback/);
  assert.throws(() => contracts.parseProjectFeedback({ ...feedback, advisory_only: false }, "P"), /project_feedback/);
  assert.throws(() => contracts.parseProjectFeedback({ ...feedback, source_type: undefined }, "P"), /project_feedback/);
  assert.throws(() => contracts.parseProjectFeedback(feedback, "OTHER"), /project_feedback/);
  const preference = { ...noAuthority, schema: "quillframe_project_preference_v1", project_id: "P", hypothesis_id: "H", scope: "project", dimension: "style", statement: "Preserve character choice", mechanism: "Keep the decision consequential", state: "candidate", version: 2, applicability: {}, evidence_ids: ["E"], contradiction_ids: [], active_for_future_production: false };
  assert.equal(contracts.parseProjectPreference(preference, "P").active_for_future_production, false);
  for (const change of [{ scope: "user_taste" }, { active_for_future_production: true }, { version: 0 }, { authority: true }]) assert.throws(() => contracts.parseProjectPreference({ ...preference, ...change }, "P"), /project_preference/);
  const expected = { project_id: "P", hypothesis_id: "H", expected_version: 2, authorized_by: "studio_user", idempotency_key: "ACTION-1", action: "activate" };
  const receipt = { ...noAuthority, ...expected, schema: "quillframe_project_preference_receipt_v1", receipt_id: "PREF-1", before_version: 2, after_version: 3, after_state: "active", user_authorized: true, before_fingerprint: `sha256:${"b".repeat(64)}`, after_fingerprint: `sha256:${"c".repeat(64)}`, transaction_scope: "learning_database", cross_database_atomic: false };
  assert.deepEqual(contracts.parseProjectPreferenceReceipt({ ...noAuthority, receipt, replayed: false }, expected), receipt);
  for (const change of [{ hypothesis_id: "OTHER" }, { expected_version: 1 }, { after_version: 2 }, { user_authorized: false }, { action: "deactivate" }, { idempotency_key: "OTHER" }]) assert.throws(() => contracts.parseProjectPreferenceReceipt({ ...noAuthority, receipt: { ...receipt, ...change }, replayed: false }, expected), /project_preference_receipt/);
});

test("project parsers reject whitespace-only native text and missing WebCrypto for every response", async () => {
  const manifest = { schema: "quillframe_project_v1_0", id: "P", title: " ", language: "en-US" };
  const invalidProjection = { schema: "quillframe_project_inspection_v1_0", manifest, manifest_fingerprint: `sha256:${"a".repeat(64)}`, scope: "novel", data_boundary: ".quillframe/data", authority: false, counts: {} };
  await assert.rejects(() => contracts.parseProjectProjection(invalidProjection));
  const originalCrypto = globalThis.crypto;
  try {
    const goodManifest = { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US" };
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify({ id: "P", language: "en-US", schema: "quillframe_project_v1_0", title: "Novel" })));
    const fp = `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
    Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
    await assert.rejects(() => contracts.parseProjectProjection({ ...invalidProjection, manifest: goodManifest, manifest_fingerprint: fp }));
    await assert.rejects(() => contracts.parseProjectCreateResult({ schema: "quillframe_project_create_result_v1_0", manifest: goodManifest, manifest_fingerprint: fp, scope: "novel", data_boundary: ".quillframe/data", created: true, authority: false }));
    await assert.rejects(() => contracts.parseProjectListProjection({ schema: "quillframe_project_list_v1_0", authority: false, items: [{ schema: "quillframe_project_registry_item_v1_0", ...goodManifest, schema: "quillframe_project_registry_item_v1_0", scope: "novel", manifest_fingerprint: fp, data_boundary: ".quillframe/data", last_opened_at: null }] }));
  } finally {
    Object.defineProperty(globalThis, "crypto", { value: originalCrypto, configurable: true });
  }
});

test("wire response parsers reject padded title and language instead of normalizing", async () => {
  const manifest = { schema: "quillframe_project_v1_0", id: "P", title: "Novel", language: "en-US" };
  const bytes = new TextEncoder().encode(JSON.stringify({ id: "P", language: "en-US", schema: "quillframe_project_v1_0", title: "Novel" }));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const fp = `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
  for (const field of ["title", "language"]) {
    const padded = { ...manifest, [field]: ` ${manifest[field]} ` };
    await assert.rejects(() => contracts.parseProjectProjection({ schema: "quillframe_project_inspection_v1_0", manifest: padded, manifest_fingerprint: fp, scope: "novel", data_boundary: ".quillframe/data", authority: false, counts: {} }));
    await assert.rejects(() => contracts.parseProjectCreateResult({ schema: "quillframe_project_create_result_v1_0", manifest: padded, manifest_fingerprint: fp, scope: "novel", data_boundary: ".quillframe/data", created: true, authority: false }));
    await assert.rejects(() => contracts.parseProjectListProjection({ schema: "quillframe_project_list_v1_0", authority: false, items: [{ schema: "quillframe_project_registry_item_v1_0", ...padded, schema: "quillframe_project_registry_item_v1_0", scope: "novel", manifest_fingerprint: fp, data_boundary: ".quillframe/data", last_opened_at: null }] }));
  }
});

test("production service selection uses connected and enabled evidence, not token presence", () => {
  const relay = { service_id: "local-relay", endpoint: "http://127.0.0.1:8766/v1", enabled: 1, discovery_state: "connected", credential_present: 0 };
  const unavailable = [
    { ...relay, service_id: "disabled", enabled: 0, credential_present: 1 },
    { ...relay, service_id: "stale", discovery_state: "stale", credential_present: 1 },
    { ...relay, service_id: "unknown", enabled: undefined },
    { ...relay, service_id: "" },
  ];
  assert.equal(contracts.connectedModelService([...unavailable, relay]), relay);
  assert.equal(contracts.connectedModelService(unavailable), undefined);
  const authenticated = { ...relay, service_id: "remote", enabled: true, credential_present: true };
  assert.equal(contracts.connectedModelService([authenticated]), authenticated);
});

const executionJournalFixture = () => {
  const confirmed = { call_id: "CALL-A", stage_key: "context_profile:chapter:CH012", runtime_role: "context_profile_deriver", state: "confirmed", error_code: null,
    input_fingerprint: `sha256:${"a".repeat(64)}`, result_fingerprint: `sha256:${"b".repeat(64)}`, deadline_at_ms: 12000, created_at: "now", updated_at: "now" };
  const dispatched = { ...confirmed, call_id: "CALL-B", stage_key: "context_profile:plan_test", state: "dispatched", result_fingerprint: null };
  return { schema: "quillframe_author_run_status_v1", project_id: "P", run_id: "R", target_ref: "DOC", task_mode: "DRAFT", status: "awaiting_semantic", events: [], authority: false,
    execution_journal: { schema: "quillframe_production_execution_journal_v1", run_id: "R", request_fingerprint: `sha256:${"c".repeat(64)}`,
      active_executor: true, cancel_requested: false, calls: [confirmed, dispatched], unconfirmed_call_ids: ["CALL-B"], confirmed_call_count: 1, dispatched_call_count: 2,
      model_call_budget: 64, safe_to_resume_confirmed_only: false, private_payloads_visible: false, authority: false } };
};

test("repair action exposes only exact failed-run references, never source prose or active/foreign evidence", () => {
  const value = executionJournalFixture();
  value.status = "failed_gate";
  value.execution_journal.active_executor = false;
  value.execution_journal.calls = value.execution_journal.calls.slice(0, 1);
  value.execution_journal.dispatched_call_count = 1;
  value.execution_journal.unconfirmed_call_ids = [];
  value.repair_source = { source_run_id: "R", source_checkpoint_id: "CHECKPOINT", expected_candidate_fingerprint: `sha256:${"d".repeat(64)}`,
    candidate_text: "PRIVATE INCUMBENT", diagnosis: "PRIVATE DIAGNOSIS" };
  const expected = { project_id: "P", run_id: "R", document_id: "DOC" };
  assert.deepEqual(contracts.projectRepairSource(value, expected), { source_run_id: "R", source_checkpoint_id: "CHECKPOINT", expected_candidate_fingerprint: `sha256:${"d".repeat(64)}` });
  for (const change of [{ status: "semantic_pending" }, { project_id: "OTHER" }, { target_ref: "OTHER" },
    { repair_source: { ...value.repair_source, source_run_id: "OTHER" } },
    { repair_source: { ...value.repair_source, expected_candidate_fingerprint: "invalid" } },
    { execution_journal: { ...value.execution_journal, active_executor: true } }]) {
    assert.equal(contracts.projectRepairSource({ ...value, ...change }, expected), undefined);
  }
});

test("execution journal projects exact confirmed/dispatched counts and pending stages without private payloads or progress scores", () => {
  const value = executionJournalFixture();
  value.execution_journal.job = { payload: "PRIVATE-JOB-SENTINEL" };
  value.execution_journal.calls[1].result = { manuscript: "PRIVATE-RESULT-SENTINEL" };
  const progress = contracts.projectExecutionJournal(value, { project_id: "P", run_id: "R", document_id: "DOC" });
  const pending = { call_id: "CALL-B", stage_key: "context_profile:plan_test", runtime_role: "context_profile_deriver", state: "dispatched", error_code: null };
  assert.deepEqual(progress, { run_status: "awaiting_semantic", active_executor: true, cancel_requested: false,
    confirmed_call_count: 1, dispatched_call_count: 2, model_call_budget: 64, pending_calls: [pending], last_call: pending, latest_stage_failure: null, latest_gate_rejection: null });
  assert.doesNotMatch(JSON.stringify(progress), /PRIVATE-|input_fingerprint|result_fingerprint|safe_to_resume|payload|percentage|success/);
});

test("execution journal rejects mixed run/document evidence, contradictory counters and unsafe authority", () => {
  const value = executionJournalFixture();
  const expected = { project_id: "P", run_id: "R", document_id: "DOC" };
  assert.equal(contracts.projectExecutionJournal(undefined, expected), undefined);
  for (const change of [{ project_id: "OTHER" }, { run_id: "OTHER" }, { target_ref: "OTHER" }, { authority: true }, { execution_journal: undefined }]) {
    assert.equal(contracts.projectExecutionJournal({ ...value, ...change }, expected), undefined);
  }
  for (const change of [{ run_id: "OTHER" }, { schema: "legacy" }, { authority: true }, { private_payloads_visible: true }, { active_executor: "yes" },
    { confirmed_call_count: 2 }, { confirmed_call_count: -1 }, { dispatched_call_count: 1.5 }, { dispatched_call_count: 3 }, { model_call_budget: 0 }, { model_call_budget: 1 },
    { request_fingerprint: "unknown" }, { unconfirmed_call_ids: [] }, { unconfirmed_call_ids: ["CALL-A"] }, { unconfirmed_call_ids: ["CALL-B", "CALL-B"] },
    { calls: [value.execution_journal.calls[0], { ...value.execution_journal.calls[1], call_id: "CALL-A" }] },
    { calls: [value.execution_journal.calls[0], { ...value.execution_journal.calls[1], state: "successful" }] }]) {
    assert.equal(contracts.projectExecutionJournal({ ...value, execution_journal: { ...value.execution_journal, ...change } }, expected), undefined);
  }
  assert.equal(contracts.projectExecutionJournal(value, { ...expected, document_id: "" }), undefined);
});

test("execution journal preserves unknown outcomes, interruption, cancellation and an unfrozen empty budget", () => {
  const value = executionJournalFixture();
  const expected = { project_id: "P", run_id: "R", document_id: "DOC" };
  const unknown = { ...value, status: "semantic_pending", execution_journal: { ...value.execution_journal, active_executor: false,
    calls: [value.execution_journal.calls[0], { ...value.execution_journal.calls[1], state: "unconfirmed", error_code: "executor_interrupted" }] } };
  const pending = contracts.projectExecutionJournal(unknown, expected);
  assert.equal(pending.pending_calls[0].state, "unconfirmed");
  assert.equal(pending.pending_calls[0].error_code, "executor_interrupted");
  assert.equal(pending.confirmed_call_count, 1);
  assert.equal(pending.active_executor, false);
  const cancelled = { ...unknown, status: "cancelled", execution_journal: { ...unknown.execution_journal, cancel_requested: true, unconfirmed_call_ids: [],
    calls: [value.execution_journal.calls[0], { ...value.execution_journal.calls[1], state: "cancelled", error_code: "run_cancelled" }] } };
  assert.equal(contracts.projectExecutionJournal(cancelled, expected).last_call.state, "cancelled");
  assert.deepEqual(contracts.projectExecutionJournal(cancelled, expected).pending_calls, []);
  const empty = { ...value, execution_journal: { ...value.execution_journal, active_executor: false, request_fingerprint: null,
    calls: [], unconfirmed_call_ids: [], confirmed_call_count: 0, dispatched_call_count: 0, model_call_budget: null } };
  assert.deepEqual(contracts.projectExecutionJournal(empty, expected), { run_status: "awaiting_semantic", active_executor: false, cancel_requested: false,
    confirmed_call_count: 0, dispatched_call_count: 0, model_call_budget: null, pending_calls: [], last_call: null, latest_stage_failure: null, latest_gate_rejection: null });
});

test("current Core leases and rejected gates disable resume without blocking query or cancellation", () => {
  const appShell = fs.readFileSync(new URL("../src/AppShell.tsx", import.meta.url), "utf8");
  const resume = appShell.slice(appShell.indexOf("const resumeRun ="), appShell.indexOf("const cancelRun ="));
  const resumeGuard = resume.match(/if \(([^\n]+)\) return;/)?.[1];
  const disabled = (handler) => appShell.match(new RegExp(`disabled=\\{([^{}\\n]+)\\} onClick=\\{\\(\\) => void ${handler}\\(\\)\\}`))?.[1];
  const evaluate = (expression, journal, pending = false) => {
    assert.ok(expression, "evaluate the actual AppShell control expression");
    return new Function("projectId", "runId", "aiBusy", "controlBusy", "executionPending", "executionJournal", "supported", `return (${expression});`)(
      "P", "R", () => false, () => false, () => pending, () => journal, () => ["author.run.resume", "author.run.cancel"],
    );
  };
  const value = executionJournalFixture();
  const expected = { project_id: "P", run_id: "R", document_id: "DOC" };
  value.execution_journal.calls.forEach((call) => { call.deadline_at_ms = 0; });
  const active = contracts.projectExecutionJournal(value, expected);
  assert.equal(evaluate(resumeGuard, active), true, "a lease read from Core blocks the handler even without a local execution request");
  assert.equal(evaluate(disabled("resumeRun"), active), true);
  assert.equal(evaluate(disabled("cancelRun"), active), false);
  assert.equal(evaluate(disabled("refreshRunEvidence"), active), false);
  const inactive = contracts.projectExecutionJournal({ ...value, execution_journal: { ...value.execution_journal, active_executor: false } }, expected);
  const rejected = { ...inactive, run_status: "failed_gate" };
  assert.equal(evaluate(disabled("refreshRunEvidence"), rejected), false);
  for (const expression of [resumeGuard, disabled("resumeRun")]) {
    assert.equal(evaluate(expression, inactive), false, "an updated Core snapshot clears the lease restriction");
    assert.equal(evaluate(expression, inactive, true), true, "the existing pending-request guard remains");
    assert.equal(evaluate(expression, rejected), true, "a Core-rejected gate requires a new run even with no active executor");
    assert.equal(evaluate(expression, { ...inactive, run_status: "semantic_pending" }), false, "pending semantic results retain the existing explicit resume path");
    for (const changed of [{ project_id: "OTHER" }, { run_id: "OTHER" }, { document_id: "OTHER" }]) {
      assert.equal(evaluate(expression, contracts.projectExecutionJournal(value, { ...expected, ...changed })), false, "another run/project/document cannot lend its lease to the selected run");
    }
  }
});

test("confirmed model results remain distinct from failed semantic stages and failure details stay private", () => {
  const value = executionJournalFixture();
  const expected = { project_id: "P", run_id: "R", document_id: "DOC" };
  value.status = "semantic_pending";
  value.execution_journal.active_executor = false;
  value.execution_journal.confirmed_call_count = 2;
  value.execution_journal.calls[1].state = "confirmed";
  value.execution_journal.unconfirmed_call_ids = [];
  value.events = [
    { event_kind: "production_stage_failed", payload: { code: "earlier_error", mechanism: "earlier_stage" } },
    { event_kind: "production_stage_failed", payload: { code: "semantic_output_invalid", mechanism: "character_simulation", message: "PRIVATE-MODEL-RESULT", detail: { proposal: "PRIVATE-PROPOSAL" } } },
  ];
  const progress = contracts.projectExecutionJournal(value, expected);
  assert.equal(progress.confirmed_call_count, 2);
  assert.deepEqual(progress.pending_calls, []);
  assert.deepEqual(progress.latest_stage_failure, { code: "semantic_output_invalid", mechanism: "character_simulation" });
  assert.equal(progress.latest_gate_rejection, null);
  assert.doesNotMatch(JSON.stringify(progress), /PRIVATE-|message|detail|proposal/);
  value.events[1].payload.code = "unexpected private error prose";
  assert.equal(contracts.projectExecutionJournal(value, expected).latest_stage_failure, null, "malformed latest metadata must not expose prose or resurrect an earlier failure");
});

test("gate rejection remains distinct from transport failures even when every model call is confirmed", () => {
  const value = executionJournalFixture();
  const expected = { project_id: "P", run_id: "R", document_id: "DOC" };
  value.status = "failed_gate";
  value.execution_journal.active_executor = false;
  value.execution_journal.confirmed_call_count = 2;
  value.execution_journal.calls[1].state = "confirmed";
  value.execution_journal.unconfirmed_call_ids = [];
  const rejection = { mechanism: "scene_simulation", stage_result_fingerprint: `sha256:${"d".repeat(64)}` };
  value.events = [{ event_kind: "production_gate_rejected", payload: { ...rejection, repair_routes: [{ reason: "PRIVATE-REPAIR" }], message: "PRIVATE-MESSAGE", detail: "PRIVATE-DETAIL" } }];
  const progress = contracts.projectExecutionJournal(value, expected);
  assert.equal(progress.confirmed_call_count, progress.dispatched_call_count);
  assert.deepEqual(progress.pending_calls, []);
  assert.equal(progress.run_status, "failed_gate");
  assert.deepEqual(progress.latest_gate_rejection, rejection, "a gate rejection has no invented error code");
  assert.equal(progress.latest_stage_failure, null);
  assert.doesNotMatch(JSON.stringify(progress), /PRIVATE-|repair_routes|message|detail|passed|success/);
  for (const change of [{ mechanism: "private reason prose" }, { stage_result_fingerprint: "unverified" }]) {
    assert.equal(contracts.projectExecutionJournal({ ...value, events: [...value.events, { event_kind: "production_gate_rejected", payload: { ...rejection, ...change } }] }, expected).latest_gate_rejection, null);
  }
  const transport = contracts.projectExecutionJournal({ ...value, status: "semantic_pending", events: [{ event_kind: "production_stage_failed", payload: { mechanism: "scene_simulation", code: "semantic_pending", detail: { transport: "PRIVATE-TRANSPORT" } } }] }, expected);
  assert.equal(transport.latest_gate_rejection, null);
  assert.deepEqual(transport.latest_stage_failure, { mechanism: "scene_simulation", code: "semantic_pending" });
  assert.equal(transport.run_status, "semantic_pending");
});

test("runtime inspector rows are tied to their exact project, kind and read-only authority", () => {
  const row = { run_id: "RUN-A", task_mode: "DRAFT", target_ref: "DOC-A", status: "semantic_pending" };
  const value = { schema: "quillframe_inspector_projection_v1", project_id: "P", kind: "runs", authority: false, items: [row] };
  assert.equal(contracts.parseRuntimeInspectorList(value, "P", "runs").items[0], row);
  for (const change of [{ project_id: "OTHER" }, { kind: "sessions" }, { authority: true }, { items: [row, row] }, { items: [{ ...row, run_id: "" }] },
    { items: [{ ...row, target_ref: undefined }] }, { items: [{ ...row, task_mode: "" }] }]) {
    assert.throws(() => contracts.parseRuntimeInspectorList({ ...value, ...change }, "P", "runs"), /runtime_inspector/);
  }
});

test("viewing an existing production run resolves only a real registered chapter/document association", () => {
  const expected = { project_id: "P", run_id: "RUN-A", task_mode: "DRAFT", target_ref: "DOC-LATER" };
  const status = { ...expected, schema: "quillframe_production_run_status_v1", status: "semantic_pending", authority: false };
  const chapters = { schema: "quillframe_chapter_list_v1", project_id: "P", authority: false,
    items: [{ chapter_id: "CH012", document_id: "DOC-LATER", title: "后续章节", ordinal: 12, parent_id: null }] };
  assert.deepEqual(contracts.resolveRuntimeRunSelection(status, expected, chapters), { project_id: "P", run_id: "RUN-A", task_mode: "DRAFT", chapter_id: "CH012", document_id: "DOC-LATER" });
  assert.equal(contracts.resolveRuntimeRunSelection({ ...status, task_mode: "REVISE" }, { ...expected, task_mode: "REVISE" }, chapters).task_mode, "REVISE");
  for (const change of [{ project_id: "OTHER" }, { run_id: "OTHER" }, { target_ref: "CH012" }, { task_mode: "REVISE" }, { authority: true }, { schema: "legacy" }]) {
    assert.throws(() => contracts.resolveRuntimeRunSelection({ ...status, ...change }, expected, chapters), /runtime_run_selection/);
  }
  for (const change of [{ project_id: "OTHER" }, { authority: true }, { items: [] }, { items: [chapters.items[0], { ...chapters.items[0], chapter_id: "CH013" }] }]) {
    assert.throws(() => contracts.resolveRuntimeRunSelection(status, expected, { ...chapters, ...change }), /runtime_run_selection|chapter_list/);
  }
  assert.throws(() => contracts.resolveRuntimeRunSelection({ ...status, target_ref: "chapter:CH012" }, { ...expected, target_ref: "chapter:CH012" }, chapters), /runtime_run_selection_target_unknown/);
  assert.throws(() => contracts.resolveRuntimeRunSelection({ ...status, task_mode: "AUDIT" }, { ...expected, task_mode: "AUDIT" }, chapters), /runtime_run_selection/);
});

test("independent review progress stays bound to actual current Core evidence", () => {
  const status = { project_id: "P", run_id: "R", status: "awaiting_external", events: [] };
  const execution = { ...status, schema: "quillframe_production_execution_result_v1", awaiting: "independent_provenance", candidate_visible: false, raw_draft_visible: false, authority: false };
  assert.equal(contracts.pendingIndependentReview(status, execution), "independent_provenance");
  assert.equal(contracts.pendingIndependentReview(status, { ...execution, awaiting: "independent_semantic_review" }), "independent_semantic_review");
  assert.equal(contracts.pendingIndependentReview(status, undefined), undefined);
  assert.equal(contracts.pendingIndependentReview(status, { ...execution, awaiting: "unknown_boundary" }), undefined);
  for (const change of [{ project_id: "other" }, { run_id: "other" }, { status: "completed" }, { status: "cancelled" }]) {
    assert.equal(contracts.pendingIndependentReview({ ...status, ...change }, execution), undefined);
  }
  assert.equal(contracts.pendingIndependentReview(status, { ...execution, candidate_visible: true }), undefined);
  const requested = { ...status, events: [{ event_kind: "production_independent_requested", payload: { authority: false } }] };
  assert.equal(contracts.pendingIndependentReview(requested, execution), "independent_semantic_review");
  assert.equal(contracts.pendingIndependentReview({ ...requested, status: "completed" }, execution), undefined);
  const requalified = { ...requested, events: [...requested.events, { event_kind: "production_candidate_qualified" }] };
  assert.equal(contracts.pendingIndependentReview(requalified, { ...execution, awaiting: "independent_semantic_review" }), undefined);
});

const publicationPreview = {
  schema: "quillframe_publication_preview_v1", persistent: false,
  source_acceptance_id: "accept-current", source_fingerprint: `sha256:${"a".repeat(64)}`,
  document_id: "document-1", content: "<script>untrusted()</script>\n# Plain manuscript text",
};

test("publication preview consumes exact top-level Core content and acceptance binding", () => {
  assert.equal(contracts.parsePublicationPreview(publicationPreview, "accept-current").content, publicationPreview.content);
  assert.equal(contracts.parsePublicationPreview({ ...publicationPreview, content: "" }, "accept-current").content, "");
  for (const value of [
    { ...publicationPreview, source_acceptance_id: "accept-other" },
    { ...publicationPreview, persistent: true },
    { ...publicationPreview, source_fingerprint: "not-a-fingerprint" },
    { ...publicationPreview, content: undefined, preview: { content: "legacy html", kind: "html" } },
    { ...publicationPreview, content: {} },
  ]) assert.throws(() => contracts.parsePublicationPreview(value, "accept-current"), /publication_preview_invalid/);
});

test("publication build receipts match the preview source and supported output format", () => {
  const receipt = {
    schema: "quillframe_publication_build_v1", build_id: "pub-1", persistent: true,
    source_acceptance_id: publicationPreview.source_acceptance_id, source_fingerprint: publicationPreview.source_fingerprint,
    output_ref: ".quillframe/data/artifacts/publication/pub-1.md", format: "md",
    compiler_contract: "quillframe_core_publication_text_v1", identity_fingerprint: `sha256:${"b".repeat(64)}`,
    artifact_fingerprint: `sha256:${"c".repeat(64)}`, byte_size: 42,
  };
  assert.equal(contracts.parsePublicationBuild(receipt, publicationPreview, "md"), receipt);
  assert.equal(contracts.parsePublicationBuild({ ...receipt, format: "txt" }, publicationPreview, "txt").format, "txt");
  for (const value of [
    { ...receipt, source_acceptance_id: "accept-other" },
    { ...receipt, source_fingerprint: `sha256:${"d".repeat(64)}` },
    { ...receipt, format: "txt" },
    { ...receipt, format: "epub" },
    { ...receipt, persistent: false },
    { ...receipt, output_ref: undefined, artifact_ref: "legacy" },
    { ...receipt, byte_size: -1 },
  ]) assert.throws(() => contracts.parsePublicationBuild(value, publicationPreview, "md"), /publication_build_invalid/);
  assert.throws(() => contracts.parsePublicationBuild({ ...receipt, format: "epub" }, publicationPreview, "epub"), /publication_build_invalid/);
});

test("late publication responses cannot restore a previous source, format, or superseded request", async () => {
  let source = { project_id: "P", acceptance_id: "accept-A", format: "md" };
  const guard = contracts.createPublicationRequestGuard(() => source);
  const original = guard.begin();
  assert.equal(original.isCurrent(), true);
  assert.deepEqual(original.source, source);
  source = { ...source, acceptance_id: "accept-B" };
  assert.equal(original.isCurrent(), false);
  guard.invalidate();
  source = { ...source, acceptance_id: "accept-A" };
  assert.equal(original.isCurrent(), false, "returning to the same acceptance cannot revive an invalidated response");
  const next = guard.begin();
  source = { ...source, project_id: "P2" };
  assert.equal(next.isCurrent(), false);
  const build = guard.begin();
  source = { ...source, format: "txt" };
  assert.equal(build.isCurrent(), false);
  let deliver;
  const late = guard.begin();
  const output = new Promise((resolve) => { deliver = resolve; }).then((value) => late.isCurrent() ? value : undefined);
  const current = guard.begin();
  deliver(publicationPreview);
  assert.equal(await output, undefined);
  assert.equal(current.isCurrent(), true);
  guard.invalidate();
  assert.equal(current.isCurrent(), false, "unmount/source reset invalidates outstanding work");
});

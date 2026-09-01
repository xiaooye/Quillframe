import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

async function load(relative) {
  const output = ts.transpileModule(fs.readFileSync(new URL(relative, import.meta.url), "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

const corpus = await load("../src/research/corpusContracts.ts");
const taste = await load("../src/learning/userTasteContracts.ts");
const hash = `sha256:${"a".repeat(64)}`;

test("Corpus parser accepts a bounded dynamic cohort and rejects private locators", () => {
  const value = {
    schema: "quillframe_corpus_study_status_v1",
    collection_id: "COL-1",
    study_id: "STUDY-1",
    profile: "general",
    status: "proposed",
    private_local_only: true,
    proposal_hash: hash,
    eligibility_counts: { excluded: 3, quarantined: 5 },
    works: Array.from({ length: 24 }, (_, index) => ({ public_work_id: `PW-${String(index).padStart(32, "0")}`,
      display_label: `Licensed work ${index + 1}`, creator: `Creator ${index + 1}`,
      ordinal: index + 1, status: "pending" })),
  };
  const parsed = corpus.parseCorpusSelection(value, { allowPrivateLabels: true });
  assert.equal(parsed.items.length, 24);
  assert.equal(parsed.profile, "general");
  assert.equal(parsed.status, "proposed");
  assert.deepEqual(parsed.eligibility_counts, { excluded: 3, quarantined: 5 });
  assert.equal(parsed.items[0].title, "Licensed work 1");
  assert.equal(parsed.items[0].creator, "Creator 1");
  assert.equal("relative_locator" in parsed.items[0], false);
  assert.equal(parsed.proposal_fingerprint, hash);
  assert.equal(parsed.items.some((item) => "content" in item || "path" in item), false);
  const existing = { ...value };
  delete existing.collection_id;
  assert.equal(corpus.parseCorpusSelection(existing, { allowPrivateLabels: true }).study_id, "STUDY-1");
  assert.equal(corpus.parseCorpusSelection({ ...value, works: value.works.slice(0, 7) }, { allowPrivateLabels: true }).items.length, 7);
  assert.throws(() => corpus.parseCorpusSelection({ ...value, works: [] }, { allowPrivateLabels: true }), /corpus_selection_projection_invalid/);
  assert.throws(() => corpus.parseCorpusSelection({ ...value, works: Array.from({ length: 501 }, (_, index) => ({ public_work_id: `PW-${index}`,
    display_label: `Work ${index}` })) }, { allowPrivateLabels: true }), /corpus_selection_projection_invalid/);
  assert.throws(
    () => corpus.parseCorpusSelection({ ...value, profile: "unspecified" }, { allowPrivateLabels: true }),
    /corpus_selection_projection_invalid/,
  );
  assert.throws(
    () => corpus.parseCorpusSelection({ ...value, works: value.works.map((item, index) => index ? item : { ...item, relative_locator: "private/work-1.txt" }) }, { allowPrivateLabels: true }),
    /corpus_selection_private_boundary_invalid/,
  );
  assert.throws(
    () => corpus.parseCorpusSelection({ ...value, eligibility_counts: { excluded: -1, quarantined: 5 } }, { allowPrivateLabels: true }),
    /corpus_aggregate_counts_invalid/,
  );
  assert.throws(
    () => corpus.parseCorpusSelection({ ...value, exclusion_counts: { identity_unknown: 3 } }, { allowPrivateLabels: true }),
    /corpus_selection_private_boundary_invalid/,
  );
  const hosted = { ...value, works: value.works.map(({ display_label, creator, ...item }) => item) };
  delete hosted.private_local_only;
  const anonymous = corpus.parseCorpusSelection(hosted);
  assert.equal(anonymous.items[0].title, anonymous.items[0].work_id);
  assert.throws(() => corpus.parseCorpusSelection(value), /corpus_selection_private_boundary_invalid/);
  assert.throws(
    () => corpus.parseCorpusSelection({
      schema: "quillframe_corpus_selection_v1", status: "insufficient_eligible_works",
      required: 120, eligible: 0, profile: "general", study_created: false,
    }, { allowPrivateLabels: true }),
    /corpus_selection_insufficient_eligible_works/,
  );
  assert.deepEqual(corpus.corpusEligibilityCounts({
    schema: "quillframe_corpus_scan_v1", eligibility: { excluded_count: 8, quarantined_works: 11 },
  }), { excluded: 8, quarantined: 11 });
  assert.deepEqual(corpus.corpusEligibilityCounts({ schema: "quillframe_corpus_scan_v1" }), {});
  assert.deepEqual(corpus.corpusProgress({
    schema: "quillframe_corpus_study_operation_v1", status: "awaiting_semantic", performed: false,
    runner: { status: "queued", progress: { completed_works: 7, total_works: 120 } },
  }), { status: "awaiting_semantic", compatibility_work_count: 7 });
  assert.deepEqual(corpus.corpusProgress({
    schema: "quillframe_corpus_study_operation_v1", status: "running",
    progress: {
      compatibility_work_count: 5, completed_works: 99, available_pool_count: 120,
      activated_count: 3, analysed_count: 5, semantic_attempts: 14,
    },
    runner: { status: "running", cohort_states: { available_unanalysed: 112, activated: 3, analysed: 5 } },
  }), {
    status: "running", compatibility_work_count: 5, available_pool_count: 120,
    activated_count: 3, analysed_count: 5, semantic_attempts: 14,
  });
  assert.deepEqual(corpus.corpusProgress({
    schema: "quillframe_corpus_study_operation_v1", runner: {
      status: "running", work_states: { complete: 6 }, semantic_attempts: 9,
      cohort_states: { available_unanalysed: 110, activated: 4, analysed: 6 },
    },
  }), {
    status: "running", compatibility_work_count: 6, available_pool_count: 120,
    activated_count: 4, analysed_count: 6, semantic_attempts: 9,
  });
});

test("Corpus metadata view hides source text, paths and preview release token", () => {
  assert.deepEqual(corpus.corpusMetadataView({
    schema: "quillframe_corpus_public_preview_v1",
    content: "COPYRIGHTED TEXT",
    passage: "IMITATION-READY PASSAGE",
    source_path: "C:\\private\\book.epub",
    exclusion_counts: { identity_unknown: 3 },
    location: "/Users/private/library",
    preview_token: "release-capability",
    aggregate_metrics: { dialogue_marks: 14 },
  }), {
    schema: "quillframe_corpus_public_preview_v1",
    content: "<not displayed in Studio>",
    passage: "<not displayed in Studio>",
    source_path: "<not displayed in Studio>",
    exclusion_counts: "<not displayed in Studio>",
    location: "<not displayed in Studio>",
    preview_token: "<not displayed in Studio>",
    aggregate_metrics: { dialogue_marks: 14 },
  });
});

test("Style Atlas fingerprints are valid preview and registry lookup identities", () => {
  assert.equal(corpus.previewFingerprint({
    schema: "quillframe_public_general_style_atlas_v1", atlas_fingerprint: hash,
  }), hash);
  assert.equal(corpus.corpusVersion({
    schema: "quillframe_public_general_style_atlas_v1", atlas_fingerprint: hash,
  }), hash);
  const token = `style-preview-${"b".repeat(64)}`;
  assert.equal(corpus.stylePreviewToken({
    schema: "quillframe_corpus_style_atlas_preview_v1", preview_token: token,
  }), token);
  assert.equal(corpus.stylePreviewToken({
    schema: "quillframe_corpus_style_atlas_preview_v1", preview_token: "caller-token",
  }), undefined);
});

test("User-taste contracts preserve policy authority and reversible state bindings", () => {
  const policy = taste.parseUserTastePolicy({
    schema: "quillframe_user_taste_auto_activation_policy_v1",
    policy_id: "default",
    enabled: true,
    policy_version: 2,
    source_kinds: ["feedback", "corpus"],
    authorization_ref: "studio_user_explicit_authorization",
    authorized_at: "2026-08-28T00:00:00Z",
    revoked_at: null,
    authority_scope: "user_taste_only",
    framework_write: false,
    canon_write: false,
    fingerprint: hash,
  });
  assert.equal(policy.enabled, true);
  const preference = {
    hypothesis_id: "UT-1", scope: "user_taste", project_id: null, dimension: "dialogue",
    statement: "Prefer dialogue with live resistance.", mechanism: "counter-goal pressure", state: "contested",
    confidence: 0.8, applicability: {}, evidence_ids: ["EV-1"], contradiction_ids: ["EV-2"], version: 4,
  };
  const transition = taste.parseUserTasteTransition({
    preference,
    receipt: { schema: "quillframe_user_taste_activation_receipt_v1", hypothesis_id: "UT-1", action: "pause",
      before_version: 3, after_version: 4, reason: "new contradiction", authority: false },
  }, { hypothesis_id: "UT-1", expected_version: 3, action: "pause", reason: "new contradiction" });
  assert.equal(transition.preference.state, "contested");
  assert.throws(() => taste.parseUserTasteTransition({ ...transition, receipt: { ...transition.receipt, after_version: 5 } },
    { hypothesis_id: "UT-1", expected_version: 3, action: "pause", reason: "new contradiction" }), /transition_invalid/);
});

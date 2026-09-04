import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (relative) => fs.readFileSync(new URL(`../${relative}`, import.meta.url), "utf8");
const start = read("src/routes/Start.tsx");
const manuscript = read("src/routes/Manuscript.tsx");
const review = read("src/routes/Review.tsx");
const context = read("src/routes/Context.tsx");
const appShell = read("src/AppShell.tsx");
const settings = read("src/routes/Settings.tsx");
const styles = read("src/styles/authoring-product.css");
const plan = read("src/routes/Plan.tsx");
const story = read("src/routes/Story.tsx");
const learning = read("src/routes/Learning.tsx");
const runtime = read("src/routes/Runtime.tsx");
const publication = read("src/routes/Publication.tsx");
const webManifest = JSON.parse(read("public/manifest.webmanifest"));

test("Start and Binder consume canonical Core registries", () => {
  assert.match(start, /project\.list/);
  assert.match(manuscript, /document\.list/);
  assert.match(manuscript, /document\.open/);
  assert.match(manuscript, /document\.revisions\.list/);
});

test("Manuscript exposes autosave status, proposal authority, conflict alert and accessible editor", () => {
  assert.match(manuscript, /aria-live="polite"/);
  assert.match(manuscript, /aria-label=\{zh\(\) \? "正文" : "Manuscript text"\}/);
  assert.match(manuscript, /authority_class: "proposal"/);
  assert.match(manuscript, /revision conflict/);
  assert.match(manuscript, /role="alert"/);
});

test("Review consumes exact evidence and keeps lifecycle operations separate", () => {
  assert.match(review, /candidate\.review\.get/);
  assert.match(review, /candidate\.visible\.get/);
  assert.match(review, /released\(\)\.content/);
  assert.doesNotMatch(review, /detail\(\)\.diff\?\.diff/);
  assert.match(review, /reviewRequestGeneration/);
  assert.match(review, /selectedId\(\) !== candidateId/);
  assert.match(review, /candidate\.accept/);
  assert.match(review, /candidate\.reject/);
  assert.match(review, /candidate\.revision\.request/);
  assert.match(review, /evidence\.surface_rules/);
  assert.match(review, /quillframe_production_release_v2/);
  assert.match(review, /Accepted ✓/);
  assert.match(review, /Settlement unconfirmed/);
  assert.match(review, /accepted=\{acceptance\(\) \? "true" : detail\(\)\.candidate\.persisted_status === "accepted" \? "unknown" : "false"\}/);
  assert.match(review, /settled=\{settlement\(\)\?\.status === "settled" \? "true" : "unknown"\}/);
  assert.match(review, /settlement\.preflight/);
  assert.match(review, /settlement\.apply/);
  assert.match(review, /parseReviewSettlementPreflight/);
  assert.match(review, /expected_before_fingerprint: verifiedPreflight\.expected_before_fingerprint/);
  const acceptFlow = review.slice(review.indexOf("const accept ="), review.indexOf("const reject ="));
  assert.match(acceptFlow, /setAcceptance\(accepted\)/);
  assert.match(acceptFlow, /persisted_status: "accepted"/);
  assert.doesNotMatch(acceptFlow, /await load\(\)/);
});

test("Review restores Core receipts and blocks settlement without a proven chapter association", () => {
  assert.match(review, /document\.list/);
  assert.match(review, /resolveReviewSettlementTarget/);
  assert.doesNotMatch(review, /chapter:\$\{[^}]*document_id\}/);
  assert.doesNotMatch(review, /onInput=\{[^}]*setSettleTarget/);
  assert.match(review, /inspector\.receipts\.list/);
  assert.match(review, /recoverReviewLifecycleReceipts/);
  assert.match(review, /parseReviewAcceptanceResult/);
  assert.match(review, /parseReviewSettlementResult/);
  assert.match(review, /projectId\(\) !== requestedProject/);
  assert.match(review, /createEffect\(on\(\[projectId, operations\]/);
  assert.doesNotMatch(review, /localStorage|sessionStorage/);
  assert.doesNotMatch(review, /latest_revision\??\.content/);
});

test("Review shows the settlement proposal before a separate author confirmation and binds its fingerprint", () => {
  const prepare = review.slice(review.indexOf("const prepareSettlement"), review.indexOf("const settle ="));
  assert.match(prepare, /settlement\.preflight/);
  assert.doesNotMatch(prepare, /invokeBridge(?:<[^>]+>)?\("settlement\.apply"/);
  assert.match(review, /!settlementConsent\(\)/);
  assert.match(review, /narrative_proposal/);
  assert.match(review, /reader_observations/);
  assert.match(review, /expected_preflight_fingerprint: verifiedPreflight\.preflight_fingerprint/);
  assert.match(review, /setSettlementPreflight\(undefined\); setSettlementConsent\(false\)/);
});

test("Plan and Story use Core versioned plans, explicit reader intent and authority-labeled facts", () => {
  assert.match(plan, /"plan\.inspect"/);
  assert.match(plan, /"plan\.save"/);
  assert.match(plan, /expected_version: saved\(\)\?\.version \?\? 0/);
  assert.match(plan, /requestVersion === editVersion/);
  assert.match(plan, /reader_intent: \{ \.\.\.readerIntent\(\) \}/);
  assert.match(plan, /expectation_refs:/);
  assert.match(story, /"story\.inspect"/);
  assert.match(story, /"reader\.expectations\.inspect"/);
  assert.match(story, /AuthorityLabel/);
  assert.match(story, /source_state === "stale"/);
  assert.match(story, /source_chapter_id/);
  assert.match(story, /<SourceEvidence source=\{item\}/);
  assert.doesNotMatch(`${plan}\n${story}`, /localStorage|sessionStorage|innerHTML=/);
});

test("Learning separates source-bound feedback, model review, activation and next-run selection", () => {
  for (const operation of ["learning.feedback.observe", "learning.feedback.execute", "learning.feedback.resume", "learning.preference.review", "learning.preference.list"]) assert.ok(learning.includes(operation));
  assert.match(learning, /source_type: sourceType\(\)/);
  assert.match(learning, /candidate_fingerprint: candidate\.candidate_fingerprint/);
  assert.match(learning, /expected_version: preference\.version/);
  assert.match(learning, /user_authorized: true/);
  assert.match(learning, /activationConsent/);
  assert.match(appShell, /selected_preference_ids: selectedPreferenceIds/);
  assert.doesNotMatch(learning, /localStorage|sessionStorage/);
});

test("Publication only initiates browser download after actual-byte verification and a current binding check", () => {
  const download = publication.slice(publication.indexOf("const downloadArtifact"), publication.indexOf("return ("));
  assert.ok(download.indexOf("await parsePublicationArtifact") < download.indexOf("URL.createObjectURL"));
  assert.match(download, /await parsePublicationArtifact[\s\S]*?if \(!current\(\)\) return;[\s\S]*?URL\.createObjectURL/);
  assert.match(download, /link\.download = verified\.data\.filename/);
  assert.match(download, /URL\.revokeObjectURL/);
  assert.match(publication, /current_acceptance_id/);
});

test("Context Inspector exposes loaded versus considered semantics and textual authority", () => {
  assert.match(context, /ACTUALLY LOADED INTO THIS STAGE/);
  assert.match(context, /MODEL CONSIDERED RELEVANT/);
  assert.match(context, /<AuthorityLabel value=\{item\.authority\}/);
  assert.match(context, /private_chain_of_thought_exposed/);
});

test("AI Dock has keyboard access, explicit production execution and no self-advancing progress timer", () => {
  assert.match(appShell, /event\.key\.toLowerCase\(\) === "i"/);
  assert.match(appShell, /aria-controls="qf-ai-dock"/);
  assert.match(appShell, /author\.run\.start/);
  assert.match(appShell, /author\.run\.execute/);
  assert.match(appShell, /author\.run\.status/);
  assert.match(appShell, /current_request/);
  assert.doesNotMatch(appShell, /setInterval|setTimeout\([^)]*RunProgress/);
});

test("AI Dock keeps cancellation available during a long execution request and validates the returned run", () => {
  assert.match(appShell, /disabled=\{controlBusy\(\) \|\| !supported\(\)\.includes\("author\.run\.cancel"\)\}/);
  assert.match(appShell, /executionPending\(\)/);
  assert.match(appShell, /executionRequest === executionGeneration/);
  assert.match(appShell, /run_cancel_binding_invalid/);
  const cancel = appShell.slice(appShell.indexOf("const cancelRun"), appShell.indexOf("const go ="));
  assert.doesNotMatch(cancel, /if \([^\n]*aiBusy\(\)/);
  assert.match(cancel, /user_authorized: true/);
});

test("AI Dock presents persisted execution counters and suppresses resumption for a bound active lease or failed gate", () => {
  assert.match(appShell, /projectExecutionJournal\(runEvidence\(\), \{/);
  assert.match(appShell, /document_id: currentDocument\(\) \?\? ""/);
  const journal = appShell.slice(appShell.indexOf('<section class="qf-ai-journal"'), appShell.indexOf('<Show when={workflowEvents().length}>'));
  for (const marker of ["confirmed_call_count", "dispatched_call_count", "model_call_budget", "pending_calls", "active_executor", "unconfirmed", "executor_interrupted", "budget_exhausted", "latest_stage_failure", "semantic_output_invalid", "latest_gate_rejection", "failed_gate"]) assert.ok(journal.includes(marker), marker);
  assert.match(journal, /call\.stage_key/);
  assert.doesNotMatch(journal, /JSON\.stringify|invokeBridge|job\.payload|result\.payload|role="progressbar"/);
  const otherControls = appShell.slice(appShell.indexOf("const startRun ="), appShell.indexOf("const resumeRun ="))
    + appShell.slice(appShell.indexOf("const cancelRun ="), appShell.indexOf("const go ="));
  assert.doesNotMatch(otherControls, /executionJournal/);
  const resume = appShell.slice(appShell.indexOf("const resumeRun ="), appShell.indexOf("const cancelRun ="));
  assert.match(resume, /if \([^\n]*executionJournal\(\)\?\.active_executor === true[^\n]*\) return;/);
  assert.match(resume, /if \([^\n]*executionJournal\(\)\?\.run_status === "failed_gate"\) return;/);
  assert.match(journal, /executionRoleLabel\(rejection\(\)\.mechanism\)/);
  assert.match(journal, /未通过；先处理阻断原因，再注册新运行/);
  assert.match(journal, /did not pass; resolve the blocker, then register a new run/);
  assert.doesNotMatch(journal, /repair_routes|rejection\(\)\.message|rejection\(\)\.detail/);
  assert.ok(resume.indexOf("executionJournal()") < resume.indexOf('"author.run.resume"'));
  assert.match(resume, /if \(!current\(\)\) return;/);
  assert.match(resume, /run_resume_binding_invalid/);
  assert.match(appShell, /!executionJournal\(\) && !workflowEvents\(\)\.length/);
});

test("Runtime selection verifies persisted run and chapter evidence before changing the viewing context", () => {
  assert.match(runtime, /parseRuntimeInspectorList/);
  assert.match(runtime, /"查看这次运行"/);
  assert.match(runtime, /\["DRAFT", "REVISE"\]\.includes/);
  const selection = runtime.slice(runtime.indexOf("const selectRun ="), runtime.indexOf("createEffect(on("));
  assert.match(selection, /generation === selectionGeneration/);
  assert.match(selection, /projectId\(\) === requestedProject/);
  assert.match(selection, /studio\.projectId\(\) === requestedProject/);
  assert.match(selection, /runListProjectId !== requestedProject/);
  assert.match(selection, /"author\.run\.status"[\s\S]*?if \(!current\(\)\) return;[\s\S]*?"chapter\.list"[\s\S]*?if \(!current\(\)\) return;/);
  assert.ok(selection.indexOf("resolveRuntimeRunSelection") < selection.indexOf("studio.setChapterId"));
  assert.ok(selection.indexOf("studio.setChapterId") < selection.indexOf("studio.setLastRunId"));
  assert.ok(selection.indexOf("studio.setLastRunId") < selection.indexOf("navigate("));
  assert.match(selection, /registeredInStudio\(\)[\s\S]*?await studio\.refreshChapters\(\);[\s\S]*?if \(!current\(\)\) return;/);
  assert.match(runtime, /onCleanup\(\(\) => \{ disposed = true; loadGeneration \+= 1; selectionGeneration \+= 1;/);
  assert.doesNotMatch(runtime, /author\.run\.(?:start|execute|resume|cancel)|candidate\.accept|localStorage|sessionStorage/);
  assert.match(appShell, /createEffect\(on\(\(\) => studio\.lastRunId\(\), \(selectedRunId\) => \{\s*if \(selectedRunId !== run\(\)\?\.run_id\) resetRunView\(\);/);
});

test("AI & Models remains endpoint-plus-token and token is never persisted by Settings", () => {
  assert.match(settings, /Endpoint \+ Access Token/);
  assert.match(settings, /model\.service\.add/);
  assert.match(settings, /model\.service\.list/);
  assert.match(settings, /type="password"/);
  assert.match(settings, /Production model/);
  assert.match(settings, /studio\.setSelectedModel/);
  assert.match(settings, /Automatic selection \(Core default\)/);
  assert.doesNotMatch(settings, /(?:localStorage|sessionStorage)\.(?:setItem|getItem|removeItem|clear)\s*\(/);
  assert.doesNotMatch(settings, /indexedDB\.(?:open|deleteDatabase)\s*\(/);
});

test("responsive authoring CSS encodes touch and focus-first constraints", () => {
  assert.match(styles, /min-block-size: 44px/);
  assert.match(styles, /@media \(max-width: 1080px\)/);
  assert.match(styles, /@media \(max-width: 760px\)/);
  assert.match(styles, /\.qf-manuscript-editor \{ order: 1;/);
  assert.match(styles, /prefers-reduced-motion/);
});

test("manuscript layout responds to content width and run rows cannot trap text in a 24px grid column", () => {
  assert.match(styles, /container-name: qf-manuscript/);
  assert.match(styles, /container-type: inline-size/);
  assert.match(styles, /@container qf-manuscript \(max-width: 1119px\)/);
  const narrow = styles.slice(styles.indexOf("@container qf-manuscript (max-width: 760px)"), styles.indexOf("@media (prefers-reduced-motion"));
  assert.match(narrow, /\.qf-manuscript-workspace \{ display: flex; flex-direction: column/);
  assert.match(narrow, /\.qf-manuscript-editor \{ order: 1/);
  assert.match(narrow, /\.qf-binder \{ order: 2/);
  assert.match(narrow, /\.qf-revision-rail \{ display: block; order: 3/);
  const progressRow = styles.match(/\.qf-run-progress li \{([^}]+)\}/)?.[1] ?? "";
  assert.match(progressRow, /display: flex/);
  assert.match(progressRow, /grid-template-columns: none/);
  assert.doesNotMatch(progressRow, /24px 1fr/);
});

test("Studio web manifest references only present Quillframe assets", () => {
  for (const icon of webManifest.icons ?? []) {
    assert.match(icon.src, /^\/quillframe-/);
    assert.equal(fs.existsSync(new URL("../public" + icon.src, import.meta.url)), true);
  }
});

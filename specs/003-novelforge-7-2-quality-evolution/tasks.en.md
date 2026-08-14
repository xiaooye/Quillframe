# Tasks · NovelForge 7.2 Author Control + Quality Evolution

## Phase 0 · Baseline
- [x] T001 Freeze `main@5e8f586b...`.
- [x] T002 Read 7.1 spec/plan/tasks and Self-Improvement Protocol.
- [x] T003 Create the 7.2 feature branch and spec/plan/tasks.
- [ ] T004 Convert the stale 7.1 checklist into a historical completion ledger.

## Phase 1 · Common Findings
- [ ] T101 Add `quality/__init__.py`.
- [ ] T102 Add `quality/findings.py` + self-test.

## Phase 2 · Reader Panel
- [ ] T201 Add `quality/reader_panel.py` single-candidate job builder.
- [ ] T202 Add A/B pairwise + per-persona order swap.
- [ ] T203 Add disagreement / templating / first-shown-bias diagnostics.
- [ ] T204 Make panel diagnostic status explicitly distinct from mandatory independent semantic review.

## Phase 3 · Quality Evolution
- [ ] T301 Add `quality/quality_evolution.py` SQLite lifecycle.
- [ ] T302 Candidate/comparison fingerprints + result consume-once.
- [ ] T303 Repair-owner + plateau stopping.
- [ ] T304 Resume/idempotency/illegal-winner self-test.

## Phase 4 · Context Inspector
- [ ] T401 Add `harness/context_inspector.py`.
- [ ] T402 Authority/stage/relevance/pin inspection.
- [ ] T403 Protected edit → proposal; direct Canon mutation forbidden.
- [ ] T404 Regression/hidden-gold stage-isolation self-test.

## Phase 5 · Tiered Memory
- [ ] T501 Add `harness/memory_tiers.py`.
- [ ] T502 Hard budget + whole-item-or-skip.
- [ ] T503 Event/participant relevance + pin-first promotion.
- [ ] T504 Provenance + derived authority=false self-test.

## Phase 6 · Character Integrity
- [ ] T601 Add `quality/character_integrity.py`.
- [ ] T602 Bounded `artifact_audit` packaging.
- [ ] T603 Forbidden-context scan.
- [ ] T604 Result → evidence-chained normalized findings.

## Phase 7 · State Graph
- [ ] T701 Add `quality/state_graph.py`.
- [ ] T702 Node/edge normalization + stable-field diff.
- [ ] T703 Transition-evidence binding.
- [ ] T704 Before/after finding + derived-authority self-test.

## Phase 8 · CLI / Release Contracts
- [ ] T801 Update `novelforge.py` to 7.2.0 with new routers/doctor/self-test.
- [ ] T802 Update `HARNESS_MANIFEST.yaml` with 7.2 quality/control modules.
- [ ] T803 Extend reusable CI with all 7.2 deterministic self-tests.
- [ ] T804 Update only necessary machine/Harness version contracts; do not redo customer docs.

## Phase 9 · Verification
- [ ] T901 Branch compile/hygiene green.
- [ ] T902 Existing 7.1 deterministic contracts green.
- [ ] T903 7.2 self-tests green.
- [ ] T904 Bundle double-build reproducible.
- [ ] T905 Normal CI `model_execution=false`.
- [ ] T906 Draft PR created.
- [ ] T907 Exact candidate commit CI green.

## Release Follow-up (not executed in this run)
- [ ] F001 Determine exact 7.2 commit after merge/acceptance.
- [ ] F002 Build and record the new immutable bundle fingerprint.
- [ ] F003 Migrate consuming projects in separate dependency-migration runs.
- [ ] F004 Verify Canon/story state unchanged after consumer migration.

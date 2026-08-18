# Tasks · NovelForge 7.2 Author Control + Quality Evolution

> Status: implementation is landing directly on `main` after explicit user direction to drop the feature-branch/PR requirement. The final release gate remains **CI + deterministic bundle on the exact final HEAD**.

## Phase 0 · Baseline
- [x] T001 Freeze the post-7.1 / Story Loom development baseline.
- [x] T002 Read the 7.1 spec/plan/tasks and Self-Improvement Protocol.
- [x] T003 Create 7.2 spec/plan/tasks, then move implementation directly to `main` per user instruction.
- [x] T004 Identify the stale 7.1 checklist; repair the historical ledger separately.

## Phase 1 · Common Findings
- [x] T101 Add `quality/__init__.py`.
- [x] T102 Add `quality/findings.py` + fingerprint/tamper self-test.

## Phase 2 · Reader Panel
- [x] T201 Add `quality/reader_panel.py` single-candidate job builder.
- [x] T202 Add A/B pairwise + per-persona order swap.
- [x] T203 Add disagreement / templating / first-shown-bias diagnostics.
- [x] T204 Make panel diagnostics explicitly distinct from mandatory independent semantic review.

## Phase 3 · Quality Evolution
- [x] T301 Add `quality/quality_evolution.py` SQLite lifecycle.
- [x] T302 Candidate/comparison fingerprints + result consume-once.
- [x] T303 Repair-owner + plateau stopping.
- [x] T304 Resume/idempotency/illegal-winner self-test and fix comparison replay ordering.

## Phase 4 · Context Inspector
- [x] T401 Add `harness/context_inspector.py`.
- [x] T402 Authority/stage/relevance/pin inspection.
- [x] T403 Protected edit → proposal; direct Canon mutation forbidden.
- [x] T404 Regression/hidden-gold stage-isolation self-test.

## Phase 5 · Tiered + Editable Memory
- [x] T501 Add `harness/memory_tiers.py`.
- [x] T502 Hard budget + whole-item-or-skip.
- [x] T503 Event/participant relevance + pin-first promotion.
- [x] T504 Provenance + derived authority=false self-test.
- [x] T505 Add durable `harness/memory_bank.py`.
- [x] T506 Protected accepted/locked edits become proposals; editable entries use exact before-fingerprint guards.
- [x] T507 Proposal memory defaults to `never` injection stage so future/contested state cannot silently prime drafting.
- [x] T508 Export Memory Bank as a non-authoritative Context Manifest view with pin/priority controls.

## Phase 6 · Character Integrity
- [x] T601 Add `quality/character_integrity.py`.
- [x] T602 Bounded `artifact_audit` packaging.
- [x] T603 Forbidden-context scan.
- [x] T604 Result → evidence-chained normalized findings.

## Phase 7 · State Graph
- [x] T701 Add `quality/state_graph.py`.
- [x] T702 Node/edge normalization + stable-field diff.
- [x] T703 Transition-evidence binding.
- [x] T704 Before/after finding + derived-authority self-test.

## Phase 8 · Multi-pass Revision + CLI / Release Contracts
- [x] T801 Add `quality/revision_orchestrator.py` narrow-pass planning / failure isolation / finding aggregation.
- [x] T802 Route surface clusters to whole-scene regeneration and reader flatness to Reader Pressure + Scene Simulation.
- [x] T803 Update `novelforge.py` to 7.2.0 with Reader/Quality/Context/Memory/Revision routers/doctor/self-test.
- [x] T804 Update `HARNESS_MANIFEST.yaml` with 7.2 author-control/quality contracts.
- [x] T805 Extend reusable CI with all 7.2 deterministic self-tests, including Memory Bank and Revision Orchestrator.
- [x] T806 Update `SKILL.md`, `SKILL.en.md`, and `SKILL.zh-CN.md` to the 7.2 runtime contract without redoing customer-facing docs.
- [x] T807 Update `project_sdk.py` so new projects default to Framework 7.2.0 and declare the quality-control scaffold.

## Phase 9 · Verification
- [x] T901 First 7.2 tranche (Reader/Context/Evolution/Character/State) exact-commit CI green.
- [x] T902 Existing 7.1 deterministic contracts remained green in the first 7.2 verification.
- [x] T903 First-tranche bundle double-build reproducible and Normal CI `model_execution=false`.
- [ ] T904 Expanded Memory Bank + Revision Orchestrator exact final HEAD compile/hygiene green.
- [ ] T905 Expanded full 7.2 self-tests + 7.1 regressions green.
- [ ] T906 Exact final HEAD bundle double-build reproducible + fingerprint recorded.
- [ ] T907 Exact final HEAD Normal CI `model_execution=false`.

## Release Follow-up
- [ ] F001 Record the final release commit + immutable bundle fingerprint after final green HEAD.
- [ ] F002 Migrate consuming projects only if needed later; do not touch the stopped legacy project repository in this run.

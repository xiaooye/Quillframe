# Plan · NovelForge 7.2 Author Control + Quality Evolution

## Strategy

7.2 keeps the 7.1 `deterministic shell + optional semantic capability` architecture. No new feature may silently invoke a model. Reader Panel, Character Integrity and revision quality passes package/validate/aggregate typed work; actual semantic execution still obeys Host Capability, Runtime Routing, and independent-session rules.

Primary loop:

`observe → classify → repair owning mechanism → compare → keep/discard → regression → stop/continue`

—not “ask more agents for scores.”

Per explicit user direction, implementation lands directly on `main`; there is no PR/feature-branch release gate. The replacement gate is stricter: **exact final HEAD + deterministic CI + deterministic bundle**.

## Phase 0 · Baseline Audit

- Freeze the post-7.1 / Story Loom development baseline.
- Reconcile the 7.1 specification with implemented modules.
- Convert the stale 7.1 checkbox list into a historical completion ledger.
- Do not redo Story Loom/customer-facing docs.

## Phase 1 · Common Quality Finding Contract

Add `quality/findings.py` with normalized severity/category/repair owner, candidate evidence, authority evidence, source refs, confidence, stable fingerprint, and self-test.

## Phase 2 · Reader Simulation Panel

Add `quality/reader_panel.py` with default reading-behavior personas, single-candidate and A/B builders, per-persona order swap, validated-result aggregation, disagreement/templating/first-shown-bias diagnostics, explicit `independent_gate=false`, and self-test. Reuse semantic kind `external_review`.

## Phase 3 · Durable Quality Evolution

Add `quality/quality_evolution.py` with SQLite runs/candidates/comparisons, exact candidate fingerprints, comparison-result consume-once, exact replay idempotency, repair-owner tracking, no-gain plateau detection, illegal winner rejection, and crash/resume tests.

## Phase 4 · Context Inspector

Add `harness/context_inspector.py` exposing authority/stage/relevance/pin state and low-authority overlays for pin/unpin/priority/hide/invalidate-derived. Protected-authority edits become proposals. Validate pre-draft/post-draft/reviewer isolation. Never write Project Canon.

## Phase 5 · Tiered + Durable Editable Memory

1. Add `harness/memory_tiers.py` with `hot | working | archival`, provenance validation, hard budgets, whole-item-or-skip, current-event/participant relevance boosts, pin-first ordering, derived `authority=false`, invalidation metadata, and self-test.
2. Add `harness/memory_bank.py` with durable SQLite entries, explicit authority classes, exact before-fingerprint edit guards, protected accepted/locked edit→proposal semantics, pin/priority controls, and Context Manifest export.
3. Proposal memory defaults to `never` injection stage so future/contested state cannot silently enter writer pre-draft context.
4. Free-text semantic consolidation remains a separate bounded semantic job; deterministic memory code never invents Canon summaries.

## Phase 6 · Character Integrity

Add `quality/character_integrity.py` with bounded character snapshot + scene excerpt, agenda/knowledge/voice/relationship/spatial-task state, `artifact_audit` semantic job packaging, forbidden-context scan, result normalization into common findings, and self-test.

## Phase 7 · State Graph Audit

Add `quality/state_graph.py` with scene snapshot node/edge/transition normalization, stable-attribute diff, transition-evidence binding, unexplained-change findings, before/after evidence chains, derived `authority=false`, and self-test. Complex narrative plausibility remains semantic work.

## Phase 8 · Multi-pass Revision Orchestration

Add `quality/revision_orchestrator.py`:

- plan narrow continuity/character/reader/surface/research passes;
- isolate missing/failing pass execution;
- consume normalized findings and deduplicate equivalent issues;
- preserve evidence/diagnostics;
- build a repair queue by owning mechanism;
- route clustered surface failures to scene regeneration;
- route SAFE-BUT-FLAT / reader-grip failures to Reader Pressure + Scene Simulation;
- never treat a reviewer/panel pass as Canon authority.

## Phase 9 · CLI / Manifest / Project SDK / CI

- Update `novelforge.py` to 7.2.0 and route reader-panel, quality-evolution, revision-orchestrator, context-inspect, memory-tiers, memory-bank, character-integrity and state-graph.
- Extend doctor/self-test across every 7.2 module.
- Update `HARNESS_MANIFEST.yaml` and `SKILL*` contracts.
- Update `project_sdk.py` so new projects default to 7.2.0 and advertise the quality-control scaffold.
- Extend reusable CI with all new deterministic self-tests while retaining all 7.1 regressions.
- Preserve deterministic bundle reproducibility and `model_execution=false` in normal CI.

## Phase 10 · Verification

1. Run exact-HEAD compile and repository hygiene.
2. Keep all existing 7.1 contracts green.
3. Run every 7.2 self-test, including Memory Bank and Revision Orchestrator.
4. Run top-level `novelforge.py self-test`.
5. Verify two Framework bundle builds are byte/fingerprint identical and tamper detection remains active.
6. Assert normal CI performs no model execution.
7. Repair failures in the owning module; do not weaken the gate.
8. Only call the final exact HEAD release-ready after all required workflows are green.

## Release Follow-up

- Record the exact final 7.2 commit and deterministic bundle fingerprint after green verification.
- Do not migrate the stopped legacy consumer repository in this run.
- Any future maintained consumer migration remains a separate dependency migration and must not mutate story Canon/state.

## Rollback

Framework rollback base: `5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`. Individual 7.2 mechanisms are additionally isolated by their introducing commits and deterministic self-tests, so a failed mechanism can be reverted without inventing replacement story state.

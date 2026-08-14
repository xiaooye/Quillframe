# Plan · NovelForge 7.2 Author Control + Quality Evolution

## Strategy

7.2 keeps the 7.1 `deterministic shell + optional semantic capability` architecture. This release adds no hidden model calls. Reader Panel and Character Integrity only package, validate, aggregate, and persist typed work; actual semantic execution still obeys Host Capability, Runtime Routing, and independent-session rules.

Primary loop:

`observe → classify → repair owning mechanism → compare → keep/discard → regression → stop/continue`

—not “ask more agents for scores.”

## Phase 0 · Baseline Audit

- Freeze `main@5e8f586b...`.
- Reconcile the 7.1 specification with implemented modules and the published consumer lock.
- Convert the stale 7.1 checkbox list into a historical completion ledger.
- Do not redo Story Loom/customer-facing docs.

## Phase 1 · Common Quality Finding Contract

Add `quality/findings.py` with normalized severity/category/repair owner, candidate evidence, authority evidence, source refs, confidence, stable fingerprint, and self-test.

## Phase 2 · Reader Simulation Panel

Add `quality/reader_panel.py` with default reading-behavior personas, single-candidate and A/B builders, order-swap metadata, validated-result aggregation, disagreement/templating/first-shown-bias diagnostics, explicit `independent_gate=false`, and self-test. Reuse semantic kind `external_review`.

## Phase 3 · Durable Quality Evolution

Add `quality/quality_evolution.py` with SQLite runs/candidates/comparisons, start/add-candidate/record-comparison/status commands, exact candidate fingerprints, comparison result consume-once, repair-owner tracking, no-gain plateau detection, illegal transition/winner rejection, and crash/resume/idempotency self-test.

## Phase 4 · Context Inspector

Add `harness/context_inspector.py` exposing authority/stage/relevance/pin state and low-authority overlays for pin/unpin/priority/hide/invalidate-derived. Protected-authority edits become proposals. Validate pre-draft/post-draft/reviewer isolation. Never write Project Canon.

## Phase 5 · Tiered Derived Memory

Add `harness/memory_tiers.py` with `hot | working | archival`, provenance validation, hard budgets, whole-item-or-skip, current-event and participant relevance boosts, pin-first ordering, derived `authority=false`, invalidation metadata, and self-test. Free-text semantic consolidation remains a separate bounded semantic job.

## Phase 6 · Character Integrity

Add `quality/character_integrity.py` with bounded character snapshot + scene excerpt, agenda/knowledge/voice/relationship/spatial-task state, `artifact_audit` semantic job packaging, forbidden-context scan, result normalization into common findings, and self-test.

## Phase 7 · State Graph Audit

Add `quality/state_graph.py` with scene snapshot node/edge normalization, stable-attribute diff, transition-evidence binding, unexplained-change findings, before/after evidence chains, derived `authority=false`, and self-test. Complex narrative plausibility remains semantic work.

## Phase 8 · CLI / Manifest / CI

Update `novelforge.py` to 7.2.0 and route reader-panel, quality-evolution, context-inspect, memory-tiers, character-integrity, and state-graph. Extend doctor/self-test. Update `HARNESS_MANIFEST.yaml`, reusable CI, and only the necessary machine/Harness version contracts. Preserve deterministic bundle reproducibility.

## Phase 9 · Verification

1. Push branch and run CI.
2. Keep all existing 7.1 contracts green.
3. Run every new 7.2 self-test.
4. Verify double bundle build fingerprint equality.
5. Assert normal CI performs no model execution.
6. Repair failures in the owning module.
7. Open a draft PR for review.
8. Only call the result a release candidate after exact-commit CI is green; do not auto-merge.

## Phase 10 · Release Follow-up (not executed in this run)

After merge/acceptance, determine the exact 7.2 commit, build a new immutable bundle/fingerprint, then migrate consumer locks in a separate dependency-migration run. Framework migration must not mutate story Canon/state.

## Rollback

- Framework branch rollback base: `5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`.
- Existing consumer remains pinned to `d9126b...`, so a failed 7.2 branch cannot contaminate the current novel runtime.

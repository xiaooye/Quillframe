# Specification · NovelForge 7.2 Author Control + Quality Evolution

## Baseline

- Previous release: NovelForge 7.1.0
- Framework development baseline: `5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`
- Known 7.1 release commit used by the historical consumer: `d9126b2ac39abce0554d83ad74a0ded97017b2a2`
- Rollback: development baseline commit
- Change class: Framework release / structural feature
- Primary mode: `SYSTEM-IMPROVE`

## Problem

7.1 established typed capabilities, durable learning, provenance, independent semantic execution, immutable bundles, and strict Canon boundaries. The next production gap is not “more agents”; it is **author-visible control plus a measurable, recoverable quality loop**.

7.2 addresses:

1. no first-class simulated reader-reaction panel or reader-disagreement signal;
2. no resumable candidate-evolution ledger with pairwise comparison and plateau detection;
3. no direct inspection of exactly which context was injected, why, or at what stage;
4. no durable author-editable memory bank that preserves Canon authority boundaries;
5. no common evidence-chained finding contract for character/continuity/quality audits;
6. no event-relevance + tiered derived-memory budget layer;
7. no unified narrow-pass revision report that routes failures back to the owning mechanism.

## External mechanism evidence

External systems generate `adopt | adapt | reject` candidates only; they are not dependencies:

- AuthorAgent `47e9570fb96b9d151a3b1f9c22e3a365eab9bd9c`: reader/beta-reader signals, narrow revision passes, tiered memory.
- autonovel `d165f267a0ffd34f3b0a70a8a72ac38cb8e4a542`: reader consensus/disagreement, pairwise comparison, iterative revision, plateau stopping.
- NovelClaw `226d50d3ec284c9cc037c47eb14af39505f9ed74`: author-visible workspace, memory banks, runs, storyboard, character/world control surfaces.
- StoryWriter `08c32d74ce08b46a762951c7f2235772022baa77` / arXiv:2506.16445: event-based outline and current-event-aware history compression.
- MAGNET + ATLAS / arXiv:2607.00918: character actions grounded in goals/shared world state and graph-based world-state verification.
- StoryState / arXiv:2602.01305: explicit editable story state without treating implicit model memory as authority.

## Goals

### G1 · Reader Simulation Panel

`quality/reader_panel.py` must:
- use reading-behavior personas rather than demographic profiling by default;
- support single-candidate reactions and A/B pairwise comparison;
- perform swapped visible order for pairwise diagnostics;
- aggregate continue intent, confusion, attention loss, favorite/stumble, reward and emotion signals;
- detect persona disagreement, templated-reason/judge collapse and first-shown bias;
- reuse bounded `external_review` jobs without claiming same-model personas are independent reviewers.

### G2 · Durable Quality Evolution

`quality/quality_evolution.py` implements:

`baseline → candidate → comparison → keep/discard → repair owner → next candidate → plateau/complete`

Requirements:
- SQLite run/candidate/comparison ledger;
- candidate/result fingerprint binding;
- exact replay idempotency + logical result consume-once;
- winner restricted to the compared candidates or no-decision/tie;
- repair-owner tracking;
- no-gain plateau stopping;
- no Canon or Framework-write authority.

### G3 · Context Inspector

`harness/context_inspector.py` must expose item id/class/source/authority/inclusion reason/stage/relevance/pin state and distinguish:

`locked | accepted | active_plan | review | proposal | runtime | learning | corpus | derived`

It supports low-authority pin/unpin/priority/hide/invalidate controls. Protected edits become proposals. Regression/hidden-gold material cannot leak into `writer_pre_draft`.

### G4 · Tiered Derived Memory + Event Relevance

`harness/memory_tiers.py` must:
- consume already-derived or project-provided items rather than autonomously summarize Canon;
- allocate `hot | working | archival` under hard budgets;
- prioritize explicit pin > current-event overlap > participant overlap > relevance/priority;
- use whole-item-or-skip budgeting;
- require source refs/fingerprints for derived items;
- enforce derived `authority=false`.

### G5 · Durable Editable Memory Bank

`harness/memory_bank.py` adds the author-editable storage/control surface requested by 7.2:
- durable SQLite entries grouped by context/character/relationship/thread/style/learning/runtime/corpus/derived bank;
- the same explicit authority classes used by Context Inspector;
- `locked` / `accepted` rows are protected reference snapshots, not mutable Canon copies;
- editing protected rows creates a proposal child and leaves the original unchanged;
- editable entries require exact before-fingerprint matching;
- proposal entries default to `never` injection stage so contested/future data cannot silently prime drafting;
- pin/priority affect retrieval only;
- exported Context Manifest remains non-authoritative.

### G6 · Character Integrity + Evidence-Chained Findings

`quality/findings.py` defines the normalized finding contract. `quality/character_integrity.py` packages bounded character audits for agenda alignment, knowledge boundary, voice drift, relationship position, spatial/task state, and surprise-within-consistency.

Findings carry candidate evidence, authority evidence, repair owner, severity, confidence, source refs, and a stable fingerprint. Writer private reasoning and hidden gold remain excluded.

### G7 · Scene / World State Graph Audit

`quality/state_graph.py` provides a derived verification view:
- typed nodes/edges/transitions;
- stable-field contradiction detection;
- unexplained nonstable change warnings;
- transition/event evidence may explain a change;
- before/after evidence chains;
- graph state never becomes a second Canon authority.

### G8 · Multi-pass Revision Orchestrator

`quality/revision_orchestrator.py` must:
- plan narrow continuity / character / reader / surface / research passes;
- skip unavailable passes without aborting other eligible passes;
- aggregate and deduplicate normalized findings;
- preserve diagnostics/provenance;
- route findings to the owning repair mechanism;
- route surface clusters to whole-scene regeneration rather than endless local patching;
- route SAFE-BUT-FLAT / reader-grip failure to Reader Pressure + Scene Simulation rather than line editing.

This is a quality-control orchestrator, not a default multi-agent round table.

### G9 · Author-facing CLI / Project Scaffold

`novelforge.py` exposes deterministic routes for Reader Panel, Quality Evolution, Revision Orchestrator, Context Inspector, Memory Tiers, Memory Bank, Character Integrity and State Graph. These commands package/inspect/persist deterministic state and do not silently call a model.

`project_sdk.py` defaults newly scaffolded projects to Framework 7.2.0 and declares reader simulation, quality evolution and author context-memory control support.

### G10 · Release / CI Contract

- `HARNESS_MANIFEST.yaml` reports 7.2.0 and declares every 7.2 author-control/quality module;
- `SKILL.md`, `SKILL.en.md`, and `SKILL.zh-CN.md` carry the 7.2 runtime authority contract;
- Normal CI compiles and self-tests every new deterministic module while retaining all 7.1 regressions;
- Normal CI and packaging perform no hidden model execution;
- deterministic Framework bundle reproducibility remains mandatory;
- customer-facing Story Loom visual/doc redesign is not part of this feature;
- no stopped consumer repository is migrated in this run.

## Adopt / Adapt / Reject

### Adopt

Reader disagreement as editorial signal; pairwise comparison over absolute scores; narrow specialist passes; unified finding taxonomy; author-visible memory/context inspection; durable editable memory; tiered/event-relevant retrieval; character-goal/shared-state verification; graph-based state diff; explicit plateau stopping.

### Adapt

Reader personas focus on reading behavior/genre expectation. Memory banks are authority-aware views/stores rather than source of truth. Same-model personas never impersonate independent review. State graphs remain derived. Revision is fingerprint-bound and routed to the owning mechanism instead of “polish the lowest score.”

### Reject

Default multi-agent round tables; same-manager persona roleplay presented as independent PASS; model memory/summary/dashboard edits silently becoming Canon; proposal/future data silently entering drafting; demographic-sensitive persona inference; absolute 1–10 scores deciding revisions alone; reviewer shopping; endless revision; whole-store context injection.

## Acceptance Criteria

1. Reader Panel jobs are fingerprint-bound and self-tests detect templated-reason collapse plus first-shown bias.
2. Quality Evolution proves durable resume, exact replay idempotency, comparison consume-once, illegal-winner rejection and plateau stopping.
3. Context Inspector blocks protected direct mutation and rejects pre-draft regression/hidden-gold leakage.
4. Memory Tiers prove hard budget, whole-item-or-skip, event relevance, pin priority and derived `authority=false`.
5. Memory Bank proves protected edit→proposal, exact before-state guard, editable derived memory, proposal pre-draft isolation, and non-authoritative context export.
6. Character Integrity proves bounded packets exclude forbidden context and normalize evidence-chained findings.
7. State Graph distinguishes stable-field contradiction from evidence-backed transition.
8. Revision Orchestrator proves pass-failure isolation, finding dedupe and owning-mechanism routing including surface-cluster regeneration.
9. `novelforge.py self-test` covers all 7.2 deterministic modules.
10. Project SDK self-test proves 7.2 default scaffold and quality-control capability flags.
11. Normal CI keeps `model_execution=false` and all existing 7.1 deterministic contracts remain green.
12. Two Framework bundle builds remain byte/fingerprint identical and tamper verification still fails correctly.
13. Framework hygiene detects consumer Canon/private user-taste leakage.
14. Only an exact CI-green final 7.2 HEAD may be called release-ready.
15. No consumer lock or Canon migration is executed in this run.

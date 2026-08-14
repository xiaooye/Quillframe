# Specification · NovelForge 7.2 Author Control + Quality Evolution

## Baseline

- Previous release: NovelForge 7.1.0
- Framework development baseline: `5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`
- Published 7.1 consumer lock: `d9126b2ac39abce0554d83ad74a0ded97017b2a2`
- Rollback: development baseline commit
- Change class: Framework release / structural feature
- Primary mode: `SYSTEM-IMPROVE`

## Problem

7.1 established typed capabilities, a durable learning cycle, provenance, independent semantic execution, immutable bundles, and strict Canon boundaries. Six production gaps remain:

1. Reader Engagement is a strong generic quality model, but there is no first-class simulated reader-reaction panel or disagreement signal.
2. Rewrite/Regenerate has owning-mechanism rules, but no resumable candidate-evolution ledger with pairwise comparison and plateau detection.
3. Sparse Context is strict, but authors cannot easily inspect exactly what was injected, why, at which stage, or pin/unpin it.
4. Runtime/Learning/Project storage is separated, but there is no authority-aware editable memory/control-surface contract.
5. Character Simulation and Continuity rules exist, but there is no common typed integrity artifact exposing agenda/knowledge/voice/relationship/spatial-task state with evidence chains.
6. Long-history selection lacks a generic deterministic event-relevance + tiered derived-memory budget layer.

## External mechanism evidence

These sources create `adopt | adapt | reject` candidates only; they are not dependencies:

- AuthorAgent `47e9570fb96b9d151a3b1f9c22e3a365eab9bd9c`: reader panels, beta-reader metrics, narrow revision passes, tiered memory.
- autonovel `d165f267a0ffd34f3b0a70a8a72ac38cb8e4a542`: multi-reader consensus/disagreement, iterative revision, pairwise comparison, plateau stopping.
- NovelClaw `226d50d3ec284c9cc037c47eb14af39505f9ed74`: author-visible workspace, memory banks, runs, storyboard and character/world control surfaces.
- StoryWriter `08c32d74ce08b46a762951c7f2235772022baa77` / arXiv:2506.16445: event-based outlines and current-event-aware dynamic history compression.
- MAGNET + ATLAS / arXiv:2607.00918: persona-grounded character actions over shared world state and graph-based scene/world-state verification.
- StoryState / arXiv:2602.01305: explicit editable story state and localized editing without treating implicit model memory as authority.

## Goals

### G1 · Reader Simulation Panel

Add provider-neutral `quality/reader_panel.py`:

- reading-behavior personas rather than demographic profiling by default;
- single-candidate reaction and A/B pairwise comparison;
- semantic jobs reuse the existing `external_review` contract and runtime routing;
- aggregate tension, continue intent, confusion, favorite/stumble moments, emotions, and next-page desire;
- diagnose persona disagreement, templated-reason/judge collapse, and first-shown bias;
- panel output is diagnostic evidence and never automatically satisfies a mandatory independent semantic gate.

### G2 · Durable Quality Evolution

Add `quality/quality_evolution.py` implementing:

`baseline → candidate → comparison → keep/discard → repair owner → next candidate → plateau/complete`

Requirements:

- SQLite durable run/candidate/comparison ledger;
- candidate/result fingerprint binding;
- comparison result logical consume-once;
- repair-owner tracking;
- pairwise winner must be one of the compared candidates;
- configurable no-gain plateau stopping;
- no Canon or Framework-write authority.

### G3 · Context + Memory Inspector

Add `harness/context_inspector.py`:

- expose item id/class/source/authority/inclusion reason/stage/relevance/pin state;
- distinguish `locked | accepted | active_plan | review | proposal | runtime | learning | corpus | derived`;
- support low-authority overlay actions such as pin/unpin/priority/hide/invalidate-derived;
- edits to locked/Accepted content become proposals, never direct Canon mutation;
- expose injection stages including `writer_pre_draft | post_draft_critic | independent_reviewer | never`;
- preserve regression/hidden-gold isolation.

### G4 · Tiered Derived Memory + Event Relevance

Add `harness/memory_tiers.py`:

- consume already-derived or project-provided memory items; do not autonomously summarize Canon;
- `hot | working | archival` tiers;
- priority: explicit pin > current-event overlap > participant/relationship match > relevance/priority;
- whole-item-or-skip budgeting;
- source refs/fingerprints required for derived items;
- derived memory always has `authority=false` and may be invalidated/rebuilt;
- current event ids boost relevant history instead of injecting the whole store.

### G5 · Character Integrity + Evidence-Chained Findings

Add:

- `quality/findings.py` normalized finding schema;
- `quality/character_integrity.py` bounded audit-job packaging for important scene characters.

Audit at minimum agenda alignment, knowledge boundary, voice drift, relationship position, spatial/task state, and surprise-within-consistency. Findings include candidate evidence, established/authority evidence, repair owner, severity, confidence, and source refs. Writer private reasoning and hidden gold remain excluded.

### G6 · Scene/World State Graph Audit

Add `quality/state_graph.py`:

- typed scene snapshot nodes/edges;
- deterministic diff reports unexplained state changes or explicit stable-field contradictions only;
- changes may bind transition/event evidence;
- before/after evidence chain output;
- graph is a derived verification view, never a second Canon authority.

### G7 · Author-facing CLI Surface

Top-level CLI adds:

- `reader-panel`
- `quality-evolution`
- `context-inspect`
- `memory-tiers`
- `character-integrity`
- `state-graph`

These commands provide deterministic packaging, inspection, and state transitions only. They never invoke a model without declared semantic capability.

### G8 · Release / CI Contract

- update `HARNESS_MANIFEST.yaml` to 7.2.0 with new quality/control modules;
- normal CI compiles and self-tests every new deterministic module;
- immutable bundle remains deterministic;
- customer-facing visual docs are out of scope for this feature; only machine/Harness/engineering version contracts may change;
- consumer projects are not upgraded in this run; dependency migration requires an exact green Framework commit and new bundle fingerprint.

## Adopt / Adapt / Reject

### Adopt

Reader disagreement as editorial signal; pairwise comparison over absolute scores; narrow passes with unified finding taxonomy; author-visible context/memory inspection; tiered memory budgets; event-relevance retrieval; character-goal/shared-state verification; graph-based state diff.

### Adapt

Reader personas focus on reading behavior/genre expectation; memory banks are authority-aware views/overlays rather than source of truth; same-model personas never impersonate independent review; graph state remains derived; revision is fingerprint-bound and routed to the owning mechanism.

### Reject

Default multi-agent round tables; same-manager persona roleplay presented as independent PASS; model memory/summary/dashboard edits silently becoming Canon; demographic-sensitive inference; absolute 1–10 scores deciding revisions alone; reviewer shopping; endless revision; whole-store context injection or future-data leakage.

## Acceptance Criteria

1. Reader Panel self-test proves fingerprint-bound jobs and detects disagreement + templated-reason collapse.
2. Pairwise self-test normalizes swapped order and detects first-shown bias.
3. Quality Evolution proves durable resume, consume-once comparisons, illegal-winner rejection, and plateau stopping.
4. Context Inspector proves locked/Accepted direct mutation is blocked and downgraded to proposal.
5. Memory Tier proves hard budgets, whole-item-or-skip, event relevance, and derived `authority=false`.
6. Character Integrity proves bounded packets exclude forbidden context and results normalize into evidence-chained findings.
7. State Graph distinguishes stable-field contradiction from evidence-backed transition.
8. `novelforge.py self-test` covers all 7.2 deterministic modules.
9. Normal CI keeps `model_execution=false` and never spends provider usage for panel/evolution packaging.
10. Framework hygiene detects any consumer Canon/private taste leakage.
11. Two bundle builds remain byte/fingerprint identical.
12. Only an exact CI-green 7.2 candidate may be called release-ready.
13. No consumer lock or Canon migration occurs in this run.

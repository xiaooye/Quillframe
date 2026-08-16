# Orchestration Protocol · One task mode, explicit gates, repair at the owning mechanism

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>MODE GRAPHS</kbd>&nbsp;&nbsp;<kbd>CHECKPOINTED SIDE EFFECTS</kbd></p>

This protocol defines how the NovelForge manager turns a validated task mode into a run graph. It does not decide literary meaning itself; semantic nodes are model-readable contracts, while identity, permissions, fingerprints, persistence, routing, and transactions remain deterministic.

> **Boundary ✦** Orchestration controls *sequence and gates*. Story truth remains Project authority; semantic judgment remains the model worker's responsibility inside its bounded contract.

## 01 · Common prefix

Every mode begins from the same execution spine:

```text
resolve Framework authority
→ validate Project + exact lock
→ choose exactly one task_mode
→ create/resume manager session + run
→ resolve authority cutoff + permissions
→ build sparse Context Manifest
→ resolve required capabilities
→ execute the selected mode graph
```

A resumed run does not trust yesterday's environment:

```text
load checkpoint
→ revalidate Framework / Project compatibility
→ revalidate artifact fingerprints
→ rebuild permitted sparse context
→ revalidate approval / write intent
→ re-resolve pending external capabilities
→ validate and consume pending result once
→ continue saved workflow cursor
```

## 02 · Shared semantic subroutine

Any semantic task—reader reaction, character integrity, revision diagnosis, research interpretation, or a mandatory independent gate—uses the same generic boundary:

```text
freeze semantic subject
→ choose model contract / rubric
→ package bounded context + permissions
→ compute semantic fingerprint
→ checkpoint if work may leave the current invocation
→ route eligible runtime
→ execute / handoff / relay / await
→ receive typed result
→ validate identity + fingerprint + provenance + output contract
→ consume once at the named workflow step
```

A material change to input, rubric, or output contract creates a new semantic fingerprint. Infrastructure retry with the same frozen semantic question may preserve it.

A valid semantic reject is a semantic result, not infrastructure failure.

## 03 · DRAFT / REVISE

The default production graph is:

```text
Context Freeze
→ Adaptive Context Assembly
→ Story / Canon Preflight
→ Planning Commitment State
→ Character Private State
→ Character Action / Tactic Simulation
→ Scene Action Collision / World Resolution
→ Writer-safe Realization Projection
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ freeze candidate
→ post-generation diagnostics / regression
→ Reader Production Audit
→ Editor Repair Spec
→ repair at owning mechanism / re-realize
→ Reader Engagement
→ Continuity / state audit
→ required independent semantic gate
→ User-visible Gate
```

Important ordering rules:

- Raw Draft is not user-visible.
- Regression bad examples and answer-key-like evidence remain post-generation.
- `context.select` may decide semantic relevance, but `context_assembly.py` deterministically validates stage eligibility, authority, required context classes, provenance, invalidation state, and hard failure when a required context class is unavailable.
- Private character/simulation state is not a Writer exposition payload. Character state drives `character.action_propose`; `scene.resolve_actions` resolves collisions; `scene.realization_project` exposes only a writer-safe event/interaction projection.
- `reader.production_audit` judges reading experience from the frozen candidate; `editor.repair_spec` assigns preserve/change goals and repair ownership. Neither receipt acquires release or Canon authority.
- Scene/Character/Reader simulation may be model-semantic work; durable invariants around them remain deterministic.
- Surface-clean prose can still fail Reader Engagement.
- Agenda-to-dialogue leakage / HF-30 routes to interaction/realization or Character/Scene simulation when structural; it is not repaired by mechanically shortening every line.
- SAFE-BUT-FLAT routes upstream, not to generic line polishing.
- A changed repaired candidate receives a new content fingerprint before a fingerprint-bound gate.

REVISE begins from a frozen candidate plus explicit repair goals/evidence; it does not assume every dimension needs rewriting.

## 04 · Failure routing

The orchestrator should diagnose before choosing repair depth.

```text
isolated surface defect         → local rewrite
surface failure cluster         → block / whole-scene realization
agenda-dialogue serialization   → realization / Character / Scene simulation
reader-grip / SAFE-BUT-FLAT     → Reader Pressure + Scene Simulation
character integrity failure     → Character Simulation / state reasoning
story / plan failure            → Story / Plan
continuity/state mismatch       → continuity / state owner
context contamination/staleness → rebuild Context Manifest / Context Assembly
memory-derived error            → invalidate / rebuild derived memory
research uncertainty            → Research
runtime/tool failure            → capability / transport layer
artistic direction unresolved   → user / human decision
```

Do not repair a higher-level failure by polishing its prose symptoms.

## 05 · DESIGN / PLAN

`DESIGN-BOOK`, `DESIGN-VOLUME`, `PLAN-UNIT`, and `PLAN-CHAPTER` create planning artifacts such as `proposal` and `active_plan`.

They may:

- inspect current authority;
- model alternatives;
- update future planning objects when authorized;
- create dependencies and expected state deltas.

They may not:

- treat planned events as occurred;
- settle current Canon;
- give characters future knowledge as current knowledge.

Use rolling elaboration: high resolution near the production frontier, lower resolution farther away. Commitment horizons and bounded rebalance restrict how much future detail can become committed at once; they do not create a second plan authority.

## 06 · RESEARCH

Research produces source-bound evidence rather than story truth by side effect.

A generic graph is:

```text
research question
→ capability / source selection
→ authoritative/primary source retrieval where possible
→ source/provenance capture
→ bounded semantic interpretation if needed
→ REF / CLAIM-equivalent evidence
→ user/plan consumption
```

Keep separate:

`real-world fact ≠ project fictionalization ≠ character knowledge ≠ current Canon`

Search capability never grants project-write authority.

## 07 · CORPUS-INGEST

Corpus work separates discovery, rights, analysis, and durable storage:

```text
craft / learning question
→ corpus gap
→ discovery request
→ capability-aware source discovery
→ source verification + provenance
→ rights gate
→ bounded ingestion / analysis
→ benchmark / eval evidence
```

Discovery does not imply ingestion. Corpus content never becomes Canon or automatic writer context.

## 08 · LEARN

Learning uses the narrowest evidence-supported scope:

`one_off | project | user_taste | general_craft`

A generic graph is:

```text
feedback / evidence
→ semantic preference interpretation when needed
→ scoped evidence in the existing Learning Store
→ revisable hypothesis
→ contradiction / counterexample search
→ corpus or eval gap
→ bounded semantic analysis
→ candidate
→ deterministic evidence-completeness / promotion gate
→ explicit activation / promotion / rollback
```

`learning.preference_interpret` may propose the mechanism and narrowest plausible scope; `learning/author_model.py` persists evidence/hypotheses through the existing Learning Store and projects only active applicable preferences into future production.

Project preference activation still requires its explicit project write authority. Durable `user_taste` activation requires **both** a current passing `promotion_gate` prerequisite evaluation and explicit durable-user-taste write authorization. A caller boolean alone cannot activate the hypothesis. `general_craft` never auto-promotes through the Author Model path.

Model repetition is not new evidence. General Craft requires stronger cross-work evidence than project/local learning.

## 09 · AUDIT

AUDIT inspects; it does not silently repair.

It may produce:

- deterministic violations;
- semantic findings;
- continuity/state discrepancies;
- stale derived views;
- broken dependency or documentation references;
- explicit proposed repair owners.

If the user asks for repair, that becomes a separate authorized mode/run rather than a hidden side effect of the audit.

## 10 · SETTLE

Only explicit acceptance/Canon instruction permits settlement.

```text
freeze Accepted artifact + fingerprint
→ derive exact State Delta
→ validate target + before-state
→ compute dependency impact
→ checkpoint / write intent
→ authorized mutation
→ rebuild derived views
→ verify post-condition
→ trace / receipt
```

A mismatch returns `settlement_incomplete`. Do not guess, partially claim success, or repeat already-completed side effects after resume.

## 11 · SYSTEM-IMPROVE

Material Framework change follows engineering rather than prompt editing:

```text
evidence / problem
→ mechanism analysis
→ alternatives + conflict review
→ spec / plan / tasks when structural
→ implementation
→ deterministic tests + semantic eval evidence where needed
→ rollback point / versioning
→ acceptance
```

Project-specific characters, plot facts, or Canon must not become generic Framework defaults.

## 12 · Parallelism

Parallelize when workers can operate on immutable/frozen inputs and their results can be independently validated.

Avoid concurrent mutation of shared project/Canon state unless an explicit transaction/version protocol exists.

Do not use multi-agent parallelism merely to duplicate the same judgment.

## 13 · Completion states

A run must end in a truthful explicit state such as:

`complete | review | awaiting_user | awaiting_external | semantic_pending | semantic_invalid | failed_gate | blocked | settlement_incomplete`

`semantic_reject` is normally consumed as a gate outcome and routed to repair rather than mislabeled as infrastructure failure.

## 14 · Related contracts

- [Harness Agent](HARNESS_AGENT.en.md) — manager responsibilities and authority.
- [Session Runtime](session_runtime/SESSION_RUNTIME.en.md) — lifecycle, checkpoints and resume.
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) — semantic identity/fingerprint/result boundary.
- [Production Pipeline](../docs/production-pipeline.en.md) — customer-facing explanation of DRAFT/REVISE.
- [Context & Memory](../docs/context-and-memory.en.md) — Context Inspector, Assembly, selection, and memory boundaries.
- [Adaptive Learning](../docs/adaptive-learning.en.md) — Learning Store, Author Model, promotion, and rollback.
- [Canon & State Model](../core/CANON_STATE.en.md) — settlement authority.
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
→ Story / Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ freeze candidate
→ post-generation diagnostics / regression
→ repair at owning mechanism
→ Reader Engagement
→ Continuity / state audit
→ required independent semantic gate
→ User-visible Gate
```

Important ordering rules:

- Raw Draft is not user-visible.
- Regression bad examples and answer-key-like evidence remain post-generation.
- Scene/Character/Reader simulation may be model-semantic work; durable invariants around them remain deterministic.
- Surface-clean prose can still fail Reader Engagement.
- SAFE-BUT-FLAT routes upstream, not to generic line polishing.
- A changed repaired candidate receives a new content fingerprint before a fingerprint-bound gate.

REVISE begins from a frozen candidate plus explicit repair goals/evidence; it does not assume every dimension needs rewriting.

## 04 · Failure routing

The orchestrator should diagnose before choosing repair depth.

```text
isolated surface defect         → local rewrite
surface failure cluster         → block / whole-scene realization
reader-grip / SAFE-BUT-FLAT     → Reader Pressure + Scene Simulation
character integrity failure     → Character Simulation / state reasoning
story / plan failure            → Story / Plan
continuity/state mismatch       → continuity / state owner
context contamination/staleness → rebuild Context Manifest
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

Use rolling elaboration: high resolution near the production frontier, lower resolution farther away.

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
→ scope classification
→ hypothesis
→ contradiction / counterexample search
→ corpus or eval gap
→ bounded semantic analysis
→ candidate
→ deterministic evidence-completeness gate
→ explicit activation / promotion / rollback
```

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
- [Canon & State Model](../core/CANON_STATE.en.md) — settlement authority.

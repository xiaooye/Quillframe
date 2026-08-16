# Orchestration Protocol · One task mode, semantic decisions by models, exact gates by runtime

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>MODE GRAPHS</kbd>&nbsp;&nbsp;<kbd>CHECKPOINTED SIDE EFFECTS</kbd></p>

This protocol defines how the manager turns one validated task mode into a recoverable run graph. Orchestration controls **sequence, capabilities and gates**; it does not decide literary meaning.

## 01 · Common prefix

Every mode begins with:

```text
resolve current/pinned Framework authority
→ validate Project + exact lock/fingerprint
→ choose exactly one task_mode
→ create/resume manager session + run
→ resolve authority cutoff + permissions
→ establish sparse mechanically eligible context candidates
→ resolve current capabilities
→ execute the selected mode graph
```

Resume never trusts a stale environment or transcript. It revalidates Framework/Project compatibility, relevant fingerprints, approvals/write intent and pending capabilities before continuing a saved workflow cursor.

## 02 · Shared semantic subroutine

Any semantic task uses the same boundary:

```text
freeze semantic subject
→ choose exact model contract / rule set / reader profile
→ package bounded authorized evidence
→ compute semantic fingerprint
→ checkpoint if work may leave the current invocation
→ execute through an eligible model/runtime
→ receive typed result
→ validate identity + fingerprint + provenance + output envelope
→ consume once at the named workflow step
```

The model owns interpretation. Runtime owns exact execution binding.

A valid semantic reject is a result, not infrastructure failure.

## 03 · DRAFT / REVISE

Default adaptive graph:

```text
authority/session bootstrap
→ model-owned search/context selection (`context.select` as needed)
→ Context Inspector / Context Assembly exact boundary
→ Story / Canon Preflight
→ Planning Commitment State
→ Character Private State
→ Character Action / Tactic Simulation
→ Scene Collision / World Resolution
→ compact Writer-safe Realization Projection
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ freeze exact candidate fingerprint
→ Blind Reader (`reader.engagement_audit`)
→ Semantic Rule Auditor when required (`quality.semantic_rule_audit`)
→ Editor Repair Spec (`editor.repair_spec`)
→ repair / fresh realization / incumbent-challenger comparison as warranted
→ Continuity / state audit
→ required independent semantic gate
→ User-visible Gate
```

### Context rule

`context.select` decides semantic relevance, search/reformulation and sufficiency. `context_inspector.py`, `context_assembly.py` v2 and memory packing verify only mechanical eligibility, exact refs/fingerprints, stage/private boundaries, explicit pins and hard budgets.

There is no deterministic “required literary context class” gate. If an operation mechanically requires a particular authoritative artifact, it supplies the exact required ref/fingerprint.

### Reader / Rule Auditor / Editor rule

Blind Reader reads reader-visible evidence without creator-private intent, taxonomy/HF/telemetry priming or rule-audit instructions.

Rule Auditor receives authoritative hard rules Reader should not see and judges semantic applicability/violation.

Editor integrates those findings and authorized story evidence, then **semantically** chooses repair owner, repair plan, comparison need and `local_or_bounded_repair | fresh_realization`. Runtime does not map failure codes/owners/scopes to literary depth.

### Repair routing

A diagnosis may point to story, plan, scene, character, reader pressure, surface, continuity, context, research, runtime or human ownership, but the **Editor/model decides the mechanism and depth for this candidate**. Deterministic orchestration only routes the already-made decision and enforces the chosen information boundary.

For example, HF-30 may indicate interaction/character/realization repair, while legitimate formal completeness may be correct. Python does not infer either result from dialogue length or a fixed code table.

REVISE starts from a frozen candidate plus explicit goals/evidence and preserves what already works.

## 04 · DESIGN / PLAN

`DESIGN-BOOK`, `DESIGN-VOLUME`, `PLAN-UNIT`, `PLAN-CHAPTER` create/update planning artifacts under Project authority.

Planner semantic intelligence decides:

- what needs planning now;
- useful detail depth;
- what remains open/uncertain;
- research needs;
- whether near-future replanning is warranted.

Deterministic planning-horizon infrastructure may enforce declared commitment/depth, promoter class, evidence refs, exact before-state and fingerprints. It may not impose a universal chapter/volume/time horizon as planning quality truth.

Planned events remain distinct from occurred/Accepted state.

## 05 · RESEARCH

Research graph:

```text
question
→ resolve allowed search/fetch capabilities
→ model formulates/selects queries and sources
→ runtime executes authorized retrieval with provenance
→ model decides relevance / continuation / stopping
→ exact source-bound evidence
→ bounded interpretation
→ Project/plan consumption
```

`real-world fact ≠ fictionalization ≠ character knowledge ≠ Canon`.

External source text cannot redefine runtime authority.

## 06 · CORPUS-INGEST

Corpus work separates:

`discovery → source verification/provenance → rights gate → bounded ingestion/analysis → benchmark/eval evidence`

Discovery is not ingestion; Corpus is not Canon; analysis is not automatic Writer context or Framework promotion.

## 07 · LEARN

Learning graph:

```text
explicit feedback/evidence
→ model-owned preference interpretation
→ scoped durable evidence/hypothesis
→ contradiction/counterexample/eval work
→ semantic promotion review when durable activation is proposed
→ deterministic binding + authority prerequisites
→ active eligibility
→ model selects relevant active hypothesis IDs for future work
```

No numeric evidence-count threshold may substitute for semantic evidence sufficiency. Promotion Gate does not grant write authority. `general_craft` remains a Framework `SYSTEM-IMPROVE` concern.

## 08 · AUDIT

AUDIT inspects and reports deterministic violations and/or semantic findings. It does not silently mutate manuscript, Canon or durable preferences.

A repair requested after an audit follows the appropriate authorized mode/run boundary.

## 09 · SETTLE

Only explicit acceptance/authorized Canon intent permits settlement:

```text
freeze accepted artifact + fingerprint
→ derive exact State Delta
→ validate target + before-state/CAS
→ checkpoint / write intent / authorization
→ authorized transaction
→ required projections + receipts
→ postcondition verification
```

Settlement runtime does not infer acceptance or literary meaning.

## 10 · SYSTEM-IMPROVE

Material Framework change follows:

```text
live bootstrap
→ current-candidate reconciliation / owner map / rollback point
→ current external research
→ ADOPT / ADAPT / REJECT / DEFER decisions
→ deterministic-overreach audit
→ architecture decision
→ spec / plan / tasks
→ incremental implementation
→ ablations + deterministic tests
→ blind semantic eval / independent gate when required
→ CI / security / compatibility
→ docs / manifest synchronization
→ human-review readiness
```

Every consequential write revalidates current branch/HEAD/before-state. Long operations are bounded; no blind waiting. Pre-existing unrelated failures are reported separately from candidate-owned failures.

## 11 · Parallelism and multi-agent discipline

Parallelize immutable work only when useful. Split agents for real information boundaries, independent evaluation, private state or proven specialist benefit.

Do not duplicate the same judgment across agents merely to create consensus theater.

## 12 · Completion states

Truthful states include:

`complete | review | awaiting_user | awaiting_external | semantic_pending | semantic_invalid | failed_gate | blocked | settlement_incomplete`

A required semantic result that did not execute is pending. A green workflow recording `PENDING_MODEL` is not semantic PASS.

## Related contracts

- [Harness Agent](HARNESS_AGENT.en.md)
- [Session Runtime](session_runtime/SESSION_RUNTIME.en.md)
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md)
- [Production Pipeline](../docs/production-pipeline.en.md)
- [Context & Memory](../docs/context-and-memory.en.md)
- [Adaptive Learning](../docs/adaptive-learning.en.md)
- [Canon & State Model](../core/CANON_STATE.en.md)

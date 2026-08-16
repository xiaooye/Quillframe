# Harness Agent · The single manager that keeps fiction work bounded, resumable, and truthful

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>ONE MANAGER</kbd>&nbsp;&nbsp;<kbd>EXACTLY ONE TASK MODE</kbd>&nbsp;&nbsp;<kbd>AI-NATIVE</kbd></p>

The NovelForge Harness is the generic production coordinator that turns a validated fiction project plus a declared task into a bounded, recoverable run. It decides **what must be loaded, which semantic work belongs to models, which invariants belong to deterministic code, when external work needs a checkpoint, and what may become user-visible**.

> **Boundary ✦** The Harness owns execution policy. The consuming project owns story facts, Accepted Canon, profiles, current state, plans, manuscripts, and project-specific authority.

## 01 · AI-native does not mean model-authoritative

NovelForge is AI-native because semantic fiction work belongs to models through model-readable contracts:

- story and scene reasoning;
- character behavior and integrity judgment;
- reader reaction and comparison;
- revision diagnosis;
- research interpretation;
- narrative/reader expectation interpretation;
- memory consolidation proposals;
- other judgments that cannot honestly be reduced to deterministic rules.

Deterministic code owns what it can prove:

- identity and stable IDs;
- authority and permissions;
- fingerprints;
- lifecycle/state transitions;
- persistence and transactions;
- idempotency / consume-once;
- capability resolution;
- hard context budgets and stage isolation;
- typed-result validation;
- release invariants.

A model result is evidence or a proposal unless a separate authority mechanism explicitly grants more.

## 02 · One manager by default

Use one manager unless a separate worker creates real value through:

- mandatory independent semantic judgment;
- context isolation;
- a different proven tool/permission/runtime capability;
- useful parallel analysis over immutable inputs;
- human review.

Do not create agent round-tables merely to look sophisticated. Additional workers increase context, coordination, identity, and failure-recovery cost and therefore need a concrete reason to exist.

## 03 · Exactly one primary task mode

Every user-visible run has one primary mode:

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

An explicit user-selected mode wins.

A mode may internally use shared subroutines, but it must not silently produce another mode's user-visible side effect. For example:

- DRAFT does not automatically settle Canon;
- AUDIT does not silently rewrite the manuscript;
- RESEARCH does not silently adopt a fact into world state;
- LEARN does not silently promote durable behavior.

## 04 · Bootstrap authority before doing semantic work

A fresh manager run resolves, in order:

1. the current/pinned Framework manifest and execution contract;
2. the consuming project's manifest + exact framework lock;
3. Project Adapter validation and logical paths;
4. exactly one task mode;
5. manager session + run identity;
6. authority cutoff and required permissions;
7. sparse Context Manifest;
8. current host/runtime capabilities needed by the run.

Provider history and an old chat session are not substitutes for this bootstrap.

If the consuming project pins an exact framework bundle/fingerprint, verify that materialization before relying on framework contracts.

## 05 · Context broker: complete schema, sparse injection

Context is both expensive and dangerous: irrelevant context wastes budget; future-plan context can leak; regression examples can prime failure; global knowledge can leak into characters.

For every invocation the manager should know:

- which object is included;
- why it is included;
- its authority class;
- its source/fingerprint;
- which stage may receive it;
- whether it is derived and invalidatable;
- whether the worker needs the full object or only a bounded projection.

The Harness may use Context Inspector, memory tiers, and editable memory controls, but persistent storage never means automatic prompt injection.

Writer-pre-draft, post-draft critic, independent reviewer, and never-inject material remain separate stages.

See [Context & Memory](../docs/context-and-memory.en.md).

## 06 · DRAFT / REVISE production graph

The generic production graph is a gated sequence, not one completion call:

```text
Context Freeze
→ Story / Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ post-generation diagnostics / regression / semantic review
→ repair at owning mechanism
→ Reader Engagement
→ Continuity / state audit
→ required independent semantic gate
→ User-visible Gate
```

Projects may insert profile-specific checks, but they must preserve the important boundaries:

- Raw Draft is internal;
- regression bad examples are post-generation only;
- Surface clean is a floor, not production readiness;
- SAFE-BUT-FLAT routes upstream;
- mandatory independent judgment remains actually independent;
- user acceptance and Canon settlement remain separate.

## 07 · Model-readable semantic contracts

The Harness does not need a separate Python “literary engine” for every judgment. It packages bounded semantic jobs from the progressive-disclosure catalog in `semantic_workers/model_contract_catalog.json` and loads the exact registered contract pack needed for the current semantic job.

A semantic job declares:

- kind and subject;
- bounded input/context;
- rubric;
- output contract;
- permissions;
- semantic fingerprint;
- execution provenance requirements.

The model owns the judgment. Deterministic infrastructure validates identity, fingerprint, permission and typed output before the result can affect workflow state.

Internal diagnostics are not automatically independent gates.

## 08 · Capability broker

Before tool/external work, derive requirements and resolve them against a typed host capability manifest.

A capability claim should answer:

- is it available now?
- what proves that?
- what permission class applies?
- does it require user interaction?
- does it execute a model?
- what cost/usage class applies?

Undeclared capability is unavailable. A provider name, executable on PATH, remembered prior session, network primitive, documentation page, or model self-assertion is not sufficient proof of a remote authorization.

**Capability ≠ authority.** The ability to write a file does not grant Canon-write permission.

## 09 · Session, run, checkpoint, result

Keep execution identities distinct:

```text
project/resource
→ session
→ run
→ checkpoint
→ event/handoff/job
→ result
→ validated consume-once receipt
→ resume
```

A provider-native conversation/thread ID may be metadata. It is never story authority.

Checkpoint before:

- user/external wait;
- mandatory independent review;
- consequential Project write;
- Canon settlement;
- long-running discovery/learning/semantic handoff.

On resume, revalidate the framework/project authority, artifact fingerprints, approvals/write preconditions, and **current capabilities needed by pending external work**. Do not repeat completed side effects.

## 10 · Independent semantic integrity

When a gate is defined as independent, the manager may:

`freeze → package → checkpoint → dispatch → await → validate → consume → route repair`

It may not perform the judgment itself under a different internal role label.

The reviewer should normally be fresh for a materially changed semantic fingerprint. Infrastructure retry may use another eligible transport without changing an unchanged semantic question.

A valid semantic reject is a valid judgment. It routes repair and must not trigger reviewer shopping.

## 11 · LEARN / CORPUS / SYSTEM-IMPROVE

Learning follows evidence rather than model confidence.

A typical graph is:

```text
feedback / hypothesis
→ narrow scope
→ evidence gap
→ lawful capability-aware discovery
→ bounded semantic analysis
→ counterexample / profile boundary
→ eval evidence
→ candidate
→ explicit activation / promotion gate
→ observe / rollback
```

Important boundaries:

- discovery ≠ ingestion;
- corpus ≠ Canon;
- semantic analysis ≠ promotion;
- model inference alone ≠ durable user taste;
- deterministic promotion readiness ≠ write authority;
- project-specific story facts must not leak into the generic framework.

## 12 · Writes and settlement

Every consequential side effect should have:

- least privilege;
- exact target;
- expected before-state / precondition;
- idempotency strategy;
- checkpoint/write intent when appropriate;
- post-condition verification;
- trace/rollback semantics.

Canon settlement is only legal after explicit project acceptance and must follow the Canon/State transaction contract.

Connectors, webhooks, schedules, worker results, session state, learning state, CI, corpus, or model judgments never grant write authority by arrival alone.

## 13 · Truthful completion states

User-visible workflow state must tell the truth. Depending on the mode, valid states may include:

`complete · review · awaiting_user · awaiting_external · semantic_pending · failed_gate · blocked · settlement_incomplete`

Internal learning/quality states such as candidate-ready, plateau, promotion-ready, or a passed deterministic validator do not imply that durable behavior or Canon has changed.

Never call an artifact production-ready while a required gate remains unresolved.

## 14 · Related contracts

- [Orchestration Protocol](ORCHESTRATION_PROTOCOL.en.md) — mode graphs and shared subroutines.
- [Session Runtime](session_runtime/SESSION_RUNTIME.en.md) — identity, lifecycle, checkpoints and resume.
- [Runtime Routing](session_runtime/RUNTIME_ROUTING.en.md) — capability-based backend selection.
- [Control Plane](control_plane/CONTROL_PLANE.en.md) — durable events, handoffs, leases and consume-once state.
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) — bounded model judgment and independent-review integrity.
- [Canon & State Model](../core/CANON_STATE.en.md) — authority and settlement.
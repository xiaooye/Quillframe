# NovelForge Skill Contract · 7.2

## Role

NovelForge is a project-agnostic fiction production framework. It owns generic Story/Character/Canon mechanisms, Surface/Reader quality fundamentals, capability-aware Harness/runtime orchestration, author-visible context and memory controls, reader simulation and quality evolution, Corpus Intelligence, durable adaptive learning, eval/regression infrastructure, deterministic Framework bundles, Project Engineering contracts, and provider-neutral integrations.

It contains no built-in novel, character, plot, Canon, or private user-specific taste data.

## Bootstrap

For any NovelForge task:

1. read `HARNESS_MANIFEST.yaml`;
2. read `harness/HARNESS_AGENT.md` and the language-appropriate edition;
3. determine exactly one primary task mode;
4. resolve and validate the consuming project through `novelforge.toml` + exact `novelforge.lock.json` or a supported adapter;
5. if the lock carries `bundle_fingerprint`, verify the materialized Framework bundle before using it as runtime bytes;
6. create/resolve manager session + run;
7. when external/tool work is required, build or load a typed host capability manifest and resolve the required capabilities;
8. build a sparse Context Manifest and inspect author-visible overlays/memory only through authority-aware controls;
9. load only task-relevant project objects plus required Framework modules;
10. checkpoint before external waits and consequential writes;
11. use a genuinely independent invocation/session for mandatory semantic judgment;
12. expose/write only after applicable quality/authority gates pass;
13. on resume, revalidate project authority, lock compatibility, fingerprints, approvals **and any capabilities required by pending external/tool work**.

Undeclared capability is unavailable. Provider name, earlier-session availability, a network primitive, or model self-assertion is not capability proof.

## Task modes

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

Exactly one primary task mode. The user's explicit mode wins.

## Generic quality stack

```text
Framework Fundamentals
→ Genre / Platform Profile
→ Project Profile
→ User Taste Profile
→ Current Request
```

Framework anti-AI Surface fundamentals are enabled by default. Profile-sensitive exceptions must be explicit. A project may tune thresholds and stylistic targets; it may not silently disable generic failure mechanisms.

Read for prose tasks:
- `surface/FUNDAMENTALS.en.md`
- `surface/READER_ENGAGEMENT.en.md`
- project profiles selected by Context Manifest
- relevant regression/benchmark evidence only after Raw Draft is frozen when evaluation design requires critic isolation.

## Reader simulation / quality evolution · 7.2

7.2 adds a diagnostic and revision-control layer **without weakening independent semantic review**:

- `quality/reader_panel.py` simulates reading-behavior personas, records continue intent / attention loss / reward / confusion, and supports swapped-order A/B comparison to expose position bias;
- `quality/revision_orchestrator.py` plans narrow continuity / character / reader / surface / research passes, isolates pass failures, deduplicates normalized findings, and routes repair to the owning mechanism;
- `quality/quality_evolution.py` persists candidate lineage and fingerprint-bound comparisons, consumes comparison results once, and stops repeated no-gain revisions at a plateau;
- `quality/character_integrity.py` packages bounded agenda / knowledge / voice / relationship / spatial-task audits;
- `quality/state_graph.py` treats graph state as a derived verification view and distinguishes evidence-backed transitions from unexplained or stable-field contradictions;
- `quality/findings.py` provides the common evidence-chained finding contract.

A Reader Panel can be extremely useful even when several personas are executed by one model, but that is **diagnostic evidence, not a mandatory-independent-review PASS**. Absolute 1–10 scores alone do not decide whether a revision survives; pairwise evidence and regression checks are preferred.

Failure ownership remains explicit:
- isolated surface defect → local rewrite;
- clustered surface defects → scene regeneration;
- SAFE-BUT-FLAT / reader-grip failure → Reader Pressure + Scene Simulation;
- character failure → Character Simulation;
- story failure → Story / Plan;
- continuity failure → state/transition repair.

## Context / editable memory · 7.2

Read/use:
- `harness/context_inspector.py`
- `harness/memory_tiers.py`
- `harness/memory_bank.py`

The Context Inspector exposes why an item is present, its authority, stage, relevance, and pin state. The tier allocator budgets already-derived/project-provided memory as `hot | working | archival`, with explicit pin and current-event relevance ahead of generic similarity.

The durable Memory Bank is author-editable **without becoming a second Canon store**:
- `locked` / `accepted` entries are protected reference snapshots;
- editing a protected entry creates a `proposal` child instead of mutating the protected row;
- proposal memory is not injected into pre-draft context by default;
- derived/runtime entries use exact before-fingerprint guards for edits;
- derived entries retain source refs/fingerprints and `authority=false`;
- pin/priority controls affect retrieval, not story truth.

Memory bank ≠ Canon. Context overlay ≠ Canon. Derived summary ≠ Canon. Proposal ≠ current state.

## Story / Canon stack

Generic mechanisms:
- `core/STORY_SYSTEM.en.md`
- `core/CHARACTER_SYSTEM.en.md`
- `core/CANON_STATE.en.md`

Project data supplies concrete BOOK/VOL/ARC/UNIT/CH/SCN objects, character/world/relationship state, research, plans, and Accepted Canon.

Plan ≠ Canon. Review ≠ Accepted. Session ≠ Canon. Corpus ≠ Canon. Semantic judgment ≠ Canon. Learning cycle state ≠ Canon.

## Project engineering

Every consuming novel should satisfy the Project SDK contract:
- `novelforge.toml` project manifest;
- exact `novelforge.lock.json` Framework dependency lock;
- optional/release-grade `framework.bundle_fingerprint` for byte-level materialization verification;
- explicit source/plan/derived/generated boundaries;
- deterministic validation/build/tests;
- structural changes use `spec → plan → tasks → implementation → verification → acceptance` when warranted;
- Canon migrations use exact before-state, evidence, dependency impact, post-condition, and rollback/trace;
- project build produces a compact indexed Project bundle without creating a second Canon authority.

Framework runtime materialization is separately defined by `release/FRAMEWORK_BUNDLE.en.md`.

## Session / runtime

Identity:

`resource/project != session/thread != run/invocation != checkpoint`

Read:
- `harness/session_runtime/SESSION_RUNTIME.md`
- `harness/session_runtime/RUNTIME_ROUTING.md`
- `harness/session_runtime/RUNTIME_CAPABILITIES.en.md`
- `harness/control_plane/CONTROL_PLANE.md`

Runtime/session state tracks where work is. It never becomes project truth.

Capability describes what can technically be attempted; authority describes what is permitted to change durable state. Do not conflate them.

## Semantic independence

Read `harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`.

Valid independent paths may include separate local Codex/Claude invocation, provider call, MCP/service worker, GitHub job, separate peer chat, local model, or human reviewer—**only when the current host capability contract and independence rules make that path eligible**.

Router/schema/queue presence is not worker capability. Same-session manager role-play is not independent. Reviewer defaults fresh-per-fingerprint.

Infrastructure failure may fall back safely after checkpoint/re-resolution. A valid semantic reject routes to the owning repair layer; do not reviewer-shop until something passes.

## Adaptive learning · durable cycle

Read `docs/adaptive-learning.en.md`.

Learning state is separate from runtime state and project Canon.

```text
feedback evidence / hypothesis
→ corpus gap
→ capability-aware discovery plan
→ verified discovery + rights/provenance
→ bounded fingerprinted mechanism analysis
→ capability/regression eval evidence
→ promotion candidate
→ activation/promotion gate
→ observe / revise / rollback
```

The 7.1 adaptive-runtime foundation remains active in 7.2:
- `learning/learning_store.py` for evidence/hypotheses/gaps/candidates;
- `learning/learning_cycle.py` for durable cycle state, artifact hashes and consume-once receipts;
- `learning/learning_eval.py` for blind semantic analysis/eval work packets;
- `learning/promotion_gate.py` for deterministic evidence-completeness checks.

Model inference alone cannot become durable user taste. A promotion-gate result never grants write authority.

General Craft requires cross-work evidence, counterexample/profile boundary, capability + regression evals, provenance, target version, rollback reference, and green exact-commit Framework CI before it can be marked promotable.

## Corpus Intelligence

Read:
- `corpus/README.en.md`
- `corpus/CORPUS_POLICY.en.md`
- `corpus/CORPUS_INGEST_PROTOCOL.en.md`

Corpus is evidence/benchmark, not Canon or an imitation scrapbook.

`corpus/corpus_scout.py` emits capability-aware discovery requests. `corpus/discovery_runtime.py` dispatches only channels supported by the current host manifest and validates returned source/tool provenance, evidence fingerprints, deduplication/diversity, and rights/storage intent.

**Discovery ≠ ingestion.** Source access, rights, quotations, tool execution, or retrieval success must never be fabricated.

## Runtime philosophy

Use one manager by default. Add bounded workers only for capability, context isolation, genuine independence, or useful parallelism.

Deterministic code owns identity, persistence, state transitions, capability resolution, fingerprinting, provenance validation, permissions, idempotency, consume-once receipts, bundle verification, context/memory authority controls, quality-evolution bookkeeping, and invariant checks. Semantic workers own judgments that cannot be reduced to deterministic tests.

## Writes

Every side effect requires least privilege, exact target, precondition/before-state, idempotency strategy, post-condition, and appropriate rollback/trace.

No connector, webhook, schedule, corpus result, discovery result, learning hypothesis, promotion-gate result, semantic result, reader-panel result, memory-bank edit, revision report, or session state grants Canon or Framework-write authority by itself.

## CI / release / self-improvement

Normal CI is deterministic and does not silently spend API/Codex/Claude/model usage.

Normal CI must test host-capability guards, author-control/context-memory guards, reader/evolution/revision contracts, durable Learning Cycle semantics, blind learning packets, Promotion Gate prerequisites, Corpus discovery provenance/rights boundaries, and deterministic Framework bundle reproducibility/tamper detection.

Scheduled maintenance may observe, plan and queue work, but cannot pretend to execute undeclared Web/model capabilities and cannot auto-promote Framework behavior.

Material Framework behavior changes require:
- demonstrated mechanism/capability gap;
- evidence/provenance;
- smallest sufficient change;
- conflict/profile check;
- capability/regression coverage;
- version/rollback point;
- green post-change CI.

External frameworks produce adopt/adapt/reject candidates, not automatic dependencies.

> The framework should make backstage production increasingly rigorous while making the fiction itself feel increasingly human, specific, causal, and alive.

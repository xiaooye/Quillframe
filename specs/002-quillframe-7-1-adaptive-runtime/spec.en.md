# Specification · NovelForge 7.1 Adaptive Runtime

## Baseline

- Previous release: NovelForge 7.0.0
- Baseline commit: `de05666cc4eae13f09868d87659e76f2aa524314`
- Rollback point: the baseline commit above
- Change class: framework release / structural feature

## Problem

NovelForge 7.0 can persist preference evidence and hypotheses, generate Corpus gaps, produce typed discovery requests, validate declared rights metadata, route semantic work, and checkpoint long-running sessions. It does not yet provide one deterministic lifecycle that connects those pieces into a resumable learning cycle. Host tool availability is also described by documentation/runtime routing rather than represented as a typed capability contract, and the framework dependency lock has no immutable bundle fingerprint.

This leaves three failure modes:

1. a model may infer that a Web/GitHub/MCP connector exists instead of proving capability;
2. Corpus discovery, source verification, semantic analysis, eval evidence, and promotion candidacy can become loosely coupled ad-hoc steps;
3. consumers pin a commit but cannot independently verify a materialized framework bundle by content fingerprint.

## Goals

### G1 · Typed Host Capability Contract

Add a provider-neutral host capability manifest and deterministic resolver. A capability may be used only when explicitly declared or locally proven. Missing capability produces a truthful pending/blocked route instead of fabricated access.

### G2 · Durable Adaptive Learning Cycle

Add an executable stdlib-only learning-cycle state machine that coordinates:

`evidence/hypothesis → corpus gap → discovery planning → verified discovery results → semantic mechanism analysis → eval evidence → promotion candidate → activation/promotion gate`

The cycle state is operational/learning state, never Canon.

### G3 · Discovery / Provenance Runtime

Add typed discovery result contracts with source locator, retrieval channel, tool/provider provenance, retrieval timestamp, evidence fingerprint, declared rights basis, storage intent, and deduplication/diversity accounting.

Discovery remains separate from ingestion. Rights status is never inferred deterministically from a URL/title.

### G4 · Analysis + Eval Work Packaging

Create bounded fingerprinted semantic jobs for Corpus mechanism analysis and learning evaluation. Hidden gold, writer private reasoning, user private data unrelated to the learning question, and whole copyrighted source text are excluded by default.

### G5 · Promotion Gate

Add a deterministic gate that can declare a learning candidate `blocked`, `ready_for_activation`, or `promotable`, but cannot itself rewrite Framework behavior or durable user taste.

General Craft requires provenance, counterexample/profile boundary, cross-work evidence, capability + regression eval evidence, target version, rollback reference, and green deterministic CI.

### G6 · Immutable Framework Bundle

Add deterministic bundle construction and verification. Bundle contents are sorted and normalized; generated bundle metadata is excluded from its own fingerprint. The output includes a content manifest and SHA-256 bundle fingerprint that consuming projects may pin in `novelforge.lock.json`.

### G7 · Release-grade Automation

Normal CI and scheduled maintenance remain model-free. Weekly maintenance may advance deterministic cycle planning and produce typed work queues, but it may not pretend to execute Web/model tools it does not have and may not auto-promote behavior.

Optional live semantic/provider execution remains explicit and separately metered.

### G8 · Consumer Upgrade Contract

Project SDK/Adapter validation must understand NovelForge 7.1 locks and optional/required bundle fingerprint verification. The Chinatown consumer will be upgraded only after the final 7.1 framework commit is green and the deterministic bundle fingerprint is known.

## Non-goals

- No consumer novel Canon, characters, plot, private project state, or private user taste in Generic Framework source.
- No autonomous Canon write or next-chapter drafting.
- No automatic General Craft source edit merely because a candidate is promotable.
- No hidden API/model usage in normal CI or weekly maintenance.
- No mass mirroring of modern copyrighted text.
- No named-author imitation profile.
- No requirement that every host provide Web, GitHub, MCP, provider API, Codex, or Claude.

## Runtime Contracts

### Host capability manifest

Minimum fields:
- schema/version;
- host identity and runtime class;
- declared capabilities with availability, provenance and permission scope;
- cost/usage class;
- user-interaction requirement;
- model-execution flag;
- credential material is never embedded.

### Learning-cycle identity

`learning_cycle_id != runtime session_id != semantic job_id != project Canon state`.

A cycle records exact references/fingerprints for every consumed discovery/analysis/eval result and consumes each logical result once.

### Discovery result

Every candidate source records where it came from and what tool/provider returned it. Unknown or analysis-only rights cannot produce stored full text.

### Semantic analysis

Corpus analysis jobs must be bounded to the research question and permitted evidence. They return typed mechanism observations, counterexamples, applicability boundaries, evidence refs and confidence.

### Promotion

A deterministic gate checks evidence completeness only. Human/manager/authorized Framework workflow performs actual behavior-source mutation.

## Acceptance Criteria

1. `runtime_capabilities.py self-test` proves undeclared capabilities are never selected.
2. `learning_cycle.py self-test` proves legal transitions, resume/idempotency, result consume-once, and no Canon authority.
3. `discovery_runtime.py self-test` proves provenance binding, dedupe/diversity accounting, and rights-gate enforcement.
4. `learning_eval.py self-test` proves blind fingerprinted analysis/eval packaging without answer-key leakage.
5. `promotion_gate.py self-test` proves General Craft cannot pass without counterexample, cross-work, eval, rollback and CI evidence.
6. `build_framework_bundle.py self-test` proves deterministic bytes/fingerprint and verification failure after tamper.
7. Top-level `novelforge.py self-test` includes all 7.1 modules.
8. Normal CI compiles and tests all 7.1 modules with `model_execution=false`.
9. Weekly maintenance emits capability-aware queues and never claims Web/model work was executed when unavailable.
10. Paired English/Simplified Chinese docs are updated.
11. `HARNESS_MANIFEST.yaml`, `SKILL*`, README/CHANGELOG and Project SDK report 7.1.0.
12. Final NovelForge CI is green.
13. Chinatown project lock is upgraded to that exact green commit + deterministic bundle fingerprint and its Project CI is green.
14. Chinatown Canon/active story state is unchanged by the engineering migration.

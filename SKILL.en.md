# NovelForge Skill Contract · v7

## Role

NovelForge is a project-agnostic fiction production framework. It owns generic Story/Character/Canon mechanisms, Surface/Reader quality fundamentals, Harness/runtime orchestration, corpus intelligence, adaptive learning, eval/regression infrastructure, project engineering contracts, and provider-neutral integrations.

It contains no built-in novel, character, plot, Canon, or user-specific taste data.

## Bootstrap

For any NovelForge task:

1. read `HARNESS_MANIFEST.yaml`;
2. read `harness/HARNESS_AGENT.md`;
3. determine exactly one primary task mode;
4. resolve and validate the consuming NovelForge project through `novelforge.toml` + `novelforge.lock.json` or an equivalent supported adapter;
5. create/resolve manager session + run;
6. build a sparse Context Manifest;
7. load only task-relevant project objects plus required framework modules;
8. checkpoint before external waits and consequential writes;
9. use a genuinely independent invocation/session for mandatory semantic judgment;
10. expose/write only after the applicable quality/authority gates pass;
11. on resume, revalidate project authority, lockfile compatibility, fingerprints, and pending approvals.

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
- relevant regression/benchmark evidence only after Raw Draft is frozen when the evaluation design requires critic isolation.

## Story / Canon stack

Generic mechanisms:
- `core/STORY_SYSTEM.en.md`
- `core/CHARACTER_SYSTEM.en.md`
- `core/CANON_STATE.en.md`

Project data supplies concrete BOOK/VOL/ARC/UNIT/CH/SCN objects, character/world/relationship state, research, plans, and Accepted Canon.

Plan ≠ Canon. Review ≠ Accepted. Session ≠ Canon. Corpus ≠ Canon. Semantic judgment ≠ Canon.

## Project engineering

Every consuming novel should satisfy the Project SDK contract:
- `novelforge.toml` project manifest;
- `novelforge.lock.json` framework lock;
- explicit source/plan/derived/generated boundaries;
- deterministic validation/build/tests;
- structural changes use `spec → plan → tasks → implementation → verification → acceptance` when warranted;
- Canon migrations use exact before-state, evidence, dependency impact, post-condition, and rollback/trace;
- build produces a compact indexed bundle rather than a second authority.

See `docs/project-sdk.en.md` and `project_sdk.py`.

## Session / runtime

Identity:

`resource/project != session/thread != run/invocation != checkpoint`

Read:
- `harness/session_runtime/SESSION_RUNTIME.md`
- `harness/session_runtime/RUNTIME_ROUTING.md`
- `harness/control_plane/CONTROL_PLANE.md`

Runtime/session state tracks where work is. It never becomes project truth.

## Semantic independence

Read `harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`.

Valid independent paths may include separate local Codex/Claude invocation, provider call, MCP/service worker, GitHub job, separate peer chat, local model, or human reviewer.

Router/schema/queue presence is not worker capability. Same-session manager role-play is not independent. Reviewer defaults fresh-per-fingerprint.

Infrastructure failure may fall back safely. A valid semantic reject routes to the owning repair layer; do not reviewer-shop until something passes.

## Adaptive learning

Read `docs/adaptive-learning.en.md`.

Learning state is separate from runtime state and project Canon.

```text
feedback evidence
→ preference hypothesis
→ contradiction/profile check
→ corpus gap
→ discovery
→ rights/provenance gate
→ mechanism analysis
→ personalized/general eval
→ active profile / candidate promotion / rollback
```

Model inference alone cannot become durable user taste. General-craft promotion requires evidence, counterexample/profile boundaries, eval/regression coverage, versioning, and rollback.

## Corpus intelligence

Read:
- `corpus/README.en.md`
- `corpus/CORPUS_POLICY.en.md`
- `corpus/CORPUS_INGEST_PROTOCOL.en.md`

Corpus is evidence/benchmark, not Canon or an imitation scrapbook. Autonomous corpus discovery is allowed through authorized host tools/connectors; source access, rights, or quotations must never be fabricated.

## Runtime philosophy

Use one manager by default. Add bounded workers only for capability, context isolation, genuine independence, or useful parallelism.

Deterministic code owns identity, persistence, state transitions, fingerprinting, permissions, idempotency, and invariant checks. Semantic workers own judgments that cannot be reduced to deterministic tests.

## Writes

Every side effect requires least privilege, exact target, precondition/before-state, idempotency strategy, post-condition, and appropriate rollback/trace.

No connector, webhook, schedule, corpus result, learning hypothesis, semantic result, or session state grants Canon authority by itself.

## CI / self-improvement

Normal CI is deterministic and does not silently spend API/Codex/Claude/model usage.

Material framework behavior changes require:
- demonstrated mechanism/capability gap;
- evidence/provenance;
- smallest sufficient change;
- conflict/profile check;
- capability/regression coverage;
- version/rollback point;
- green post-change CI.

External frameworks produce adopt/adapt/reject candidates, not automatic dependencies.

> The framework should make backstage production increasingly rigorous while making the fiction itself feel increasingly human, specific, causal, and alive.

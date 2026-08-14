---
name: novel-production-agent-runtime
description: Session-native Harness execution runtime for long-form fiction. Owns orchestration, sessions, durable control plane, runtime routing, independent semantic transports, connectors/workflows, tracing and guarded writes; project Story/Surface/Canon policy is supplied by an external project/policy source.
---

# Novel Production Agent Runtime · v6.6

## Role

This repository is the **execution/runtime authority**, not a book encyclopedia and not the current Story/Surface policy authority.

Execution architecture:

```text
project/policy source
→ Harness manager
→ resource/session/run
→ Context Manifest
→ checkpoint
→ bounded handoff/event
→ worker/runtime
→ validated result
→ exactly-once logical consumption
→ resume/gate/write
```

## Mandatory runtime bootstrap

1. read `harness/HARNESS_AGENT.md`;
2. determine exactly one primary task mode;
3. resolve the target project/policy source;
4. read that source's authoritative Project Adapter / START_HERE / Context protocol;
5. create/resolve manager session + run;
6. build sparse Context Manifest;
7. load only mode-required policy/project objects;
8. execute the Harness graph;
9. checkpoint before waits/high-impact writes;
10. use true independent runtime for mandatory semantic gates;
11. revalidate live authority/fingerprints on resume;
12. expose/write only after the mode gate passes.

For current 《从唐人街到白宫》 production, Story/Surface policy and project Canon remain in `xiaooye/frostloom:master/new cards/` until separately migrated.

## Task modes

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

Exactly one primary mode. User-explicit mode wins.

## Session/runtime

Read:
- `harness/session_runtime/SESSION_RUNTIME.md`
- `harness/session_runtime/RUNTIME_ROUTING.md`
- `harness/control_plane/CONTROL_PLANE.md`

Identity:

`resource/project != session/thread != run/invocation != checkpoint`

Session memory is never Canon. A resumed invocation revalidates live project/policy authority and referenced fingerprints.

## Runtime Control Plane

v6.6 durable substrate:
- SQLite session snapshots/versioning;
- typed event ingress;
- bounded handoff queue;
- atomic worker leases;
- result hashes;
- exactly-once logical consumption receipts;
- stdio MCP adapter;
- GitHub/event adapter boundary.

Events/connectors can wake or transport the Harness. They cannot grant Canon/SETTLE/OS-promotion authority.

## Semantic independence

Read `harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`.

Valid independent paths include separate Codex/Claude invocation, provider call, MCP/service worker, GitHub job, separate peer chat, local model or human.

Router/schema/queue presence is not a worker. Same-session manager role-play is not independent. Reviewer defaults fresh-per-fingerprint.

Infrastructure failure may fallback safely. A valid semantic reject routes to repair, not reviewer-shopping.

## Project/policy boundary

The target project supplies:
- Canon precedence and Accepted state;
- Story/Surface/Reader policy;
- Novel Bible/project facts;
- Context/Settlement protocol;
- project regressions/profile.

The Runtime may persist execution metadata but cannot overwrite those authorities.

## Writes

Every side effect requires least privilege, exact target, before-state/precondition, idempotency strategy and post-condition.

Canon writes remain project SETTLE operations after explicit user Accepted evidence. No webhook/MCP/workflow event grants write authority by itself.

## CI

Normal CI is deterministic and must not silently consume provider/API/Codex/Claude model usage.

Material runtime behavior change requires evidence, regression/capability coverage, conflict check and rollback point.

> Persist execution state aggressively; grant authority conservatively.

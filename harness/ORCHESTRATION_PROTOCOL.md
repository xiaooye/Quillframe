# Orchestration Protocol · v6.6

## Common prefix

```text
resolve runtime authority
→ resolve project/policy authority
→ exactly one task_mode
→ create/resolve manager session
→ start run
→ build Context Manifest
→ resolve Canon cutoff/permissions
→ persist session/checkpoint
→ execute mode graph
```

On resume:

```text
load durable session/checkpoint
→ revalidate both authority domains
→ revalidate artifact fingerprints
→ revalidate pending approval/write intent
→ bind/consume result once
→ continue saved workflow step
```

## Cross-runtime execution

Separate work uses:

```text
bounded artifact
→ handoff envelope
→ Control Plane / direct transport
→ worker claim/session
→ result
→ deterministic binding
→ gate consumer receipt
```

Never use full conversation copying as a default handoff.

## DRAFT / REVISE

The target project/policy source defines the exact prose workflow and quality codes. Runtime responsibilities are:

1. freeze the candidate when an independent gate is reached;
2. keep regression/gold isolation rules supplied by project/policy;
3. create a semantic job/fingerprint;
4. checkpoint manager;
5. route to an independent session/invocation;
6. wait honestly when needed;
7. validate typed result;
8. record logical consumption once;
9. route semantic reject back to the owning repair layer;
10. allow user-visible output only when all mandatory project/runtime gates pass.

Raw/private artifacts remain private when project policy requires it.

## PLAN / DESIGN

Plans are proposal/active-plan artifacts. Runtime execution never upgrades them to Canon. Persisting a plan in a session or handoff does not change authority.

## RESEARCH / CORPUS

External retrieval/analysis uses bounded tasks and provenance. Research truth does not automatically become character knowledge. Corpus evidence does not become Canon.

## SETTLE

Project Settlement protocol is authoritative.

Runtime adds:
- checkpoint before mutation;
- durable write intent;
- exact precondition/idempotency tracking;
- resume revalidation;
- post-condition trace.

A control-plane event may observe/request settlement preparation but may not apply Canon mutation by itself.

## LEARN / SYSTEM-IMPROVE

Behavior-changing runtime work requires:
- demonstrated mechanism/capability gap;
- evidence/provenance;
- regression/capability coverage;
- conflict check against project/policy boundaries;
- smallest sufficient change;
- rollback point;
- post-change CI.

External framework changes remain adopt/adapt/reject evidence, not automatic merge authority.

## Semantic lifecycle

```text
frozen semantic payload
→ blind job
→ fingerprint
→ optional execution lineage
→ checkpoint
→ eligible runtime selection
→ direct execute | queued handoff | peer relay | pending
→ result
→ identity/fingerprint/provenance/lineage validation
→ consume once
```

Changed payload creates a new fingerprint and normally a fresh reviewer. Infrastructure retry can preserve fingerprint. Semantic reject is not infrastructure retry.

## Event lifecycle

```text
external/native event
→ transport adapter
→ novel_os_event_v1
→ idempotency validation
→ persist receipt
→ Harness classification
→ checkpoint/run action if authorized
```

Unsupported event types are rejected. Event arrival does not grant authority.

## Parallelism

Parallelize independent analysis and immutable-input reviews. Do not parallelize writes to shared Canon/project state or the same mutable runtime record without explicit transaction/version semantics.

## Completion states

- `complete`
- `review`
- `awaiting_user`
- `awaiting_external`
- `blocked`
- `failed_gate`
- `semantic_pending`
- `semantic_invalid`
- `settlement_incomplete`

> Resume from validated state; never reconstruct authority from conversational vibes.

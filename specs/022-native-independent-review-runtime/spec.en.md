# Spec 022 · Native Independent Review Runtime

## Status

`SYSTEM-IMPROVE` implementation contract. Frozen baseline:
`05efed31d37a27e901ab777fa3d544e078d65305`.

## Problem

Quillframe currently equates independent semantic review with one GitHub
Project/Actions receipt. Codex and Claude can create fresh native subagent
invocations, but Core cannot attest their lifecycle, bind them to the exact
frozen review packet, or distinguish a valid judgment from caller-fabricated
JSON. The legacy action also rebuilds a packet after Core freezes it, changing
the random relay nonce and causing `independent_packet_mismatch`.

Mapped Projects have a separate broken boundary: their Git/Markdown adapter
can validate and build a deterministic bundle, but cannot materialize bounded
runtime objects in Project SQLite.

## Required invariants

1. Core creates each independent-review packet exactly once. Native, local,
   and GitHub transports consume its canonical exact bytes and use the frozen
   relay nonce as the worker run reference.
2. Native review begins from a one-time durable lease. A lifecycle hook binds
   it atomically to the actual child invocation and a reviewer session distinct
   from the parent session.
3. `quillframe_independent_invocation_receipt_v1` binds Project, run, job,
   candidate/input/packet/result fingerprints, nonce, provider, parent/child
   sessions, host agent/invocation IDs, lifecycle events, assurance class, and
   its self-fingerprint.
4. The receipt is host lifecycle attestation, not cryptographic or OS-level
   isolation. Native assurance is `host_native_separate_context`.
5. The reviewer receives only the frozen packet and declares no Project,
   filesystem, shell, network, memory, or write access.
6. A receipt is valid only when it matches durable lifecycle state.
7. The first valid `pass` or `fail` consumes the run/candidate across all
   transports and providers. Exact evidence may replay idempotently; reviewer
   shopping is forbidden. Only infrastructure failure permits a new invocation.
8. Concurrent identical submission has one processing owner and returns one
   persisted terminal response without duplicated release side effects.
9. `author.run.independent.submit` accepts `independence_receipt`;
   `bridge_receipt` remains a deprecated GitHub-v1 alias.
10. Readiness reports transport, provider, and assurance class without
    universally requiring GitHub issue/comment fields.
11. GitHub review is truthfully identified as `github_copilot_actions` until a
    different provider is implemented. It must consume the frozen packet.
12. Mapped Projects may declare `paths.runtime_context_manifest`. The
    Project-owned manifest explicitly maps source fingerprints to stable IDs,
    object types, authority, lifecycle, domain, allowed stages, targets, and
    bounded runtime payloads. Core never guesses Markdown semantics.
13. `project.projection.preview` is deterministic and read-only;
    `project.projection.apply` is CAS-guarded, idempotent, and transactional;
    `project.projection.status` reports current source/projection identity.
14. Projection never creates Canon, Acceptance, Settlement, accepted
    revisions, or authorial authority. Git/Markdown remains durable authority;
    SQLite is a rebuildable runtime projection.
15. Before the first model call, projected Projects must verify Project,
    target story node/document, and manifest/source fingerprint. Missing or
    stale prerequisites fail closed with zero model invocations.
16. Candidate text remains inaccessible until the exact released candidate is
    read through `candidate.visible.get`.

## Native lifecycle

`author.run.independent.dispatch.prepare` freezes the existing packet and
creates one pending lease for provider and parent session. It returns lease and
dispatch metadata but not candidate text or packet bytes.

`SubagentStart` claims the unique pending lease using trusted parent session,
agent type, and actual agent ID; prompt text is not a trust source. It creates a
fresh reviewer session and injects the frozen packet as additional context.
`SubagentStop` validates one JSON judgment, deterministically wraps the typed
result, records the terminal event, creates the receipt, and submits it. Bad
JSON or a missing hook is infrastructure failure, not semantic rejection.

## Mapped Project projection

The manifest is the semantic compiler boundary. Preview reads only adapter-
declared sources and writes nothing. Apply rechecks source and target snapshots
in one transaction, then writes projected sources, required story/document
targets, the idempotency record, and immutable receipt. Source drift,
authority escalation, or conflicting replay rolls back completely.

## Compatibility

- Existing GitHub peer receipt v1 remains readable.
- Standard Projects and Projects without a runtime manifest retain existing
  behavior.
- Candidate visibility and Acceptance/Settlement contracts do not change.
- This spec does not mutate or repin a consumer repository.

## Acceptance

- Baseline and new native/projection/visibility tests pass.
- Parent/child distinction, lease one-time use, exact packet propagation,
  cross-transport consumption, concurrency, and tool denial are proven.
- Rebuilt/tampered packets, nonce/provider/fingerprint changes, fabricated
  receipts, reused agent IDs, stale candidates, and authority escalation fail
  closed.
- Projection is deterministic, idempotent, atomic, and stage-bounded.
- Missing target/manifest prerequisites cause zero model calls.
- One real native Codex review releases one local Review Draft only through
  `candidate.visible.get`.
- Acceptance and Settlement remain unexecuted.

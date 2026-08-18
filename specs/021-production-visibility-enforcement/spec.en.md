# Spec 021 · Production Visibility Enforcement

## Status

SYSTEM-IMPROVE implementation contract. Frozen baseline: `c6832365be6c4e3816b9c779dd0c2aa88b42cab9`.

## Problem

Quillframe Core already hides raw drafts and returns `candidate_visible=false` while production gates are pending or failed. Agent hosts can still bypass Core by reading Framework instructions and generating manuscript text directly. Ephemeral chat hosts also need a reproducible way to materialize the exact Framework runtime when their sandbox cannot clone GitHub directly.

## Required invariants

1. In `DRAFT` and `REVISE`, a host MUST NOT surface manuscript text unless Core issued a fingerprint-bound production release for the exact candidate.
2. A host assertion, prompt statement, session memory, or boolean copied from an unverified payload is never release evidence.
3. The only public manuscript read path for a production candidate MUST validate run completion, candidate identity, candidate fingerprint, persisted user-visible gate, readiness/release evidence, and revision fingerprint before returning content.
4. Pending, failed, stale, missing, or mismatched evidence MUST return a typed blocked result with no manuscript content field.
5. Raw draft text MUST remain unavailable through the public visibility operation.
6. `quality.production_release` MUST become the final structural release aggregator instead of remaining an unused parallel contract.
7. Ephemeral agent hosts MAY run Quillframe locally, but runtime code MUST be materialized from an exact Git commit with verifiable Git identity. Runtime SQLite is execution state, not a second durable Canon authority.
8. Git-backed consumer Projects remain the durable source/authority when their adapter defines Git as persistence. Settlement remains the only Canon mutation path.
9. Independent semantic review remains genuinely independent and fingerprint-bound; visibility enforcement MUST NOT weaken or emulate it.

## Ephemeral runtime bundle

CI MUST publish an exact-source runtime bundle for the source commit being tested. For pull requests, this is the PR head SHA, not GitHub's synthetic merge SHA. The bundle MUST retain sufficient `.git` metadata for the Framework authority verifier to prove `HEAD == declared source SHA`. The artifact MUST include a SHA-256 digest and a declared source-commit file.

## Host bridge contract

Add a query operation `candidate.visible.get` available to agent-capable read surfaces. It accepts `project_id` and `candidate_id` and either:

- returns `quillframe_user_visible_candidate_v1` with exact candidate content and release evidence when every invariant passes; or
- fails closed with a typed error and no content when release is not proven.

`candidate.review.get` may continue serving Studio review projections, but agent hosts MUST use `candidate.visible.get` to obtain production manuscript text.

## Release composition

`ProductionRunExecutor.submit_independent` MUST aggregate final `quality.production_readiness` through `quality.production_release`. Required structural receipts include at minimum the current Context Freeze / production execution binding and the user-visible gate binding required by the runtime contract. The persisted candidate must be bound to the resulting release fingerprint.

## Acceptance

The change is accepted only when:

- all existing Quillframe tests pass;
- new negative tests prove no release / stale release / mismatched fingerprint / pending gate returns no content;
- a positive test proves a fully released candidate can be read through `candidate.visible.get`;
- an exact PR-head runtime artifact can be downloaded into an isolated Linux directory, passes authority verification, and runs the Core test suite;
- a real DRAFT integration run reaches the appropriate gated state and only a released candidate is shown to the user.

No consumer Project repin or Canon mutation is part of this spec.
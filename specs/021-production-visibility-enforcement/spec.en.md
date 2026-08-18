# Spec 021 · Production Visibility Enforcement

## Status

`SYSTEM-IMPROVE` implementation contract. Frozen baseline: `c6832365be6c4e3816b9c779dd0c2aa88b42cab9`.

## Problem

Quillframe Core already hides raw drafts and returns `candidate_visible=false` while production gates are pending or failed. Agent hosts can still bypass Core by reading Framework instructions and generating manuscript text directly. Ephemeral chat hosts also need a reproducible way to materialize the exact Framework runtime when their sandbox cannot clone GitHub directly.

Real integration testing also exposed three adjacent gaps:

- a pre-release qualified checkpoint contains `candidate_text`, so an agent surface that can enumerate raw checkpoints creates a visibility bypass;
- the Project peer bridge `validate-result` path calls a missing `peer_bridge_receipt.py build` CLI command;
- `author.run.execute` only shallow-checks `rule_material`, allowing an invalid registered-contract shape to fail after expensive production stages have already run.

## Required invariants

1. In `DRAFT` and `REVISE`, a host MUST NOT surface manuscript text unless Core issued a fingerprint-bound production release for the exact candidate.
2. A host assertion, prompt statement, session memory, or boolean copied from an unverified payload is never release evidence.
3. The only public manuscript read path for a production candidate MUST validate run completion, candidate identity, candidate fingerprint, persisted user-visible gate, readiness/release evidence, and revision fingerprint before returning content.
4. Pending, failed, stale, missing, or mismatched evidence MUST fail closed with no manuscript content field.
5. Raw draft and pre-release qualified candidate text MUST NOT be readable through agent-facing inspector/query bypasses.
6. `quality.production_release` MUST be the final structural release aggregator rather than an unused parallel contract.
7. Ephemeral conversational hosts MAY run Quillframe locally, but runtime code MUST be materialized from an exact Git commit with verifiable Git identity. Runtime SQLite is execution state, not a second durable Canon authority.
8. A chat-host manager relay MUST be loopback-only transport, use atomic request/response materialization, declare `independent_review_evidence=false`, and never satisfy the independent gate.
9. Independent semantic review MUST come from a genuinely distinct invocation/provider. Project-owned GitHub Actions MAY use GitHub Models as the separate provider, but the model owns only semantic judgment; exact job/fingerprint/nonce/provenance/receipt binding remains deterministic and is revalidated.
10. `rule_material` MUST be deterministically schema-preflighted against the registered `quality.candidate_self_audit` input contract before the production graph begins. This preflight performs no literary judgment and does not inject regression bad examples into the Writer.
11. Git-backed consumer Projects remain the durable source/authority when their adapter defines Git persistence. Settlement remains the only Canon mutation path.

## Ephemeral runtime bundle

CI MUST publish an exact-source runtime bundle for the source commit being tested. For pull requests, this is the PR head SHA, not GitHub's synthetic merge SHA. The bundle MUST retain sufficient `.git` metadata for the Framework authority verifier to prove `HEAD == declared source SHA`. The artifact MUST include a SHA-256 digest and a declared source-commit file.

## Chat host relay

Framework provides a loopback OpenAI-compatible relay so a conversational sandbox without a directly configured Model API credential can still drive the real Quillframe Model Runtime:

`ProductionRunExecutor → Model Runtime → localhost relay → current manager host → typed response → Core`

The relay is transport only. It does not reinterpret semantic contracts, receives no write authority, and is never independent-review evidence.

## Project-owned independent review

The `project-peer-semantic` action supports independent GitHub Models review. The consumer workflow MUST explicitly grant `models: read`; the consuming Project repository continues to own the issue and runtime trace. The model receives only the bounded peer packet, not the writer conversation or Project checkout. After the model returns a judgment, Framework MUST revalidate exact job identity, candidate fingerprint, relay nonce, registered contract, Project/Framework provenance, and runtime trace before issuing a peer validation receipt.

The manual/fresh-chat `prepare → validate-result` route remains supported and MUST remain executable.

## Host bridge contract

Add `candidate.visible.get`. It accepts `project_id` and `candidate_id` and either:

- returns `quillframe_user_visible_candidate_v1` with exact candidate content and release evidence when every invariant passes; or
- fails closed with a typed error and no content when release cannot be proven.

`candidate.review.get` may continue serving Studio review projections, but agent hosts MUST use `candidate.visible.get` for production manuscript text. `agent_package` MUST NOT enumerate raw production checkpoints that can contain pre-release manuscript text.

## Release composition

`ProductionRunExecutor.submit_independent` MUST aggregate final `quality.production_readiness` through `quality.production_release`. Required structural receipts include at minimum the current Context Freeze / production execution binding and the user-visible gate binding required by the runtime contract. The persisted candidate must bind the resulting release fingerprint.

## Acceptance

The change is accepted only when:

- all existing Quillframe tests pass;
- negative tests prove no release / stale release / fingerprint mismatch / pending gate / raw-checkpoint bypass returns content;
- a positive test proves a fully released candidate is readable through `candidate.visible.get`;
- an exact PR-head runtime artifact downloads into an isolated Linux directory, passes authority verification, and runs the Core suite;
- malformed `rule_material` fails before any semantic generation;
- the localhost manager relay can drive a real DRAFT to independent handoff while candidate/raw draft remain hidden;
- a Project-owned independent provider produces a valid fingerprint/nonce-bound receipt;
- a real DRAFT integration run reaches final production release and only then becomes user-visible.

No consumer Project repin or Canon mutation is part of this spec.
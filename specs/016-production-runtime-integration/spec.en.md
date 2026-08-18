# 016 · Production Runtime Integration & Model Service Foundation

## Authority
- Primary task mode: `SYSTEM-IMPROVE`.
- Frozen Framework authority: `5fd991a5621f2c68e1030aa6e0b35014ca4011c7`.
- Branch: `agent/production-runtime-integration`.
- No consumer Project repin/migration, Canon mutation, novel DRAFT/REVISE delivery, or Studio visual change is authorized.
- Current Studio consumer is PR #130; this workstream owns Core runtime semantics and typed Host Bridge contracts only.

## Problem
Quillframe already had `author.run.start`, Semantic Context Runtime, Agent Runtime and Endpoint+Token Model Runtime, but production execution was not yet one fingerprint-bound runtime transaction. A worker could otherwise depend on later Project reads, Studio lacked a complete production execution boundary, and the Model Runtime lacked a stable product-facing Model Service projection. The authoring UI also required six missing Core primitives rather than browser-owned substitute state: Project list, Document list, Candidate Review evidence, Reject, Request Revision, and Settlement preflight.

## Required architecture
`Project authoritative state → tracked Context source projection → semantic profiles → deterministic eligibility → Context Decision Agent → stage Greenlights → Context Freeze → immutable production Context bundle → mandatory production mechanisms → pre-independent qualification → genuine external independent review → user-visible Review Draft`.

Each mechanism receives only its frozen stage context and bounded upstream artifacts. It receives no SQLite handle and cannot enlarge its own candidate universe. A tracked orchestration preflight may re-read current Project state only to validate that the freeze remains current. Mutation or a newly visible source after freeze produces `stale_conflict`; continuation requires explicit Context refresh/supersession or a fresh run.

## Production mechanisms
The existing mandatory graph remains authoritative: Story/Canon Preflight, Scene Simulation, Character Simulation, Reader Pressure, Event-first Raw Draft, Surface Realization, registered Reader Engagement, Continuity, registered manager self-audit/pre-independent qualification, external Independent Semantic Gate, and User-visible Gate.

Raw Draft/private simulation artifacts never enter user-visible output. A new AgentJob/session is not independence. The manager Model Service must not execute `quality.production_review` as its own release gate. Independent review requires the exact peer packet/result and Project-owned validation receipt. A semantic reject is valid and is not reviewer-shopped until a PASS appears.

## Context bundle
Context Freeze binds candidate universes, stage selections and source/source-state/profile fingerprints. Production additionally persists an immutable selected-source payload bundle so a stage does not need a later DB fetch. The bundle binds the Freeze fingerprint, selected `model_view` payloads, source-universe fingerprint, stage bindings and explicit supersession metadata. Payloads are secret-checked before persistence.

## Model Service
Do not create a second provider subsystem. Extend the existing Generic Model Runtime:
- user setup remains exactly `Endpoint + Access Token`;
- Quillframe discovers protocol/model/capability evidence;
- compatible OpenAI Chat, OpenAI Responses and Anthropic Messages paths are supported where objectively discovered/probed;
- unknown capability remains unknown;
- model capability never grants semantic/Canon/Settlement authority;
- expose stable connect/list/get/discover/test/capabilities and token-lifecycle projections.

## Credential boundary
Access Token values must never enter Project SQLite, Canon, Context, Context Freeze/bundle, AgentJob, receipts, exports, semantic-worker input, or public bridge output. Durable state may contain only `credential_ref` and public presence metadata. Public bridge results redact secret-bearing keys and scrub the corresponding secret values from nested data/error strings. Desktop should inject a Tauri/OS-keychain SecretStore; hosted environments should inject server-side secure secret/session storage. Generic Core has no Cloudflare dependency.

## Host Bridge v8 authoring primitives
Core-owned Host Bridge exposes real typed operations only. In addition to the production/model/document primitives, v8 must provide:
- `project.list`: canonical read-only global Project registry projection;
- `document.list`: canonical project document list with latest revision identity/fingerprint;
- `candidate.review.get`: exact Candidate-bound Review projection with safe Reader, Character, Continuity, Independent and production-readiness evidence, incumbent revision and diff; private reasoning is not exposed;
- `candidate.reject`: explicit, exact-fingerprint, idempotent Reject; no Canon/Settlement write;
- `candidate.revision.request`: durable Request Revision receipt/event and effective state; it must not silently start REVISE, and the old Candidate becomes non-acceptable;
- `settlement.preflight`: read-only authoritative acceptance/fingerprint/current-Canon before-state validation; mutation occurs only in separately authorized `settlement.apply`.

Unsupported project delete/portable import-export/free-floating review capabilities remain explicitly unsupported or `awaiting_external`, never fabricated.

## Persistence hygiene
SQLite connection owners must actually close context-managed connections while preserving WAL, foreign keys, busy timeout and durability policy.

## Acceptance
Deterministic acceptance requires tests proving frozen-only production Context, no stage hidden DB fetch, Research≠Character Knowledge, invalid Context IDs rejected, stale source universe blocked, explicit refresh supersession, mandatory graph preservation, real independent-review boundary, secret-safe Endpoint+Token discovery/probes, truthful provider failures, bridge output secret scrubbing, SQLite hygiene, the six v8 authoring primitives and lifecycle guards, existing authority contracts, Studio typecheck/build, docs/site checks, and deterministic exact Framework bundle verification.

A real provider acceptance is required only when a usable credential/provider capability is actually present. Otherwise semantic readiness remains `PENDING_MODEL / awaiting_external`; deterministic fixtures are never promoted to live acceptance.

# 016 · Production Runtime Integration & Model Service Foundation

## Authority
- Primary task mode: `SYSTEM-IMPROVE`.
- Frozen Framework authority: `5fd991a5621f2c68e1030aa6e0b35014ca4011c7`.
- Branch: `agent/production-runtime-integration`.
- No consumer Project repin/migration, Canon mutation, DRAFT/REVISE user artifact, or Studio visual change is authorized.
- Parallel Studio UI work is PR #129; this workstream owns Core runtime semantics and Host Bridge Core contracts only.

## Problem
Current Quillframe can register `author.run.start`, has a first-class Semantic Context Runtime, Agent Runtime, and Endpoint+Token Model Runtime, but production execution is not yet one fingerprint-bound runtime transaction. A production worker could otherwise require later Project reads, and Studio has no real `author.run.execute` Core primitive. Model Service discovery exists in lower layers but lacks a stable Core/Bridge projection for connect/discover/test/capabilities.

## Required architecture
`Project authoritative state → tracked Context source projection → semantic profiles → deterministic eligibility → Context Decision Agent → stage Greenlights → Context Freeze → immutable production Context bundle → production mechanisms → gated Candidate → independent fingerprint-bound review → Review Draft`.

Each mechanism receives only its frozen stage context and bounded upstream artifacts. It receives no SQLite handle and cannot expand its own candidate universe. A tracked orchestration preflight may re-read current Project state before a mechanism only to validate that the freeze remains current. Mutation/new source after freeze produces `stale_conflict`; continuation requires explicit Context refresh/extension or a fresh run.

## Production mechanisms
The existing mandatory mechanisms remain authoritative and are not redesigned:
1. Story/Canon Preflight
2. Scene Simulation
3. Character Simulation
4. Reader Pressure
5. Event-first Raw Draft
6. Surface Realization
7. Reader Engagement
8. Continuity
9. Independent Semantic Gate
10. User-visible Gate

Raw Draft and private simulation artifacts never enter public receipts. Independent review must be a genuinely separate semantic invocation and exact candidate/result fingerprints remain binding. A semantic rejection is not retryable by reviewer-shopping.

## Context bundle
The existing Context Freeze binds candidate universes, stage selections, source/source-state/profile fingerprints. Production adds an immutable payload bundle because profile metadata alone is insufficient to execute a stage without a later DB fetch. The bundle binds the Context Freeze fingerprint, full selected source `model_view` payloads, source-universe fingerprint, stage bindings, and explicit supersession metadata. Payload values are secret-checked before persistence.

## Model Service
Do not create a second provider subsystem. Extend the existing Generic Model Runtime:
- user setup remains exactly `Endpoint + Access Token`;
- Quillframe discovers protocol/model/capability evidence;
- support current OpenAI Chat, OpenAI Responses, and Anthropic Messages dialects where objectively discovered/probed;
- unknown capability remains unknown;
- model capability never grants semantic/Canon/Settlement authority;
- add stable connect/list/get/discover/test/capabilities projections.

## Credential boundary
Access Token values must never enter Project SQLite, Canon, Context, Context Freeze/bundle, AgentJob, receipts, logs, exports, or semantic worker inputs. Durable state may contain only `credential_ref` and public presence metadata. Hosts inject a SecretStore: Desktop should use Tauri/OS keychain; hosted environments should use server-side secure secret/session storage. Generic Core has no Cloudflare dependency. Process-local MemorySecretStore is a non-durable fallback, not a persistence promise.

## Host Bridge
Core-owned Host Bridge contract advances additively and must expose real primitives only. Required additions include document open/revision list, run status/execute/context refresh, Model Service lifecycle/test/discovery/capabilities, and existing Context Inspector. Unsupported project delete/portable import-export/ad-hoc review capabilities are reported as unsupported rather than fabricated.

## Persistence hygiene
Fix the known SQLite ResourceWarning source by ensuring repository/store context-managed connections actually close, without changing WAL, foreign-key, busy-timeout or durability policy.

## Acceptance
Deterministic acceptance requires tests proving:
- production mechanisms receive only frozen stage payloads;
- no stage-time hidden DB fetch path;
- Research does not become Character Knowledge;
- invalid semantic Context IDs are rejected, not guessed;
- source mutation/new source after freeze blocks execution;
- explicit refresh creates a new bundle fingerprint;
- mandatory graph cannot be disabled;
- selection/capability cannot create authority;
- independent review is a separate invocation and no reviewer-shopping occurs;
- Endpoint+Token discovery/probe capability evidence remains secret-safe;
- bad endpoint/token/network/unsupported protocol remain truthful failures;
- Host Bridge secret values are redacted from request/result fingerprints and durable state;
- SQLite connections close cleanly;
- existing Agent/Context/Model/Settlement/authority tests remain green;
- Studio TypeScript still builds against the public bridge contract.

A real provider acceptance is required only when a usable credential/provider capability is actually present. Otherwise final semantic readiness is `PENDING_MODEL / awaiting_external`, never a deterministic mock PASS.

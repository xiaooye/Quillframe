# Frontend Contract Handoff · Host Bridge v8

Current consumer: Studio PR #130.

## Ownership
UI owns SolidJS/Tauri presentation, routes, Writer/Review/Inspector UX and BridgeClient transport. Core owns operation semantics, authority, persistence and typed errors. UI must not read SQLite directly, reproduce Python production logic, or create browser-owned semantic/authority truth.

This Core workstream changes no `studio/app/**` visual/frontend composition files.

## Production state machine
`author.run.start` durably registers exactly one authoring task mode. `author.run.execute` consumes frozen Context and runs the mandatory production graph through registered Reader/manager qualification, then normally returns `awaiting_external` with a fingerprint-bound peer packet. Raw Draft is never returned and no Review Draft Candidate exists yet.

The same manager/Writer/Model Service cannot satisfy the independent gate. `author.run.independent.submit` requires the exact peer packet, external semantic result and current Project-owned `quillframe_project_peer_validation_receipt_v2`; v1 remains valid only for historical replay compatibility. Only a valid independent PASS that satisfies `quality.production_readiness` can create a user-visible Review Draft. Independent FAIL is `failed_gate`; do not reviewer-shop the same run.

Any tracked source/project change after freeze returns `stale_conflict`. `author.run.context.refresh` is the explicit supersession path; Core never silently edits an old freeze.

## Context boundary
Each production mechanism receives only its frozen stage Context plus bounded upstream artifacts. Stage materialization has no SQLite/store access path and reports `db_fetch_performed=false`. Workers cannot enlarge the candidate universe or perform hidden Project retrieval.

## Authoring primitives added in v8
These six primitives close the blockers reported by Studio PR #130:

### `project.list`
Read-only canonical global Project registry projection. Browser storage is not authority.

### `document.list`
Read-only canonical Binder/document list for one Project. Items include latest revision identity/fingerprint/authority metadata.

### `candidate.review.get`
Exact Candidate-bound Review projection. It fails closed on missing/stale independent evidence and returns the Review Draft revision, incumbent parent revision, unified diff, and safe Reader/Character/Continuity/Independent/production-readiness/user-visible-gate evidence. `private_reasoning_exposed=false`.

### `candidate.reject`
Explicit user-authorized, exact-fingerprint, idempotent Reject. It moves an actionable Review Draft to `rejected`, writes an auditable receipt/event, and does not mutate Canon or Settlement.

### `candidate.revision.request`
Explicit user-authorized, exact-fingerprint, idempotent durable Request Revision. Physical Candidate status stays within the existing schema; Core projects effective status `revision_requested`, blocks later Accept/Reject of that old Candidate, and returns an explicit next-action descriptor for `author.run.start` with `task_mode=REVISE`. It **does not auto-start REVISE**.

### `settlement.preflight`
Read-only authoritative Acceptance/Candidate/source-revision/current-Canon validation. It returns exact `expected_before_fingerprint` (`absent` when no Canon target exists) for a separately user-authorized `settlement.apply`. Preflight performs no mutation.

## Model Service
User setup remains **Endpoint + Access Token**. Core discovers protocol/model/capability evidence and exposes `model.service.add/list/get/discover/test`, token lifecycle commands, delete, and `model.capabilities`. Unknown remains unknown. Capability never grants semantic, Canon, or Settlement authority.

## Credential boundary
Credential values remain in the host-injected SecretStore; durable Core stores only `credential_ref` plus public metadata. Bridge request fingerprints redact credentials, and public result/error projections also scrub exact secret values if an upstream provider echoes them inside nested strings. Business authorization objects for Candidate actions remain fingerprint-bound and are not treated as credentials.

Desktop should inject Tauri/OS-keychain storage. Hosted Web should inject server-side secure secret/session storage. `MemorySecretStore` is process-local fallback only. Generic Core has no Cloudflare dependency.

## Deferred, not fabricated
- `project.delete`: `unsupported` until a reversible Core transaction exists.
- portable `project.export/import`: `awaiting_external` until a transport contract exists.
- free-floating `candidate.review.request`: `unsupported`; mandatory semantic review belongs to production execution.

## Studio PR #130 integration sequence
After Core PR #131 merges, rebase/integrate PR #130 from fresh main and make BridgeClient consume v8 operations as authority:
1. replace browser-owned Project registry with `project.list`;
2. replace fixture Binder/document truth with `document.list`;
3. hydrate Review from `candidate.review.get`;
4. wire Accept / `candidate.reject` / `candidate.revision.request` as explicit typed commands;
5. call `settlement.preflight` immediately before `settlement.apply` and pass its exact before fingerprint;
6. preserve execute → `awaiting_external` → independent transport → `author.run.independent.submit`;
7. keep Endpoint+Token Model Service UX on the typed bridge.

Then run the Studio typecheck/tests/build and real browser smoke on Web plus the available Tauri contract surface. Do not copy Python runtime logic into the frontend.

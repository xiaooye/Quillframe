# Frontend Contract Handoff · Host Bridge v7

Parallel consumer: Studio PR #129.

## Ownership
The UI owns SolidJS/Tauri presentation, routes, AI/Models UX, Writer/Review/Inspector UX and BridgeClient transport adapters. Core owns operation semantics, authority, persistence and typed error states. UI must not directly read SQLite, reproduce Python production logic, or invent a UI-specific authority model.

No Studio visual/frontend composition files are changed by this Core workstream.

## Production state machine

### `author.run.start`
Input: `project_id`, one `task_mode`, `payload`, optional `target_ref/session_id/idempotency_key`.
Output: durable run with `awaiting_semantic`. This creates no Candidate.

### `author.run.status`
Input: `project_id`, `run_id`.
Output: current run status, persisted typed runtime events, result fingerprint and latest Candidate projection when one exists.

### `author.run.execute`
Required input:
- `project_id`
- `run_id`
- `service_id`
- `instruction`
- `reader_grip`
- `rule_material`
- `independent_provenance` containing `project_id`, `project_repo`, `framework_repo`, `framework_commit`

Optional input: `document_id`, `model_id`, `stage_budgets`, `reader_visible_context`, `repair_preservation`.

DRAFT/REVISE path:

`Context profiles → eligibility/Decision/Greenlights → deterministic packing → Context Freeze + immutable payload bundle → Story/Canon Preflight → Scene Simulation → Character Simulation → Reader Pressure → Event-first Raw Draft → Surface Realization → registered Blind Reader (reader.engagement_audit) → Continuity → registered manager self-audit (quality.candidate_self_audit) → pre-independent qualification → external quality.production_review handoff`.

A successful local/manager execution normally returns `status=awaiting_external` plus a fingerprint-bound `independent_review_request.peer_packet`. At this point:
- Raw Draft is not returned.
- Review Draft Candidate does not exist yet.
- the same Writer/manager/model-service invocation cannot satisfy independence.
- the peer packet requires a fresh independent conversation/worker.

Important typed states/errors include `awaiting_external`, `completed`, `stale_conflict`, `failed_gate`, `semantic_pending`, `run_in_progress`, `failed_gate_requires_fresh_run`, `target_document_required`, `not_qualified_for_independent`, plus typed Model Runtime errors.

### `author.run.independent.submit`
Required input:
- `project_id`
- `run_id`
- exact frozen `peer_packet`
- peer semantic `result`
- Project-owned `bridge_receipt`

Core validates the exact registered `quality.production_review` job, peer relay nonce/result binding, `quillframe_project_peer_validation_receipt_v1`, candidate fingerprint, pre-independent qualification and the still-current frozen Context boundary. A valid independent PASS may then satisfy `quality.production_readiness` and create one user-visible Review Draft Candidate. An independent FAIL returns `failed_gate`; the same run is not reviewer-shopped until a PASS appears.

A Review Draft is still neither Accepted nor Settled.

### `author.run.context.refresh`
Explicitly creates a new fingerprint-bound Context bundle after source state changes. It never silently mutates an existing freeze. Returns new bundle/freeze fingerprints plus supersession linkage. Any source/project mutation detected before production continuation or independent submission produces `stale_conflict` instead of silent continuation.

## Context contract consumed by production
Every production mechanism receives only its current run's materialized frozen stage context plus upstream artifacts. Stage packets expose `context_fingerprint`, `stage_context_fingerprint`, source fingerprints and selector provenance. Stage materialization has no SQLite/store access path and reports `db_fetch_performed=false`.

Workers cannot enlarge the candidate universe or perform hidden DB retrieval. Additional context requires explicit refresh/extension semantics and a new fingerprint.

## Model Service operations
The product setup model remains exactly **Endpoint + Access Token**. Provider/protocol labels are discovered compatibility evidence, not required user choices and never authority.

- `model.service.add(endpoint, access_token)` — connect/discover and persist public service/model metadata; the secret value remains in injected host SecretStore.
- `model.service.list()` / `model.service.get(service_id)` — public metadata only.
- `model.service.discover(service_id)` — refresh discovery using the host credential reference.
- `model.service.test(service_id, model_id?, verify_tools?)` — bounded real protocol/text/tool probe.
- `model.capabilities(service_id)` — public per-model capability-evidence matrix. Unknown remains unknown; capability grants no authority.
- `model.service.token.replace/remove` and `model.service.delete` — explicit lifecycle commands.

The underlying Generic Model Runtime discovers compatible protocol/model evidence rather than requiring a vendor selection. Supported compatibility paths include OpenAI-style model listing, Responses-compatible and Chat-Completions-compatible invocation, Anthropic-compatible Messages where objectively discovered, plus local/custom compatible endpoints. Tool support is verified by probe when requested rather than inferred from vendor branding.

Failure states remain typed Model Runtime errors, including invalid endpoint, authentication/discovery failure, network failure, unresolved/unsupported protocol, unavailable credential and no eligible model.

## Credential boundary
Bridge request fingerprints redact credential values such as `access_token`; business authorization objects used by Candidate Acceptance remain fingerprint-bound. Token values never enter Canon, project semantic state, Context, Context Freeze, AgentJob, semantic-worker input, receipts, logs, exports or `.qfproject` data.

Host integration requirement:
- Desktop: inject a Tauri/OS-keychain `SecretStore` through `configure_secret_store`.
- Hosted Web: inject a server-side secure secret/session facility.
- `MemorySecretStore` is process-local fallback only and must not be presented as durable credential persistence.
- Generic Core has no Cloudflare dependency.

## Other stable Core operations
Available operations include project create/open/inspect/search/backup/restore; document create/open/save/revisions/compare; Candidate Accept; Settlement apply; publication preview/build; feedback capture; and Inspector projections for sessions, runs, checkpoints, Context, receipts, Candidates, learning and Context Runtime.

## Explicitly deferred
Do not fabricate normal-path success for:
- `project.delete` — `unsupported` until a reversible Core-owned delete transaction exists.
- `project.export` / `project.import` — `awaiting_external` until a portable transport contract exists.
- `candidate.review.request` — `unsupported` as a free-floating authority path; mandatory review belongs to the production state machine above.

## Stream/event behavior
Host Bridge v7 operations are request/response. Durable `runtime_events`, run status and checkpoints are the canonical progress surface. A WebSocket/Tauri event transport may project those states later, but transport must not change Core semantics or create a second state machine.

## UI integration sequence
After this Core PR is reviewed/merged, UI PR #129 should rebase on fresh main and reconcile its overlapping `studio/host_bridge.py` / `host_bridge_contract.json` edits in favor of Core v7 semantics. BridgeClient should then implement:
1. run start/status;
2. execute → `awaiting_external` handoff;
3. host/project peer-review transport;
4. `author.run.independent.submit`;
5. Review Draft / Candidate acceptance / Settlement flows;
6. Model Service Endpoint + Token setup/discovery/test/capability views.

Run Web + Tauri E2E after rebase. Do not copy Python runtime logic into the frontend.

# Frontend Contract Handoff · Host Bridge v6

Parallel consumer: Studio PR #129.

## Ownership
The UI owns SolidJS/Tauri presentation and BridgeClient transport adapters. Core owns the operations below, their authority semantics, persistence and error states. UI must not directly read SQLite or create replacement semantic truth.

## Production operations
### `author.run.start`
Input: `project_id`, one `task_mode`, `payload`, optional `target_ref/session_id/idempotency_key`.
Output: durable run with `awaiting_semantic`. This does not create a Candidate.

### `author.run.status`
Input: `project_id`, `run_id`.
Output: current run status, persisted events and latest candidate projection when one exists.

### `author.run.execute`
Input: `project_id`, `run_id`, `service_id`, `instruction`, optional `document_id/model_id/stage_budgets`.
Normal DRAFT/REVISE path: Context profiles/Decision/Greenlights/Freeze → frozen payload bundle → mandatory production mechanisms → independent semantic gate → user-visible gate → Review Draft Candidate.
Possible states/errors: `completed`, `stale_conflict`, `failed_gate`, `semantic_pending`, `run_in_progress`, `failed_gate_requires_fresh_run`, `target_document_required`, Model Runtime errors. Raw Draft is never returned.
Authority: false. A completed Candidate is still not Accepted or Settled.
Streaming: v6 is request/response. Progress is represented by persisted typed `runtime_events`; clients may refresh `author.run.status` or use a host event transport later without changing Core semantics.

### `author.run.context.refresh`
Explicitly creates a new fingerprint-bound Context bundle after source state changes. It never silently mutates the existing freeze. Returns new bundle/freeze fingerprints and supersession linkage.

## Model Service operations
User mental model remains exactly Endpoint + Access Token.

- `model.service.add(endpoint, access_token)` — discover and persist public service/model metadata; secret value remains in injected host SecretStore.
- `model.service.list()` / `model.service.get(service_id)` — public metadata only.
- `model.service.discover(service_id)` — refresh discovery using the host credential reference.
- `model.service.test(service_id, model_id?, verify_tools?)` — bounded real protocol/text/tool probe.
- `model.capabilities(service_id)` — public capability-evidence matrix. Unknown remains unknown; capability grants no authority.
- `model.service.token.replace/remove` and `model.service.delete` — explicit lifecycle commands.

Failure states remain typed Model Runtime errors, including invalid endpoint, discovery failure, network failure, unresolved protocol, unavailable credential and no eligible model.

## Credential boundary
Bridge request fingerprints redact only credential values such as `access_token`; business authorization objects used by Candidate Acceptance remain fingerprint-bound. Token values never enter SQLite, Context, AgentJob, receipts, exports or semantic worker payloads.

Host integration requirement:
- Desktop: inject a Tauri/OS-keychain `SecretStore` through `configure_secret_store`.
- Hosted Web: inject a server-side secure secret/session store.
- MemorySecretStore is process-local fallback only and must not be presented as durable credential persistence.
- No Cloudflare API/binding is part of this contract.

## Document/project operations added
- `project.open` (same Core projection as inspect)
- `project.restore` (CLI/local_app only; hosted file upload transport remains separate)
- `document.open`
- `document.revisions.list`

Existing backup, revision save/compare, Candidate Accept, Settlement, publication and Inspector operations remain compatible.

## Explicitly deferred
Do not fabricate normal-path success for:
- `project.delete` — unsupported until a reversible Core delete transaction exists.
- `project.export` / `project.import` — awaiting a portable transport contract.
- `candidate.review.request` — unsupported as a free-floating operation; mandatory review belongs to production execution.

## UI integration sequence
After this Core PR is reviewed/merged, UI PR #129 should rebase on fresh main, reconcile its overlapping `studio/host_bridge.py` / `host_bridge_contract.json` changes in favor of Core v6 semantics, wire BridgeClient to the real operations, then run Web + Tauri E2E. Do not copy Python runtime logic into the frontend.

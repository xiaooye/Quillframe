# Quillframe Studio → Core consumer handoff

Frozen Studio authority: `5fd991a5621f2c68e1030aa6e0b35014ca4011c7`.

This file records **consumer requirements**, not Core implementation design. Studio must not implement these semantics in TypeScript, browser storage, Tauri Rust, Cloudflare bindings, or fixtures.

| Desired operation | User action | Minimal input | Minimal output | Required error states | Authority expectation | Why Studio cannot implement it |
|---|---|---|---|---|---|---|
| `project.list` | Open an existing Project without remembering its id | pagination/cursor optional | `project_id`, title, language, last-opened metadata | `host_unavailable` | read-only, `authority=false` | Browser history is not the canonical Project registry. |
| `document.list` | Populate Binder | `project_id`, optional kind | document id/title/story node + latest revision id/fingerprint | `project_not_found` | read-only | UI cannot infer canonical manuscript structure from browser state. |
| `document.get` | Open/reload/restart an existing manuscript safely | `project_id`, `document_id` | metadata + exact latest revision content/id/fingerprint/authority class | `document_not_found`, `revision_not_found` | read-only; preserve persisted authority | Without this, Studio must not restore text from localStorage or switch manuscript buffers. |
| `model.connect` | Settings → AI & Models → Endpoint + Access Token → Test / Connect | endpoint, access token | service id, connection/discovery state, discovered model/capability evidence or refs | `endpoint_unreachable`, `authentication_failed`, `unsupported_protocol`, `discovery_failed` | runtime observation only; never echo secret | Provider protocols, discovery and secret storage are Core-owned. |
| `model.services.list` | Show Model Services and available Models | none | service metadata, `credential_present`, discovered model/capability projection | `host_unavailable` | read-only; no token values | Endpoint history/vendor hostname is not health or capability evidence. |
| `author.run.execute` | Continue a real `awaiting_semantic` author Run | `project_id`, `run_id` or exact registered receipt | typed status and Candidate/result ref only after production gates | `semantic_pending`, `model_unavailable`, `context_failed`, `review_failed`, `cancelled` | no raw-draft visibility; Candidate only after user-visible gate | Semantic execution, Context Freeze and independent review are Core-owned. |
| `run.events.list` | Show AI Dock progress | `project_id`, `run_id` | safe stage/event/status/timestamp records | `run_not_found` | read-only; private CoT excluded | UI cannot infer completed semantic stages from timers or animations. |
| `candidate.review.get` | Incumbent vs Candidate Review | `project_id`, `candidate_id` | incumbent/candidate revision refs/content or diff source, findings, Reader evidence, Character integrity, Continuity, independent review, exact fingerprints | `candidate_not_found`, `review_pending`, `stale_review` | read-only fingerprint-bound evidence | Candidate table metadata cannot reconstruct prose or semantic evidence. |
| `candidate.reject` | Click Reject | `project_id`, candidate id/fingerprint, explicit authorization, idempotency key, optional rejection reason/evidence | durable candidate state transition + receipt | `candidate_not_found`, `candidate_fingerprint_mismatch`, `already_accepted`, `stale_state`, `authorization_required` | operation-specific candidate mutation; no Canon/Settlement authority | `feedback.observe` is learning intake, not Candidate lifecycle mutation. |
| `candidate.revision.request` | Click Request Revision | `project_id`, candidate id/fingerprint, explicit revision request, idempotency key | durable revision-request state/receipt and next permissible action/run ref if Core defines one | `candidate_not_found`, `candidate_fingerprint_mismatch`, `already_accepted`, `stale_state`, `authorization_required` | operation-specific Candidate/Run transition; no silent DRAFT/REVISE chaining | Studio cannot convert a Review action into a new semantic Run without Core policy. |
| `settlement.preflight` | Click Settle… after explicit Acceptance | `project_id`, acceptance id, target ref | exact current before fingerprint + accepted/candidate fingerprints + readiness | `acceptance_not_found`, `before_state_conflict`, `not_settleable` | read-only preflight; no Canon mutation | `settlement.apply` requires exact canonical before-state that only Core may read. |

## Secondary authoring projections

These are lower priority than the primary vertical slice but still Core-owned:

- typed Plan + Scene Card projection and operation-specific mutations;
- typed Character / Relationship / World / Timeline / Canon Story projection with textual authority fields;
- Research/Corpus source, provenance, rights and claim projections;
- model preference/default-selection contract if exact user model preference becomes supported.

## Host primitives

Hosted Web requires a real durable Core API endpoint compatible with the same typed Bridge semantics. Tauri requires a real `bridge_invoke` local host primitive. These are host integration requirements; neither permits Studio to copy Python Core semantics.

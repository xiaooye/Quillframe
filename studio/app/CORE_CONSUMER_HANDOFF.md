# Quillframe Studio → Core consumer handoff

Frozen Studio authority: `5fd991a5621f2c68e1030aa6e0b35014ca4011c7`.

This file records **consumer requirements**, not Core implementation design. Studio must not implement these semantics in TypeScript, browser storage, Tauri Rust, Cloudflare bindings, or fixtures.

## Current-main gaps

The operations below are still missing from current `main`. They also remain missing in the observed Draft Core PR #131 unless stated otherwise. Studio therefore keeps the corresponding actions `awaiting_external` / disabled instead of synthesizing authority.

| Desired operation | User action | Minimal input | Minimal output | Required error states | Authority expectation | Why Studio cannot implement it |
|---|---|---|---|---|---|---|
| `project.list` or equivalent | Open an existing Project without remembering its id | pagination/cursor optional | `project_id`, title, language, optional last-opened metadata | `host_unavailable` | read-only, `authority=false` | Browser history is not the canonical Project registry. |
| `document.list` or equivalent | Populate Binder | `project_id`, optional kind | document id/title/story node + latest revision id/fingerprint | `project_not_found` | read-only | UI cannot infer canonical manuscript structure from browser state. |
| `candidate.review.get` or equivalent typed Candidate Review projection | Incumbent vs Candidate Review | `project_id`, `candidate_id` | incumbent/candidate revision refs or diff source; Reader, Character, Continuity and Independent Review / production-readiness evidence; exact Candidate fingerprint binding | `candidate_not_found`, `review_pending`, `stale_review` | read-only fingerprint-bound evidence; no private CoT | Candidate table metadata cannot reconstruct prose or semantic evidence. |
| `candidate.reject` or equivalent | Click Reject | `project_id`, candidate id/fingerprint, explicit authorization, idempotency key, optional rejection reason/evidence | durable candidate state transition + receipt | `candidate_not_found`, `candidate_fingerprint_mismatch`, `already_accepted`, `stale_state`, `authorization_required` | operation-specific Candidate mutation; no Canon/Settlement authority | `feedback.observe` is learning intake, not Candidate lifecycle mutation. |
| `candidate.revision.request` or equivalent | Click Request Revision | `project_id`, candidate id/fingerprint, explicit revision request, idempotency key | durable revision-request state/receipt and next permissible action/run ref if Core defines one | `candidate_not_found`, `candidate_fingerprint_mismatch`, `already_accepted`, `stale_state`, `authorization_required` | operation-specific Candidate/Run transition; no silent DRAFT/REVISE chaining | Studio cannot convert a Review action into a new semantic Run without Core policy. |
| `settlement.preflight` or equivalent authoritative before-state read | Click Settle… after explicit Acceptance | `project_id`, acceptance id, target ref | exact current `canon_state[target_ref]` fingerprint or `absent`, accepted/candidate fingerprint binding, settleability | `acceptance_not_found`, `before_state_conflict`, `not_settleable` | read-only preflight; no Canon mutation | `settlement.apply` requires `expected_before_fingerprint`; Studio has no authority to derive or guess it. |

### Settlement safety note

The observed Draft Core PR #131 exposes `settlement.apply`, but that command correctly requires an exact `expected_before_fingerprint`. No current read operation exposes the authoritative current fingerprint for an arbitrary settlement `target_ref`. Therefore the Studio **must keep `Settle…` disabled** until Core exposes a non-mutating preflight/current-state projection. Sending a browser-derived or guessed value would violate the exact before-state contract even if Core would fail closed with `settlement_incomplete`.

## Observed Draft Core PR #131 candidate mappings

These mappings are **not current Core truth and are not enabled by Studio**. They were observed on Draft PR #131 only so that Studio does not request duplicate primitives. Activation requires: Core PR review + merge → fresh-main rebase/reconcile → exact contract compatibility tests → Web/Tauri E2E.

| Studio product concept | Draft PR #131 exact Core operation(s) | Studio state before merge |
|---|---|---|
| Reload/restart exact manuscript | `document.open` | `pending_core_pr_131` |
| Revision history | `document.revisions.list` | `pending_core_pr_131` |
| Endpoint + Access Token connection | `model.service.add` | `pending_core_pr_131` |
| Refresh discovered models/protocol evidence | `model.service.discover` | `pending_core_pr_131` |
| Test a discovered model/capability | `model.service.test` | `pending_core_pr_131` |
| List connected Model Services | `model.service.list` | `pending_core_pr_131` |
| Read per-model capability evidence | `model.capabilities` | `pending_core_pr_131` |
| AI Dock durable run progress/events | `author.run.status` | `pending_core_pr_131` |
| Execute DRAFT/REVISE production graph | `author.run.execute` | `pending_core_pr_131` |
| Explicit stale-Context refresh | `author.run.context.refresh` | `pending_core_pr_131` |
| Submit externally independent semantic result | `author.run.independent.submit` | `pending_core_pr_131` |

### Important adapter replacements after merge

The earlier Studio consumer names below were conceptual placeholders and must **not** become duplicate Core APIs:

- `document.get` → use merged `document.open` if its final response still contains exact latest persisted revision content/id/fingerprint/authority class.
- `model.connect` → use merged `model.service.add`, then `model.service.discover` / `model.service.test` as required by the final contract.
- `model.services.list` → use merged `model.service.list`.
- `run.events.list` → use merged `author.run.status` if the final status projection still exposes durable typed runtime events; Studio must not invent a parallel progress/event API.

`author.run.execute` already has the desired product meaning in Draft PR #131, but remains inactive until the Core PR is merged. Studio must preserve `raw_draft_visible=false`, Candidate visibility only after the real user-visible gate, explicit `awaiting_external` independent-review handoff, and typed `stale_conflict` / `failed_gate` / `semantic_pending` states.

## Secondary authoring projections

These are lower priority than the primary vertical slice but still Core-owned:

- typed Plan + Scene Card projection and operation-specific mutations;
- typed Character / Relationship / World / Timeline / Canon Story projection with textual authority fields;
- Research/Corpus source, provenance, rights and claim projections;
- model preference/default-selection contract if exact user model preference becomes supported.

## Host primitives

Hosted Web requires a real durable Core API endpoint compatible with the same typed Bridge semantics. Tauri requires a real `bridge_invoke` local host primitive. These are host integration requirements; neither permits Studio to copy Python Core semantics.

Draft Core PR #131 remains a parallel Core workstream. PR #130 must not stack or merge it before Core review/merge. After it lands on `main`, Studio must freeze fresh `main`, reconcile only the merged contract, and rerun the full Studio + browser + responsive/accessibility verification gates.
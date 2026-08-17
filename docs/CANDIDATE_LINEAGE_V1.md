# Candidate Lineage v1

Status: Framework structural extension; derived authority only.

## Problem

`quality/quality_evolution.py` already models an incumbent/challenger evolution graph and exact fingerprint-bound `quality.compare` jobs. Its legacy `parent_candidate_id` has one necessary meaning: the challenger must descend from the **current comparison incumbent**. After objective-preserving repair landed, that field is insufficient to answer a different question: **did this candidate actually reuse the parent's prose?**

A repair normally does. A fresh regeneration deliberately must not consume the rejected/incumbent prose even though it competes against that incumbent. Treating one `parent_candidate_id` as both relationships makes runtime/debugging ambiguous and makes review/acceptance provenance harder to audit.

## Decision

ADOPT an additive Candidate Lineage projection over the existing quality-evolution ledger. Do not create a second comparator, objective envelope, candidate winner, Canon system, settlement system, or Git branch per prose candidate.

The existing `evolution_candidates.parent_candidate_id` remains **comparison ancestry**. Candidate Lineage adds:

- `origin = draft | repair | fresh_regeneration | user_edit`
- `comparison_parent_candidate_id` — must mirror the existing evolution parent
- `prose_parent_candidate_id` — actual prose derivation; null for fresh regeneration
- `created_by_run_id`, optional `created_by_session_id`
- optional `authority_snapshot_fingerprint` and `diff_fingerprint`
- exact semantic-review receipts bound to candidate fingerprint
- exact mirrors of externally authoritative explicit acceptance receipts
- a read-only SETTLE preflight that verifies the exact Accepted fingerprint

All records remain `authority=false`.

## Authority boundary

Candidate Lineage cannot:

- Accept a candidate.
- Promote a semantic result into Canon.
- Write Canon or settlement state.
- Infer acceptance from incumbent status, latest-candidate status, review pass, user silence, or comparison victory.
- Change `quality.compare` winner semantics.
- Treat a fresh regeneration as inheriting rejected prose.

`bind_external_acceptance()` only mirrors an explicit acceptance receipt produced by the existing authority/user gate. `validate_settlement_binding()` only proves exact fingerprint identity for a later SETTLE preflight; it performs no settlement write.

## Schema and migration

The migration is additive and lazy. Three companion SQLite tables are created in the **same quality-evolution database**:

1. `evolution_candidate_lineage`
2. `evolution_review_receipts`
3. `evolution_acceptance_bindings`

No existing `evolution_runs`, `evolution_candidates`, or `evolution_comparisons` row is rewritten. Existing databases remain valid. Existing callers can continue using `quality_evolution` without Candidate Lineage; migrated callers register lineage immediately after creating a candidate.

### Backfill policy

Do not guess prose derivation for historical candidates. A migration tool may backfill only when provenance is explicit. Unknown historical derivation remains unregistered rather than inferred.

## Runtime contract

### Draft baseline

- comparison parent: null
- prose parent: null
- origin: `draft`

### Repair

- comparison parent: current incumbent
- prose parent: same direct parent
- origin: `repair`

### Fresh regeneration

- comparison parent: current incumbent
- prose parent: null
- origin: `fresh_regeneration`

The candidate can therefore enter the existing incumbent/challenger comparison without importing rejected realization.

### User edit

- comparison parent: current incumbent
- prose parent: optional exact source candidate when known
- origin: `user_edit`

The user edit still receives no automatic Canon/Accepted status.

## Review receipt binding

A review receipt is accepted only when:

- the semantic result validates against its exact typed job;
- the job payload's `candidate_fingerprint` equals the target evolution candidate fingerprint;
- result `input_fingerprint` equals the job fingerprint;
- the review/job/result has not already been rebound inconsistently.

Thus a review of A cannot validate A1 after repair, even if the text is superficially similar.

## Human-facing projection

A UI may render:

- current incumbent
- origin
- comparison parent
- prose parent
- high-level diff reference/digest
- reviews bound to this exact fingerprint
- explicit acceptance binding, if any
- settlement binding status

The UI should not require the author to understand validator caches, SQLite tables, or semantic routing.

## Required verification

A. Draft A -> repair A1: exact prose parent A.

B. A1 -> fresh regeneration A2: comparison ancestry remains valid but prose parent is null.

C. Review for A cannot validate A1.

D. Accepted A1 does not imply A2 Accepted.

E. Stale review is invalidated.

F. Incumbent remains A1 when A2 loses the existing semantic comparison.

G. Resume reconstructs the exact graph from durable SQLite state.

H. SETTLE preflight requires the exact externally Accepted fingerprint.

The deterministic self-test in `quality/candidate_lineage.py` exercises A-H. `evals/candidate_lineage_ablation.py` compares legacy representation with the extension and verifies that the ambiguity is removed with zero added semantic calls and no change to winner selection.

## Compatibility

- No writer prompt change.
- No extra semantic call.
- No change to `quality.compare`, objective envelope, qualification, Blind Reader, independent production review, Canon precedence, or SETTLE authorization.
- No consumer Project migration is required until a consumer chooses to use lineage-aware quality evolution.

## Rollback

Stop invoking `candidate_lineage` and, if desired, drop only the three companion tables. The core quality-evolution tables and all candidate/comparison results remain intact. Because the extension has no Canon/Settlement write authority, rollback cannot revert or mutate Canon.

## Cold-read decision in the same SYSTEM-IMPROVE study

Do **not** add a second mandatory ColdRead agent in this slice. Current NovelForge already has:

- a production Blind Reader (`reader.engagement_audit`) isolated from outline/active plan/repair brief/prior review/telemetry; and
- a fresh independent holistic `quality.production_review` that attempts to falsify readiness.

External systems provide useful evidence that front-to-back cold reading can discover accumulated failures missed by local/editorial passes, but adding another always-on reviewer now would overlap current semantic ownership and add cost. Revisit only with an ablation demonstrating a distinct miss class (for example repair seams or book-level accumulated-state failures) not already caught by Blind Reader + continuity + independent production review.

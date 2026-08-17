# Candidate Lineage v1

Status: Framework structural extension; derived/provenance authority only.

## Problem

`quality/quality_evolution.py` already owns incumbent/challenger comparison. Its legacy `parent_candidate_id` means **comparison ancestry**: a challenger competes with the current incumbent. That is not always the same as **prose derivation ancestry**. A repair normally reuses parent prose; a fresh regeneration deliberately must not consume rejected/incumbent prose even though it still competes with that incumbent.

## Decision

Candidate Lineage is an additive projection over the existing quality-evolution ledger. It does not create another comparator, objective system, Canon system, settlement system, or Git branch per prose candidate.

It records:
- `origin = draft | repair | fresh_regeneration | user_edit`;
- `comparison_parent_candidate_id`, mirroring the existing evolution parent;
- `prose_parent_candidate_id`, null for fresh regeneration;
- creator run/session provenance;
- optional authority-snapshot/diff fingerprints;
- semantic review receipts bound to one exact candidate fingerprint;
- opaque external acceptance-evidence references bound to one exact candidate fingerprint.

All rows remain `authority=false`.

## Authority boundary

Candidate Lineage cannot accept a candidate, authenticate that an external event was an authoritative user acceptance, write Canon or settlement state, infer acceptance from comparison victory/latest status/review pass/user silence, or change `quality.compare` winner semantics.

`bind_acceptance_evidence()` stores only an opaque reference. It requires an exact candidate fingerprint, authority source reference, receipt fingerprint, and timestamp, while retaining `authority_verified=false` and `settlement_authorized=false`.

`check_settlement_reference_consistency()` returns only `REFERENCE_MATCH` or `REFERENCE_MISMATCH`; it always returns `settlement_authorized=false` and requires external authority verification. Project/User Gate + SETTLE remain authoritative.

## Migration and rollback

Migration is additive and lazy in the same quality-evolution SQLite database:
1. `evolution_candidate_lineage`
2. `evolution_review_receipts`
3. `evolution_acceptance_evidence`

Existing core tables are not rewritten. Historical derivation or Accepted state must never be guessed during backfill. Rollback is to stop invoking this projection and optionally drop the three companion tables; core candidate/comparison state and Canon are untouched.

## Runtime semantics

| Origin | Comparison parent | Prose parent |
|---|---|---|
| draft | null | null |
| repair | current incumbent | same parent |
| fresh_regeneration | current incumbent | null |
| user_edit | current incumbent | exact source when known |

This lets a fresh realization challenge the incumbent without inheriting rejected prose.

## Required verification

A. Draft A -> repair A1 has exact prose parent A.  
B. A1 -> fresh A2 keeps comparison ancestry but prose parent is null.  
C. Review for A cannot validate A1.  
D. Acceptance evidence for A1 does not imply A2 Accepted or authenticate A1 by itself.  
E. Stale review is invalidated.  
F. Existing incumbent remains when challenger loses `quality.compare`.  
G. Resume reconstructs exact durable lineage.  
H. Settlement reference must match the exact externally referenced fingerprint while never authorizing SETTLE.

`quality/candidate_lineage.py self-test` exercises A-H. `evals/candidate_lineage_ablation.py` proves the legacy representation ambiguity is removed with zero new semantic calls and no change to incumbent selection. This is an architecture/provenance ablation, not proof of literary-quality gain.

## Cold-read decision from the same study

Do not add a second mandatory ColdRead agent in this slice. Current NovelForge already has a production Blind Reader isolated from creator-private context plus a fresh independent holistic production review. External OSS evidence supports cold reading as useful, but another always-on reviewer would overlap semantic ownership and add cost. Revisit only if an ablation demonstrates a distinct miss class, such as repair seams or book-level accumulated-state failures, not already caught by Blind Reader + continuity + independent production review.

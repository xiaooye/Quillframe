# Spec 015 — Candidate Lineage

## Goal

Make prose-candidate derivation inspectable and fingerprint-bound without replacing NovelForge's existing quality evolution, authority, Canon, semantic comparison, or settlement mechanisms.

## Required behavior

1. Reuse `quality_evolution` as the single incumbent/challenger ledger and `quality.compare` as the semantic winner owner.
2. Distinguish comparison ancestry from prose derivation ancestry.
3. Support origins `draft`, `repair`, `fresh_regeneration`, and `user_edit`.
4. Require repairs to derive prose from their direct comparison parent.
5. Require fresh regenerations to retain a comparison parent while having no prose parent.
6. Bind semantic review receipts to one exact candidate fingerprint and reject stale/cross-candidate reuse.
7. Permit only opaque external acceptance-evidence references; the lineage layer must never authenticate user acceptance or authorize SETTLE.
8. Preserve exact resume reconstruction from durable state.
9. Add no Writer context and no mandatory semantic call.
10. Keep all lineage/evidence records `authority=false`.

## Non-goals

- No Git branch per prose candidate.
- No automatic candidate winner.
- No acceptance inference from latest/incumbent/review-pass state.
- No Canon or settlement write.
- No second objective-preservation system.
- No second ColdRead agent.

## Compatibility

Migration is additive in the existing quality-evolution SQLite database. Existing callers remain valid. Historical provenance is not guessed. Consumers require no automatic repin or migration.

## Acceptance criteria

Required deterministic tests A-H in `docs/CANDIDATE_LINEAGE_V1.en.md` pass; the legacy-vs-lineage ablation demonstrates the representation gap is closed without changing incumbent selection; repository hygiene and relevant CI pass; no authority boundary is weakened.

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
11. Expose machine-readable projections through `quality/candidate_lineage.schema.json`, versioned as `novelforge_candidate_lineage_v1` using JSON Schema draft 2020-12.
12. Route new lineage-aware evolution through `quality/candidate_lineage_runtime.py`, which must fail closed before comparison/consumption when any candidate lacks valid explicit lineage. Legacy `quality_evolution.py` remains available for compatibility but cannot silently satisfy the lineage-aware runtime contract.

## Non-goals

- No Git branch per prose candidate.
- No automatic candidate winner.
- No acceptance inference from latest/incumbent/review-pass state.
- No Canon or settlement write.
- No second objective-preservation system.
- No second ColdRead agent.
- No guessed lineage for a legacy or crash-partial candidate.

## Compatibility

Migration is additive in the existing quality-evolution SQLite database. Existing callers remain valid. Historical provenance is not guessed. Consumers require no automatic repin or migration.

The machine-readable schema is additive and describes the lineage candidate view, durable graph projection, and SETTLE reference-consistency receipt. It does not grant those projections authority.

The lineage-aware runtime is a facade over the same core ledger/comparator. If a legacy caller creates a candidate without lineage, the core row remains compatible, while the lineage-aware runtime reports `MISSING_LINEAGE` and refuses comparison until the exact provenance is supplied. This provides compatibility without weakening fail-closed provenance semantics.

## Acceptance criteria

Required deterministic tests A-H in `docs/CANDIDATE_LINEAGE_V1.en.md` pass; the legacy-vs-lineage ablation demonstrates the representation gap is closed without changing incumbent selection; the lineage-aware runtime test proves direct legacy/bypass insertion is detected and blocks comparison until explicit recovery; `quality/candidate_lineage.schema.json` parses with identity `novelforge_candidate_lineage_v1`; repository hygiene and relevant CI pass; no authority boundary is weakened.

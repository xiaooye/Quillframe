# Candidate Lineage v1

Candidate Lineage makes provenance explicit where a single “parent” field would be ambiguous. It extends Quality Evolution; it does not create a second comparison system, acceptance system, Canon system, or settlement authority.

<img src="assets/concepts/candidate-lineage.en.svg" alt="Candidate lineage separating comparison parent from prose parent for draft, repair, fresh regeneration, and user edit origins" width="100%" />

## Two parent relations

**Comparison parent** answers: which incumbent was this challenger evaluated against? The existing Quality Evolution parent remains the comparison ancestry used by `quality.compare`.

**Prose parent** answers: which earlier prose was directly used as the realization source? This is separate because a fresh regeneration may be compared with the incumbent while deliberately not inheriting its prose.

## Origin rules

`draft` has neither comparison nor prose parent. `repair` must have a comparison parent and must derive prose from that same direct parent. `fresh_regeneration` must have a comparison parent but must not have a prose parent. `user_edit` is an explicit challenger with a comparison parent; its derivation is recorded rather than guessed.

The runtime facade fails closed when required lineage is missing or contradicts the origin. It never infers prose ancestry from similarity.

## Exact review receipts

A semantic review receipt binds one `candidate_id` and exact candidate fingerprint to the contract ID, job fingerprint, result fingerprint, and result status. A result for another candidate or an earlier fingerprint is stale.

## Acceptance evidence boundary

Lineage can bind an opaque external acceptance reference to one exact candidate fingerprint, authority source reference, authority receipt fingerprint, and accepted artifact fingerprint. It deliberately does not authenticate the authority source.

Every view remains `authority=false`. Acceptance evidence reports `authority_verified=false` and `settlement_authorized=false`. The authority/settlement layer must validate the actual user or editorial acceptance independently.

## Compatibility

The schema ID remains `quillframe_candidate_lineage_v1`. That is a stable technical identifier under the legacy namespace and is not renamed with the Quillframe public brand.

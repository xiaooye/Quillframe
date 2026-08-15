# 010 · Creative Decision Provenance

## Status

Implementation candidate for NovelForge General Craft. External systems are evidence, not authority.

## Problem

NovelForge can hold an active plan, explore scenario forks, reconcile plans after new causal evidence, and track downstream propagation debt. It does not yet have a first-class artifact for a meaningful choice that is intentionally unresolved and owned by a specific resolver.

Without that boundary, a writer or repair run may silently concretize an author-owned choice simply to finish prose. Later, the project may know what the plan says but lose why a meaningful choice was made, what alternatives were rejected, what risks were accepted, or which prior decision was superseded.

## External mechanism evidence

- `notnotype/neuro-book@306e563ad7a4d4a58354fa8d582ad9aa9b886e8c`: durable open/decided story decisions, alternatives, rationale, risks, dependency refs and supersession history.
- `github/spec-kit@bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`: durable `[NEEDS CLARIFICATION]` markers, explicit user clarification before planning, decision records with rationale/open questions, and fail/stop behavior when meaningful uncertainty remains unresolved.

Counterexample: ordinary local prose choices and low-cost edits must remain lightweight and must not require decision artifacts.

## Required mechanism

A portable `creative_decision` artifact SHALL:

1. carry stable `decision_id`, scope, bounded question, resolver policy, alternatives, dependency/served refs and source fingerprints;
2. use lifecycle `open | decided | superseded | dropped`;
3. allow a writer to *surface* an open question without thereby receiving resolution authority;
4. permit `open -> decided` only when the resolving actor class is explicitly allowed and exact before-version/fingerprint matches;
5. record a concise user-visible chosen outcome, rationale, rejected alternatives/reasons and accepted risks; private model chain-of-thought is forbidden;
6. preserve supersession history by linking an old decision to an explicit successor rather than overwriting the old rationale;
7. expose downstream revalidation candidates after decision changes but never auto-write the active plan or auto-create propagation debt;
8. remain non-Canon and non-Settlement: decision records cannot write Project state, Canon, Framework behavior, or Settlement by themselves.

## Context isolation

- `writer` projection of an `open` decision exposes the unresolved question and a `DO_NOT_RESOLVE` warning but hides alternatives by default.
- `planner` projection may inspect alternatives and decision provenance.
- `reader` and `character` projections hide planning decisions entirely.
- A `decided` choice is not duplicated into writer decision context; the active plan remains the normal execution surface for decided future intent.

## Compatibility

The artifact is provider-neutral JSON and does not create a second session store, plan store, scenario store, or Canon database. Storage belongs to the consuming Project/host. Existing Projects are unchanged until they opt to persist/use creative-decision artifacts.

## Evaluation

Deterministic regressions SHALL prove:

- writer cannot silently resolve an author-owned open decision;
- authorized resolution is CAS/fingerprint bound;
- future alternatives do not leak into writer/reader/character context;
- concise provenance is retained after resolution;
- supersession preserves the old resolution and requires explicit successor lineage;
- scope mismatch/tamper fails closed;
- decision change only emits revalidation candidates, never automatic #63 debt or plan mutation;
- rollback consists of disabling this optional artifact path without reinterpretation of Canon/Settlement state.

Before promotion, General Craft evidence must also include capability/regression evaluation and green exact-head Framework CI.

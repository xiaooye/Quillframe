# Planning Commitment Horizon — Specification

## Status

Implementation candidate for #67. This specification is Generic NovelForge work only. It does not change any downstream Project lock, Canon, manuscript, user taste, or Settlement state.

## Evidence basis

This candidate adapts implementation-backed mechanisms from two independent systems:

1. `VioletEvergar-den/AI-Novel-Writing-Assistant@43a78b8d295ba060c1037df49bca942014154074`: machine-validated hard/soft volume planning plus adjacent rebalance after a regenerated volume. The useful idea is planning commitment strength; the source system is also a counterexample because soft volumes can still be over-expanded by later calls.
2. `joonspk-research/generative_agents@fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4`: broad daily plan -> hourly plan -> only roughly two hours of near-future minute-level decomposition at a time, with event reactions rewriting a bounded schedule slice. The useful idea is runtime-enforced progressive realization and local replanning; the hard-coded time window is domain-specific and must not be copied.

## Problem

NovelForge already knows how to reconcile an active plan after causal evidence changes (`plan.reconcile`), explore alternative futures (`scenario_fork`), and record downstream invalidation work (#63 propagation debt). It does not yet express how much future detail a planner is allowed to commit before that evidence exists.

Without a commitment horizon, a serialized-fiction planner can over-specify distant chapters simply because the artifact schema allows it. Later emergence then creates unnecessary staleness, brittle causal forcing, and false "plan failure" instead of normal adaptation.

## Goals

1. Represent a bounded planning region with explicit commitment strength and maximum allowed planning depth.
2. Deterministically reject known planning operations whose registered artifact kind exceeds that region's depth ceiling.
3. Require an explicit, fingerprint-bound transition before a region may gain stronger/deeper planning permission.
4. Select the first local rebalance frontier only from explicit dependency evidence, including non-adjacent dependencies and excluding merely adjacent unrelated regions.
5. Preserve existing NovelForge authority boundaries: planning strength never implies Canon, acceptance, Settlement, or automatic active-plan mutation.
6. Remain profile-sensitive. A tightly plotted short novel may allow deep hard planning across most of the work; a discovery-writing profile may keep even near-future regions soft.

## Non-goals

- Do not create a second active-plan store.
- Do not replace `plan.reconcile` with deterministic story judgment.
- Do not create a second propagation/dirty graph beside #63.
- Do not infer literary over-concretization from arbitrary prose using Python.
- Do not automatically promote, regenerate, reconcile, settle, or create Canon.
- Do not impose a universal number of chapters, volumes, days, or story-order units as the horizon.

## Planning region

A portable planning-region artifact records at minimum:

- `project_id`
- `region_id`
- `plan_ref`
- optional story-order bounds / semantic scope
- `commitment_strength`: `open | soft | hard`
- `max_planning_depth`: one of the registered depth levels
- `assumption_refs`
- `dependency_refs`
- opaque `unresolved_decision_refs` when a separate decision system supplies them
- `version`
- exact artifact fingerprint

`hard` means a stronger **active-plan commitment**, never immutable truth or Accepted Canon.

## Planning depth

The initial generic depth order is deliberately small:

1. `arc_boundary` — role, boundary, reward/escalation obligation, broad outcome class
2. `beat` — causal beat or milestone intent
3. `scene_intent` — scene-level dramatic/action intent
4. `chapter_detail` — sufficiently detailed chapter plan intended to guide drafting

Known planning artifact kinds map deterministically to a required depth:

- `arc_role` -> `arc_boundary`
- `beat_sheet` -> `beat`
- `scene_card` -> `scene_intent`
- `chapter_plan` -> `chapter_detail`

Unknown kinds fail closed until registered. This mapping is an admission-control contract, not a claim that arbitrary text can be perfectly classified without semantic review.

## Profile policy

A policy defines the maximum depth allowed for each commitment strength. Example profiles may choose:

- serialized/adaptive: `open <= arc_boundary`, `soft <= beat`, `hard <= chapter_detail`
- discovery-heavy: `open <= arc_boundary`, `soft <= scene_intent`, `hard <= chapter_detail` but may leave nearby regions soft
- tightly plotted short work: most regions may begin `hard` with `chapter_detail`

The Framework must not ship a universal "first N volumes hard" rule.

## Realization admission

A realization request names an existing region fingerprint/version and a registered artifact kind. The deterministic runtime:

1. validates the region and policy;
2. resolves the artifact kind to a required depth;
3. compares required depth with both the region ceiling and profile ceiling;
4. returns `allowed` or `blocked_depth_ceiling`;
5. performs no model execution and writes no plan.

A caller cannot gain permission by putting an arbitrary `requested_depth` label on a more concrete registered operation.

## Horizon transition

Changing commitment strength or maximum depth is an explicit transition with:

- actor class allowed by policy;
- exact before `version` and artifact fingerprint;
- target strength/depth within profile ceilings;
- concise public reason and evidence refs;
- new fingerprint/version.

A writer is not an implicit horizon promoter. The transition artifact remains non-authoritative and does not itself mutate a separate active-plan store.

## Dependency-bounded rebalance frontier

The runtime accepts a source change plus explicit dependency evidence. Each dependency record binds:

- `dependency_ref` + fingerprint
- `source_ref`
- `dependent_ref` + current fingerprint
- either `scope=all_source_changes` or specific `assumption_refs`
- required action (`replan` for this contract)
- optional #63 `propagation_debt_ref`

A dependent enters the frontier only when its source matches the changed source and its declared scope is affected. Physical adjacency has no authority. A non-adjacent dependent with matching evidence is included; an adjacent item with no evidence is excluded.

The frontier is intentionally one evidence-bounded wave. If reconciliation actually changes a dependent, #63 can record the resulting downstream debt and expose a later frontier. This avoids recursively invalidating the entire future merely because an upstream item *might* change.

## Context and authority guardrails

- `open`/`soft` speculative future detail must not be treated as character knowledge, current state, reader-visible fact, or Accepted Canon.
- Context projection remains owned by existing context/worker contracts; this mechanism only exposes strength/depth metadata and never grants visibility authority.
- `scenario_fork` remains the exploration mechanism.
- `plan.reconcile` remains the semantic reconciliation operation.
- #63 remains the durable propagation-debt lifecycle.
- #65 creative-decision artifacts, if available, are referenced opaquely; #67 must not depend on #65 being installed.

## Acceptance / regressions

1. A `soft` region whose ceiling is `beat` rejects a `chapter_plan` realization.
2. A valid `hard` region may admit `chapter_plan` when policy permits it.
3. An authorized exact-before transition can deepen/promote a region and advances version/fingerprint exactly once.
4. Writer/self-declared authority cannot promote a region.
5. Stale version/fingerprint transition fails closed.
6. A non-adjacent evidence-linked dependency appears in the rebalance frontier.
7. A physically adjacent but evidence-unlinked region is excluded.
8. The frontier never auto-runs `plan.reconcile` and never auto-opens debt.
9. A short tightly plotted profile can permit broad deep hard planning.
10. A discovery profile can keep near-future regions soft without error.
11. All outputs report no Canon/Project/Framework/Settlement authority.
12. Semantic counterexample eval must verify that meaningful far-future over-concretization is blocked while trivial/local planning does not become bureaucratic horizon management.

## Rollback

Disabling horizon enforcement must leave existing active-plan artifacts untouched and return planning behavior to the pre-existing `plan.reconcile` / scenario / context contracts. No migration may rewrite Canon as part of rollback.

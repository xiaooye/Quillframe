# Tasks 012 · Adaptive Production Learning and Realization Boundary

## Design

- [x] Freeze real production failure evidence and separate historical pinned authority from current engineering target.
- [x] Benchmark mature writing/agent systems and revise the architecture around persistent intent, sparse context, simulation-before-prose, evaluator/editor loops, and bounded learning.
- [x] Reuse existing Author Steering, Learning Store, Context Inspector, story simulation, readiness, and quality-evolution owners rather than duplicating them.

## Author Model / feedback

- [ ] Add `learning.preference_interpret` semantic contract.
- [ ] Add deterministic Author Model projection/runtime backed by existing Learning Store.
- [ ] Enforce scope/authority boundaries for one_off, project, user_taste, and general_craft.
- [ ] Add contradiction/supersession tests.
- [ ] Connect material Review feedback to typed evidence/proposed preference delta without changing primary task mode.

## Context assembly

- [ ] Add simulation/private-state stages and pre-draft isolation.
- [ ] Add required context obligations and satisfaction receipt.
- [ ] Add deterministic Context Assembly validator/self-test.
- [ ] Preserve model-owned semantic relevance selection.

## Simulation / realization

- [ ] Add writer-safe `scene.realization_project` semantic contract.
- [ ] Require private character state to remain causal state, not prose payload.
- [ ] Add formal-completeness counterexample boundary.

## Reader / Editor / quality

- [ ] Register HF-30 in quality taxonomy.
- [ ] Add profile-sensitive prose telemetry as non-authoritative signals.
- [ ] Add structured Reader production assessment dimensions for paragraph/profile/dialogue realization.
- [ ] Add `editor.repair_spec` contract.
- [ ] Reuse pairwise incumbent/challenger comparison for material repairs.
- [ ] Extend structural readiness only where deterministic receipts are required.

## Safety / integrity

- [ ] Add typed write-intent/action mismatch guard.
- [ ] Fix stale semantic registry references.
- [ ] Add semantic-reference integrity self-test/CI.
- [ ] Preserve semantic reject vs transport/configuration/result-validation failure distinctions.

## Integration

- [ ] Register tools/contracts in manifest/catalog.
- [ ] Update Harness/Orchestration and user-facing production/context/learning docs in EN/ZH.
- [ ] Register this spec in documentation governance.
- [ ] Integrate deterministic tests into normal reusable contracts CI.
- [ ] Add semantic/regression eval fixtures with hidden-gold isolation.

## Verification

- [ ] Compile all Python modules.
- [ ] Run all new deterministic self-tests.
- [ ] Run existing deterministic regressions touched by the change.
- [ ] Build/validate semantic contract catalog.
- [ ] Build blind semantic judge queue.
- [ ] Verify framework bundle reproducibility after final file set.
- [ ] Run exact-head CI and classify pre-existing versus introduced failures.
- [ ] Obtain exact-candidate independent semantic capability/counterexample evidence if transport is eligible.
- [ ] Produce rollback points and human-review handoff summary.

## Release boundary

- [ ] Do not merge PR #90, promote Framework behavior, or migrate the consuming Project lock in this SYSTEM-IMPROVE run without separate authority.

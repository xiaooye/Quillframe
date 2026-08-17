# Plan 013 · Automatic Feedback Learning Intake

## Phase 0 · Before-state / compatibility

- Freeze base: `f7732856311814d82012159e5856c4aa592007a5`.
- Consumer Project lock/attestation validated separately; Project is not repinned by this work.
- Preserve `novelforge_event_v1`, `feedback.observed`, Author Steering v1, Learning Store, Author Model projection and Promotion Gate authority model.

## Phase 1 · Contract evolution

1. Evolve `learning.preference_interpret` output to support `capture_decision=capture|skip`.
2. Add semantic hypothesis reconciliation action and new evidence types.
3. Keep `independent_gate=false` and write permissions false.
4. Update model contract catalog/CI synthetic fixture validation as required.

## Phase 2 · Author Model capture evolution

1. Keep existing capture request compatible.
2. Accept optional deterministic `evidence_id` from automatic intake.
3. Support model-directed `create|strengthen|contest|supersede|split` against exact hypothesis IDs.
4. Preserve activation authority: automatic intake passes all activation flags false.
5. Preserve active-index relevance projection and current-explicit-request priority.

## Phase 3 · Feedback intake runtime

Add `learning/feedback_intake.py` plus schema.

Responsibilities:

- validate/normalize a `feedback.observed` event;
- support legacy author-steering payload and generic feedback-observation payload;
- create/bind a `learning.preference_interpret` semantic job;
- persist `awaiting_semantic` when no semantic capability is eligible;
- validate semantic results/fingerprint;
- process `skip` without hypothesis creation;
- process `capture` through Author Model with stable evidence identity;
- use `learning_feedback:<project-or-resource>` consumer-scoped Control Plane receipt;
- provide read-only status/list projection;
- preserve minimal target/provenance fields only.

No literary heuristics, profile mutation, Canon writes, Framework promotion or automatic activation.

## Phase 4 · Harness wiring/docs

Update the Framework manifest and human docs so every production mode treats basic learning intake as a bounded internal subroutine. LEARN remains the dedicated mode for deeper analysis/corpus/eval/promotion.

Document:

- same feedback event can feed steering and learning independently;
- current explicit instruction acts immediately while durable candidate remains gated;
- missing semantic route yields resumable pending state;
- active != relevant;
- rejection/bad-example isolation;
- privacy and storage boundary.

## Phase 5 · Deterministic verification

Implement self-tests for all requested controls:

1. automatic project feedback in REVISE;
2. one-off;
3. user-taste candidate;
4. general-craft overreach;
5. non-feedback skip;
6. weak acknowledgement skip;
7. rejection metadata only;
8. comparison strengthens existing hypothesis;
9. contradiction/applicability review;
10. same-event retry exactly once;
11. two independent turns strengthen one hypothesis;
12. dual consumer;
13. missing semantic capability pending;
14. pending resume exactly once;
15. current explicit instruction priority;
16. privacy/no generic commit of personal state;
17. deterministic CI has no model execution.

Normal CI uses synthetic typed semantic results. It validates contracts; it does not claim those fixtures are real model judgments.

## Phase 6 · Semantic / ablation evidence

Extend AI-native eval inventory with a feedback-learning family:

- BEFORE: steering-only event has no learning intake;
- AFTER: same feedback becomes bounded candidate;
- negative control: non-feedback → skip;
- authority control: candidate does not activate/promote;
- dual-consumer control;
- contradiction control.

If existing Framework ablation policy requires registered independent semantic comparison, build the exact packets and route to an eligible separate invocation/session. Missing capability remains `PENDING_MODEL`.

## Phase 7 · Bundle / compatibility / PR

- Compile all changed Python and JSON.
- Run new self-tests plus existing Author Model, Control Plane, semantic contract, Learning Store/cycle/promotion tests.
- Run generic evals and deterministic framework bundle reproducibility if CI infrastructure is available.
- Record bundle fingerprint implication: any Framework source change produces a new bundle fingerprint; 在 Framework acceptance / CI / bundle attestation 完成前，不得 repin consumer Project。
- Open draft PR from `agent/automatic-feedback-learning-intake` to `main`.

## Rollback

Rollback is the feature-branch commit/PR. No consumer Project state changes are part of this implementation. Existing producers and Author Steering remain valid because shared event v1 is preserved.

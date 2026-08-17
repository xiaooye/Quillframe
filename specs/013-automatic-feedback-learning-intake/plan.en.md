# Plan 013 · Automatic Feedback Learning Intake

## 0. Freeze compatibility baseline

Base implementation is Framework `f7732856311814d82012159e5856c4aa592007a5`. The consumer Project remains pinned independently and is not repinned by this work. Preserve shared event v1, `feedback.observed`, Author Steering v1, Learning Store, Author Model projection, and Promotion Gate authority semantics.

## 1. Evolve semantic contract

- Add `capture_decision=capture|skip` and nullable `skip_reason` to `learning.preference_interpret`.
- Add model-selected hypothesis reconciliation action and richer feedback types.
- Keep `independent_gate=false` and all write permissions false.
- Update catalog/CI synthetic contract fixtures.

## 2. Evolve Author Model capture

- Keep legacy capture requests valid.
- Accept optional deterministic evidence IDs.
- Support exact-ID `create|strengthen|contest|supersede|split` operations.
- Keep all automatic-intake activation authority false.
- Preserve active-index semantic relevance selection and current explicit request priority.

## 3. Add feedback intake runtime

Create `learning/feedback_intake.py` and schema to normalize a `feedback.observed` event, prepare a registered semantic job, persist pending state, apply validated results, call Author Model capture, record a distinct `learning_feedback:*` consume receipt, and expose read-only status/list projections.

It must support both legacy author-steering payloads and a generic feedback-observation payload. It must not contain literary keyword heuristics, promotion logic, profile writes, Canon writes, or Framework behavior writes.

## 4. Wire Harness/docs

Describe basic intake as an internal subroutine available inside any primary mode. LEARN remains the dedicated mode for research, corpus expansion, hypothesis evaluation, and promotion work.

## 5. Deterministic verification

Cover all 17 requested controls: project/one-off/user-taste/general-craft scope safety, non-feedback/ack skips, rejection, comparison, contradiction, retry, distinct-turn strengthening, dual consumers, missing semantic capability, resume, current-instruction priority, privacy, and model-free normal CI.

Synthetic semantic judgments in CI prove typed wiring only; they are not represented as live semantic evidence.

## 6. Semantic ablation

Add feedback-learning paired-ablation inventory for BEFORE/AFTER, negative, authority, dual-consumer and contradiction controls. When the registered ablation contract requires independence, execute via a separate eligible invocation/session or report `PENDING_MODEL`.

## 7. Bundle and PR

Run deterministic tests/evals/bundle reproducibility when infrastructure is available. Any Framework source change necessarily changes the deterministic bundle fingerprint; consumer Project repin remains a separate later migration after Framework acceptance and attestation. Open a draft PR to `main`.

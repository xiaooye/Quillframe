# Tasks 014 — Semantic Context Runtime

- [x] Freeze Quillframe main `0d211675fd9f545b83d02ab4102563f0c67e11b9` and Shujuku main `12fec85bae325cacd8370b4dd0f4aff0dfd6da0e`.
- [x] Read current Harness, Context, Story, Character, Canon, Agent/Model Runtime, Persistence and Host Bridge contracts.
- [x] Implement fingerprint-bound Semantic Context Profiles with regeneration/stale semantics and manual override preservation.
- [x] Implement deterministic lifecycle/visibility/stage eligibility before semantic relevance.
- [x] Implement exact candidate-universe validation for Agent selections.
- [x] Implement stage-specific greenlights and deterministic hard-budget packing with incomplete-grounding status.
- [x] Implement reproducible Context Freeze, stale/conflict validation and explicit refresh/extension fingerprinting.
- [x] Implement typed Context Query and mandatory-vs-adaptive graph validation.
- [x] Implement public Inspector projection without private reasoning.
- [x] Add SQLite migration and typed ContextRepository; preserve backup/restore/doctor compatibility.
- [x] Add semantic worker contracts `context.profile_derive` and `context.stage_select` while retaining `context.select`.
- [x] Add read-only Studio Host Bridge context projection; no UI changes.
- [x] Document Shujuku patterns adopted/rejected and architecture differences in English/Chinese.
- [x] Add required deterministic/integration tests.
- [ ] GitHub CI + aggregate release/bundle verification (filled by verification run after commit).
- [ ] Acceptance report after all checks are green.

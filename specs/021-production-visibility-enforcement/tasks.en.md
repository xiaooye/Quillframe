# Tasks 021 · Production Visibility Enforcement

- [x] Freeze SYSTEM-IMPROVE baseline at `c6832365be6c4e3816b9c779dd0c2aa88b42cab9`.
- [x] Create isolated implementation branch and draft PR.
- [x] Prove the minimal visibility invariant in a local smoke harness: unreleased candidates return no content.
- [ ] Fix runtime artifact to bind PR head SHA and retain verifiable shallow Git identity.
- [ ] Download exact-head artifact into isolated Linux runtime and pass authority/bootstrap tests.
- [ ] Wire `quality.production_release` into final production execution and persist release receipt.
- [ ] Add Core `candidate_visible_get` projection with fail-closed content withholding.
- [ ] Add Host Bridge `candidate.visible.get` and contract version update.
- [ ] Add host/HARNESS requirement forbidding DRAFT/REVISE manuscript synthesis outside released production runtime.
- [ ] Add regression tests for missing/stale/mismatched/pending/failing/fabricated release evidence and valid release success.
- [ ] Run complete Python/Core/Host Bridge/Studio/site CI.
- [ ] Download final exact-head artifact and rerun tests in ChatGPT Linux container.
- [ ] Execute a real gated DRAFT candidate and surface it only after release for user review.
- [ ] Record verification evidence in PR and mark ready only after all acceptance criteria pass.
- [ ] Do not repin consumer Project or mutate Canon in this task.
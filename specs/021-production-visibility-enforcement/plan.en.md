# Plan 021 · Production Visibility Enforcement

## Sequence

1. Fix CI runtime materialization so PR artifacts bind the exact PR head SHA, retain shallow `.git` metadata, and include source SHA plus archive digest.
2. Download the artifact into an isolated Linux directory and verify declared SHA, digest, `git rev-parse HEAD`, Framework authority bootstrap, and the full Core test suite.
3. Wire `quality.production_release.aggregate` into the final production path and persist a fingerprint-bound release receipt.
4. Add Core `candidate_visible_get` with strict candidate/run/revision/readiness/release binding; any failed condition returns no content.
5. Expose `candidate.visible.get` through Host Bridge and close the `agent_package → raw production checkpoints` pre-release manuscript bypass.
6. Constrain conversational-sandbox manager execution to a loopback OpenAI-compatible relay using atomic request/response files. The relay is transport only and explicitly cannot satisfy independent review.
7. Repair the Project peer receipt CLI `build/validate` commands so the existing manual peer workflow is actually executable.
8. Add GitHub Models `review` mode to the Project peer action. The model returns semantic judgment only; the deterministic bridge binds exact job/fingerprint/nonce/provider/runtime receipt evidence.
9. Add registered-contract dry preflight for `rule_material` so malformed schema fails before any Context/Story/Raw Draft semantic execution.
10. Add regressions for missing/tampered/mismatched release, checkpoint leakage, fabricated host booleans, relay atomicity, GitHub Models provider nonce binding, peer receipt CLI, rule-material fail-fast, and valid release success.
11. Run complete Framework CI; download the final exact-head artifact and rerun the complete tests in the current ChatGPT Linux container.
12. Execute a real DRAFT through the localhost manager relay to independent handoff; use a Project-owned independent provider to complete peer review, submit, production release, and `candidate.visible.get`.
13. Surface the new school-drama candidate to the user for manual quality review only after final release.

## Design constraints

- No alternate production engine in prompts or host code.
- The ChatGPT host drives exact Core through a local `cli` transport; do not achieve this by widening `agent_package` semantic authority.
- Ephemeral SQLite is not a second Canon authority.
- The manager relay never satisfies the independent gate.
- The independent provider receives only the bounded peer packet, not the writer conversation or private Project context.
- Release/visibility remain deterministic authorization/composition layers; literary judgment remains owned by registered semantic contracts.
- No consumer Project repin before Framework merge; consumer repin is a separate engineering run.
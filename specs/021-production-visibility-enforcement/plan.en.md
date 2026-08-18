# Plan 021 · Production Visibility Enforcement

## Sequence

1. Fix CI runtime materialization so PR artifacts bind the exact PR head SHA and retain shallow `.git` metadata.
2. Download the artifact into an isolated Linux directory and verify declared SHA, archive digest, `git rev-parse HEAD`, Framework authority bootstrap, and the existing Core test suite.
3. Introduce a Core-owned production visibility projection that validates candidate/run/revision/review/readiness/release bindings and returns no content on any failed precondition.
4. Wire `quality.production_release.aggregate` into the final production path and persist a fingerprint-bound release receipt for the candidate.
5. Expose `candidate.visible.get` through `studio/host_bridge.py` and `host_bridge_contract.json`; keep `candidate.review.get` for richer Studio review data, but document it as not the agent manuscript release boundary.
6. Update host bootstrap/HARNESS contracts so DRAFT/REVISE agent hosts require the production runtime capability and are forbidden from synthesizing Quillframe manuscript output when the capability/release is unavailable.
7. Add unit and integration regression tests for missing release, pending/fail, stale candidate, fingerprint mismatch, fabricated host booleans, raw-draft non-disclosure, and valid release success.
8. Run full CI, download the final exact-head artifact, rerun tests in the chat Linux container, then execute one real DRAFT flow for user quality review.

## Design constraints

- No alternate production engine in prompts or host code.
- No second Canon authority in ephemeral SQLite.
- No weakening of independent semantic review.
- Release and visibility are deterministic authorization/composition layers; literary judgment remains owned by registered semantic contracts.
- No consumer Project repin until Framework change is merged and separately authorized.
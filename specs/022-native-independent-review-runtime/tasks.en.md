# Tasks 022 · Native Independent Review Runtime

- [x] Freeze baseline `05efed31d37a27e901ab777fa3d544e078d65305`.
- [x] Create isolated branch and record the 116-test/v9 baseline.
- [x] Task 1: frozen packet, durable lease/attempt, generic receipt, Host Bridge v10, readiness (`a0f0a15` and follow-up recovery/fencing fixes).
- [x] Task 2: native agents/hooks, exact-packet local runner, repaired GitHub adapter (`2bb6068`).
- [x] Task 3: mapped manifest, projection preview/apply/status, early preflight (`9480b06` through `ee70d2d`, including migration compatibility).
- [x] Task 4: paired docs, complete regressions, deterministic build, final review (`ccd3cd5` through `0775147`; clean Framework suite 181/181).
- [x] Task 5: local Project design, CH001, native Codex review, visibility-only retrieval. The fresh local chain is recorded in `runtime/evidence/CH-001.v0.9.1-local-chain.evidence.json`; the quarantined pre-reset material remains outside the active overlay.
- [x] Prove `accepted=false` and `settled=false` and record all exact fingerprints. The released candidate was retrieved only through `candidate.visible.get`; the handoff is `runtime/evidence/CH-001.v0.9.1-local-chain.human-review.md`.

## Task 5 evidence

- Framework commit: `9668aefa1dfc7cbdd1be01b7b0b990cd585a7b21`.
- Framework bundle: `sha256:38cf2ed4b8ec62704c5522a25fc54a251148b900397d1619941d2da56dd81ad7`.
- Projection: `sha256:d7e26adf0cb1752bdaa8f8d300e04b4bf51a2547857c11d956ae21835f031fb9`.
- Projection manifest: `sha256:a2ab5c2bd75bca410472bfe0cfa1a53dd77fccd1f48b33832248eee76308a581`.
- CH001 run: `run_4f4aa5346081460c9cb2db67bc88f65d`; candidate: `cand_0c8dfacc021449959da57d643f8a072f`.
- Candidate: `sha256:a7d4ca13a245c5c6d3d0e5c2b6ea32c25d7350241d335d1f8f7eb4918bcf6d9b`.
- Native reviewer: exactly one `codex_native_subagent` invocation through the isolated exact-packet local adapter; Claude was not used to review this candidate.
- The overlay contains only CH001 review evidence and handoff output for this run. CH002/CH003 were not projected, contextualized, drafted, or reviewed.

# Tasks 022 · Native Independent Review Runtime

- [x] Freeze baseline `05efed31d37a27e901ab777fa3d544e078d65305`.
- [x] Create isolated branch and record the 116-test/v9 baseline.
- [x] Task 1: frozen packet, durable lease/attempt, generic receipt, Host Bridge v10, readiness (`a0f0a15` and follow-up recovery/fencing fixes).
- [x] Task 2: native agents/hooks, exact-packet local runner, repaired GitHub adapter (`2bb6068`).
- [x] Task 3: mapped manifest, projection preview/apply/status, early preflight (`9480b06` through `ee70d2d`, including migration compatibility).
- [x] Task 4: paired docs, complete regressions, deterministic build, final review (`ccd3cd5` through `0775147`; clean Framework suite 181/181).
- [x] Task 5: reset and rerun the local Project design/CH001 chain, native Codex review, and visibility-only retrieval. The current chain is recorded in the consumer overlay at `runtime/evidence/CH-001.v0.9.1-local-chain.current.evidence.json`; all pre-reset material remains in a recoverable `/tmp` quarantine.
- [x] Prove `accepted=false` and `settled=false` and record all exact fingerprints. The current released candidate was retrieved only through `candidate.visible.get`; the handoff is `runtime/evidence/CH-001.v0.9.1-local-chain.current.human-review.md`.

## Task 5 evidence · current reset chain

- Fresh Project and runtime data are recorded in the external, machine-readable CH001 evidence JSON; no consumer Project database is stored in this Framework repository.
- Exact Framework commit is resolved from the consumer lock and repeated in the external CH001 evidence JSON at execution time.
- Framework bundle: `sha256:3fd739b14b6c9ef9e0493cf186f4ca6eb4a7092e9c6180234eeccc300a5074d3`.
- Projection: `sha256:5143ee28e8e1ef1bd43d2ba9c04026d57ca94db5df8c1b901f8c49ac85170a7e`; manifest: `sha256:a3cfb21678401cc7def3d92a8c18948764654fbf9d498ec426e3866d85c317c8`.
- Context bundle, run ID, candidate ID, and all lifecycle fingerprints are authoritative in the external CH001 evidence JSON.
- Candidate: `sha256:27604cafbab04b5e4cf2dacb25cbcad8f3f3db8c1f59b7d4f096cabbf7955145`.
- Native reviewer: exactly one `codex_native_subagent` lifecycle with a distinct reviewer session, exact packet/result/receipt binding, and reviewer tool denial; Claude was not used to review this candidate. The exact identities are authoritative in the external evidence JSON.
- Review Draft, handoff, and evidence are stored in the user-selected consumer overlay outside this Framework repository.
- CH002/CH003 were not projected, contextualized, drafted, or reviewed. `accepted=false`, `settled=false`, and Frostloom remote remained untouched.

The previous 9668aef chain is historical evidence only; it is not the current Review Draft and must not be presented as the release-chain result.

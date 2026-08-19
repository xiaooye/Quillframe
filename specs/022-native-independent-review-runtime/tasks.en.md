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

- Fresh Project: `/tmp/qf-ch001-current-3gsi8ej8/project`; runtime data: `/tmp/qf-ch001-current-3gsi8ej8/runtime`.
- Framework commit: `004e17fe8467ca7548b5f5ca631907b243d6deef`.
- Framework bundle: `sha256:5d11762146b592d78a21107ea18efd35ac06d15f17ef37f9fa5516efc0421a2e`.
- Projection: `sha256:5143ee28e8e1ef1bd43d2ba9c04026d57ca94db5df8c1b901f8c49ac85170a7e`; manifest: `sha256:a3cfb21678401cc7def3d92a8c18948764654fbf9d498ec426e3866d85c317c8`.
- Context bundle: `sha256:770a0d9f267c72a47dcca8dbb6480c899122bfb2f3d2acec191cdca3f0177b53`.
- CH001 run: `run_e46dc78fca7a45ee940c10f33073b37f`; candidate: `cand_72fac8a088eb478cb46d40d1d735d3f8`.
- Candidate: `sha256:27604cafbab04b5e4cf2dacb25cbcad8f3f3db8c1f59b7d4f096cabbf7955145`.
- Native reviewer: exactly one `codex_native_subagent` lifecycle, with a distinct reviewer session `ses_review_2e11aef40cc848f38dda216288e90e56`, exact packet/result/receipt binding, and reviewer tool denial. Claude was not used to review this candidate.
- Review Draft: `/var/home/pc/Documents/card/new cards/chinaboy_webnovel_quillframe/manuscripts/review/CH-001.review-draft.v0.9.1-local.md`; handoff/evidence are the `.current.*` files beside it.
- The current overlay contains only CH001 review output and hook/lock metadata. CH002/CH003 were not projected, contextualized, drafted, or reviewed. `accepted=false`, `settled=false`, and Frostloom remote remained untouched.

The previous 9668aef chain is historical evidence only; it is not the current Review Draft and must not be presented as the release-chain result.

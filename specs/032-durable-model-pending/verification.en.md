# Durable model pending verification

2026-08-31 · deterministic evidence recorded; live production evidence is intentionally separate.

## Contract under test

The verified claim is narrow: a keyed local model worker may outlive its HTTP waiter without duplicate dispatch, charge, or result consumption. This record does not claim that a model result is literarily good, independently reviewed, or released.

## Deterministic evidence

The focused suites cover:

- stable loopback request-key hashing with unchanged request bodies;
- `202 model_pending` normalization and terminal worker failure;
- same-key packet reuse, changed-body conflict, and concurrent first publication;
- worker running/finalizing/completed/failed state and heartbeat publication;
- keyed execution past the original deadline with no default process timeout;
- pollable stage survival after its original deadline;
- crash before the first 202 and transient polling failures;
- same stage-call identity and exactly one journal row on resume;
- text-free native pending projection;
- exact author-revision checkpoint reuse with eight fresh main calls when context is unchanged.

The full author-revision and production-runtime regression completed `107/107` before the final no-timeout delta. The final focused and combined suite results must be recorded after the delta is complete.

## Live evidence still required

- final source snapshot fingerprint and deployed commit;
- REVISE run ID and one-off pack fingerprint;
- every main call's stage identity and confirmed/pending history;
- proof that polling did not add rows or charges;
- fresh independent-review invocation and exact judgment binding;
- final candidate/revision fingerprints;
- reset-epoch usage, historical ledger offset, and remaining budget;
- explicit confirmation that acceptance and settlement were not performed.

## Completion rule

Engineering is complete only when deterministic suites and documentation pass. Live execution is complete only when the authorized REVISE and independent review pass Core. Literary acceptance remains the user's decision.

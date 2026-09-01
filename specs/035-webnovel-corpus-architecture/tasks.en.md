# Web-Novel Corpus Architecture Tasks

2026-08-31 · task ledger

## Contracts and execution

- [x] Define the six-domain hierarchy, chapter positions, and narrative spans.
- [x] Add v2 observation, candidate, compiled, and Writer projection schemas.
- [ ] Add an independent v2 research run and dimension state without migrating V5.
- [x] Replace the five semantic contracts and local model adaptation.
- [x] Make old v1 input fail closed at the current entry.

## Production and publication

- [ ] Move the public atlas and production loader to `domain + dimension`.
- [ ] Limit Writer selection to one through four Chinese mechanism cards per task.
- [ ] Preserve Reader/reviewer blindness and manual promotion authority.

## Verification

- [x] Add hierarchy, schema, fingerprint, cross-work support, and counterexample tests.
- [ ] Add demand-driven activation, holdout isolation, and no-fabricated-artifact tests.
- [ ] Rebuild web-novel fixtures and three-arm order-swapped evaluation.
- [ ] Run documentation QA, focused tests, relevant deterministic CI, and `git diff --check`.
- [ ] Run a separately authorized live literary A/B; make no uplift claim before it exists.

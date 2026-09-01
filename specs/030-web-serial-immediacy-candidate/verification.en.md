# Web-serial immediacy candidate · Verification record

2026-08-28. The version-3 candidate and one-chapter review protocol have completed deterministic verification. This record reports only completed engineering evidence; literary quality remains in `review` until the author has reviewed a fresh complete chapter.

## Current evidence

- The version-2 registry and bilingual foundation have been preserved byte-for-byte with SHA-256 values matching the pre-edit files.
- Both pairs in the first version-2 batch are recorded as `both_bad`; mappings remain sealed, and the two remaining batches are unreviewed and ineligible for inference.
- Deterministic tests cover one-chapter preparation, production-release binding, feedback lineage, snapshot blocking after rejection, private-material isolation and append-only storage.
- This work made no additional model call. The default remains `baseline`, and version 3 remains an explicit opt-in candidate.

## Deterministic results

- WSL Python 3.14.4: 137 relevant tests passed — 18 craft-resource/runtime-routing, 12 historical-pairwise-artifact, 7 sequential one-chapter review, 14 prose-quality-contract and 86 production-runtime tests.
- `python3 scripts/docs_quality.py`: 0 errors and 21 pre-existing non-blocking warnings in unrelated documents. `python3 scripts/quillframe_docs_quality.py`: 0 errors.
- Python compilation, JSON/YAML parsing and `git diff --check` passed. The first combined test command omitted the tests directory from `PYTHONPATH`, causing two module import errors; the repository-correct invocation then passed all 30 affected tests with no assertion failure.
- A wheel built from the working tree installed successfully. The installed package loads registry version 3, contains the exact version-2 registry and bilingual foundation history, and keeps candidate cards absent from default `baseline`.
- The current registry SHA-256 is `4168261f627cbfbada263923c55756940d2d89ff6e5ce0019df96bedccaf6495`; the version-3 Chinese and English foundation file SHA-256 values are `c53d9e405cd95b63629090873f17c68adeedef5832362045678d9ceb39e6b333` and `009a2be04ac43b1c5d19656d2e842f4ea14ddfc164c5b2941f4757d57394a7a7`.

These results establish versioning, freeze, rollback, isolation and review-sequence behavior. They do not prove version 3 has achieved the intended web-fiction feel. The remaining gate is a separately run full production execution that presents one entirely fresh complete chapter for the author's absolute review.

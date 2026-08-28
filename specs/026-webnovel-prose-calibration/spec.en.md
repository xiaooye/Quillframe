# Chinese webnovel realization and reader calibration

2026-08-28 · Primary mode: `SYSTEM-IMPROVE` · In implementation; quality improvement is unverified.

This authorized change applies the [preceding research](../025-chinese-webnovel-production/prose-quality-research.en.md) to actual model inputs, review criteria, and evaluation. Historical research remains intact. No external skill code, original novel text, consumer facts, or automatic preference activation is introduced.

## Scope and acceptance

1. Writing separates causal constraints from prose organization. Authorized viewpoint, character responses, conversational aims, and narrative duration guide realization. No universal event, gesture, sentence, viewpoint, or gratification quota is imposed.
2. Reading context comes from an explicit public declaration in the current frozen request, with closed types, provenance, and fingerprints. Writing, pressure, blind reading, and independent review receive only their permitted inputs. Arbitrary plan dictionaries are not mined for presumed public information; missing positioning is not invented.
3. Actual Reader and independent rubrics require evidence of reading value in the prose and may reject coherent but flat event reports. Quiet scenes, restraint, and engaging procedure remain valid. A pressure proposal does not establish experienced payoff.
4. An author can explicitly request changes to a released, unaccepted draft. A new revision binds the original candidate, release evidence, and revision receipt without changing the old manuscript or verdict. The request is not relabeled as a model rejection, and all new-candidate gates remain required.
5. Complete synthetic Chinese scenes cover at least two genres and positive/negative contrasts. Expected labels are evaluation hypotheses, not human approval or retention evidence. Normal tests make no model calls.

## Evaluation and authority

Reader calibration uses registered `reader.engagement_audit`. A sample without real prequalification cannot dispatch `quality.production_review`. Its rubric calibration instead uses the existing blind-evaluation entry point, binding the complete registered purpose, rubric, and output specification as a snapshot without production authority. Actual independent production review runs separately after the new candidate qualifies.

Generation comparisons and reviewer calibration separately record inputs, models, call counts, original responses, order, and versions. False acceptance/rejection on fixed fixtures does not establish general quality. Tests and model reports do not replace author reading.

## Compatibility and rollback

Version targets: quality pack 8, production-loop pack 6, narrative-memory pack 4, and `quillframe_repair_policy_v3`. The native project format remains 1.0. Old contracts may verify immutable historical evidence or explicitly isolated baselines only; new production jobs require the current registry. Historical verdicts never become review evidence for a new candidate.

Registered semantic workers retain one model request and a 180-second deadline, with a 64,000-token hard ceiling matching ordinary production stages. The earlier 32,000-token ceiling could reject a complete rule audit solely because of authoritative rules, project plans, candidate text, and host overhead. This change neither removes rules nor increases the host's cumulative call authorization.

Rollback baseline: `54c64c0`. New runs freeze exact code and inputs; active source replacement is forbidden. Code rollback does not rewrite receipts, candidates, or usage records. Model execution retains the host's existing cumulative authorization without resetting historical spending.

## Non-goals

No cloud deployment, remote push, automatic acceptance or settlement, later chapters, platform-retention claim, or named-author imitation is included.

## Runtime interfaces and verification artifacts

The author entry point accepts a closed `payload.reader_positioning` declaration: `schema=quillframe_reader_positioning_v1`, `visibility=reader_eligible`, and at least one nonempty `genre_profile` or `platform_profile`. Each profile is limited to 160 characters and must contain only reader-visible positioning. Chapter position derives from the frozen reading order and cannot be overridden here. Missing positioning does not authorize inference from private plans.

`candidate.revision.request` retains its authorization and idempotency checks. It returns `next_action.payload.repair_source` for a subsequent explicit `author.run.start`, containing only `source_candidate_id`, `revision_request_id`, and `expected_candidate_fingerprint`. The new revision verifies the original release, complete review evidence, and parent ancestry, then freezes a safe instruction projection. Full authorization receipts never enter writing context. Internal failed candidates retain their existing three-reference entry point.

Internal repairs inherit explicit author revision requests from the verified preceding objective envelope. Later author directions take precedence where requests conflict; the Editor judges that conflict, while Core preserves their exact source references and chronological order. Current plans are frozen again rather than copied from an obsolete envelope. Neither these requests nor the repair history enter blind Reader or independent review.

`evals/chinese_reader_calibration.py` prepares, records, and counts evaluations without dispatching models. `prepare_calibration` / `save_prepared` separate blind packets from hidden labels; `capture_execution_identity` binds actual run settings; `record_result` preserves exact results; `summarize` / `compare_reports` report disagreements. Only an explicitly authorized external executor may spend model calls. Local provenance requires an actual `host_run_id` and cannot impersonate a GitHub workflow.

If the author supplies a separate outline during implementation, production validation may create a native project and run `DRAFT`. It cannot borrow another draft's revision ancestry or inherit legacy project state. Private materials and their source records remain in the downstream project.

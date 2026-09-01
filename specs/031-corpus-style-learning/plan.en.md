# Corpus style learning implementation plan

2026-08-28 · planned `SYSTEM-IMPROVE` sequence, updated with the 2026-08-29 execution checkpoint · research and specification are frozen; deterministic implementation evidence is recorded, while live V5 evidence remains pending.

The work proceeds from private evidence boundaries to source-free contracts, then to runtime selection and blind evaluation. It does not begin by training a model or publishing a corpus. Each phase has a rollback point, deterministic evidence and an explicit boundary between completed engineering and unresolved literary judgment.

## 01 · Preconditions and reconciliation

1. Re-read current HEAD and preserve unrelated concurrent changes.
2. Confirm the local V5 study is still `proposed`, with no semantic run or public release.
3. Freeze a private backup and before-state fingerprint before any same-ID V5 mutation.
4. Record the current source cohort, content profile, eligibility policy and analysis protocol as separate values.
5. Reconcile this specification with the current Corpus policy, ingest protocol, semantic contract catalog, learning promotion gate, craft registry and runtime isolation rules.

The allowed V5 mutation is narrow: while the study is unconfirmed, refresh its same-ID proposal atomically and produce a new preview/fingerprint. Do not create V6. Do not confirm, run or release merely because the proposal refresh succeeds.

The current read-only source checkpoint is `evidence_scope_routed`, not a literary-quality `HOLD`. Its anonymous routes are one language-scope signal; three short-or-incomplete signals that may support local prose/scene evidence but not unsupported whole-work claims; and two restart/concatenation signals that require a boundary, a non-crossing passage or a narrower claim. Window hygiene applies only to passages actually requested by AI; no pre-confirmation full-pool exposure is required. The user has not confirmed the exact rights/scope/profile/hash, so V5 remains `proposed` at `sha256:87cebcbc251992ba7b5ed19714117c53d688524c1114734bfaf204e58f6d856b`, with no checklist lock, semantic run or publication.

## 02 · Phase A — typed style domain

Introduce the canonical ordered `STYLE_AXES` and closed, deterministic types for:

- private structural segment identity and work-family split;
- `quillframe_style_observation_v1` and its opaque evidence references;
- `quillframe_cross_work_craft_candidate_v1`;
- `quillframe_style_contract_v1`;
- `quillframe_writer_style_projection_v1`;
- `quillframe_style_leakage_report_v1`, evaluation bundle and invalidation receipt.

Implement and test the public module boundary through `make_observation`, `validate_observation`, `make_craft_candidate`, `validate_craft_candidate`, `compile_source_free_craft_candidate`, `compile_style_contract`, `validate_style_contract`, `compile_writer_safe_projection`, `validate_writer_projection`, `check_local_leakage` and `validate_leakage_report`.

Validators own schema, enums, bounds, exact identity, fingerprints, source-free forbidden-field checks and version compatibility. They do not decide whether a passage is elegant, which scene function matters, or whether evidence semantically supports a mechanism.

Add migration-free storage only where the current development contract permits it. New state must be isolated from Project Canon, runtime production state and private user taste. A schema mismatch fails closed; no adapter or automatic upgrade is added for pre-1.0 data.

Rollback point: remove the unused new tables/contracts while leaving V5 and existing craft v4 behavior unchanged.

## 03 · Phase B — scene-aware private sampling

Build an addressable range inventory that owns only mechanical boundaries, locators and identity; keywords, punctuation and scores must not become scene/style classification. Model contracts classify scene function, style dimensions, evidence scope and uncertainty from bounded candidates. Persist locators, fingerprints and prose-free judgments, not prose.

Replace fixed-position-only analysis with an adaptive queue:

1. let the model request a bounded initial evidence set from the available source pool;
2. bind identity and ephemerally materialize the requested passages;
3. let the model classify scene/style, evidence scope, contradiction and uncertainty;
4. let the model propose the next minimum-sufficient batch or cross-work synthesis;
5. let the model give a continue/converge reason while the runtime validates citations, budget and typed stopping state.

The TXT adapter must materialize a bounded requested passage and bind the exact active source version, raw file identity/hash and final passage fingerprint. Neither a whole-book mechanical scan nor a full-pool performance benchmark is a confirmation gate. The existing streaming implementation and full-source fingerprint may remain as safe-I/O machinery and engineering diagnostics, but they do not decide literary quality, scene classification, next sample or semantic convergence.

Window hygiene remains lossless and contextual: an AI-requested window containing URL/domain, HTML/script or distribution/navigation boilerplate is rejected as a whole window, never line-edited into synthetic prose; the model then requests replacement evidence. Ordinary body/appearance language, including isolated `巨乳`, is not a hygiene or adult-profile trigger. When one requested source cannot be materialized safely, only that evidence request is blocked and routed truthfully; the entire 120-work pool does not automatically fail.

Split by logical work family before analysis. Fixtures must cover alternate editions, serial snapshots, missing chapters, very long paragraphs, dialogue-heavy material, quiet reflection, body/appearance description and ambiguous boundaries.

Rollback point: the old fixed-window runner remains callable under its frozen protocol for historical receipts; no new run silently changes protocol after confirmation.

## 04 · Phase C — semantic observation and synthesis

Version semantic contracts for three distinct judgments:

- segment function and multi-axis observation;
- per-work claim, variation and contradiction synthesis;
- cross-work contrast, counterexample and applicability synthesis.

Inputs contain only the minimum bounded range and required private context. Private observations retain only opaque evidence references and bind exact job, protocol, source version, segment and model-execution provenance in their enclosing audit records. Reject records that quote, closely paraphrase or expose identities, characters, settings or plot details. Source-free status begins only after the explicit compiler boundary.

Use PROSE-inspired iterative refinement: test each claim across multiple independent samples, remove unsupported specificity, seek contrary successful examples and split a broad claim when evidence supports narrower conditions. Do not use evidence counts as a semantic merge heuristic.

Rollback point: semantic results remain candidates and can be invalidated without affecting Writer, Canon or the public registry.

## 05 · Phase D — `StyleContract` and source-free compiler

Compile eligible cross-work claims into the exact version-1 schemas. A private candidate must contain:

- one canonical style axis, operation and intended effect;
- applicable and avoid conditions plus a failure boundary;
- an explicit content zone and integer confidence representation;
- opaque evidence references plus bounded support and counterexample explanation strings;
- support from at least two distinct governed works and at least one counterexample;
- a deterministic record fingerprint.

Use `compile_source_free_craft_candidate` to remove evidence references, then `compile_style_contract` to build a `source_free` contract. The internal contract may retain opaque craft IDs and aggregate support/counterexample counts. Use `compile_writer_safe_projection` for Writer and public delivery: its craft entries retain only axis, operation, effect, conditions, failure boundary, content zone and confidence. They contain no evidence/source/work/contract/craft IDs and no counts. Integrity fingerprints, evaluation binding, lifecycle and rollback state remain in their exact governed layers rather than being added as ad hoc schema fields.

Generate examples from unrelated synthetic premises only. Before a card may leave the private boundary, compare every public string and synthetic example against private source identities and sampled ranges using exact/normalized character n-grams, token shingles/MinHash, identity/content review and external semantic similarity review. Store the exact local report with policy, numeric findings and fingerprints; it always records `release_ready=false` and `semantic_check.status=required_external`. Invalid/incomplete inputs fail as typed errors, while tool/model provenance belongs in the enclosing execution receipt.

Rollback point: disable the compiler version and delete only releasable projections; keep private dependency evidence needed for audit unless rights policy requires removal.

## 06 · Phase E — runtime selector

Extend the craft snapshot path without changing the default behavior. An explicitly selected candidate mode freezes the eligible pack and asks the semantic selector for zero to four mechanisms relevant to the current scene. Validate selection against the internal contract, then build and validate the compact Writer projection. The projection sets `attribution_mode` to `source_free` and `semantic_leakage_check` to `required_external`; a deterministic local leakage report is necessary but cannot satisfy that external semantic gate by itself.

The projection enters raw-draft and surface-realization stages only. Add negative tests proving that it is absent from Blind Reader, independent review, Canon/state consumers, hidden expected data and unrelated stages. Current explicit instructions and accepted Project authority remain higher priority.

Rollback point: disable the candidate mode and restore the prior craft registry/snapshot. Existing frozen runs keep their exact snapshot; new runs use the prior default.

## 07 · Phase F — blind evaluation and promotion evidence

Create source-independent held-out fiction tasks covering the intended scene-function × style-axis cells. Build sealed control/candidate queues with order swapping and fingerprint-bound inputs. A baseline arm may be added as an ablation, but the promotion comparison remains current control versus candidate.

Collect separately:

- deterministic measurements and leakage results;
- Blind Reader reactions;
- independent aspect-level semantic judgments;
- explicit author/human decisions.

Evaluate content/Canon fidelity, causal movement, target mechanism, naturalness, readability, engagement, diversity, originality and leakage. Report ties, mixed outcomes and insufficient evidence. Do not collapse them into one automatic promotion score.

A promotion candidate must bind its exact contract pack, tasks, outputs, randomized mapping, judgments, CI commit and rollback reference. The existing promotion gate may report prerequisites satisfied but continues to return no behavior-write authority.

Rollback point: mark the pack contested/deprecated, remove future eligibility and restore the previous registry version. Preserve failed evidence as regression material outside Writer context.

## 08 · Phase G — public General Style Atlas

Add or extend closed schemas only after private leakage and evaluation paths pass. The public artifact is the exact validated Writer-safe projection or a stricter subset: controlled axes, operations, effects, applicability/avoidance conditions, failure boundaries, content zones, confidence representations and integrity fingerprints. It contains no evidence references, record/work/contract/craft IDs or support/counterexample counts and is never a reduced copy of the private ledger.

Before release:

1. create an exact local preview and manifest fingerprint;
2. validate the closed schema and bilingual human explanation;
3. run private identity/prose leakage comparison;
4. perform rights/provenance and semantic overreach review;
5. request exact human confirmation;
6. publish through the authorized release transaction;
7. verify the registry and post-release artifact hashes.

V5 remains the source study identifier. Analysis-protocol, StyleContract, craft-pack and public-atlas versions advance independently; none is called V6.

## 09 · Test strategy

### Deterministic tests

- schemas, enum and forbidden-field rejection;
- same-ID V5 atomic refresh and before-state mismatch;
- work-family split and no cross-split derivative leakage;
- exact binding of model evidence requests, scene/style judgments and next-sample results;
- bounded materialization, window reopen and replay on small synthetic fixtures;
- exact raw-file, decoded-text, prior-manifest and final-passage binding, with drift rejection at every reopen/materialization boundary;
- whole-window hygiene rejection plus deterministic refill, without trimming suspect lines into a new passage;
- hard-budget incomplete state and stopping-state truthfulness;
- exact binding and invalidation on source/protocol/candidate drift;
- body/appearance vocabulary remains eligible for general analysis;
- explicit-content profile separation and no cross-profile aggregation;
- Writer-only projection and reviewer isolation;
- closed public projection and adversarial leakage fixtures;
- sealed/randomized A/B queue and stale-review rejection;
- version, rollback and consume-once behavior;
- no normal-CI model or external-service calls.

Large-file CPU, memory and throughput benchmarks are adapter diagnostics only. They are not gates for source-pool confirmation, real semantic execution, literary quality or release, and no pre-confirmation full-pool performance smoke should be run merely to “finish 120 works.”

### Semantic and human verification

- range observations genuinely distinguish scene function from prose style;
- contracts preserve mechanism and boundaries without source reconstruction;
- counterexamples narrow rather than merely decorate claims;
- blind candidate outputs improve intended axes without homogenizing voice;
- reviewers remain unaware of treatment;
- author judgments are recorded without converting one preference into universal craft.
- registered-contract and synthetic-runner tests now mark the dynamic work-pool and early-convergence engineering slice complete: model-contract requests activate the requested eligible work/scene-function evidence, untouched members stay available and unanalysed, and a larger pool can stop early. This does not mark real V5, style learning, blind/leakage qualification or publication complete.

## 10 · Documentation and release synchronization

After behavior exists, synchronize the manifest, Corpus policy and ingest protocol, adaptive-learning docs, Corpus/public README, semantic-contract catalog, craft guidance docs, eval documentation and bilingual specifications. Current implementation and schemas remain higher authority than this proposed plan.

Run focused tests first, then the relevant full deterministic suite, documentation QA, schema/JSON/YAML parsing, package/wheel smoke checks and diff hygiene. Real model runs are separately authorized and never part of ordinary CI.

## 11 · Completion truth

Engineering is complete only when the implementation, deterministic tests, rollback and documentation are green on an exact commit. Style learning is complete only when the real V5 analysis, holdout evidence, leakage review and blind human/independent evaluation pass. Public release is complete only when an exact authorized publication exists in the registry.

Those are three distinct completion claims and must be reported separately.

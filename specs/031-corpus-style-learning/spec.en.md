# Corpus style learning specification

2026-08-28 · proposed `SYSTEM-IMPROVE` contract · deterministic/synthetic engineering evidence is recorded; live V5 and literary validation remain pending.

Quillframe will turn a governed, private collection of works into source-free, transferable prose guidance without treating source count as learning depth, exposing source identity, or asking Writer to imitate a named author. The design keeps the existing V5 study identity, replaces fixed-position style inference with scene-aware adaptive evidence collection, represents conclusions as typed `StyleContract` candidates, and promotes guidance only after leakage checks and blind causal evaluation.

The target uses an AI-native ownership boundary: the model owns scene/style classification, evidence scope, gaps, next-sample choice and cross-work convergence; the Python runner owns only source identity/version binding, minimum bounded materialization, window hygiene, budgets and receipts. Typed schema and leakage gates remain deterministic release controls rather than literary judgment. Registered-contract and synthetic-runner tests now demonstrate the dynamic-pool engineering behavior, while the real V5 run and literary qualification remain separate and undone.

## 01 · Fixed decisions

1. The study remains `STUDY-GENERAL-QUALITY-REBUILD-V5`. No V6 study is created and V5 is not invalidated merely to revise its still-unconfirmed protocol or membership.
2. V5's 120 works are a governed source set and release cohort. They are not a learning-depth target, a guarantee of representativeness, or a completion threshold.
3. The study remains unconfirmed, unrun and unreleased until the refreshed same-ID preview, exact fingerprint confirmation and all required gates occur.
4. Original prose, quotations, close paraphrases, source-reconstructive summaries, titles, creators, paths, characters, settings and source-derived embeddings remain private and never enter Git.
5. Writer receives only source-free, task-relevant mechanisms. Blind Reader and independent evaluators receive neither the selected guidance nor the treatment identity.
6. Terms that describe anatomy, body shape or appearance—including `巨乳`—do not by themselves classify a work as `adult_explicit`. Body, appearance and clothing description are legitimate style-observation domains. Explicit sexual acts, coercion and other genuinely explicit content remain separately governed.

## 02 · Objective and non-goals

### Objective

Produce versioned General Craft candidates that describe **how** prose creates an effect, **when** the mechanism applies, **when it fails**, and **what evidence supports its boundary**. Demonstrate benefit on unseen tasks without leaking or imitating source material.

### Non-goals

- reconstructing or simulating a named author's identity;
- creating a single “good webnovel style” or scalar quality score;
- making every Project use Save the Cat, Story Grid, Promise–Progress–Payoff or another macro framework;
- training or publishing LoRA/SFT/DPO weights from the V5 novels in this phase;
- raw-excerpt or source-embedding retrieval into Writer;
- inferring copyright permission, adult content or literary quality from weak metadata;
- allowing a green deterministic test to stand in for literary judgment;
- changing the current default craft mode or promoting a candidate without explicit authority.

## 03 · Authority and lifecycle

The evidence path is deliberately non-authoritative:

```text
private source evidence
→ private observation
→ private claim candidate
→ cross-work verified StyleContract candidate
→ source-free craft-pack candidate
→ blind evaluation evidence
→ promotable report
→ explicit SYSTEM-IMPROVE promotion
```

Every artifact before the final authorized promotion carries:

```text
canon_authority = false
framework_write_authority = false
durable_user_taste_write_authority = false
writer_activation_authority = false
```

Minimum truthful states are `proposed`, `sampling`, `semantic_pending`, `candidate`, `evaluation_pending`, `contested`, `promotable`, `promoted`, `deprecated` and `invalidated`. `Promotable` reports satisfied evidence prerequisites; it does not grant write authority.

V5's source identity, content profile, source-version fingerprints and confirmation receipt remain distinct from the analysis-protocol version and resulting craft-pack version. After exact confirmation, immutable V5 source membership/profile cannot be silently changed; a later source drift invalidates dependent observations and requires an authorized rebuild path. Before confirmation, same-ID refresh is atomic and must issue a new exact preview/fingerprint.

## 04 · Private Style Observatory

### Structure-aware segmentation

The deterministic runtime may build a reproducible, addressable private locator map with mechanical chapter/paragraph boundaries, source/version fingerprints and offsets, but it must not treat keywords, punctuation or scores as scene-function or style judgments. The model classifies actual scene/style function, evidence scope and uncertainty from bounded candidates. The locator map never stores source prose.

Fixed opening/middle/closing positions remain useful coverage strata but are no longer the entire learning sample. The sampler additionally covers:

- scene position: opening, development, pivot, aftermath, closure and transition;
- dominant function: dialogue, physical action, interiority, exposition, environment, body/appearance/clothing, relationship movement, reveal, reflection and connective summary;
- pressure/register: quiet, comic, intimate, tense, formal, colloquial and high-action where evidenced;
- viewpoint and dialogue configurations relevant to the work.

A segment may belong to more than one semantic stratum. The model decides literary function, uncertainty and the next evidence request under a typed contract; deterministic code validates only the request identity, range, budget and receipt.

### Adaptive sampling

Sampling is iterative and question-bounded:

1. build a low-cost addressable range inventory with no literary conclusion;
2. let the model request a bounded initial evidence set;
3. let the model classify scene function, style dimensions, evidence scope and uncertainty;
4. let the model identify coverage gaps, contradictions or the most valuable claim to test;
5. let the model request only the next minimum-sufficient passages or advance to cross-work synthesis;
6. let the model submit a reasoned converge/continue decision while the deterministic runtime validates bindings and budget; a hard-budget limit returns an honest incomplete state.

The sampler must not maximize calls, read an entire work by default or exhaust the entire 120-work source pool. The deterministic runtime makes accepted model requests and materialized results replayable from the protocol version, source fingerprints, ledger state and receipts; it need not recreate a literary judgment with heuristics. Budget exhaustion is `sampling_incomplete`, not evidence of saturation.

Train/development/holdout assignment occurs at logical-work-family level before semantic synthesis. Alternate editions, serial snapshots and close derivatives cannot cross splits.

### Evidence-scope routing

Language, completeness and concatenation signals are not pre-confirmation quality gates. The model routes each to the narrowest evidence scope: a language mismatch limits language-specific claims; a short, serial or incomplete work cannot support unsupported whole-work structure claims but may still support local prose/scene observations; and restart or concatenation signals require a boundary, a non-crossing materialization or a narrower claim. A selected window that fails hygiene is rejected and replaced without failing the pool. Only invalid rights, source identity or the safety boundary of an actually requested range blocks that source or evidence.

## 05 · Observation model

The existing eight narrative-effect axes remain useful but are no longer presented as a complete model of prose style:

`scene_entry · causal_progression · dialogue_voice · interiority_distance · information_timing · paragraph_rhythm · relationship_movement · chapter_forward_pull`

The Style Observatory adds a separate prose-style layer. Its canonical `STYLE_AXES` order is fixed so stored records, validators and evaluation cells cannot silently disagree:

```text
prose_voice · syntax_rhythm · lexical_register · psychic_distance ·
descriptive_attention · body_appearance · imagery · dialogue_voice ·
interiority_summary · information_flow
```

These ten axes cover narrator stance and evaluative presence; sentence/paragraph shape, cadence and controlled repetition; diction and specificity; viewpoint access and distance; sensory and descriptive attention; body, appearance, clothing and embodied movement; comparison, humor and irony; dialogue individuation, tactic and turn rhythm; thought, omission, compression, summary and transition; and reveal/orientation. Scene function is a separate sampling stratum, not an extra style axis.

Sentence/paragraph length, punctuation, dialogue proportion and similar deterministic measurements are optional diagnostics only when explicitly requested by the model, not a required style-learning gate. No threshold may declare scene class, prose quality, relevance, adult status, next sample or promotability.

Semantic observations explain effect, mechanism, context, counterexample and uncertainty. Every observation binds exact protocol, model-execution provenance, segment identity and source-version fingerprint outside the public projection. Private observation records may retain opaque evidence references, but never source prose, source identity, quotation, close paraphrase, character/setting detail or an unbounded plot summary. The compiler removes those references before Writer or public use.

## 06 · `StyleContract`

The private observation and cross-work candidate schemas are `quillframe_style_observation_v1` and `quillframe_cross_work_craft_candidate_v1`. They deliberately share one exact field set:

```yaml
schema: quillframe_style_observation_v1 | quillframe_cross_work_craft_candidate_v1
record_id: opaque private identifier
axis: one canonical STYLE_AXES value
operation: bounded craft operation
effect: intended reader or prose effect
applies_when: [bounded condition, ...]
avoid_when: [bounded negative condition, ...]
failure_boundary: observable misuse or regression
content_zone: general | adult_explicit
evidence_refs:
  - work_id: opaque governed work identifier
    evidence_id: opaque segment/evidence identifier
    role: support | counterexample
    evidence_fingerprint: integrity fingerprint
supports: [non-source explanatory support string, ...]
counterexamples: [non-source explanatory counterexample string, ...]
confidence_ppm: integer from 0 through 1000000
record_fingerprint: deterministic integrity fingerprint
```

Conditions, support explanations and counterexample explanations are non-empty, unique bounded string lists; they are not containers for prose evidence. The private ledger retains the reversible mapping from opaque evidence references to V5 sources. Every record needs both support and counterexample evidence; a cross-work candidate additionally requires support from at least two distinct governed works before compilation. This is a deterministic eligibility prerequisite, not proof of semantic convergence: a bound semantic review still decides whether the records genuinely support the same operation, effect and conditions.

Claims must be contrastive. A successful claim distinguishes the mechanism from at least one neutral or superficially similar alternative, records a successful counterexample where the surface pattern is absent, and states when the mechanism causes harm. Single-work observations cannot become `general_craft` contracts.

The source-free compiled contract is the exact closed schema `quillframe_style_contract_v1`:

```yaml
schema: quillframe_style_contract_v1
contract_id: opaque internal contract identifier
content_zone: general | adult_explicit
attribution_mode: source_free
craft_candidates:
  - craft_id: opaque internal craft identifier
    axis: one canonical STYLE_AXES value
    operation: bounded craft operation
    effect: intended effect
    applies_when: [bounded condition, ...]
    avoid_when: [bounded negative condition, ...]
    failure_boundary: observable misuse or regression
    content_zone: general | adult_explicit
    confidence_ppm: integer from 0 through 1000000
    supporting_work_count: aggregate count, minimum 2
    counterexample_count: aggregate count, minimum 1
leakage_policy:
  exact_ngram_size: bounded integer; current default 24
  normalized_ngram_size: bounded integer; current default 32
  shingle_size: bounded integer; current default 7
  fuzzy_jaccard_threshold_ppm: bounded integer; current default 350000
  minhash_signature_size: bounded integer; current default 64
  semantic_check: required_external
contract_fingerprint: deterministic integrity fingerprint
```

No extra status, version, source, title, author, quotation, example or narrative-detail field is permitted inside that object. Lifecycle, protocol version, evaluation binding and rollback state live in their governed enclosing records.

## 07 · Source-free mechanism compiler

The compiler converts eligible cross-work candidates into a versioned, source-free contract and then a smaller Writer/public projection. The implementation boundary is expressed by `compile_source_free_craft_candidate`, `compile_style_contract`, `validate_style_contract`, `compile_writer_safe_projection`, `validate_writer_projection`, `check_local_leakage` and `validate_leakage_report`. The typed leakage result uses `quillframe_style_leakage_report_v1`. The compiler must:

- remove all private evidence references and source identity;
- express guidance as a mechanism, condition, desired effect and failure boundary;
- create examples only from unrelated synthetic content, never by paraphrasing a source scene;
- validate the closed schema and deterministic fingerprint;
- run exact, approximate, entity/content and semantic leakage checks against private identities and sampled source ranges;
- bind every enclosing release record to a contract fingerprint, evaluation bundle and rollback reference;
- fail closed when provenance, novelty or profile separation is unresolved.

The compiler cannot grant promotion or runtime activation. A leakage pass means only that the configured tests found no prohibited match; it is not a copyright opinion.

`check_local_leakage` accepts ephemeral candidate/reference strings at the private boundary but returns no matching prose. Its exact `quillframe_style_leakage_report_v1` result contains `schema`, `local_status`, the always-false `release_ready`, `candidate_fingerprint`, `policy`, `findings`, `semantic_check` and `report_fingerprint`. Each finding contains only `reference_id`, exact/normalized hit counts, shingle and MinHash similarity in parts per million, and `blocked`. The semantic record remains `{status: required_external, performed: false, reason: ...}`. Invalid or incomplete inputs raise a typed failure; even a local `pass` can never grant release.

## 08 · Runtime selection and stage isolation

A frozen production run may expose eligible style cards to a semantic selector using the exact scene goal, viewpoint, pressure, emotional register, genre/platform profile and current user request. The selector chooses zero to four cards by default; zero is valid. “Active” or “eligible” never means automatic injection.

Precedence is:

```text
current explicit request
> accepted Project profile
> authorized user taste
> optional General Craft candidate mode
> baseline
```

Only raw-draft and surface-realization Writer stages receive `quillframe_writer_style_projection_v1`:

```yaml
schema: quillframe_writer_style_projection_v1
style_contract_fingerprint: integrity binding
content_zone: general | adult_explicit
attribution_mode: source_free
craft_candidates:
  - axis: one canonical STYLE_AXES value
    operation: bounded craft operation
    effect: intended effect
    applies_when: [bounded condition, ...]
    avoid_when: [bounded negative condition, ...]
    failure_boundary: observable misuse or regression
    content_zone: general | adult_explicit
    confidence_ppm: integer from 0 through 1000000
semantic_leakage_check: required_external
projection_fingerprint: deterministic integrity fingerprint
```

The projection contains no record, evidence, work, contract or craft ID; no source metadata; no support/counterexample counts; no treatment label; and no judge rubric. Fingerprints bind integrity without revealing provenance. A public craft-pack artifact may use this exact validated projection or a stricter subset, never the private observation, cross-work candidate or internal contract object.

Blind Reader, independent quality review and leakage review receive no selected guidance and no treatment identity. Canon/state context remains separate. Style guidance cannot override Canon, current instructions, character simulation or planning authority.

## 09 · Blind causal evaluation

Promotion requires a fingerprint-bound evaluation bundle with unseen, source-independent fiction tasks. The minimal experiment compares the current control against the candidate on the same frozen scene/plan inputs. Where budget permits, a separate baseline arm measures the value of both the current craft pack and the new candidate.

Requirements:

- work-family and task holdouts are frozen before candidate synthesis;
- arm labels and display order are sealed and order-swapped;
- generation inputs differ only by the bound craft treatment and registered randomness;
- Blind Reader and independent reviewers cannot see the treatment, StyleContract, source evidence or hidden expected outcome;
- multiple tasks cover relevant scene functions rather than one showcase opening;
- automatic metrics, independent semantic review and explicit author/human review remain separate evidence types;
- materially changed candidates invalidate prior reviews.

Evaluation reports separate outcomes for content/Canon fidelity, causal scene movement, target style mechanism, naturalness, readability, engagement, diversity, originality and leakage. No weighted scalar alone can decide promotion. A candidate must show reproducible target improvement without unacceptable regression in the other outcomes.

## 10 · Public projection

The public General Style Atlas artifact committed to Git must be the validated `quillframe_writer_style_projection_v1` object described above, or a stricter closed-schema subset. Its craft entries contain only controlled axes, operations, effects, application/avoidance conditions, failure boundaries, content zones and confidence representations. The two integrity fingerprints bind the projection and its source-free contract without exposing an ID or source relation. Evaluation and release receipts remain separately governed artifacts and cannot be smuggled into this closed object.

Forbidden fields include:

- source title, creator, filename, path or stable private ID;
- record, evidence, work, contract or craft IDs, and support/counterexample counts;
- source prose, quotation, close paraphrase or source-reconstructive summary;
- characters, settings, plot events, distinctive entities or signature phrases;
- raw embeddings, activation vectors, adapter weights or arbitrary extension fields;
- private user-taste evidence or Project-specific facts.

Public release requires exact preview/fingerprint confirmation, schema validation, private leakage comparison, rights/provenance review and an authorized release transaction. Public visibility, abstraction and non-commercial intent do not automatically settle copyright questions.

## 11 · Content-profile boundary

Content profile and style dimension are orthogonal.

- Anatomy, breast/body size, shape, attractiveness, clothing, grooming, scars, disability, posture, movement and other appearance details are ordinary observation material unless explicit context establishes a separately governed content zone.
- The isolated token `巨乳`, or an equivalent body-description term, is not a sufficient adult-classification signal.
- Explicit sexual acts, sexual coercion, exploitation and other genuinely explicit material may remain in a separately confirmed `adult_explicit` study/profile.
- A general study must not import explicit-content mechanisms merely because both profiles analyze body description.
- Classification based on prose requires authorized semantic review; weak title/filename heuristics may only create conservative review candidates, never literary or legal truth.

The public general atlas may therefore include source-free mechanisms for body and appearance description—attention order, viewpoint motivation, embodiment, social meaning, movement and character-specific noticing—without reproducing explicit source content.

## 12 · Stopping, promotion and rollback

Sampling may report `converged` only when:

- required scene-function × style-axis coverage has no material unexplained gaps;
- claim discovery has reached a registered saturation policy across consecutive independent work-family batches;
- each candidate has supporting, contrast and counterexample evidence;
- held-out evidence supports its scope or narrows it explicitly;
- unresolved contradictions are either reconciled or keep the claim contested.

A bound semantic judgment proposes `converged`, and the deterministic runtime verifies its cited evidence and registered stopping policy. Convergence does not require all 120 works to be processed; unused members remain available-pool members and must not be represented as analyzed. Registered `learning.style_axis_reconcile` and synthetic-runner tests now demonstrate that behavior: `next_evidence_requests` activate exactly the requested eligible discovery work and scene-function hints, a larger pool can stop early after model-contract convergence, and untouched members remain `available_unanalysed`. This proves the engineering path only; it does not prove a real V5 run, style learning, blind/leakage qualification or publication.

Promotion additionally requires passing deterministic schemas/tests, leakage review, capability and regression evaluation, independent blind evidence, explicit version/rollback, green CI and human-authorized Framework change.

Rollback disables the craft-pack version, invalidates dependent runtime eligibility, restores the prior registry/default behavior, preserves evidence and receipts, and reruns affected regressions. It never deletes private evidence needed to explain the correction unless rights/storage policy requires deletion; in that case dependent artifacts are invalidated first.

## 13 · Normative requirements

- **SL-001:** retain the exact V5 study identifier; do not create V6 for this correction.
- **SL-002:** treat 120 as source-cohort cardinality only.
- **SL-003:** use scene-aware, function-stratified, adaptive and reproducible sampling.
- **SL-004:** split work families before synthesis and keep derivatives in one split.
- **SL-005:** maintain separate narrative-effect and prose-style axes.
- **SL-006:** require cross-work contrast, counterexample and applicability boundaries.
- **SL-007:** compile private cross-work candidates only into the exact closed, source-free `StyleContract` schema.
- **SL-008:** generate public examples synthetically and run multilayer novelty checks.
- **SL-009:** inject zero to four relevant cards only into Writer stages.
- **SL-010:** preserve Blind Reader, reviewer and treatment isolation.
- **SL-011:** require held-out blind causal evaluation and explicit human promotion.
- **SL-012:** keep originals, identities, evidence mappings and private preferences out of Git.
- **SL-013:** do not classify body/appearance vocabulary alone as `adult_explicit`.
- **SL-014:** keep explicit-content profiles separate without erasing legitimate appearance craft.
- **SL-015:** keep normal CI deterministic and free of implicit model calls.
- **SL-016:** version protocol, contract, craft pack, evaluation and rollback independently.
- **SL-017:** invalidate stale evidence on source, protocol, candidate or treatment drift.
- **SL-018:** never describe a leakage/schema pass as legal clearance or literary proof.
- **SL-019:** treat the 120 works as an exact rights/scope/profile/hash-confirmed available source pool, not a queue that must be completed work by work.
- **SL-020:** route language, completeness and concatenation signals by evidence scope rather than using them as literary judgments.
- **SL-021:** assign scene/style classification, gaps, next-sample choice and cross-work convergence to model contracts.
- **SL-022:** never use full-pool exposure or CPU/memory benchmarks as V5 confirmation, semantic-convergence or literary-quality gates.

## 14 · Acceptance boundary

Engineering acceptance requires schemas, persistence and invalidation tests; bound model-planning request/result and budget tests; evidence-scope routing tests; family-split tests; body/appearance boundary tests; source-free and leakage adversarial tests; runtime stage-isolation tests; sealed blind-queue tests; rollback tests; bilingual documentation parity; and green deterministic CI. The dynamic source-pool slice now meets its synthetic runner and semantic-contract condition; that status grants no live semantic, literary, leakage-review or release credit.

Literary acceptance remains separate. It requires real semantic runs on the confirmed V5 evidence, held-out tasks, independent blind review and explicit author/human decisions. Until those executions occur, this specification defines the target mechanism but proves no style improvement.

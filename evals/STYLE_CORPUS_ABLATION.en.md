# Corpus style three-arm ablation

This evaluation asks whether a source-free corpus candidate changes reader experience relative to both an unguided baseline and the current version-5 craft guidance. It does not generate prose, decide a literary winner, activate learned guidance, or grant release authority. The implementation is [`style_corpus_ablation.py`](style_corpus_ablation.py); its checked-in suite is an explicitly test-only synthetic fixture in [`fixtures/style_corpus_ablation_synthetic.json`](fixtures/style_corpus_ablation_synthetic.json).

## Frozen three-arm comparison

Every case carries one task, one context object, and one randomness object above the arm boundary. The evaluator fingerprints those three values separately and as one generation binding. The three supplied artifacts are then bound as:

- `baseline`: prose produced without craft guidance;
- `current_craft_v5`: prose produced with the currently frozen version-5 craft pack; and
- `corpus_candidate`: prose produced with one source-free corpus-derived projection.

The candidate fingerprint is the SHA-256 digest of the exact UTF-8 prose bytes. The craft fingerprint is the SHA-256 digest of canonical JSON for the complete craft binding. Changing line endings, prose, the writer projection, evidence membership, or any other bound craft field invalidates the prepared plan.

The suite is leave-one-work-out rather than a random passage split. Every opaque work ID is held out exactly once, and the corpus candidate for that fold must cite precisely the remaining work universe. Each case also holds out its declared scene function: that function cannot appear in the candidate's training-scene set. These checks establish experimental separation; they do not establish literary quality.

## Anonymous pair matrix

Three arms create three unordered comparisons. For every case and comparison, the evaluator creates two repetitions, and each repetition contains both presentation orders. The default synthetic suite therefore produces twelve Blind Reader jobs per case.

The registered independent contract is `learning.blind_prose_pair`. Its payload contains only:

- an opaque comparison ID;
- the shared evaluation task and context;
- the shared scene function;
- anonymous samples `A` and `B`; and
- reader-facing criteria.

Arm names, treatment metadata, corpus origin, work IDs, candidate fingerprints, craft fingerprints, holdout declarations, and expected outcomes have no field in that payload. The true `A`/`B` mapping remains in the fingerprint-sealed private plan. Swapped presentations must reuse the exact two prose artifacts, while every completed review requires distinct independent invocation lineage.

Each completed review preserves one separate pair preference—`a`, `b`, `tie`, `both_bad`, or `insufficient_evidence`—and exactly eight dimension records. Every dimension record contains only a leaning (`a`, `b`, `tie`, or `unclear`) and an observation of at most 800 characters:

- `content_fidelity`: compliance with the task, frozen facts, viewpoint, and other content boundaries;
- `causal_movement`: whether actions, reactions, and information change what can happen next;
- `target_mechanism`: whether the case's intended scene function actually works;
- `naturalness`: whether narration, action, and dialogue feel unforced;
- `readability`: clarity of reference, space, sequence, paragraphing, and information load;
- `engagement`: scene pressure, curiosity, emotional pull, and desire to continue;
- `diversity`: context-appropriate expressive and structural range rather than mechanical repetition; and
- `originality`: perceived freshness rather than a claim of source distance or leakage clearance.

The pair preference is not calculated from these records. Aggregation preserves preference counts, dimension-specific counts, bounded observations, and order-consistency evidence independently. It applies no dimension weights, computes no total score, and selects no winner.

Body and appearance description is ordinary prose evidence in this evaluation. Anatomical specificity, including terms such as `巨乳`, neither changes the frozen content profile nor creates a quarantine or preferred answer by itself.

## Separate leakage evidence

Leakage review is not part of the Blind Reader payload. The evaluator first calls the bounded local overlap checker in [`../corpus/style_contract.py`](../corpus/style_contract.py), which reports exact, normalized, shingle, and MinHash findings without returning matched reference prose. A local clean result still records semantic review as required and cannot mark the artifact release-ready.

The second registered independent contract, `learning.prose_semantic_leakage`, receives the candidate sample plus bounded anonymous reference samples with exact text fingerprints. It can report `clear`, `blocked`, or `insufficient_evidence`. Its findings may cite only the supplied opaque reference IDs. Common genre material, ordinary syntax, or an isolated body-description term is not enough to establish leakage.

Semantic leakage is the ninth evidence item, not a ninth Blind Reader dimension. It cannot be converted into originality points or merged into pair preference. The publication boundary also registers `corpus.provenance.public_abstraction`: its closed input contains only completion, candidate, identity-policy, and provenance fingerprints; a declared rights class and bounded basis; current source-dependency status; and the `public_general_style_atlas` target. It has no title, path, or prose field. Its result is `pass`, `blocked`, or `insufficient_evidence` with bounded findings, `authority_scope=evidence_only`, and `legal_safety_claim=false`.

Local and semantic checks are separate gates. A local block can stop the leakage path. A semantic block or insufficient result remains visible. Even when every local report is clean and every semantic review is clear, the output says only that semantic evidence is ready; `release`, `framework_promotion`, `canon_write`, and `durable_user_taste_write` stay false.

## Result states and APIs

Preparation performs zero model calls and starts at `PENDING_MODEL`. Missing, failed, or unsupported reviews stay pending. Complete registered results can produce `SEMANTIC_EVIDENCE_READY`, `LEAKAGE_BLOCKED`, or `INCONCLUSIVE`, but the evidence artifact never weights dimensions, computes a literary-quality score, or selects an automatic winner. Completed results attached to the checked-in synthetic suite require the explicit `allow_synthetic=True` test switch and remain `SYNTHETIC_VALIDATION_ONLY`.

The public evaluator surface is:

- `load_suite` and `validate_suite` for the closed suite contract;
- `prepare_evaluation` and `validate_prepared` for the private, fingerprint-bound plan;
- `blind_reader_queue` for mapping-free pair jobs;
- `semantic_leakage_queue` for the separate leakage jobs; and
- `consume_evidence` for independent-result validation and non-authorizing aggregation.

[`../tests/test_quillframe_style_corpus_ablation.py`](../tests/test_quillframe_style_corpus_ablation.py) uses only original synthetic prose. It verifies determinism, exact bindings, holdout separation, payload blindness, order counterbalancing, independent lineage, leakage-state composition, ordinary `body_appearance` handling, and the absence of fabricated model outcomes. Passing those tests proves the evaluation machinery behaves as specified; it says nothing about which prose arm readers would prefer in a real run.

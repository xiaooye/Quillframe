# Corpus Policy · Govern evidence without turning source access into story or style authority

Quillframe uses corpus material to study **mechanisms**, test preference/craft hypotheses, build eval evidence and identify counterexamples. Corpus is an evidence domain. It is never Project Canon, character knowledge, a hidden imitation prompt, or automatic Framework guidance.

> **Core invariant ✦** Access, rights, storage, analysis, learning and promotion are separate gates. Passing one gate never implies that the next gate has passed.

---

## 01 · What Corpus may support

Corpus evidence may support:

- project-specific craft analysis;
- user-taste hypothesis testing;
- cross-work General Craft research;
- capability/regression eval design;
- mechanism benchmarks;
- counterexample/profile-boundary discovery;
- external evidence for a bounded research question.

Corpus evidence may not by itself:

- create or modify Project Canon;
- prove that a character knows something;
- settle relationship/resource/information state;
- override explicit user/project authority;
- activate durable user taste;
- promote Framework behavior;
- create a reusable named-author imitation profile.

---

## 02 · Rights class and storage intent are different fields

Every source candidate that may enter durable Corpus handling needs a declared `rights_class` and `storage_intent`.

Reference rights classes:

### `redistributable`

Full-text storage may be permitted when there is a documented basis such as public-domain status, a compatible open license, explicit permission, or user-owned/user-authored material with permission to store.

A non-empty rights basis and provenance are required.

### `analysis_only`

The material may be accessed/analyzed under the declared basis, but Quillframe must not store the full text as Corpus data.

Allowed storage may include:

- source metadata;
- derived observations/metrics;
- mechanism analysis;
- summaries;
- a short excerpt only when genuinely required for the declared analysis/eval purpose.

### `unknown`

Rights have not been established well enough for content storage. Only metadata-level storage is permitted until the evidence changes.

A private repository does not turn unknown rights into redistributable rights.

---

## 03 · Deterministic Rights Gate is not legal analysis

[`rights_gate.py`](rights_gate.py) validates whether **declared metadata and requested storage intent are internally consistent with Quillframe policy**.

It enforces, for example:

```text
unknown + anything beyond metadata_only → reject
analysis_only + full_text                → reject
short_excerpt without excerpt_purpose   → reject
redistributable without rights_basis     → reject
```

The validator does **not** infer copyright status from a URL, title, creator name or repository visibility. `legal_analysis_performed = false` is deliberate.

Rights/source status must be established from real evidence through the authorized research process.

---

## 04 · Provenance is mandatory evidence

A durable Corpus record should be able to answer:

```yaml
corpus_id:
source_title:
creator:
source_url_or_ref:
source_type:
language:
publication_date:
rights_class:
rights_basis:
storage_intent:
accessed_at:
content_fingerprint:
analysis_scope:
research_question:
source_tool_or_capability:
```

Not every field must apply to every source class, but substantive claims must remain traceable to a real source/ref and the capability that retrieved it.

If provenance cannot be established, lower confidence, keep only safe metadata, or block the step. Never fabricate a quotation or source access event to complete a pipeline.

---

## 05 · Discovery is not ingestion

A discovery result says **a candidate source was found**. It does not mean Quillframe may copy or persist the source content.

```text
discovery
→ verify source identity + provenance
→ establish declared rights basis
→ choose storage intent
→ deterministic rights gate
→ bounded ingestion / observation
```

The Corpus Scout and discovery runtime may prepare and normalize candidate evidence, but they cannot manufacture authorization that the host/source did not provide.

---

## 06 · Analysis is question-bounded

Do not analyze an entire work merely because it is available.

Start from a concrete research question, such as:

- how does a fast scene create pressure without pseudo-speed fragmentation?
- how is exposition made causal through an active task or conflict?
- how does a supporting character maintain an independent agenda inside a protagonist-centered scene?
- how does a chapter create forward pull without narrator advertising?

Select the **minimum sufficient range/evidence** required to answer the question.

Bounded analysis reduces context waste, imitation pressure, accidental source leakage and confirmation bias.

For the legacy `quillframe_corpus_three_window_benchmark_v1` anonymous public General Corpus, “minimum sufficient” is mechanically capped and frozen:

- exactly 120 distinct logical works in a user-confirmed checklist;
- one fingerprint-bound edition per work;
- exactly three windows per work (`opening`, `middle`, `closing`);
- at most 4,000 Unicode characters per window;
- ephemeral raw materialization, with no source prose in the durable ledger or public bundle.

This sampling profile is a legacy statistical release contract, not evidence that three passages fully represent a work and not the style-learning protocol. Source drift or removal invalidates dependent work and aggregate evidence.

The legacy proposal path uses private metadata to deduplicate edition families and route unidentified, short or metadata-conflicted items for local attention. That diagnostic never establishes literary quality and is not a universal Style Atlas exclusion rule. For style learning, invalid rights or unresolved source identity blocks only the affected source evidence; language mismatch narrows language-specific claims; incomplete or serial material may support local prose/scene claims but not unsupported whole-work claims; restart or concatenation signals require boundary-aware windows or narrower claims. The user confirms the declared rights and scope, one study profile (`general` or `adult_explicit`), the exact 120-work pool membership and proposal fingerprint. Profile mixing remains forbidden.

That three-window cap defines the legacy statistical release, not the depth of prose-style learning. In the `quillframe_corpus_style_learning_v1` target, the exact 120 works form an addressable evidence pool, not a queue or a per-work literary checklist. AI owns scene/style classification, evidence gaps, the next minimum-sufficient sample and cross-work convergence. The Python runner owns only identity/version binding, minimum bounded materialization, hygiene, budgets and receipts; schema and leakage gates remain deterministic release controls rather than literary judgment. Each raw passage remains an ephemeral call payload. Full-pool exposure, CPU/memory benchmarks and larger sample counts provide no automatic completion or publication authority. Registered-contract and synthetic-runner tests now demonstrate dynamic activation of requested evidence, truthful unused pool members and early convergence before the pool is exhausted. That engineering result does not mean V5 ran, a style was learned, blind evaluation or independent leakage review passed, or publication was authorized.

Content profile and style dimension are orthogonal. Body shape, anatomy, clothing and appearance—including an isolated term such as `巨乳`—remain legitimate `body_appearance` observations and are not a sufficient adult-profile signal. Only actual contextual evidence of explicit content is separately governed.

---

## 07 · Counterexamples are required for generalization

Corpus research should actively seek:

- evidence supporting the candidate mechanism;
- successful examples that violate the superficial pattern;
- examples where the mechanism fails;
- genre/platform/profile exceptions;
- alternative explanations for the same observed effect.

A search that only retrieves examples agreeing with the current hypothesis is not strong General Craft evidence.

One work may create an observation. It does not create a universal rule.

---

## 08 · Named-author imitation boundary

Quillframe may analyze broad, transferable craft mechanisms such as:

- scene causality and pressure sequencing;
- information timing;
- paragraph function;
- dialogue embodiment;
- character-agenda independence;
- setup/payoff management;
- broad genre/platform conventions.

It must not turn modern/living authors into reusable imitation fingerprints.

Do not create Framework behavior whose goal is:

- “write exactly like Author X”;
- reproduce signature phrases/cadence from copyrighted work;
- preserve extensive copyrighted passages as style prompts;
- optimize writer context for source imitation rather than mechanism understanding.

User-owned evidence and public-domain material remain subject to their actual rights/provenance and the same authority boundaries.

---

## 09 · Writer isolation

Raw Writer context should normally receive **task-relevant mechanism/profile guidance**, not bulk Corpus text.

Preferred path:

```text
source evidence
→ rights-safe bounded observation
→ per-work mechanism analysis
→ counterexample / cross-work synthesis
→ benchmark / eval calibration
→ minimal relevant guidance
→ Writer
```

Regression bad examples and hidden eval answers stay outside Writer pre-draft context. Corpus/learning memory defaults to post-generation use unless a higher-level contract explicitly makes a particular bounded item writer-safe.

---

## 10 · Learning and promotion remain separate gates

Corpus observations can support `project`, `user_taste` or `general_craft` learning scopes, but the Corpus layer cannot activate them.

General Craft normally requires:

- multiple independent cross-work refs;
- counterexample/profile-boundary evidence;
- capability + regression evals;
- provenance;
- version/rollback evidence;
- green Framework CI;
- authorized promotion after prerequisites pass.

See the [Self-Improvement Protocol](../harness/SELF_IMPROVEMENT_PROTOCOL.en.md).

---

## 11 · Correction and removal

If rights, provenance or analysis evidence later proves invalid:

```text
mark source/item invalid
→ remove storage that is no longer permitted
→ identify dependent analyses / benchmarks / evals
→ invalidate or rebuild derived evidence
→ narrow / contest / deprecate dependent learning hypotheses
→ roll back affected promoted behavior when required
→ preserve correction provenance
```

Derived evidence must remain traceable enough for this dependency repair to be possible.

---

## 12 · Autonomous behavior boundary

The AI research planner may:

- classify scene function and prose-style axes from bounded evidence;
- identify uncertainty, contradiction and cross-work evidence gaps;
- request the next minimum-sufficient source/window;
- propose narrower evidence scopes and a cross-work convergence state.

The deterministic runtime may normalize returned source metadata, bind identity and version, enforce declared rights/storage boundaries, materialize only the requested bounded evidence, apply hygiene/leakage/schema checks, and record budgets and receipts. Deterministic keyword, punctuation or score heuristics must not become literary classification, gap analysis or convergence authority.

It may not:

- pretend Web/GitHub/MCP retrieval occurred without an eligible authorized capability;
- infer legal rights from weak metadata;
- fabricate quotations;
- promote Corpus observations into Canon, user taste or Framework behavior.

---

## 13 · Anonymous public release boundary

The public release is a source-free projection, not a less-private copy of the ledger. Its closed schemas may contain randomized IDs, numeric metrics, controlled eight-axis craft profiles, cross-work mechanism labels, applicability boundaries, counterexample states, failure modes and integrity fingerprints.

They prohibit source paths, filenames, titles, creators, prose, quotations, close paraphrases, source-reconstructive summaries, characters, settings and arbitrary extension fields. A leakage check must compare candidate public strings with private source identities and sampled prose before release. Passing the schema alone is not sufficient.

A release candidate must first produce an exact preview token and manifest fingerprint. Publication requires the caller to confirm both exact values; a preview, validation report, empty registry or semantic result does not publish anything. The legacy statistical registry remains empty until its fixed 120-work protocol passes every gate. A Style Atlas candidate follows its separate source-free, evidence-sufficient path and does not gain authority from processing all 120. Synthetic contract/runner evidence establishes the dynamic scheduling and early-stop mechanism only; it supplies none of the live V5, learned-style, blind-evaluation, independent-leakage-review or publication evidence.

---

## 14 · License and legal boundary

Repository-owned public derivatives under `corpus/general/` inherit the repository's [Quillframe Proprietary Source-Available License](../LICENSE). Public repository visibility is not a permissive data license and does not relicense any third-party source material.

Abstraction, anonymization and non-commercial intent are risk controls, not automatic legal conclusions. The rights gate validates declared metadata and storage intent; the publication validator enforces the repository's closed-schema and leakage policy. Neither substitutes for source-specific legal review when publication rights are uncertain.

---

## 15 · Related contracts

- [Corpus Intelligence](README.en.md) — end-to-end evidence pipeline.
- [Corpus Ingest Protocol](CORPUS_INGEST_PROTOCOL.en.md) — bounded ingestion mechanics.
- [`rights_gate.py`](rights_gate.py) — deterministic declared-rights/storage validator.
- [`discovery_runtime.py`](discovery_runtime.py) — typed discovery runtime.
- [Corpus Benchmarks](benchmarks/README.en.md) — cross-work mechanism evidence.
- [Anonymous Public General Corpus](general/README.en.md) — release schemas, empty registry and license boundary.
- [Adaptive Learning](../docs/adaptive-learning.en.md) — learning scopes and hypotheses.

**A useful Corpus system remembers enough to support evidence and rollback, but never so much that source possession becomes a shortcut around rights, authority, or craft reasoning.**

# Corpus Ingest Protocol · Preserve only the evidence the question and rights allow

Corpus ingestion converts a verified discovery candidate into provenance-bound **metadata, permitted source material, observations, and derived evidence**. It is intentionally narrower than “download the source.”

> **Core invariant ✦** Ingestion is a storage/evidence operation. It never grants Canon authority, character knowledge, durable user preference, or Framework behavior authority.

---

## 01 · Entry preconditions

Do not begin content ingestion from a search result alone.

A candidate should already identify:

- discovery request / Corpus gap ID;
- research question;
- proposed source identity;
- source channel / tool capability;
- expected contrast or evidence value;
- relevant language/genre/platform metadata when applicable.

Then verify as much source identity as the authorized host can establish:

- canonical work/source identity;
- creator/publisher/source owner where relevant;
- canonical URL/ref or local file identity;
- edition/version when material;
- access timestamp;
- source type;
- fingerprint for user/local content when available.

Search snippets are discovery evidence, not reliable full-source quotations or rights evidence.

---

## 02 · Establish rights class before content storage

Every durable Corpus candidate uses exactly one declared rights class:

```text
redistributable | analysis_only | unknown
```

And one requested storage intent:

```text
metadata_only | derived_only | short_excerpt | full_text
```

Run the deterministic [`rights_gate.py`](rights_gate.py) before persisting source content.

Reference policy:

```text
unknown         → metadata_only only
analysis_only   → never full_text
short_excerpt   → excerpt_purpose required
redistributable → non-empty rights_basis required
```

The deterministic gate validates policy consistency. It does not perform legal analysis or infer rights from a title/URL.

---

## 03 · Fail closed when rights or provenance are unresolved

If rights are `unknown`, keep safe source metadata and stop content storage.

If source identity/provenance is materially uncertain, do not “complete” the pipeline by guessing:

```text
verified enough for metadata → store metadata + unresolved status
not verified enough          → keep discovery candidate / blocked state
```

A private repo, local browser session, authenticated connector, or successful download proves access—not redistribution permission.

---

## 04 · Choose the minimum analysis range

Even when analysis is permitted, select only the range needed for the declared question.

Useful range metadata can include:

```yaml
range_type: chapter | scene | passage | work_metadata | user_selection
range_ref: ...
research_question: ...
why_this_range: ...
source_fingerprint: ...
```

Do not read or persist an entire work merely because the host can reach it.

Question-bounded ranges reduce copyright exposure, context cost, source leakage and imitation pressure.

---

## 05 · Separate source material from observation

An **observation artifact** records what can be supported by the permitted evidence range without pretending the observation is already a universal craft rule.

Example shape:

```yaml
observation_id: ...
corpus_id: ...
range_ref: ...
question: ...
observable_features: []
evidence_refs: []
metrics: {}
confidence: ...
```

Keep evidence references concise and source-bound. Do not store private chain-of-thought.

For `analysis_only` sources, prefer metadata + derived observation over persistent raw text.

---

## 06 · Semantic mechanism analysis is a separate step

Observation and interpretation are different artifacts.

Where literary/craft understanding is required, package bounded rights-safe evidence into the `learning` semantic contract pack. `learning.mechanism_analyze` is designed to identify:

- mechanism candidates;
- counterexamples;
- applicability boundaries;
- evidence refs;
- uncertainty / confidence.

Its contract explicitly forbids supplying unrestricted `full_text`, `raw_text`, or `source_text` fields.

Deterministic ingestion code should not replace this with heuristic literary scoring.

---

## 07 · One work does not establish General Craft

A per-work analysis may produce a hypothesis or observation such as:

```yaml
analysis_id: ...
corpus_id: ...
research_question: ...
mechanism_candidates: []
tradeoffs: []
profile_context: ...
uncertainties: []
counterexample_needed: true
```

That result can trigger contrast research. It cannot become a universal rule.

Before generalization, seek:

- same outcome with a different surface form;
- same surface form with a worse outcome;
- profile/genre/platform exceptions;
- evidence that directly contradicts the proposed mechanism.

Preserve negative evidence rather than discarding it.

---

## 08 · Cross-work benchmark handoff

Only after multiple source-bound observations and counterexamples should the system build a cross-work mechanism benchmark.

A useful benchmark may contain:

- mechanism statement;
- supporting observation refs;
- counterexample refs;
- applicability/profile boundary;
- failure modes;
- writer-safe guidance;
- capability/regression eval ideas;
- source/provenance refs.

Do not blend source signatures into a synthetic author-imitation fingerprint.

See [Corpus Benchmarks](benchmarks/README.en.md).

---

## 09 · Learning / Eval handoff

Corpus-derived evidence may create or update:

- project-specific craft evidence;
- user-taste evidence/hypothesis tests;
- General Craft candidates;
- capability eval cases;
- regression eval cases;
- additional Corpus gaps.

Each downstream artifact keeps upstream evidence/provenance refs.

Promotion remains governed by Adaptive Learning / Self-Improvement. Ingestion does not activate the result.

---

## 10 · Writer exposure is a later, narrower decision

The raw Writer should normally receive:

```text
minimal task-relevant mechanism
+ relevant profile boundary
+ project authority/context needed for the scene
```

—not bulk source text.

Modern copyrighted source text, hidden expected labels and regression bad examples do not enter first-pass Writer context by default.

A Corpus item being stored does not imply `draft` visibility.

---

## 11 · Storage by rights class

### `redistributable`

May allow `full_text` when the declared rights basis actually supports redistribution/storage. Preserve provenance and fingerprint.

### `analysis_only`

Use `metadata_only`, `derived_only`, or a justified `short_excerpt`. Do not persist full text.

### `unknown`

Use `metadata_only` only. Keep content ingestion blocked until rights evidence changes.

When a short excerpt is stored, record why that excerpt is needed. “Useful for style” is not sufficient by itself.

---

## 12 · Invalidating downstream evidence

Every derived artifact must preserve enough lineage for correction.

If a source later becomes invalid because of rights/provenance/error:

```text
invalidate source/content record
→ remove no-longer-permitted stored material
→ locate dependent observations
→ invalidate/rebuild analyses
→ invalidate/rebuild benchmarks and evals
→ contest/narrow dependent learning candidates
→ rollback promoted behavior when required
```

Do not leave an apparently valid benchmark after its only valid evidence source was removed.

---

## 13 · Automation boundary

The ingestion pipeline may automate deterministic validation and bookkeeping. It may not fabricate external retrieval, rights evidence or quotations.

If an external capability is unavailable:

```text
prepare request
→ record missing capability / awaiting external work
→ stop truthfully
```

If semantic interpretation is required:

```text
prepare bounded contract job
→ execute through eligible model/human runtime
→ validate fingerprint-bound result
```

A queue is not retrieval. A schema is not analysis. A model result is not promotion authority.

---

## 14 · Related contracts

- [Corpus Policy](CORPUS_POLICY.en.md) — normative rights/evidence boundary.
- [Corpus Intelligence](README.en.md) — complete research/learning flow.
- [`rights_gate.py`](rights_gate.py) — declared-rights/storage-intent validator.
- [`discovery_runtime.py`](discovery_runtime.py) — discovery request/result lifecycle.
- [`harness/semantic_workers/contracts/learning.json`](../harness/semantic_workers/contracts/learning.json) — bounded mechanism-analysis/eval contracts.
- [Adaptive Learning](../docs/adaptive-learning.en.md) — downstream hypothesis/eval lifecycle.

**Ingest only what the declared question needs and the established rights permit; derive the rest as traceable evidence.**

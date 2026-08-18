# Corpus Benchmarks · Mechanism evidence, not style templates

This directory stores **project-agnostic, cross-work mechanism benchmarks**. Their job is to preserve compact evidence about recurring craft mechanisms so Quillframe can design evals, test hypotheses, and calibrate guidance without feeding raw copyrighted corpus text into the Writer.

> **Boundary ✦** A benchmark is not Canon, not a user preference, not a named-author style fingerprint, and not automatic Framework guidance.

---

## 01 · Where benchmarks sit in the evidence pipeline

```text
bounded source observations
→ per-work mechanism analysis
→ contrast / counterexample search
→ cross-work benchmark
→ capability + regression evals
→ promotion candidate
→ authorized activation / promotion or rejection
```

Discovery is not ingestion. Analysis is not promotion. A benchmark is one evidence product inside the larger Corpus + Learning pipeline.

---

## 02 · What a benchmark should capture

A useful benchmark records:

- a stable benchmark ID;
- the mechanism being tested;
- the failure it is meant to prevent or repair;
- a positive operational pattern;
- a failure / counterexample boundary;
- applicable profile scopes;
- linked Surface / Reader / eval mechanisms;
- provenance class and current status;
- writer-safe guidance expressed as a mechanism, not imitation instructions.

It should be concise enough to evaluate and specific enough to falsify.

Bad benchmark:

> Successful prose uses vivid details.

Better benchmark:

> Institutional detail becomes useful when it changes permission, cost, timing, status, or the character's next available action.

The second statement exposes a mechanism and a boundary that can actually be tested.

---

## 03 · Seed registry

[`mechanisms.json`](mechanisms.json) contains the first migrated generic benchmark family:

- functional micro-action;
- decision-specific interiority;
- pressure-bound exposition;
- embodied dialogue through task / object ownership;
- historical or institutional texture through active consequences;
- task-bound exposition dialogue;
- pressure ladder to action;
- concrete forward-pull ending.

These entries are **migrated seed evidence**. The registry's internal version field describes that seed artifact; it must not be read as the current Quillframe release number.

No consumer-project facts or raw source passages are stored in this registry.

---

## 04 · Benchmarks do not bypass semantic analysis

The `learning` semantic contract pack owns mechanism interpretation and evaluation where literary understanding is required. Deterministic code owns provenance, rights boundaries, state transitions, evidence completeness and promotion prerequisites.

A benchmark therefore cannot become “true because it is in JSON.” It may be:

- strengthened by new independent evidence;
- narrowed to a smaller profile scope;
- split when one label hides multiple mechanisms;
- contested by counterexamples;
- superseded by a better explanation;
- deprecated when evals show harm or weak generalization.

---

## 05 · General-craft promotion is deliberately hard

Framework-level craft guidance requires substantially more than one benchmark entry. The current promotion gate expects, among other evidence:

- multiple distinct cross-work references;
- at least one counterexample / contrast reference;
- an explicit applicability or profile boundary;
- passing capability and regression evals;
- version and rollback evidence;
- green Framework CI bound to an exact commit;
- provenance references.

Even a `promotable` result does **not** grant Framework write authority. It creates a typed candidate for an authorized manager or human workflow.

---

## 06 · Writer isolation

The preferred path is:

```text
source evidence
→ bounded observation
→ mechanism analysis
→ benchmark / eval calibration
→ minimal task-relevant guidance
→ Writer
```

Do not use this directory as a prompt dump. Bulk source passages, hidden eval answers, regression bad examples, and named-author imitation material do not belong in Writer pre-draft context.

---

## 07 · Related contracts

- [Corpus Intelligence](../README.en.md) — complete discovery / rights / analysis pipeline.
- [Corpus Policy](../CORPUS_POLICY.en.md) — storage, rights, and imitation boundaries.
- [Corpus Ingest Protocol](../CORPUS_INGEST_PROTOCOL.en.md) — lawful bounded ingestion.
- [Adaptive Learning](../../docs/adaptive-learning.en.md) — evidence, hypotheses, evals, and promotion.
- [`learning/promotion_gate.py`](../../learning/promotion_gate.py) — deterministic promotion prerequisites.

**The benchmark registry is useful because its claims remain inspectable, contestable, and reversible.**

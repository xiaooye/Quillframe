# Corpus Policy

## 1. Corpus is evidence, not authority

Corpus material may support:
- project craft analysis;
- user-taste hypothesis testing;
- general craft research;
- regression/capability benchmark construction.

Corpus material may not by itself:
- create project Canon;
- decide character knowledge;
- settle relationship/resource/information state;
- override explicit project/user authority;
- become a hidden style-imitation prompt.

## 2. Rights classes

Every source candidate must be classified before ingestion.

### `redistributable`
Full text may be stored when there is a clear basis such as:
- public domain;
- compatible open license;
- explicit permission;
- user-owned/user-authored material with permission to store.

Store the rights basis and source provenance.

### `analysis_only`
The material may be lawfully accessed/analyzed, but repository storage must be limited to:
- source metadata;
- derived metrics;
- mechanism-level observations;
- summaries;
- short compliant excerpts only when genuinely necessary.

Do not mirror full modern copyrighted works.

### `unknown`
Metadata/source research may continue, but full-text ingestion is blocked until rights are clarified.

Private-repository status does not weaken this rule.

## 3. Source provenance

Each corpus item records at least:

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
accessed_at:
content_fingerprint:
analysis_scope:
research_question:
```

If the host cannot verify provenance, downgrade confidence or block ingestion.

## 4. Question-bounded analysis

Do not analyze an entire work merely because it is available.

Start from a declared question, for example:
- how does a scene increase pressure without fragments?
- how is exposition embedded in task conflict?
- how is a supporting character kept active during protagonist-centric scenes?
- how does a chapter end with forward pull without narrator advertising?

Select only the minimum range needed to answer that question.

## 5. Counterexample requirement

Corpus research should actively search for:
- examples that support the hypothesis;
- examples that violate the superficial pattern but still succeed;
- examples where the hypothesized mechanism fails;
- genre/profile exceptions.

This prevents “find three things I already agree with” confirmation bias.

## 6. Cross-work generalization

A single work can create an observation, not a universal rule.

General-craft promotion normally requires:
- multiple independent works/sources;
- mechanism consistency across them;
- at least one counterexample/profile-boundary check;
- regression/capability evals;
- no named-author imitation rule.

## 7. User-taste learning

User-taste corpus selection begins from a preference hypothesis and a gap, not from “find works similar to what the user likes.”

Corpus should help distinguish mechanisms.

Example:

```text
observed rejection: sentence-per-paragraph pseudo-speed
hypothesis: user wants fast causality, not fragmented typography
corpus gap: compare fast scenes with coherent paragraph units vs fragment-heavy scenes
result: strengthen/narrow/contest hypothesis
```

## 8. Named-author boundary

Do not create durable profiles whose goal is direct imitation of a living/modern author.

Allowed:
- broad genre conventions;
- high-level structural/craft mechanisms;
- cross-author aggregate patterns;
- user-owned style evidence;
- public-domain craft analysis within normal policy.

Disallowed as framework behavior:
- reusable “write exactly like Author X” mechanism sets;
- signature phrase/cadence extraction intended for imitation;
- storing extensive copyrighted excerpts as style prompts.

## 9. Writer isolation

Preferred writer input is:

```text
benchmark/mechanism
+ minimal evidence summary
+ relevant project/user profile
```

not raw corpus text.

Regression bad examples remain post-generation critic context unless a test explicitly requires otherwise.

## 10. Removal / correction

If rights, provenance, or analysis is later found invalid:
1. mark source/item invalid;
2. remove prohibited stored material;
3. identify dependent analyses/benchmarks/evals;
4. invalidate or rebuild them;
5. downgrade learning hypotheses/promotions that relied on the source;
6. record rollback trace.

## 11. Autonomous behavior boundary

The Corpus Scout may autonomously create discovery plans and candidate queues. Actual external retrieval is performed only through host tools/connectors that are available and authorized.

The scout must never fabricate source access, rights, or quotations.

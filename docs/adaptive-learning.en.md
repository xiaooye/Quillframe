<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="540" />
  <p><strong>Adaptive Learning · models interpret feedback; deterministic state controls durable authority</strong></p>
  <p><kbd>INTERPRET</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd>&nbsp;&nbsp;<kbd>HYPOTHESIS</kbd>&nbsp;&nbsp;<kbd>EVAL</kbd>&nbsp;&nbsp;<kbd>AUTHORIZE</kbd>&nbsp;&nbsp;<kbd>ROLLBACK</kbd></p>
  <p><a href="adaptive-learning.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Adaptive Learning

NovelForge learns from explicit user/project evidence without letting a model turn an interpretation into durable authority.

```text
runtime/session state != learning evidence != Project Canon
semantic interpretation != promotion judgment != write authorization
```

`learning/author_model.py` remains a projection/capture layer over the existing Learning Store. It is not a second preference database.

## 1. Semantic interpretation belongs to the model

`learning.preference_interpret` interprets supplied feedback and proposes the narrowest plausible scope:

`one_off | project | user_taste | general_craft`

It may explain the underlying mechanism, desired/avoid behavior, exceptions, uncertainty and conflicts with prior hypotheses. It does not grant durability or activation.

The model, not Python thresholds, decides whether evidence semantically supports a stable scope/mechanism.

## 2. Learning Store owns durability, not meaning

The deterministic store owns:

- evidence/hypothesis IDs and provenance;
- versioned state and contradiction/supersession records;
- exact source references;
- persistence and rollback history;
- consume-once result handling;
- Project/user scope isolation.

A durable record can still be tentative/contested. Persistence does not make an inference true.

## 3. Promotion Gate binds semantic review to authority

`learning/promotion_gate.py` no longer tries to prove semantic sufficiency with arbitrary evidence-count thresholds.

The semantic promotion review decides whether the supplied evidence actually supports the proposed scope/mechanism and whether important contradictions/counterexamples remain unresolved.

The deterministic gate then verifies objective prerequisites around that review, such as:

- exact contract/result/evidence binding;
- candidate scope and identity;
- required eval/counterexample artifacts where policy requires them;
- version/rollback/CI references for General Craft;
- explicit write authorization supplied by the surrounding authority mechanism.

A passing promotion review is a prerequisite. It is **not** permission to write.

## 4. Active != relevant

An `active` Author Model hypothesis means it is durably eligible for future use. It does not mean every production invocation should receive it.

The Author Model exposes a compact active index. The manager/model explicitly selects the active hypothesis IDs relevant to the current task. Deterministic code verifies that selected IDs are active and scope-compatible before returning details.

This prevents context pollution from automatically injecting every learned preference.

Current explicit user instruction remains stronger than an inferred or durable preference when they conflict.

## 5. Scope-specific authority

### One-off

Used for the current repair/task only unless new evidence is captured separately.

### Project preference

May activate only under the Project's explicit preference-write authority. It never changes Framework behavior.

### Durable user taste

Requires both:

1. a current bound promotion prerequisite result for the same mechanism/scope; and
2. explicit durable-user-taste write authorization.

Neither the model nor Promotion Gate can self-grant this permission.

### General Craft

General Craft remains a Framework `SYSTEM-IMPROVE` concern. It requires stronger counterexample/eval/compatibility/version/rollback evidence and explicit Framework promotion authority. Production feedback cannot auto-promote it.

## 6. Corpus/research is evidence gathering, not truth by ingestion

A semantic learning agent may identify an evidence gap and search for lawful contrast/counterexample material. Search/retrieval strategy remains model-owned inside allowed capabilities.

Corpus discovery does not imply ingestion; ingestion does not imply Canon; corpus analysis does not imply promotion.

Rights, provenance, source identity and Project/user isolation remain deterministic boundaries.

## 7. Contradiction and rollback are first-class

New feedback may:

- strengthen a hypothesis;
- narrow its applicability;
- mark it `contested`;
- split an over-broad mechanism;
- supersede an older hypothesis;
- deprecate a behavior when evidence changes.

“Strengthening” means new independent evidence, not repeated model agreement or elapsed time.

## 8. Production use

```text
explicit feedback
→ semantic preference interpretation
→ source-bound evidence
→ revisable hypothesis
→ semantic promotion review when durable activation is proposed
→ deterministic authority/prerequisite validation
→ active eligibility
→ model selects relevant active hypothesis IDs for a future task
→ production observes outcomes
→ new evidence may revise/supersede the hypothesis
```

The Writer/Editor never receive a hidden global style profile simply because records exist in `learning.db`.

## 9. Privacy

Personal preference evidence is user-scoped and is not committed to the generic Framework repository by default. NovelForge must not infer unrelated demographic/profile attributes from fiction preferences.

## Exact implementation boundaries

- `learning/learning_store.py` — durable evidence/hypothesis/candidate/promotion history.
- `learning/promotion_gate.py` — deterministic binding/authority checks around model-owned promotion review.
- `learning/author_model.py` — bounded feedback capture, contradiction/supersession, scope-aware activation binding, active index and explicit selected projection.
- `harness/semantic_workers/contracts/production-loop.json` — `learning.preference_interpret`.
- Framework self-improvement protocol — General Craft promotion authority.

<div align="center"><sub>Interpret semantically. Persist cautiously. Activate only with evidence and authority. 🌸</sub></div>

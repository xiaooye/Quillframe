<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Production Pipeline · model-owned narrative judgment inside exact execution boundaries</strong></p>
  <p><kbd>GROUND</kbd>&nbsp;&nbsp;<kbd>SEARCH</kbd>&nbsp;&nbsp;<kbd>SIMULATE</kbd>&nbsp;&nbsp;<kbd>DRAFT</kbd>&nbsp;&nbsp;<kbd>READ</kbd>&nbsp;&nbsp;<kbd>AUDIT</kbd>&nbsp;&nbsp;<kbd>EDIT</kbd>&nbsp;&nbsp;<kbd>GATE</kbd></p>
  <p><a href="production-pipeline.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Production Pipeline

NovelForge treats a chapter as a **recoverable semantic production run**, not a fixed chain of critic agents and not a deterministic story engine.

> **Models decide narrative meaning. Runtime enforces execution truth. Project authority decides what is Canon.**

## 01 · Establish authority before prose

A `DRAFT` or `REVISE` run first resolves:

- the current/pinned Framework identity;
- the consuming Project and exact lock/fingerprint;
- exactly one `task_mode`;
- manager session/run/checkpoint identity;
- current Canon/plan/candidate fingerprints and authority cutoff;
- real host capabilities and permissions.

Old chat history and provider-native sessions are context, not authority. Resume revalidates current Project/Framework authority and pending capabilities before work continues.

## 02 · Agent-owned search, deterministic context boundaries

The manager/model determines what knowledge is missing. When necessary it invokes `context.select`, formulates its own query, inspects results, rejects irrelevant matches, reformulates or continues, and stops when sufficiently grounded.

Retrieval primitives may use lexical/vector/top-k mechanics to return candidates. They do **not** make those candidates narratively relevant by fiat.

After semantic selection, deterministic context infrastructure verifies only objective boundaries:

- exact selected/source IDs and fingerprints;
- stage and private-state visibility;
- temporal eligibility where the runtime can prove it;
- exact higher-authority required refs when an operation mechanically requires them;
- hard context/resource budgets.

`context_assembly.py` v2 does not require literary context classes or declare semantic sufficiency. Missing meaning is repaired by search/selection, not by adding another Python relevance rule.

## 03 · Story and planning preflight

The manager checks whether the requested work is legal relative to current Project state. Planning artifacts remain distinct from Accepted Canon.

`planning_horizon.py` may enforce declared commitment strength/depth, promoter class, exact before-state and fingerprints. The **Planner** decides how much detail is useful now, what should remain uncertain, and whether more research or replanning is needed. NovelForge has no universal N-chapter/N-volume horizon.

## 04 · Character causality before prose

The pre-draft causal sequence is **private character/world state → `character.action_propose` → `scene.resolve_actions` → compact writer-safe realization projection → Writer**.

Character private state is causal evidence. It is not a prose payload. Runtime may enforce evidence identity, authorized visibility and story-time eligibility, but semantic questions such as motivation, plausible inference, integrity and knowledge use belong to models.

`scene.realization_project` should stay compact. Its purpose is to preserve the observable interaction/event trace and privacy boundary, not to serialize a second Character Sheet or a giant Realization Sheet.

## 05 · Raw Draft and Surface realization

Writer produces event-first Raw Draft only after the current causal problem is sufficiently grounded. Raw Draft is internal.

Negative regression examples remain out of first-pass Writer context until the candidate is frozen. Once frozen, the exact candidate fingerprint becomes the binding subject for downstream review.

Surface Fundamentals remain craft knowledge and regression vocabulary. Mechanical metrics such as paragraph or dialogue ratios are available through optional prose telemetry, **default-off** and never a generic literary verdict.

## 06 · Blind Reader

The production Reader is `reader.engagement_audit`.

It receives the candidate plus reader-visible evidence and the minimal target-reader behavior profile. It does **not** normally receive:

- author intent or future plan;
- private character state;
- Writer reasoning;
- the full quality taxonomy or expected HF code;
- prose telemetry;
- hard-rule audit instructions;
- prior reviewer verdicts or repair plan.

Its job is to read naturally and report the reading experience that actually matters: pull, boredom, confusion, disbelief, emotional response, artificiality, interest, anticipation, irritation, attachment, or another salient effect. It is not required to fill every literary dimension.

## 07 · Semantic Rule Auditor

Hard narrative rules are not Python literary rules.

`quality.semantic_rule_audit` receives an authoritative semantic-rule index and authorized evidence. It decides rule applicability and returns traceable judgments such as `PASS`, `FAIL`, `NOT_APPLICABLE`, or `INSUFFICIENT_EVIDENCE`.

The runtime verifies that the correct rule authority was available, the audit ran against the exact candidate, and any required independent identity/receipt is valid. It does not decide whether the prose semantically violated the rule.

A confirmed blocking semantic-rule FAIL routes repair. A missing required audit remains unresolved.

## 08 · Editor owns repair mechanism and depth

`editor.repair_spec` integrates:

- Blind Reader findings;
- Semantic Rule Auditor findings;
- authorized story/Canon evidence;
- Project/style constraints;
- current repair goal and relevant active preference evidence when explicitly selected.

The Editor decides the mechanism, repair owner, and whether the next generation should be `local_or_bounded_repair` or `fresh_realization`.

`quality/repair_policy.py` v2 does **not** infer literary repair depth from owner/scope/cluster. It only enforces the information boundary implied by the Editor-selected mode. When fresh realization is selected, rejected prose/concrete patch instructions can be hidden from the Writer to avoid patch-loop anchoring.

HF/RG taxonomy remains diagnostic vocabulary and regression labels. A Blind Reader may describe “these people sound like they are explaining their job descriptions”; Rule Auditor/Editor may map that evidence to HF-30 where useful.

## 09 · Challenger comparison and plateau

Revision is not automatically improvement.

When a material repair warrants comparison, `quality.compare` semantically evaluates incumbent versus challenger. `quality_evolution.py` persists candidate fingerprints, comparison receipts, consume-once state and a configurable workflow plateau limit; it does not choose the literary winner itself.

A tie or incumbent win is valid evidence. The system may stop rather than rewriting forever.

## 10 · Release gates

`production_readiness.py` and `production_release.py` validate exact binding and conjunctive gate state. They may check:

- required registered Reader / semantic-rule / independent results exist;
- exact candidate/subject/fingerprint match;
- worker/provenance/independence requirements are satisfied;
- deterministic structural receipts and authority invariants are valid.

They do not re-judge whether the chapter is good.

A missing required semantic judgment is `PENDING_MODEL`/pending, not PASS. A workflow that merely records missing model capability is functioning honestly but does not provide semantic evidence.

## 11 · Independent semantic review

Independence is a separate property from semantic judgment.

When the active gate requires it, use a genuinely separate invocation/session/worker with a bounded packet and exact candidate fingerprint. The manager may package, dispatch, validate and consume; it may not satisfy the independent gate by changing its internal role label.

Transport failure may use another eligible transport. A valid semantic rejection is not a transport failure and must route repair; do not keep changing reviewers until one accepts the candidate.

## 12 · Acceptance and settlement remain separate

Review-ready prose is still not Accepted Canon.

Explicit user acceptance/authorized Canon-change intent is required before `SETTLE`. Settlement remains a deterministic transaction with exact acceptance evidence, checkpoint/write authorization, before-state/CAS, projection receipts and postcondition verification.

Quality evidence cannot approve itself into Canon.

## 13 · Default adaptive graph

The default production graph is structured as these ordered stages:

1. authority/session bootstrap;
2. agent-owned search/context selection;
3. deterministic exact-set/stage/fingerprint verification;
4. story/planning preflight;
5. character action, scene collision, then compact realization;
6. Writer Raw Draft, Surface realization, then candidate fingerprint freeze;
7. Blind Reader;
8. Semantic Rule Auditor when required;
9. Editor repair specification and repair/challenger comparison when warranted;
10. continuity/state checks;
11. required independent semantic gate;
12. user-visible Review Draft;
13. explicit acceptance, followed by `SETTLE` as a separate mode/transaction.

The manager loads the smallest semantic contract set needed by the current failure. One capable agent remains preferable unless information isolation, independent evaluation, private state, or genuine specialist benefit justifies separation.

## Exact references

- [Context & Memory](context-and-memory.en.md)
- [Quality & QA](quality-assurance.en.md)
- [Adaptive Learning](adaptive-learning.en.md)
- [Orchestration Protocol](../harness/ORCHESTRATION_PROTOCOL.en.md)
- [`harness/semantic_workers/model_contract_catalog.json`](../harness/semantic_workers/model_contract_catalog.json)
- [`quality/repair_policy.py`](../quality/repair_policy.py)
- [`quality/production_readiness.py`](../quality/production_readiness.py)

<div align="center"><sub>Constrain power. Let models understand the fiction. Bind every consequential result to exact state. 🌸</sub></div>

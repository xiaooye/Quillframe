<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Quality & QA · prove invariants with code, interpret fiction with bounded model contracts</strong></p>
  <p><kbd>DETERMINISTIC QA</kbd>&nbsp;&nbsp;<kbd>SEMANTIC CONTRACTS</kbd>&nbsp;&nbsp;<kbd>FINDINGS</kbd>&nbsp;&nbsp;<kbd>EVOLUTION</kbd>&nbsp;&nbsp;<kbd>GATES</kbd></p>
  <p><a href="quality-assurance.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# Quality & QA

NovelForge does not have one universal critic, and it does not pretend literary quality can be reduced to deterministic scores.

Its quality system separates **what code can prove**, **what a model must interpret**, **how findings route repair**, **whether a challenger actually improves the incumbent**, and **which judgments must be independent before release**.

<img src="../assets/ui/home-quality.en.svg" alt="NovelForge quality system separating deterministic QA, semantic QA, candidate evolution, and independent review" width="100%" />

---

## 01 · Quality is a set of questions, not one number

A candidate can pass one quality dimension and fail another.

NovelForge therefore asks different mechanisms to answer different questions:

**Is the artifact mechanically valid?** Schema, authority, permissions, fingerprints, lifecycle, references, idempotency, and transaction preconditions are deterministic.

**Is the prose realization structurally healthy?** Surface Fundamentals identify recurring realization failures without claiming to define all literary quality.

**What is the reader actually experiencing?** Reader contracts judge momentum, confusion, reward, investment, and desire to continue using reader-visible evidence only.

**Is an important character still behaving as that character?** Character-integrity judgment compares the scene against typed established character state.

**What actually owns this revision problem?** Revision diagnosis distinguishes story, plan, scene, character, reader-pressure, surface, continuity, context/memory, and research failures.

**Did the repair improve the candidate?** Candidate evolution compares incumbent and challenger rather than assuming another rewrite must be better.

**Does the candidate still honor long-term commitments?** Continuity and reader-expectation mechanisms audit established facts, obligations, setups, and relationship evidence.

No PASS in one dimension cancels a FAIL in another.

---

## 02 · The fundamental ownership split

The current development architecture uses a strict ownership boundary.

**Model-owned semantic intelligence** includes reading, story/character interpretation, reader reaction, revision diagnosis, relationship-memory reconciliation, long-horizon commitment auditing, and other judgments that require understanding supplied evidence.

**Deterministic runtime ownership** includes authority, permission, fingerprints, persistence, routing, hard budgets, stage isolation, typed validation, consume-once behavior, rights/provenance checks, checkpointing, and transactions.

The deterministic shell may validate that a semantic result has the right type and fingerprint. It must not quietly replace the model by inventing a “literary relevance” or “quality” heuristic.

A model result, conversely, does not acquire Canon or Framework-write authority just because it sounds persuasive.

---

## 03 · Deterministic QA: prove what can actually be proved

Deterministic checks are preferred whenever the invariant can be stated exactly.

Typical checks include:

- Project manifest and exact Framework-lock compatibility;
- schema and required-field validation;
- stable-ID uniqueness;
- authority boundaries such as Plan / Review ≠ Accepted Canon;
- artifact and semantic-job fingerprints;
- result binding and consume-once semantics;
- permission and write preconditions;
- session / run / checkpoint lifecycle;
- handoff leases and resume safety;
- dependency and reference integrity;
- Project data leaking into generic Framework source;
- Corpus rights and source provenance;
- blind-eval queue hygiene;
- deterministic bundle and project-build reproducibility;
- settlement compare-and-swap and postcondition checks.

These checks belong in ordinary CI because they are fast, reproducible, and do not need a model.

They intentionally do **not** claim to prove that a scene is moving, a character choice is psychologically convincing, or a chapter is satisfying.

---

## 04 · Surface Fundamentals: a prose floor, not a literary oracle

Surface Fundamentals protect the realization layer against recurring AI-text failure mechanisms.

Examples include malformed fragment rhythms, mechanical micro-actions, narrator hype, process-report narration, fake significance, voice / POV leakage, empty compression, and other framework-defined surface failures.

The important rule is repair ownership:

- isolated surface defect → local rewrite;
- surface failures that cluster → regenerate the realization / scene;
- surface-safe but flat → return to Reader Pressure + Scene Simulation.

This prevents iterative writing from becoming an endless pile of sentence patches over a causally dead scene.

Deep reference: [Surface Fundamentals](../surface/FUNDAMENTALS.en.md).

---

## 05 · Reader diagnostics are evidence, not an automatic independent gate

The `quality` semantic pack exposes `reader.reaction` and `reader.compare`.

`reader.reaction` simulates a cold reading-behavior persona using only the candidate and reader-visible context. Creator-only information such as outlines, future plans, author intent, hidden payoff, unrevealed Canon, or prior reviewer verdicts is explicitly outside that reader's knowledge.

The diagnostic can report evidence such as:

- whether the reader would continue;
- strength of continue desire;
- confusion or attention loss;
- favorite / stumble beats;
- emotional response;
- drop-off point;
- the reason for that reaction.

`reader.compare` performs bounded pairwise comparison and can return `A`, `B`, or `tie`. When order bias matters, repeated judgments can swap candidate order.

These reader simulations are **diagnostic evidence**. Their contract does not by itself make them a mandatory independent semantic gate.

Deep reference: [Reader Engagement](../surface/READER_ENGAGEMENT.en.md).

---

## 06 · Character integrity is its own semantic question

The `character.integrity` contract asks whether an important character remains causally and psychologically coherent against typed established state.

The judgment can consider:

- agenda alignment;
- beliefs and knowledge boundary;
- voice;
- relationship position;
- spatial / task state;
- evidence supporting intentional change;
- surprise that remains consistent with the character rather than random drift.

The reviewer cannot use manager knowledge, narrator knowledge, reader knowledge, or research truth as if the character automatically knows it.

This makes character drift diagnosable without turning the Character System into deterministic “personality rules.”

Deep reference: [Character & Relationship System](../core/CHARACTER_SYSTEM.en.md).

---

## 07 · Revision diagnosis comes before rewriting

The `revision.diagnose` contract exists to stop generic polish loops.

It asks the model to diagnose only the requested dimensions and return evidence-backed findings plus repair ownership. A meaningful defect should be classified before another rewrite begins.

Repair owners include, as applicable:

- story;
- plan;
- scene;
- character;
- reader pressure;
- surface;
- continuity;
- context / memory;
- research;
- runtime / human escalation.

SAFE-BUT-FLAT is explicitly not a line-edit problem. A cluster of surface failures may also require whole-scene realization rather than local patches.

The result is diagnosis evidence, not Canon mutation.

---

## 08 · Findings make quality evidence durable and traceable

A quality problem should survive beyond one chat message.

NovelForge uses typed findings so later repair and comparison can refer to explicit evidence rather than a vague memory that “the last reviewer disliked something.”

A finding should make clear, when applicable:

- what failed;
- which candidate fingerprint the evidence describes;
- where the evidence is observable;
- which quality dimension is involved;
- what mechanism owns repair;
- whether the issue remains open or has been addressed.

Findings are evidence records. They still have no Canon authority.

---

## 09 · Candidate evolution verifies improvement instead of assuming it

A rewrite can be different without being better.

`quality/quality_evolution.py` therefore keeps a deterministic candidate-evolution ledger containing candidate fingerprints, parent relationships, repair owners, exact comparison jobs/results, incumbent state, and plateau counters.

Semantic comparison itself is model-owned through the `creative-evolution` pack's `quality.compare` contract. The deterministic ledger only records and validates the comparison lifecycle.

A comparison may conclude:

- challenger wins;
- incumbent remains better;
- no meaningful advantage / tie.

When repeated repairs produce no gain, plateau stopping can end the evolution run rather than forcing another rewrite.

Deep guide: [Quality Evolution](quality-evolution.en.md).

---

## 10 · Long-horizon QA protects promises, not just trivia

Continuity is broader than remembering names or eye colors.

The `long-horizon` contract pack can reconcile and audit evidence that must survive across many chapters:

- `plan.reconcile` — adapt active plans after causal emergence without rewriting Accepted history;
- `relationship.memory_reconcile` — reconcile long-lived relationship evidence when memories or derived records conflict;
- `continuity.commitment_audit` — test a candidate against explicit narrative commitments and established facts.

The `narrative-memory` pack can also interpret current `reader.expectations`, which helps distinguish a genuine setup / payoff obligation from a manager's private intent.

Continuity failures may route to Story / Plan, Character, relationship state, Context / Memory, or settlement. They are not automatically prose problems.

---

## 11 · Independent review is a separate property

**Semantic judgment** and **independent semantic judgment** are not synonyms.

Many quality contracts can run as ordinary bounded model work. Their output remains typed and fingerprint-bound, but the contract itself does not claim that the invocation is independent.

When a workflow or rubric explicitly requires independence, the review must additionally satisfy the independent-gate contract:

- genuinely different invocation / session;
- bounded packet rather than inherited manager history;
- exact candidate fingerprint binding;
- typed result;
- no hidden expected / gold labels;
- fresh judgment after material fingerprint change unless the contract explicitly permits reuse.

The manager may package, dispatch, validate, and consume. It may not write the artifact and satisfy the gate by adopting a different role in the same invocation.

### No reviewer-shopping

Transport failure and semantic rejection are different states.

An infrastructure failure may route to another eligible transport. A valid `semantic_reject` is real evidence and must route to repair. Repeatedly changing reviewers until one returns PASS destroys the meaning of independence.

Deep references: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) and [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md).

---

## 12 · Semantic fingerprints and run receipts protect provenance

Every semantic job binds the kind / contract, subject, bounded input, rubric, and output contract into an exact fingerprint. Execution lineage such as worker session or transport attempt is tracked separately from the semantic identity of the job.

This means:

- a reviewer cannot silently judge a different candidate and reuse the old result;
- retrying the same semantic job through another eligible transport does not change what was asked;
- material changes to artifact, rubric, or output contract create a new semantic fingerprint;
- result validation can reject stale or incorrectly bound output.

Provider-neutral semantic run receipts preserve bounded execution provenance without turning provider history into authority.

---

## 13 · Blind evals protect reviewer independence from expected answers

Generic eval cases may contain expected outcomes for scoring, but those labels are not reviewer context.

The blind-queue builder removes expected / gold / release-decision fields before semantic dispatch. Negative regression examples also stay out of pre-Raw-Draft generation context.

A semantic eval without an eligible judgment remains `PENDING_MODEL`; deterministic CI must not fabricate PASS.

Normal CI can still validate:

- eval manifests and fixtures;
- deterministic release blockers;
- blind-queue hygiene;
- schemas and fingerprints;
- committed reviewed baselines when explicitly versioned;
- project / framework self-tests and reproducible builds.

Normal CI does not silently spend paid or login-bound model usage.

Implementation reference: [NovelForge Evals](../evals/README.en.md).

---

## 14 · User-visible quality gates are task-specific

Not every task needs every possible quality contract.

The manager loads the smallest relevant contract set and applies the gates required by the active task / Project profile / current rubric.

For `DRAFT` / `REVISE`, Raw Draft always remains internal. A review-ready claim still requires the applicable Surface, Reader, Character / Story, continuity, and independent gates to be resolved.

Honest unresolved states include:

`awaiting_user` · `awaiting_external` · `semantic_pending` · `failed_gate` · `settlement_incomplete`

NovelForge prefers an accurate unresolved state over a false “production-ready” label.

---

## 15 · Acceptance and settlement are not quality verdicts

Passing quality gates does not mutate Canon.

A user may review a candidate, accept it, and only then authorize `SETTLE`. Settlement is a separate deterministic transaction with explicit acceptance evidence, exact before→after writes, compare-and-swap preconditions, checkpoint / write authorization, projection receipts, and postcondition verification.

Likewise, a semantic reviewer cannot “approve something into Canon.”

This keeps four concepts separate:

**quality evidence → user-visible review → explicit acceptance → authorized settlement.**

---

## 16 · Costs and limitations ⚠️

This architecture has real costs.

- Semantic diagnosis consumes model or human effort.
- Independent gates add another invocation and potentially another provider / human workflow.
- Fresh fingerprints can invalidate previous judgments after material rewrites.
- Candidate comparison and scenario divergence may cost more tokens than local line edits.
- Durable findings, receipts, and checkpoints add engineering ceremony.
- Literary judgment remains probabilistic even when the execution contract is precise.

NovelForge accepts these costs only where they buy something valuable: less false confidence, less continuity drift, less self-review theater, and clearer repair ownership in long-running fiction.

---

## 17 · What “good QA” means in NovelForge

Good QA is not the largest number of critics.

It is a system in which:

- code proves only the invariants code can prove;
- models receive the smallest contract and evidence needed for interpretation;
- reader simulation does not secretly see creator-only knowledge;
- character judgment respects knowledge and agenda boundaries;
- diagnosis happens before rewrite;
- repairs go to the owning mechanism;
- candidate evolution can admit ties and stop at a plateau;
- independence is used when it is actually required;
- every result is bound to the artifact it judged;
- no quality result silently becomes Canon authority.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="52" />
  <br />
  <sub>Prove invariants. Read the fiction. Route the failure. Verify the improvement. ✦</sub>
</div>

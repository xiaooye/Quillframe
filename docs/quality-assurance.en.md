<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Quality & QA · deterministic where possible, semantic where necessary</strong></p>
  <p><kbd>CI</kbd>&nbsp;&nbsp;<kbd>BLIND EVALS</kbd>&nbsp;&nbsp;<kbd>READER QUALITY</kbd>&nbsp;&nbsp;<kbd>INDEPENDENT REVIEW</kbd>&nbsp;&nbsp;<kbd>CONTINUITY</kbd></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# Quality & QA

> 🌸 **NovelForge does not have one generic “critic agent.” It has a layered quality system in which different classes of failure are detected by different mechanisms and repaired at the layer that actually owns them.**

<img src="../assets/ui/home-quality.en.svg" alt="NovelForge quality assurance stack and failure-routing system" width="100%" />

---

## 01 · Quality is not one score

A fiction artifact can be correct in one dimension and fail badly in another. NovelForge therefore separates at least five questions:

**Is the artifact structurally valid?** Schemas, IDs, lifecycle, authority, fingerprints, dependencies, and state transitions are deterministic concerns.

**Is the prose mechanically acceptable?** Surface Fundamentals catch malformed realization and recurring AI-text failure mechanisms.

**Is the chapter compelling to read?** Reader Engagement evaluates pressure, payoff, causal motion, curiosity, contrast, and forward pull.

**Is the story semantically sound?** Independent review evaluates nuanced scene, character, story, and prose behavior that cannot honestly be reduced to deterministic rules.

**Does it remain consistent with project state?** Continuity checks knowledge, location, obligations, resources, relationships, unresolved threads, and emotional/event aftermath.

A PASS in one layer never erases a FAIL in another.

---

## 02 · Deterministic QA

Deterministic checks are used whenever the invariant can be expressed precisely. Typical checks include:

- manifest and exact framework-lock compatibility;
- schema and required-field validation;
- stable-ID uniqueness;
- authority lifecycle rules such as Plan/Review ≠ Accepted Canon;
- exact artifact fingerprints and result binding;
- permission and write preconditions;
- dependency/reference integrity;
- idempotency, leases, consume-once receipts, and resume safety;
- project-specific facts leaking into generic Framework source;
- blind semantic queue hygiene;
- regression fixture structure;
- reproducible project/framework bundle builds.

These checks are fast, reproducible, and suitable for normal CI. They do **not** claim to validate whether a paragraph is emotionally alive or a scene is satisfying.

---

## 03 · Surface Fundamentals

Surface QA is a floor, not a definition of literary quality. It protects against recurring realization failures such as malformed fragment rhythms, mechanically inserted micro-actions, generic narrator hype, fake cliffhangers, process-report prose, knowledge/voice leakage, and other framework-defined anti-AI failure mechanisms.

The important implementation rule is **cluster ownership**:

- isolated surface defect → local rewrite;
- repeated/clustered surface defects → regenerate the scene;
- surface-safe but flat → do not keep polishing sentences; return to Reader Pressure + Scene Simulation.

This prevents a common failure mode in iterative AI writing: hundreds of local patches gradually make the text cleaner while the underlying scene remains inert.

Deep reference: [Surface Fundamentals](../surface/FUNDAMENTALS.en.md).

---

## 04 · Reader Engagement

Reader Engagement is evaluated separately because grammatical cleanliness does not imply page-turning fiction.

The model looks for mechanisms such as:

- active narrative pressure;
- meaningful state change;
- reader reward and payoff;
- curiosity that evolves instead of merely being withheld;
- tonal and emotional contrast;
- scene causality;
- choices with cost;
- relationship movement;
- consequence and aftermath;
- forward pull into the next unit.

A chapter that is coherent, polished, and harmless may still fail as **SAFE-BUT-FLAT**. That failure routes upstream rather than receiving decorative prose edits.

Deep reference: [Reader Engagement](../surface/READER_ENGAGEMENT.en.md).

---

## 05 · Independent semantic review

Mandatory independent judgment has a stricter meaning than “ask the model to criticize itself.”

A valid reviewer must:

1. run in a genuinely separate invocation/session;
2. receive a bounded review packet rather than inheriting the manager's entire history;
3. bind its result to the exact artifact fingerprint;
4. return a typed verdict/result contract;
5. avoid hidden expected labels or regression gold;
6. normally be fresh when the candidate fingerprint materially changes.

The manager may freeze, package, dispatch, wait, validate, and consume the result. It may not write the candidate and then satisfy the gate by changing role labels inside the same context.

### No reviewer shopping

Infrastructure failure may trigger an eligible transport fallback. A valid semantic rejection is different: it is a real judgment and must route to repair. The system may not keep selecting fresh reviewers until one happens to say PASS.

Deep references: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) and [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md).

---

## 06 · Blind eval queues

Regression and capability evals can contain hidden expected outcomes for scoring. Reviewers must not see those labels.

NovelForge therefore builds a **blind semantic queue** that removes expected/gold/release-label information before reviewer dispatch. Regression bad examples are also excluded from first-pass Writer context so the generator is not primed by the very failures being tested.

The resulting flow is:

```text
Eval Case
→ deterministic preconditions
→ blind semantic job
→ independent reviewer
→ fingerprint-bound typed result
→ scorer / release decision
```

Missing semantic judgment is reported as pending—not silently converted into PASS.

---

## 07 · Continuity and state QA

Continuity is more than “did the model remember the character's eye color?” It includes whether state changes remain causally and epistemically valid.

Examples include:

- character location and presence;
- what each character could know at that point in the story;
- relationship and obligation changes;
- resources, injuries, deadlines, debts, promises, and constraints;
- open loops and foreshadowing;
- timeline/date consistency;
- emotional aftermath that should persist into later scenes;
- Accepted manuscript fingerprints matching project state/ledgers where required.

A continuity issue may belong to state repair, Character Simulation, Story/Plan, or settlement rather than prose revision.

---

## 08 · Failure routing

NovelForge uses failure routing because the repair mechanism matters as much as the diagnosis.

```text
isolated surface fail
→ local rewrite

surface failure cluster
→ whole-scene regeneration

SAFE-BUT-FLAT / reader-grip fail
→ Reader Pressure + Scene Simulation

character fail
→ Character Simulation

story / causal fail
→ Story / Plan

continuity / state fail
→ state repair / settlement path

valid independent semantic reject
→ owning repair layer
```

This design explicitly rejects the idea that every problem can be solved by asking an “Editor Agent” to rewrite the text one more time.

---

## 09 · Eval case types

NovelForge currently uses three broad evaluation classes.

### Regression

Protects against a previously observed failure mechanism. A regression becomes release-blocking only when the required deterministic and/or semantic baseline is actually available for that release path.

### Capability

Checks that the framework can recognize or produce a desired behavior/mechanism.

### Infrastructure

Checks schemas, files, routing, authority boundaries, runtime contracts, project/framework hygiene, and other deterministic infrastructure behavior.

Judge modes are `deterministic`, `rubric`, or `hybrid`.

---

## 10 · What normal CI does—and does not do

Normal CI should:

- validate eval manifests and fixtures;
- run deterministic release blockers;
- build blind semantic queues;
- verify that hidden expected labels are absent;
- validate committed reviewed baselines when explicitly versioned;
- run project/framework self-tests and build checks.

Normal CI does **not** silently call paid or login-bound models. Semantic execution is explicit and capability-aware.

Typical commands:

```bash
python evals/run_evals.py --release
python evals/build_judge_queue.py --output /tmp/semantic-queue.json
python evals/run_evals.py --judgments reviewed-results.json --json
```

Implementation reference: [NovelForge Evals](../evals/README.en.md).

---

## 11 · Release and user-visible gates

A candidate artifact may be exposed only when every gate required by the active task mode is resolved. Valid non-success states include:

`awaiting_user` · `awaiting_external` · `semantic_pending` · `failed_gate` · `settlement_incomplete`

The framework should prefer a truthful unresolved status over a false “production-ready” claim.

For DRAFT/REVISE, Raw Draft remains internal. Review Draft / production-ready claims require the applicable Surface, Reader Engagement, independent semantic, and continuity gates to be satisfied.

---

## 12 · Costs and limitations ⚠️

The stricter QA model has real costs:

- independent semantic review adds model/human latency and potentially API cost;
- fresh-per-fingerprint review can require another invocation after material rewrites;
- deterministic schemas and fingerprints add engineering ceremony;
- aggressive upstream regeneration may consume more tokens than endless local edits;
- literary judgment remains probabilistic even with independent reviewers.

NovelForge accepts those costs for projects where false confidence, continuity drift, and self-review loops are more damaging than the extra runtime overhead.

---

## 13 · Quality domains covered by the eval suite

Current framework evaluation covers at least:

- Surface Fundamentals;
- Reader Engagement;
- character / semantic ownership;
- Canon / Plan boundary;
- corpus rights boundary;
- Project SDK / Framework hygiene;
- semantic runtime integrity.

The suite grows through user rejection evidence, corpus research, framework changes, and discovered capability gaps.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="52" />
  <br />
  <sub>Deterministic code proves what code can prove. Independent judgment handles the rest. ✦</sub>
</div>

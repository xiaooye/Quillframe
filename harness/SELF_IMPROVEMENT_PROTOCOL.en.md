# Framework Self-Improvement Protocol · Evidence may propose change; it may not grant itself authority

Quillframe may learn from user feedback, project outcomes, corpus evidence, evals, and upstream framework research. Durable behavior change is allowed only when the evidence supports the **narrowest valid scope**, the change is testable and reversible, and an authorized workflow actually performs the promotion.

> **Core invariant ✦** Learning produces evidence, hypotheses, eval results and promotion candidates. None of those artifacts grants Framework-write, Canon-write, or durable-user-taste authority by itself.

---

## 01 · Four scopes

Every learning claim belongs to one of four scopes:

- `one_off` — useful only for the current request/run;
- `project` — convention or preference for one consuming novel;
- `user_taste` — durable preference hypothesis for one user across projects;
- `general_craft` — candidate generic mechanism for Quillframe itself.

Always select the narrowest scope justified by evidence. A project preference does not become user taste merely because it appeared twice, and user taste does not become General Craft because the model finds it reasonable.

---

## 02 · Evidence before hypothesis

Production feedback intake is automatic evidence capture, not automatic promotion. A model first decides `capture | skip`; retrying the same durable feedback event is not new evidence, while a genuinely distinct user turn may become a new evidence ref. A user universal claim may be recorded as a candidate but cannot establish General Craft without the research/counterexample/eval/authority path below. Project/user content stays project/runtime-private unless it is later abstracted into rights-safe, anonymized Generic evidence.

Useful evidence may include:

1. explicit user instruction;
2. direct user edit;
3. explicit acceptance/rejection with a reason;
4. repeated independent corrections;
5. accepted project convention;
6. cross-work corpus mechanism evidence;
7. external primary/framework evidence;
8. model inference.

Model inference is the weakest layer. **Model inference alone cannot create durable user taste or Framework behavior.**

Rejected model output is negative regression evidence only; it does not become a positive style exemplar simply because the system generated it.

---

## 03 · Durable learning cycle

[`learning/learning_cycle.py`](../learning/learning_cycle.py) tracks learning work across runtime boundaries without performing semantic judgment.

The durable lifecycle is approximately:

```text
evidence / hypothesis
→ corpus gap
→ discovery plan
→ verified discovery
→ semantic analysis
→ eval evidence
→ promotion candidate
→ authorized activation / promotion decision
```

The cycle stores state, artifact hashes and consume-once receipts. It carries:

```text
canon_authority = false
framework_write_authority = false
durable_user_taste_write_authority = false
```

A scheduler or persistent database can remember where the work is. It cannot decide that the proposed mechanism is now a rule.

---

## 04 · Semantic analysis belongs to model contracts

The `learning` semantic pack owns interpretation that requires model intelligence.

Current contract roles include:

- `learning.mechanism_analyze` — analyze bounded, rights-safe evidence for a mechanism, counterexample and applicability boundary;
- `learning.evaluate` — evaluate a proposed mechanism against a blind fixture/profile boundary without seeing hidden expected labels.

The deterministic runtime binds inputs/results, enforces permissions, records provenance and validates typed output. It does not turn heuristics into fake craft judgment.

A semantic result may support a promotion gate. It cannot perform the promotion.

---

## 05 · Corpus discovery is evidence acquisition, not learning completion

A hypothesis may create a Corpus gap when contrast evidence is missing.

Authorized hosts may search Web, GitHub, library/platform metadata, user-provided files or MCP/search connectors, but:

```text
discovery ≠ ingestion
source found ≠ rights granted
analysis ≠ preference
benchmark ≠ Framework rule
```

Corpus work must preserve source identity, provenance and rights class. General Craft requires mechanism-level synthesis across works and counterexamples, not named-author imitation fingerprints.

---

## 06 · User-taste activation

A durable `user_taste` candidate requires more than one model impression.

The current deterministic promotion prerequisite gate expects:

- explicit user evidence or repeated independent consistent corrections;
- traceable evidence refs;
- personalized eval evidence;
- contradiction review;
- applicability boundary when supported by evidence.

Even `ready_for_activation` does not let generic source control absorb private preference data. User-taste state belongs in user/host-managed storage by default.

---

## 07 · General Craft promotion

General Craft is the highest bar because it changes generic Framework behavior.

A candidate must establish, at minimum:

- a mechanism independent of one user/project;
- multiple distinct cross-work evidence references;
- at least one counterexample / contrast reference;
- an explicit profile/applicability boundary;
- passing capability eval;
- passing regression eval;
- version target and rollback reference;
- provenance references;
- green Framework CI bound to an exact commit;
- no unresolved contradiction that should instead narrow the scope.

[`learning/promotion_gate.py`](../learning/promotion_gate.py) may return `promotable`. That means **evidence prerequisites are satisfied**. It still returns `behavior_write_authority = false`.

The next step is an authorized manager/human engineering workflow, not an automatic source-code mutation.

---

## 08 · Framework change workflow

A real generic behavior change follows normal software-engineering discipline:

```text
freeze evidence + candidate
→ identify owning mechanism
→ specify smallest sufficient change
→ inspect compatibility / profile boundary
→ implement
→ deterministic tests
→ required capability + regression evals
→ independent evidence where the rubric requires it
→ review exact diff / version / rollback
→ authorized write
→ green post-change CI
→ observe later outcomes
```

Large structural changes use spec → plan → tasks. A tiny wording correction does not need fake bureaucracy.

---

## 09 · External framework learning

OpenAI Agents SDK, LangGraph, ADK/agents-cli, AutoGen, Claude Code, MCP and other systems are evidence sources for runtime engineering.

An upstream change creates an `adopt | adapt | reject` hypothesis, not an automatic dependency update.

Ask:

- what mechanism changed?
- what problem does it actually solve?
- does Quillframe already solve that problem differently?
- would adoption blur runtime state, Canon, independence or permission boundaries?
- what capability/regression evidence would prove the change beneficial?

See [Agent Framework Adoption](../knowledge/AGENT_FRAMEWORK_ADOPTION.en.md).

---

## 10 · Scheduled maintenance has no promotion authority

A schedule may trigger deterministic observation, queue construction, capability checks or learning-cycle advancement.

It does not grant permission to:

- spend model usage when the workflow forbids it;
- fabricate Web/search access that is not available;
- promote a hypothesis automatically;
- mutate Framework behavior;
- write Project Canon.

Time is a trigger, not authority.

---

## 11 · Contradiction, decay and rollback

Learning must remain reversible.

A hypothesis or promoted mechanism may become:

- `contested` when new evidence conflicts;
- `superseded` when a narrower/better explanation replaces it;
- `deprecated` when user direction changes or evals show harm.

When evidence invalidates a behavior:

```text
record contradiction
→ identify dependent benchmarks / profiles / evals
→ block or deprecate affected candidate
→ restore prior behavior/profile when required
→ preserve rollback provenance
→ rerun relevant regressions
```

Repeated self-agreement never counts as new independent evidence.

---

## 12 · Hard boundary

Framework self-improvement may change **generic mechanisms**. It may never absorb a consuming novel's characters, Canon facts, private project state, plot outcomes or private user preference records into generic source.

Project evidence may motivate a generic hypothesis only after the project-specific content is abstracted away and the generic mechanism earns its own evidence.

---

## 13 · Related contracts

- [Adaptive Learning](../docs/adaptive-learning.en.md) — user-facing learning model.
- [Corpus Intelligence](../corpus/README.en.md) — governed evidence discovery and analysis.
- [Corpus Benchmarks](../corpus/benchmarks/README.en.md) — inspectable cross-work mechanism evidence.
- [`learning/learning_cycle.py`](../learning/learning_cycle.py) — durable non-authoritative learning workflow.
- [`learning/promotion_gate.py`](../learning/promotion_gate.py) — deterministic promotion prerequisites.
- [`harness/semantic_workers/contracts/learning.json`](semantic_workers/contracts/learning.json) — learning semantic contracts.

**Autonomy may advance the evidence process. Authority remains explicit at the point where durable behavior would change.**

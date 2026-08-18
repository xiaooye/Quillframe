# Continuous Maintenance · Keep Quillframe healthy without turning automation into authority

Continuous Maintenance observes Framework health, advances safe deterministic maintenance work, and prepares bounded evidence/candidates for later review. It does **not** convert schedules, CI, webhooks, queues, or persistent state into autonomous editorial or source-code authority.

> **Core invariant ✦** Automation may decide *when to check*. It does not gain the right to decide story truth, spend undeclared model usage, fabricate unavailable capabilities, or promote Framework behavior.

---

## 01 · Maintenance is not Self-Improvement

Continuous Maintenance and Self-Improvement have different jobs:

```text
Continuous Maintenance
→ observe / validate / queue / report / advance deterministic state

Self-Improvement
→ interpret evidence / evaluate mechanism / satisfy promotion prerequisites
→ authorized Framework change when justified
```

Maintenance may feed the learning system. It does not bypass it.

---

## 02 · L0 · Unattended deterministic checks

Safe unattended work includes machine-checkable operations such as:

- Python compile/static/schema checks;
- repository hygiene and project-leakage scans;
- bilingual documentation inventory/link checks;
- Tier-A SVG structural lint;
- Session / Control Plane invariants;
- capability declarations and routing invariants;
- Corpus rights/schema/provenance checks;
- Project SDK / Adapter self-tests;
- deterministic eval release cases;
- dependency / lock / release-metadata drift detection;
- non-mutating health reports.

These checks may fail CI. They do not perform literary judgment.

---

## 03 · L1 · Deterministic candidate preparation

Maintenance may also create **bounded work candidates** without activating them:

- regression/capability case proposals;
- stale-document or stale-integration reports;
- Corpus/research gaps;
- discovery requests or dispatch plans;
- learning-cycle bookkeeping artifacts;
- adopt/adapt/reject research questions for upstream framework changes;
- schema/docs cleanup candidates;
- missing-capability reports.

Creating a queue item, issue, candidate, finding or report is not behavior promotion.

---

## 04 · Model execution is explicit

Normal scheduled maintenance must not silently invoke paid, login-bound, or otherwise usage-bearing model execution.

Current policy is:

```text
normal CI model execution       = forbidden
weekly maintenance model use    = forbidden
live semantic execution         = explicit opt-in workflow / eligible host runtime
```

When semantic work is required, maintenance may prepare the typed packet/job and stop at a truthful state such as `awaiting_semantic` / `semantic_pending` until an eligible runtime actually executes it.

A queue/router/schema is not a model capability.

---

## 05 · External search must be proven

Maintenance may plan Corpus or external-framework discovery, but it cannot pretend that Web/GitHub/MCP search occurred when the active host does not expose that capability.

Required pattern:

```text
research/discovery need
→ resolve host capability
→ if available: dispatch bounded request + preserve provenance
→ if unavailable: record missing capability / pending work
```

Network primitives alone do not prove authorization to a remote source.

---

## 06 · Scheduled learning-cycle advancement

Deterministic maintenance may advance the durable Learning Cycle only where the next transition does not require semantic judgment.

Examples:

- register known evidence/corpus gap;
- prepare a discovery queue;
- attach already-returned verified artifacts;
- validate hashes / consume-once receipts;
- detect that semantic analysis or eval is now required;
- prepare promotion prerequisite reports.

It may not invent the missing semantic result, mark a blind eval PASS without a reviewer, or auto-promote a candidate.

---

## 07 · Promotion remains gated

Any material generic behavior change returns to the [Self-Improvement Protocol](SELF_IMPROVEMENT_PROTOCOL.en.md).

At minimum, durable promotion needs evidence, scope, counterexample/profile boundary, relevant evals, version/rollback evidence, exact implementation diff and green post-change CI.

A promotion prerequisite result such as `promotable` is still non-authoritative. The actual write requires an authorized manager/human engineering workflow.

---

## 08 · Events wake work; they do not authorize it

These may trigger maintenance:

- schedule;
- repository push;
- CI completion;
- webhook;
- MCP event;
- Control Plane event;
- external worker result;
- user request.

None of them automatically grants:

- drafting authority;
- Canon mutation;
- durable user-taste activation;
- Framework source mutation;
- release authority;
- permission to consume model/API usage.

Event arrival proves only that an event arrived.

---

## 09 · Human / Project authority stays explicit

Always preserve explicit authority for consequential decisions such as:

- Canon settlement;
- story-direction changes;
- ambiguous/destructive migration;
- resolving contradictory durable user preferences;
- approving generic behavior changes;
- release/version promotion where repository policy requires it.

Maintenance can surface the decision packet. It cannot impersonate the decision owner.

---

## 10 · Failure and resume

A maintenance run should be resumable and idempotent where practical.

Before consequential external dispatch or writes:

- checkpoint current state;
- bind work to stable IDs/fingerprints;
- preserve provenance;
- use consume-once or equivalent idempotency semantics;
- distinguish infrastructure failure from valid semantic rejection.

After interruption, resume from durable state and re-resolve capabilities/authority rather than replaying side effects blindly.

---

## 11 · Reference workflow

```text
trigger
→ deterministic health observation
→ classify finding / maintenance need
→ resolve required capability
→ perform safe deterministic work
→ prepare bounded external/semantic work when needed
→ await / consume validated result
→ tests / eval evidence
→ candidate or report
→ authorized change only through owning protocol
```

---

## 12 · Related contracts

- [Self-Improvement Protocol](SELF_IMPROVEMENT_PROTOCOL.en.md) — durable behavior-change authority.
- [Adaptive Learning](../docs/adaptive-learning.en.md) — evidence/hypothesis lifecycle.
- [Runtime Capabilities](session_runtime/RUNTIME_CAPABILITIES.en.md) — capability proof and constraints.
- [Control Plane](control_plane/CONTROL_PLANE.en.md) — durable external work coordination.
- [Corpus Intelligence](../corpus/README.en.md) — discovery and provenance boundaries.
- `.github/workflows/quillframe-weekly-maintenance.yml` — scheduled deterministic maintenance entrypoint.

**Continuous maintenance should make the system more observable and less stale—not more autonomous than its authority model allows.**

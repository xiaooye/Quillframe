<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><strong>Context & Memory · agent-owned semantic selection inside deterministic authority boundaries</strong></p>
  <p><kbd>SEARCH</kbd>&nbsp;&nbsp;<kbd>SELECT</kbd>&nbsp;&nbsp;<kbd>VERIFY</kbd>&nbsp;&nbsp;<kbd>PACK</kbd>&nbsp;&nbsp;<kbd>RESUME</kbd></p>
  <p><a href="context-and-memory.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Context & Memory

NovelForge deliberately separates **stored information**, **mechanical eligibility**, **semantic relevance**, **working context**, **durable session history**, and **Project truth**.

> **The model decides what it needs, what to search, what matters, whether to search again, and when it has enough evidence. Deterministic runtime decides only what the model may access, whether an item/result is authentic and current, whether it is legal for the receiving stage, and whether hard execution budgets/authority constraints are satisfied.**

## 1. Ownership model

**Project authority** owns Canon/accepted facts and Project-level truth.

**Session Runtime** owns durable run/checkpoint/event identity. The model context window is not the durable session.

**Context Inspector** owns mechanical eligibility, stage visibility, explicit pin/priority controls, protected edits and invalidation. It rejects a `relevance` field because relevance is semantic.

**`context.select`** owns semantic context/search decisions.

**Context Assembly v2** validates the exact selected set against deterministic boundaries.

**Memory tiers / hard-budget packing** packs selected whole items under objective budgets.

**Memory Bank** stores source-bound runtime/derived memory. It is not shadow Canon.

## 2. Context Inspector: eligibility, never relevance

`harness/context_inspector.py` implements `novelforge_context_inspector_v3`.

It may normalize or verify:

- item/source identity and source fingerprint;
- authority class;
- allowed stages;
- explicit numeric priority and pin state;
- derived/hidden/invalidated state;
- protected-edit proposal behavior.

Its stable ordering (`pinned → explicit priority → stable id`) represents explicit control, not literary importance.

A protected `accepted`/`locked` source cannot be changed through the context overlay. A requested protected edit becomes a proposal; it does not mutate Canon.

## 3. Stage isolation is deterministic

Private or answer-key-like information must not leak merely because it exists in storage.

Examples:

- hidden gold / expected verdict / regression answer keys may not enter Writer context;
- private character/scene simulation state may be visible to simulation but not automatically to Writer;
- a compact writer-safe realization trace may be visible to Writer even when the private state that produced it is not;
- Blind Reader must not inherit manager/author/private-character reasoning.

This is an information-security boundary, so deterministic enforcement is appropriate.

## 4. `context.select`: search is a capability

The `context.select` semantic contract receives a bounded task description plus mechanically eligible candidate blocks and the allowed search capabilities/resource budget.

The model decides:

1. what the task actually lacks;
2. which supplied blocks matter;
3. whether current evidence is sufficient;
4. what focused query to issue next;
5. whether to broaden, narrow or reformulate after seeing results;
6. what to retain in working context;
7. when to stop searching.

The runtime does not convert recency, vector similarity, fixed top-k, item class, or task-mode mapping into narrative truth. Such mechanisms may generate candidates, but they are not authoritative relevance judgments.

Pinned items are explicit execution constraints, not proof of semantic importance.

## 5. Context Assembly v2: exact-set verification only

`harness/context_assembly.py` implements `novelforge_context_assembly_v2`.

It runs **after** model/manager selection and verifies only deterministic properties such as:

- selected IDs exist in the inspected eligible set;
- the exact receiving stage is allowed;
- hidden/invalidated/private-state restrictions hold;
- source fingerprints and exact higher-authority refs match when mechanically required;
- a selected projection does not cross a privacy/stage boundary.

It explicitly does **not** judge:

- whether a literary context class is “required”;
- whether a selected item is narratively relevant;
- whether the selection is semantically sufficient;
- whether another search should be performed.

Those decisions belong to the model/Manager. If a specific authoritative artifact is mechanically mandatory for an operation, the caller passes its **exact required ref/fingerprint**, not a semantic class/purpose proxy.

## 6. Hard-budget packing remains deterministic

When tiered packing is used, `harness/memory_tiers.py` may enforce hot/working budgets, whole-item packing, invalidated exclusion and explicit pins.

It must not summarize, rank or truncate content based on a claim of literary relevance. If an explicit pinned item cannot fit a hard budget, expose the conflict rather than silently dropping the pin.

## 7. Character knowledge is semantic, visibility is mechanical

Runtime may prove that an evidence item was not yet available at a story-time boundary or was outside an authorized perspective packet. It may not conclude that a character *semantically could or could not infer* a fact merely from labels.

Character knowledge/inference/consistency belongs to semantic character/rule-audit contracts. Evidence identity and temporal/visibility eligibility remain deterministic inputs to those judgments.

## 8. Author Model context follows the same rule

An active Author Model hypothesis is **eligible durable preference evidence**, not automatically relevant context.

`learning/author_model.py` exposes a compact active index. The manager/model explicitly selects the active hypothesis IDs useful for the current task; deterministic code checks that those IDs are active and Project-compatible before exposing details.

## 9. Typical adaptive context loop

```text
resolve Project/session authority
→ build mechanically eligible candidates
→ model inspects task and current evidence
→ model selects or requests search
→ runtime executes allowed search/fetch primitive
→ model inspects results and may reformulate
→ model stops when sufficiently grounded
→ Context Assembly v2 verifies exact refs/stage/fingerprints
→ hard-budget packing if needed
→ execute target semantic/writing contract
→ persist only source-bound, non-authoritative derived memory
```

A context-window transcript is never the source of truth for resume. After context loss/reset, Session Runtime re-resolves the current Project/Framework authority and reconstructs the working set from durable events/artifacts/checkpoints.

## 10. Failure routing

- relevant evidence omitted → semantic selection/search repair, not a new Python relevance rule;
- selected ref is stale/missing/wrong fingerprint → deterministic assembly failure;
- private state enters a forbidden stage → deterministic isolation failure;
- first search insufficient → model continues/reformulates within allowed capabilities;
- evidence is already sufficient → model should stop; runtime does not force extra retrieval;
- hard budget cannot honor an explicit pin → deterministic control conflict;
- character appears to know too much → semantic knowledge/rule audit using authorized evidence;
- protected Canon needs change → proposal → Project acceptance/Settlement, never context overlay mutation.

## 11. Exact references

- [Architecture](architecture.en.md)
- [Production Pipeline](production-pipeline.en.md)
- [Project SDK](project-sdk.en.md)
- [`harness/context_inspector.py`](../harness/context_inspector.py)
- [`harness/context_assembly.py`](../harness/context_assembly.py)
- [`harness/memory_tiers.py`](../harness/memory_tiers.py)
- [`harness/memory_bank.py`](../harness/memory_bank.py)
- [`harness/semantic_workers/contracts/context-research.json`](../harness/semantic_workers/contracts/context-research.json)

<div align="center"><sub>Models decide meaning. Runtime constrains power. Projects decide truth. 🌸</sub></div>

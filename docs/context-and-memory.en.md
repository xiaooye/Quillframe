<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><strong>Context & Memory · author-visible controls around a sparse, authority-aware working set</strong></p>
  <p><kbd>SELECT</kbd>&nbsp;&nbsp;<kbd>INSPECT</kbd>&nbsp;&nbsp;<kbd>ASSEMBLE</kbd>&nbsp;&nbsp;<kbd>PACK</kbd>&nbsp;&nbsp;<kbd>EDIT</kbd>&nbsp;&nbsp;<kbd>REBUILD</kbd></p>
  <p><a href="context-and-memory.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Context & Memory

NovelForge does not equate **stored information**, **currently eligible context**, **semantically selected context**, **derived memory**, and **story truth**.

The current architecture deliberately splits semantic selection from deterministic control:

> **The model decides semantic relevance through the `context.select` contract. Deterministic context / memory code owns authority classes, stage eligibility, required-context obligations, explicit author controls, source binding, hard budgets, whole-item packing, and protected-edit rules.**

This prevents a heuristic relevance score, stale session note, convenient summary, or private simulation record from silently becoming either prompt truth or Canon.

---

## 01 · Five things that must stay different

**Project authority** answers: *what is true for this fiction project?* Accepted / locked facts remain Project-owned.

**Context Manifest** answers: *what material is eligible for this run, under which authority class and stage?*

**Semantic selection** answers: *which eligible material is actually useful for the current task?* That interpretation belongs to the model through `context.select`.

**Context Assembly** answers: *does the selected set satisfy the stage, authority, provenance, invalidation, and required-context contracts for this invocation?* That validation is deterministic.

**Memory Bank** stores editable runtime / derived / proposal-oriented memory with provenance and versions. It can reference protected Canon, but it is not another Canon database.

A useful mental model is:

**storage → eligibility → semantic selection → deterministic assembly → hard-budget packing → model context**

Each arrow has a different owner.

---

## 02 · Context Inspector: inspect authority and eligibility, not literary relevance

`harness/context_inspector.py` implements `novelforge_context_inspector_v3`.

For each manifest item it normalizes and exposes fields such as:

- stable item ID and class;
- source reference and source fingerprint;
- authority class;
- inclusion reason;
- allowed stages;
- explicit numeric priority;
- pin state;
- whether the view is derived;
- hidden / invalidated state;
- caller-supplied metadata.

The Inspector explicitly **rejects a `relevance` field**. Semantic relevance is not a deterministic manifest property.

Its ordering policy is intentionally mechanical:

**pinned → explicit priority → stable ID**

That ordering is author/runtime control, not a claim about literary importance.

---

## 03 · Stage isolation protects each worker from the wrong evidence

Context items declare one or more allowed stages. Current production stages include writer, post-draft, reviewer, and simulation-oriented views; an item must be eligible for the exact receiving stage before it can be assembled.

The important invariant is not a fixed number of stage names. It is that **private or answer-key-like evidence cannot leak across stage boundaries merely because it exists in storage**.

Examples:

- regression evidence, hidden gold, expected verdicts, and answer keys must not enter `writer_pre_draft`;
- private character / scene simulation state may be available to simulation without becoming Writer exposition material;
- a writer-safe realization projection may enter Writer context even when the private state that produced it may not;
- reviewer context remains bounded and does not inherit manager-private reasoning by default.

This is a deterministic contamination boundary. It does not require a model to remember “please don't peek.”

---

## 04 · Semantic selection belongs to `context.select`

When a working set contains more eligible material than the current task should receive, NovelForge prepares a bounded `context.select` semantic job.

`harness/memory_tiers.py` sends the model only a task context plus typed candidate memory blocks. The model returns ordered IDs for hot, working, and archive tiers.

The deterministic runtime then validates that result against the exact semantic job fingerprint before using it.

This split is important:

- the model may interpret which evidence matters now;
- deterministic code verifies that the model selected only known, non-invalidated items;
- a stale or misbound semantic result is rejected;
- selection still does not grant authority to the selected memory.

The contract is resolved through the progressive `context-research` semantic pack.

---

## 05 · Context Assembly validates a selected set; it does not score relevance

`harness/context_assembly.py` implements `novelforge_context_assembly_v1`.

Its job starts **after** eligible material has been identified and semantic selection has occurred when needed. It validates the concrete selected IDs against deterministic requirements such as:

- the exact receiving stage;
- allowed authority classes;
- hidden / invalidated state;
- source references and fingerprints when required;
- required context class / purpose obligations;
- whether a selected item is legal for the requested projection;
- whether private simulation material is being sent directly to a Writer stage.

The output is a typed satisfaction receipt plus the bounded writer/worker-safe projection. It remains `authority=false` and performs no model execution.

### Required versus optional context

Required context is a contract, not a hint.

If an operation declares a context class/purpose as required and no eligible selected item satisfies it, assembly returns a blocking result. The manager must route the run to `BLOCK / PENDING` or acquire the missing evidence; it must not silently downgrade the requirement and generate with context starvation.

Optional context may be absent without blocking.

### Private simulation state

A private character state can legitimately drive:

```text
private state
→ action / tactic proposal
→ scene collision / world resolution
→ writer-safe realization projection
```

It must not automatically become:

```text
private state
→ Writer prompt exposition
→ dialogue paraphrase
```

This boundary is one structural defense against agenda-to-dialogue leakage / HF-30.

---

## 06 · Hard-budget packing stays deterministic

After semantic selection and stage-safe assembly, `memory_tiers.py` performs deterministic budget packing where tiered memory packing is used.

It owns:

- `hot_budget` and `working_budget` enforcement;
- pinned-item override;
- derived-memory authority checks;
- source-reference / source-fingerprint requirements;
- whole-item-or-skip packing;
- invalidated-item exclusion;
- stable archive output.

It does **not** summarize Canon, score story relevance, or truncate a semantic memory block into an ambiguous fragment just to squeeze under budget.

Pinned items must fit the hot budget; if they do not, the run fails instead of silently discarding the author's explicit control.

The output records both owners explicitly:

- `selection_owner = model`
- `budget_owner = deterministic_runtime`

---

## 07 · Author controls are overlays, not Canon writes

The Context Inspector supports low-authority controls such as:

- pin / unpin;
- explicit priority change;
- hide a derived view;
- invalidate a derived view so it must be rebuilt.

These controls alter **selection and presentation behavior** only.

Hiding or invalidating is restricted to derived views. A caller cannot use the overlay mechanism to make authoritative Project facts disappear from reality.

The overlay itself receives a fingerprint so changes remain traceable.

---

## 08 · Protected edits become proposals

If a caller requests an edit to a context item whose authority is `locked` or `accepted`, `context_inspector.py` does not mutate the protected source.

It creates a proposal record with:

- proposal ID;
- source item ID;
- original authority;
- requested patch;
- `proposal_required` status;
- `direct_mutation_performed = false`;
- `canon_write = false`.

This lets an author say “I want this fact changed” without a context UI pretending the fact has already changed.

Actual Canon mutation still belongs to explicit Project acceptance and Settlement.

---

## 09 · Memory Bank is durable working memory, not shadow Canon

`harness/memory_bank.py` provides durable banks for domains such as context, character, relationship, thread, style, learning, runtime, corpus, and derived memory.

The bank keeps provenance, fingerprints, versions, authority metadata, explicit controls, and edit history.

Two paths remain distinct:

**Editable runtime / derived memory** may be changed under the bank's version / fingerprint preconditions.

**Protected Canon references** remain read-only references. Requested changes become proposals rather than in-place mutations.

Derived memory should remain rebuildable from its source evidence wherever practical.

---

## 10 · Memory never proves story facts or character knowledge

Memory can be useful without being authoritative.

It is not proof that:

- an event happened;
- a character knows a fact;
- a relationship has officially changed;
- a plan has been accepted;
- a research claim became Project truth;
- a Corpus observation belongs in the next draft;
- a model inference is now durable user taste.

Those conclusions belong to the Project mechanisms that own them.

The ability to invalidate and rebuild memory is a feature, not a weakness: derived state should be easier to throw away than Canon.

---

## 11 · A typical draft / revision context flow

**Resolve Project authority.** Determine Canon cutoff, active plan, participating characters, commitments, and task-specific evidence.

**Build eligible context.** Create a sparse Context Manifest with authority, provenance, and stage boundaries.

**Inspect explicit controls.** Apply pin / priority / derived-view controls and reject illegal sensitive-stage placement.

**Select semantically when needed.** Use `context.select` only when interpretation is actually required.

**Assemble the exact stage view.** Validate selected IDs, required classes/purposes, provenance, invalidation state, and private-state boundaries with `context_assembly.py`.

**Pack under hard budgets.** Preserve explicit controls and pack whole blocks deterministically where tiered budgets apply.

**Execute the target semantic / writing contract.** The receiving model sees the bounded working set, not the whole project or all private simulation state.

**Persist only appropriate derived observations.** New memory remains non-authoritative and source-bound.

Any proposed Canon change still waits for explicit acceptance and Settlement.

---

## 12 · Failure routing

A context / memory failure should return to this layer rather than being disguised as a prose problem.

**Relevant evidence omitted because semantic selection was wrong** → rerun / repair `context.select` with correct bounded evidence.

**A required context class has no eligible item** → `BLOCK / PENDING`; obtain the missing evidence or change the explicit requirement rather than proceeding context-poor.

**Pinned memory exceeds hard budget** → resolve the explicit control / budget conflict; do not silently drop the pin.

**Regression, hidden gold, or private simulation state appears in Writer context** → deterministic stage / assembly failure.

**Derived memory points to stale source fingerprints** → invalidate and rebuild.

**Protected Canon fact needs to change** → create a proposal and route through Project acceptance / Settlement.

**A character acts on memory they do not know** → Character / knowledge-boundary failure, not proof that the memory should be removed globally.

---

## 13 · Exact references

- [Architecture](architecture.en.md) — authority domains and semantic / deterministic ownership.
- [Production Pipeline](production-pipeline.en.md) — where context selection occurs in DRAFT / REVISE.
- [Project SDK](project-sdk.en.md) — Project authority and exact dependency locks.
- [`harness/context_inspector.py`](../harness/context_inspector.py) — deterministic inspector / overlay contract (`novelforge_context_inspector_v3`).
- [`harness/context_assembly.py`](../harness/context_assembly.py) — required-context and stage-safe assembly (`novelforge_context_assembly_v1`).
- [`harness/memory_tiers.py`](../harness/memory_tiers.py) — model-selected, deterministic-budget context packer.
- [`harness/memory_bank.py`](../harness/memory_bank.py) — durable editable memory implementation.
- [`harness/semantic_workers/contracts/context-research.json`](../harness/semantic_workers/contracts/context-research.json) — `context.select` semantic contract.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="48" />
  <br />
  <sub>Let the model decide meaning. Let the runtime enforce boundaries. Let the Project decide truth. 🌸</sub>
</div>
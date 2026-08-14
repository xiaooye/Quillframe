<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><kbd>AUTHOR CONTROL</kbd>&nbsp;&nbsp;<kbd>SPARSE CONTEXT</kbd>&nbsp;&nbsp;<kbd>MEMORY ≠ CANON</kbd></p>
</div>

# Context & Memory · See what the model sees without turning memory into truth

NovelForge 7.2 adds an author-visible control layer around context and derived memory. The goal is not to create a second Story Bible. It is to make **selection, compression, provenance, and intervention inspectable** while preserving the existing authority boundary.

> **Core invariant ✦** Context decides what a run may see. Memory helps carry useful derived information between runs. Neither one can silently promote itself into Canon.

## 01 · Three different things

**Project authority** answers *what is true*. Accepted/locked story facts remain owned by the consuming project.

**Context Manifest** answers *what this run is allowed to receive, at which stage, and why*. It is sparse, task-scoped, and disposable.

**Memory Bank** stores editable runtime, derived, or proposal-oriented working memory. It can expose protected Canon references, but protected references are snapshots rather than editable Canon rows.

Keeping these concepts separate prevents a convenient summary, stale session note, corpus observation, or user experiment from becoming story truth by accident.

## 02 · Context Inspector

`harness/context_inspector.py` turns a Context Manifest into an inspectable control surface. For each item it can expose:

- stable item ID and class;
- source reference and source fingerprint;
- authority class;
- inclusion reason;
- injection stage;
- relevance and explicit priority;
- pin state;
- whether the view is derived and rebuildable.

The supported stages are intentionally explicit:

- `writer_pre_draft` — context that may influence first-pass generation;
- `post_draft_critic` — evidence that belongs only after a candidate exists;
- `independent_reviewer` — bounded material for an external/independent judgment;
- `never` — stored or proposed material that must not be injected automatically.

This stage model is what allows regression evidence, hidden-gold material, proposals, and critic-only evidence to exist without contaminating the writer.

## 03 · Author controls are overlays, not Canon writes

Low-authority controls may:

- pin or unpin a context item;
- change selection priority;
- hide a derived view;
- invalidate a derived view so it must be rebuilt.

These controls affect **selection behavior**, not project truth.

If an author asks to edit a protected `locked` or `accepted` reference through the memory/control surface, NovelForge does not mutate the protected row. The edit becomes a **proposal** with provenance back to the protected reference.

That distinction is deliberate: an editor can say “I want this fact changed” without the memory UI pretending the change has already happened in Canon.

## 04 · Tiered derived memory

`harness/memory_tiers.py` allocates already-derived or project-provided memory under hard budgets. It does not summarize Canon itself.

The allocator uses three tiers:

**Hot** — pinned items, current-event overlaps, and current-participant relevance.  
**Working** — relevant or prioritized derived memory that is useful but not immediately scene-bound.  
**Archival** — retained references that should not consume the active context budget.

Selection is whole-item-or-skip. A memory item is not silently truncated into an ambiguous fragment merely to fit a token budget.

Every derived item must remain non-authoritative and retain source references plus source fingerprints. Invalidated items are excluded until rebuilt.

## 05 · Editable Memory Bank

`harness/memory_bank.py` provides durable banks for:

`context · character · relationship · thread · style · learning · runtime · corpus · derived`

The bank records authority, provenance, fingerprints, versions, pin/priority controls, and edit history.

Two edit paths matter:

**Editable runtime/derived memory** may be updated when the caller supplies the exact current fingerprint. Stale writes fail.

**Protected `locked` / `accepted` memory references** cannot be edited in place. An edit creates a proposal child and leaves the protected source unchanged.

Proposal memory defaults to the `never` stage. Merely proposing a Canon change must not cause that proposed future to prime the next draft.

Learning/corpus memory defaults to post-draft use rather than writer pre-draft use unless an explicit higher-level policy permits otherwise.

## 06 · What memory must never become

Memory is not:

- a shadow Canon database;
- a substitute for explicit settlement;
- proof that a character knows something;
- proof that an event happened;
- an excuse to load the whole project;
- a place to preserve hidden evaluator answers inside writer context.

A useful memory system is valuable precisely because it can be **edited, invalidated, rebuilt, and discarded** without corrupting the authoritative story state.

## 07 · Typical run

A draft/revision run normally resolves project authority first, then builds a sparse Context Manifest. The Inspector makes that selection auditable. Derived memory may be allocated into hot/working tiers under budget. Writer-only, critic-only, reviewer-only, and never-inject material remain separated by stage.

After the run, new observations may create or update derived memory, but Canon changes still require the project’s normal acceptance and settlement transaction.

## 08 · Related contracts

- [Architecture](architecture.en.md) — where context/memory sit in the full system.
- [Production Pipeline](production-pipeline.en.md) — when context is selected and when critic evidence becomes legal.
- [Project SDK](project-sdk.en.md) — project authority and exact framework locks.
- [`harness/context_inspector.py`](../harness/context_inspector.py) — deterministic inspector/overlay implementation.
- [`harness/memory_tiers.py`](../harness/memory_tiers.py) — tier allocation and budgets.
- [`harness/memory_bank.py`](../harness/memory_bank.py) — durable editable memory implementation.

> **Design principle:** author control should make hidden machinery visible without weakening authority boundaries.

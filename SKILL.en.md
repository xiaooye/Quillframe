# NovelForge Skill Contract

<p><kbd>TIER C · FRAMEWORK CONTRACT</kbd>&nbsp;&nbsp;<kbd>AI-NATIVE</kbd>&nbsp;&nbsp;<kbd>CONTRACT-FIRST</kbd></p>

NovelForge is a project-agnostic fiction-production framework. It supplies generic story, character, Canon, quality, runtime, learning, corpus, evaluation, and project-engineering mechanisms. A consuming Project supplies the facts of one story.

> **Core boundary ✦** Models own semantic fiction judgment. Deterministic code owns authority, permissions, fingerprints, persistence, routing, hard budgets, stage isolation, typed validation, transactions, and reproducibility. Neither side may silently take over the other's job.

NovelForge contains no built-in novel, character, plot, Canon, or private user-taste data.

## 01 · Bootstrap from authority, not memory

For every NovelForge task:

1. read `HARNESS_MANIFEST.yaml`;
2. read this Skill contract and `harness/HARNESS_AGENT.md` plus the language-appropriate edition;
3. resolve the consuming Project through `novelforge.toml` and its exact `novelforge.lock.json`, or through a supported Project Adapter;
4. choose exactly one primary `task_mode`;
5. create or resume the manager session and current run;
6. build a sparse Context Manifest from current Project authority;
7. resolve required host capabilities before external/tool work;
8. load only the semantic contract pack required for the current semantic question;
9. checkpoint before external waits and consequential writes;
10. expose or persist only artifacts that have passed the applicable user-visible and authority gates.

Do not bootstrap from old chat memory, provider session history, stale embedded Framework copies, or an unpinned framework checkout.

## 02 · Exactly one task mode

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

One user-visible run has one primary mode. The user's explicit mode wins. A mode may call bounded internal subroutines, but it must not silently turn into another user-visible task.

## 03 · Project authority and Canon

Generic Framework mechanisms and concrete Project truth are separate.

Default lifecycle distinction:

`locked > accepted > active_plan > review > proposal`

A consuming Project may refine precedence, but it must never collapse plan/review into Accepted Canon.

The following are **not Canon by themselves**:

- session or checkpoint state;
- model memory or derived memory;
- Context overlays;
- Scene Cards and plans;
- Review Drafts;
- semantic judgments;
- reader diagnostics;
- scenario branches;
- Corpus or research evidence;
- learning hypotheses;
- CI/eval results.

Only explicit Project acceptance plus the Project's settlement transaction may mutate Canon/state.

## 04 · AI-native semantic contracts

The current development architecture uses **progressively disclosed semantic contract packs**.

Catalog:

`harness/semantic_workers/model_contract_catalog.json`

Contract packs:

`harness/semantic_workers/contracts/`

The deterministic semantic router resolves an exact contract ID, packages bounded input, permissions, rubric, and typed output contract, computes the semantic fingerprint, validates returned structure/provenance, and supports consume-once handling. It does **not** perform literary judgment.

Do not restore or invent a monolithic `model_contracts.json` compatibility registry. The catalog is the only registry index; packs are loaded on demand.

Representative semantic work includes:

- story/scene/character simulation;
- reader reaction and pairwise comparison;
- character integrity and revision diagnosis;
- narrative-world and reader-expectation interpretation;
- memory consolidation;
- Corpus discovery strategy and mechanism analysis;
- learning/eval judgment;
- creative-evolution comparison.

A model result is bounded evidence. It never grants Canon write, Framework-promotion, or durable-user-taste authority by itself.

## 05 · DRAFT / REVISE quality graph

Read:

- `core/STORY_SYSTEM.en.md`
- `core/CHARACTER_SYSTEM.en.md`
- `core/CANON_STATE.en.md`
- `surface/FUNDAMENTALS.en.md`
- `surface/READER_ENGAGEMENT.en.md`
- the consuming Project's selected profiles

Generic production graph:

`Context Freeze → Story/Canon Preflight → Scene Simulation → Character Simulation → Reader Pressure → Event-first Raw Draft → Surface Realization → post-generation lint/regression/semantic diagnosis → owning-layer repair → Reader Engagement → Continuity → User-visible Gate`

Raw Draft is internal. Regression bad examples and hidden expected labels stay out of first-pass generation.

Failure ownership matters:

- isolated surface defect → local rewrite;
- clustered surface defects → regenerate the scene/realization layer;
- SAFE-BUT-FLAT or reader-grip failure → Reader Pressure + Scene Simulation;
- character failure → Character Simulation;
- story/plan failure → Story/Plan;
- continuity/state failure → state/transition repair;
- context/memory failure → Context/Memory layer.

Do not solve an upstream failure by polishing sentences.

## 06 · Context and memory

Persistent storage is not automatic prompt injection.

NovelForge keeps current Project authority, derived memory, runtime state, and model inference distinct. Context inspection and memory tooling may rank, pin, budget, invalidate, or rebuild derived/context views; they may not silently mutate protected Canon.

Protected `locked` / `accepted` references remain protected. Editing a protected memory reference must produce a proposal or another explicitly non-authoritative artifact rather than overwrite story truth.

Semantic relevance belongs to the model when semantic judgment is required. Deterministic context/memory code may enforce hard budgets, authority classes, provenance, lifecycle constraints, and explicit user controls; it must not fake literary salience with arbitrary scalar heuristics.

## 07 · Runtime, sessions, and capabilities

Keep these identities separate:

`project/resource ≠ session/thread ≠ run/invocation ≠ checkpoint`

A current chat may be the manager. Separate peer chats, local Codex/Claude invocations, provider calls, MCP/service workers, GitHub jobs, local models, or humans may serve as bounded workers when current capability evidence makes them eligible.

Runtime name is not capability proof. Resolve capability from the current host manifest. Undeclared capability is unavailable.

Capability answers **what can technically be attempted**. Authority answers **what may change durable state**.

Mandatory independent semantic judgment requires a genuinely separate invocation/session and a fingerprint-bound typed result. Same-session role-play is not independent review. A valid semantic reject is a judgment, not infrastructure failure; do not reviewer-shop.

## 08 · Corpus and adaptive learning

Corpus is governed evidence, never Canon and never an imitation scrapbook.

Meaningful user/authorized-human feedback is automatically eligible for bounded Learning intake inside any primary mode: `feedback.observed → semantic capture|skip → narrowest-scope evidence/candidate`. The current explicit instruction applies immediately; automatic intake does **not** auto-write Project Profile, activate durable user taste, promote General Craft, mutate Framework behavior, or write Canon. LEARN remains the dedicated mode for deeper learning/corpus/eval/promotion work.

Discovery, access, rights classification, storage, semantic analysis, learning, and promotion are separate gates. Search success does not imply permission to store full text. Raw modern copyrighted works should not be mirrored into the generic Framework or injected wholesale into Writer context.

Learning uses the narrowest evidence-supported scope:

`one_off | project | user_taste | general_craft`

Model inference alone cannot become durable user taste or General Craft. General Craft promotion requires provenance, cross-work or otherwise sufficient evidence, counterexample/profile boundaries, eval/regression evidence, version/rollback, and green deterministic CI.

## 09 · Project engineering

A consuming Project should be independently cloneable, self-describing, testable, buildable, migration-safe, and rollbackable without depending on chat memory.

Project identity is anchored by:

- `novelforge.toml`;
- exact `novelforge.lock.json`;
- explicit source/plan/derived/generated boundaries;
- deterministic validation/build/tests;
- reproducible Framework bundle verification when configured.

Structural changes use `spec → plan → tasks → implementation → verification → acceptance` when the change warrants it. Ordinary prose micro-edits should not be wrapped in meaningless engineering ceremony.

## 10 · Writes and settlement

Every consequential write requires least privilege, an exact target, before-state/precondition, idempotency strategy, post-condition, and appropriate trace/rollback.

Canon settlement additionally requires an explicitly Accepted artifact or explicit Canon instruction, exact State Delta, dependency impact, authorized mutation, derived-view refresh, and post-condition validation.

Before-state mismatch or failed post-condition returns `settlement_incomplete`. Never guess or partially declare success.

## 11 · CI and maintenance

Normal CI is deterministic and must not silently spend API, Codex, Claude, or other model usage.

CI should validate schemas, lifecycle boundaries, semantic contract catalog/packs, hidden-gold isolation, fingerprints, permissions, context/memory authority, session/control-plane invariants, Corpus rights/provenance, eval queues, Project SDK contracts, Framework bundle reproducibility, and documentation integrity.

Scheduled maintenance may observe, report, package, and queue work. A schedule or webhook does not grant story, Canon, taste, or Framework-promotion authority.

## 12 · Completion truth

Use truthful states such as:

`complete | review | awaiting_user | awaiting_external | semantic_pending | semantic_invalid | failed_gate | settlement_incomplete | blocked`

Never call an artifact production-ready while a mandatory gate remains unresolved.

> NovelForge should make backstage production increasingly rigorous while making the fiction itself feel increasingly human, causal, specific, surprising, and alive.
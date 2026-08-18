# Canon & State Model · Persist the difference between intended, generated, accepted, and settled

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>AUTHORITY</kbd>&nbsp;&nbsp;<kbd>SETTLEMENT</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd></p>

Quillframe separates **story truth** from plans, drafts, research, review judgments, runtime state, model memory, and derived summaries. Long-form continuity depends less on remembering more than on remembering **what kind of thing each record is allowed to mean**.

> **Core invariant ✦** Something being present in context, memory, a database, a review, or a session does not make it Canon.

## 01 · What this model owns

The Canon & State Model defines generic mechanics for:

- authority classes and precedence;
- stable object identity;
- one authoritative home per fact;
- evidence scope;
- information ownership;
- explicit state deltas;
- dependency impact;
- transactional settlement;
- post-condition verification;
- separation between Canon, runtime, memory, learning, research, and review state.

It does not define the facts of any particular novel. A consuming project supplies its own entities, accepted artifacts, locked invariants, and project-specific precedence refinements.

## 02 · Authority classes

Quillframe uses a generic lifecycle vocabulary:

```text
proposal     replaceable candidate or suggested change
active_plan  current future intent
review       generated/revised artifact awaiting explicit acceptance
accepted     explicitly accepted artifact or state eligible for settlement
locked       explicit invariant / long-lived project constant
```

These labels are not interchangeable workflow decorations. They answer different questions.

- `proposal`: *could we do this?*
- `active_plan`: *is this currently intended?*
- `review`: *is this the candidate we are considering?*
- `accepted`: *did the authorized user/process explicitly accept this artifact or state?*
- `locked`: *is this an explicit invariant that ordinary planning/revision must not silently change?*

A project may refine precedence, but it must never collapse plan/review into Accepted Canon.

## 03 · Generic precedence

When sources conflict, a project normally resolves them approximately in this order:

1. current explicit user instruction;
2. project-locked invariants;
3. Accepted Canon artifacts;
4. settled authoritative current-state records;
5. authoritative current character/relationship/world/state records;
6. active plans;
7. verified research claims;
8. review drafts;
9. temporary inference.

Runtime/session/checkpoint data is **not a Canon-precedence layer**.

A model may have seen a fact earlier in the conversation. That proves only that the runtime saw it, not that the story accepted it.

## 04 · Plan ≠ current state

If a chapter plan says a character will:

- receive money;
- learn a secret;
- gain permission;
- meet someone;
- lose an object;
- change a relationship;
- make a promise;

none of those changes enters authoritative current state merely because the plan exists.

```text
active_plan: "future X should happen"
≠
current state: "X has happened"
```

The same rule applies to Scene Cards, simulated branches, outline notes, and revision proposals.

## 05 · Accepted ≠ settled

Acceptance and settlement are deliberately separate.

**Acceptance** freezes the user-approved artifact that may serve as Canon evidence.

**Settlement** applies the exact state changes supported by that artifact to authoritative state stores.

This distinction allows the system to stop safely between “the chapter is accepted” and “every affected state table has been updated.”

It also prevents a partially failed database write from being confused with successful Canon adoption.

## 06 · One authoritative home per fact

Avoid duplicated live truth. Derived views may summarize authority; they must not compete with it.

A generic mapping may look like:

```text
character identity / biography     → CHAR
relationship current state         → REL / ROM
historical/story event             → EVT
information ownership              → INFO / SEC / RUM
resources / money / debt           → RES
permissions / qualifications       → PERM
objects / evidence                 → ITEM / EVID
open question / obligation         → LOOP / OBL
foreshadow / reveal                → FS / REV
research source / claim            → REF / CLAIM
reader promise / payoff            → PAY
character arc / appeal             → CARC / APL
presence / participation           → PRES
cross-object dependency            → DEP
```

If a summary, memory bank, context cache, or generated profile duplicates one of these facts, the duplicate is a **derived reference**, not a second writable authority.

## 07 · Stable identity

Recommended generic ID families:

### Story
`BOOK · VOL · ARC · UNIT · CH · SCN`

### Character
`CHAR · CARC · APL · PRES`

### Relationship
`REL · ROM`

### World
`ORG · LOC · INST · ITEM`

### Continuity / plot state
`EVT · INFO · SEC · RUM · RES · PERM · LOOP · OBL · EVID · FS · REV`

### Research / reader / governance
`REF · CLAIM · PAY · MOM · THM · DEP · DEC`

Once an ID becomes active or accepted, do not recycle it for a different entity.

Human-readable names may change. Identity must not.

## 08 · Truth and knowledge are separate

Story truth is not the same thing as anyone knowing it.

```text
world truth
≠ narrator/POV access
≠ character knowledge
≠ character belief
≠ rumor
```

A real-world research claim may be verified while still being unavailable to a historical character. A character may sincerely state something false. A rumor may affect action without becoming world truth.

When information ownership changes action, record it explicitly through `INFO / SEC / RUM` or a project-equivalent state model.

## 09 · Evidence proves only what it establishes

Evidence scope must stay narrow.

Examples:

- possessing an object does not prove understanding it;
- hearing a rumor does not prove the rumor true;
- one character's confident statement does not automatically establish world fact;
- a Scene Card does not prove occurrence;
- a Review Draft does not prove occurrence;
- a semantic reviewer rejecting a candidate does not prove a story fact;
- an eval result does not grant Canon authority;
- a memory-bank entry does not prove character knowledge;
- a runtime checkpoint does not prove narrative occurrence.

Do not upgrade an inference merely because it is convenient.

## 10 · State Delta contract

Settlement should be explicit enough to audit.

```yaml
artifact_id:
artifact_fingerprint:
ops:
  - op: update
    object_type: RES
    id: RES-...
    before: {...}
    set: {...}
    evidence_ref: exact accepted passage / explicit Canon instruction
```

Each operation requires:

1. an exact authority object type;
2. a unique stable ID;
3. an exact expected before-state;
4. evidence from an Accepted artifact or explicit Canon instruction;
5. dependency-impact analysis;
6. authorized write intent;
7. the mutation itself;
8. derived-view refresh;
9. post-condition verification;
10. trace / receipt.

`0` matches or `>1` matches is a hard stop.

## 11 · Dependencies make change visible

`DEP` or an equivalent dependency model records which future plans, summaries, timelines, calculations, research assumptions, or continuity views rely on which authoritative state.

When a settled fact changes, downstream artifacts may need to be:

- invalidated;
- recomputed;
- re-planned;
- re-reviewed;
- marked stale.

Do not preserve future work simply because it was expensive to produce.

## 12 · Settlement is a transaction

A generic settlement sequence is:

```text
explicit acceptance
→ freeze accepted artifact + fingerprint
→ derive exact State Delta
→ verify before-state
→ compute dependency impact
→ checkpoint / write intent
→ authorized mutation
→ rebuild derived views
→ verify post-condition
→ write trace / receipt
```

Any before-state mismatch or post-condition failure yields **incomplete settlement**.

Do not:

- guess the missing before-state;
- partially claim success;
- repeat an already completed side effect on resume;
- silently write unrelated state while one operation is unresolved.

Resume must distinguish completed mutations from pending ones.

## 13 · Context, memory, and derived views are lower-authority

Quillframe may expose author-editable context or memory controls, but those controls do not become a second Canon editor.

A protected `locked` or `accepted` reference may be shown in an editable-memory surface as a snapshot. Editing that snapshot must create a **proposal**, not mutate the protected Canon row.

Derived memory must remain `authority=false`, retain source references/fingerprints, and be invalidatable/rebuildable.

See [Context & Memory](../docs/context-and-memory.en.md).

## 14 · Research is evidence, not automatic story knowledge

Verified research answers “what is supported by external evidence,” not:

- whether the project chose to fictionalize it;
- whether an event has occurred in this novel;
- whether a character knows it;
- whether a narrator may state it;
- whether a future plan has become current state.

Research claims may constrain planning or prose, but their authority remains research-scoped unless the project explicitly adopts them into its own world/Canon model.

## 15 · Runtime and review state are operational evidence

The following may trigger work, validation, or a proposal, but do not become Canon by themselves:

- session history;
- checkpoint;
- handoff;
- webhook/connector event;
- worker receipt;
- semantic-review result;
- Reader Panel result;
- integrity-audit finding;
- quality-evolution ledger;
- eval result;
- CI result;
- corpus observation;
- learning hypothesis;
- model/provider memory.

**Capability is not authority. Storage is not authority. Judgment is not authority.**

## 16 · Failure semantics

Stop rather than guess when:

- the authority class is ambiguous;
- the target ID does not resolve exactly once;
- before-state differs from the frozen expectation;
- evidence does not support the proposed delta;
- a dependency impact cannot be bounded safely;
- a protected Canon record is being edited through a lower-authority surface;
- post-condition verification fails;
- resume cannot prove whether a side effect already happened.

The correct state is `settlement_incomplete` or an equivalent explicit failure—not “probably succeeded.”

## 17 · Invariants

1. Persist the difference between **intended, generated, accepted, and settled**.
2. Plan/Scene Card/Review never imply occurrence.
3. Accepted artifact and settled state are distinct checkpoints.
4. Runtime/session/memory/learning/corpus/review state cannot grant Canon authority.
5. Every mutable authoritative fact has one canonical home.
6. State mutation is evidence-backed, preconditioned, and post-verified.
7. Resume never repeats an already completed side effect.
8. Derived views can be rebuilt; authoritative truth must remain traceable.

## 18 · Related contracts

- [Story System](STORY_SYSTEM.en.md) — future planning and dependencies.
- [Character & Relationship System](CHARACTER_SYSTEM.en.md) — information ownership, relationship/current state, and character evidence.
- [Context & Memory](../docs/context-and-memory.en.md) — author-visible controls that remain below Canon authority.
- [Project SDK](../docs/project-sdk.en.md) — manifest/lock/project engineering and project-owned authority.
- [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md) — operational state that must remain separate from Canon.

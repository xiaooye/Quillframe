# Session Runtime · Durable execution identity without confusing conversation memory for Canon

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>SESSION ≠ RUN ≠ CHECKPOINT</kbd>&nbsp;&nbsp;<kbd>RESUMABLE</kbd></p>

The Session Runtime gives Quillframe a durable execution identity across chat turns, local agents, external workers, waits, retries, and restarts. It records **where execution is**, not what is true in the novel.

> **Core invariant ✦** Session/provider history can help resume work. It never becomes Project authority merely because it persisted.

## 01 · Identity model

Keep these identities distinct:

```text
project / resource
≠ session / thread
≠ run / invocation
≠ checkpoint
≠ external attempt / handoff
```

**Project/resource** identifies the durable fiction or framework resource being worked on.

**Session** is a resumable execution container with a role, lifecycle, and memory policy.

**Run** is one invocation/execution episode inside a session.

**Checkpoint** is a validated workflow cursor plus the fingerprints/preconditions needed to resume safely.

Provider-native conversation/thread/session IDs are optional execution metadata. They do not establish story truth.

## 02 · Session roles

Reference roles include:

- `manager` — owns one primary task mode and user interaction;
- `writer` — bounded drafting worker when separated from manager;
- `specialist` — task-scoped simulation, research, analysis, or implementation worker;
- `semantic_reviewer` — reviewer identity used when a separate semantic invocation/session is required;
- `human_reviewer` — human or peer-relay reviewer;
- `other` — explicit extension only.

A role describes execution responsibility, not authority. A worker called `semantic_reviewer` does not become independent unless it is genuinely a separate eligible invocation/session with the required blind bounded job.

## 03 · Memory policies

Reference memory policies:

`none | bounded | session | external | checkpoint_only`

Memory policy describes what a runtime may retain. It does not define what the next prompt automatically receives.

Every invocation still follows an explicit Context Manifest / context policy.

Independent semantic work normally uses `none` or `bounded`: exclude writer private reasoning, unrelated project state, hidden expected verdicts, previous reviewer answers, and regression answer keys unless the declared rubric explicitly requires some bounded evidence.

## 04 · Lifecycle state machine

Reference lifecycle:

```text
created → running
running → idle | awaiting_user | awaiting_external | completed | failed | terminated | stale
idle → running | completed | terminated | stale
awaiting_user → running | failed | terminated | stale
awaiting_external → running | failed | terminated | stale
failed → running | terminated | stale
completed → stale
stale → terminated
```

Illegal transitions are deterministic errors.

`semantic_pending` is normally a workflow/gate status inside a run, not a reason to invent an impossible session transition.

## 05 · Run identity

A run should record enough information to answer:

- which session owns it;
- which task mode it is executing;
- which resource/project it targets;
- what workflow step/cursor is current;
- what inputs/artifacts are frozen;
- which external results are pending;
- what completion/failure state ended the invocation.

A new invocation after an interruption may be a new run inside the same session.

## 06 · Checkpoints

Checkpoint at boundaries where repeating or forgetting work would be dangerous:

- Context Freeze;
- frozen candidate before a fingerprint-bound review;
- user/external wait;
- before consequential Project/Framework write;
- after binding a valid external result;
- before Canon settlement;
- before long-running handoff/discovery/learning work.

A useful checkpoint records:

- session ID and run ID;
- workflow step/cursor;
- relevant artifact IDs/fingerprints;
- current authority/lock references;
- pending gate/event/handoff;
- approval/write-intent references when applicable;
- resume policy;
- timestamp/version.

A checkpoint is not a serialized copy of the whole chat.

## 07 · Resume algorithm

Resume is a fresh validation act, not “continue where the conversation memory feels like it left off.”

Automatic feedback Learning may itself be pending runtime work. If semantic capability is unavailable, the durable feedback event/intake remains `awaiting_semantic`; a later run revalidates the event hash, registered semantic-job fingerprint, current Project/Framework authority/capability, and the Learning consumer receipt before applying it exactly once. Provider/chat history is never preference authority.

```text
load durable session + checkpoint
→ revalidate Framework provenance and native Project identity/contract
→ revalidate current native Project authority/context and deterministic bundle fingerprint evidence
→ rebuild sparse context against current state
→ verify referenced artifact fingerprints
→ verify approvals / write preconditions
→ re-resolve capabilities needed by pending external work
→ bind/validate returned result if present
→ verify logical result / side effect has not already been consumed
→ continue saved workflow cursor
```

If any required binding has changed materially, stop or route repair rather than silently continuing under stale assumptions.

## 08 · Side-effect safety

Session persistence must support at-least-once delivery realities without causing duplicate logical application.

Distinguish:

```text
worker/result delivery
≠ result validation
≠ logical result consumption
≠ downstream side effect
```

A repeated identical result may be recognized as already consumed. A conflicting result for the same logical identity is a hard stop.

Consequential writes require their own before-state/idempotency/post-condition semantics; session state alone cannot make a write safe.

## 09 · Chat as a first-class runtime

An ordinary current chat may be the manager session. A separate chat can serve as independent semantic review when it receives a bounded blind packet and returns a typed result bound to the exact semantic/artifact fingerprint.

The current chat lacking subprocess/API-key capability does not prove that all Harness routes are unavailable. Runtime routing must consider actually connected/declared alternatives before declaring `semantic_pending`.

A user-mediated peer-chat relay may produce `awaiting_user` while the relay is outstanding.

## 10 · Local agent / service sessions

Codex, Claude Code, local models, MCP workers, provider APIs, GitHub/service jobs, or other runtimes may host manager or worker sessions when their capabilities are proven.

Using the same CLI family for manager and reviewer does not violate independence if the reviewer is a genuinely separate invocation/session with bounded context and no leaked verdict/gold material.

Runtime family is not session identity.

## 11 · Persistence boundary

`session_runtime.py` owns deterministic validation of session/run/checkpoint objects and lifecycle.

The Control Plane owns shared operational state such as events, handoffs, leases, result hashes, and consume-once receipts.

A provider's native memory may be referenced as execution metadata but must not become the only durable record required for safe resume.

## 12 · Failure semantics

Stop or mark explicit failure when:

- session/run/checkpoint identity cannot be reconciled;
- an artifact fingerprint changed unexpectedly;
- an approval/write precondition is stale;
- pending external result cannot be bound to the frozen job;
- a side effect may already have occurred but no receipt/precondition can prove it;
- current capability no longer satisfies the pending work;
- a reviewer packet cannot preserve required independence/context isolation.

Do not reconstruct missing truth from remembered conversation prose.

## 13 · Invariants

1. `project/resource != session != run != checkpoint`.
2. Provider-native IDs are metadata, not authority.
3. Persistent memory is not automatic prompt injection.
4. Resume revalidates current authority and capabilities.
5. Completed logical effects are not repeated.
6. Checkpoints store bounded resume state, not private reasoning transcripts.
7. Session state never grants Canon/Framework-write authority.
8. Independent review requires independent execution identity when the gate says so.

## 14 · Related contracts

- [Harness Agent](../HARNESS_AGENT.en.md) — manager execution policy.
- [Orchestration Protocol](../ORCHESTRATION_PROTOCOL.en.md) — mode graphs and checkpoint boundaries.
- [Runtime Routing](RUNTIME_ROUTING.en.md) — capability-based backend selection.
- [Control Plane](../control_plane/CONTROL_PLANE.en.md) — shared events, handoffs, leases and receipts.
- [Context & Memory](../../docs/context-and-memory.en.md) — context/memory authority boundaries.

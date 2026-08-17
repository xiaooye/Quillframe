# Control Plane · Durable coordination for work that can outlive one invocation

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>EVENTS</kbd>&nbsp;&nbsp;<kbd>LEASES</kbd>&nbsp;&nbsp;<kbd>CONSUME-ONCE</kbd></p>

The NovelForge Control Plane is the durable operational substrate for work that crosses invocation/process boundaries. It persists sessions, events, bounded handoffs, worker leases, result hashes, and logical consume-once receipts so external work can be retried and resumed without inventing what already happened.

> **Boundary ✦** The Control Plane answers **where work is, what attempt owns it, and whether a result has already been logically consumed**. It never decides story truth or literary quality.

## 01 · Operational graph

A distributed work item typically moves through:

```text
project / resource
→ manager session + checkpoint
→ typed event or bounded handoff
→ worker claim / lease
→ attempt executes
→ result stored + hashed
→ manager validates binding
→ named consumer records receipt
→ owning workflow resumes
```

These records are execution evidence, not Canon evidence.

## 02 · What the Control Plane owns

The Control Plane may own deterministic state for:

- sessions and operational versions;
- typed external/internal events;
- handoffs/jobs;
- worker attempt identity;
- leases and expiry;
- result payload hashes;
- consume-once receipts;
- timestamps and trace metadata;
- retry/reclaim bookkeeping.

It does not own:

- story direction;
- Accepted Canon;
- Canon settlement decisions;
- literary verdicts;
- durable user taste;
- Framework promotion authority;
- model reasoning.

## 03 · Typed events

Event classes should be deliberately narrow and non-authoritative. Examples include:

- resume request;
- semantic job/result arrival;
- eval request/result;
- maintenance request;
- research refresh;
- feedback observation;
- acceptance observation.

A generic event must not mean “silently write Canon,” “automatically draft the next chapter,” or “promote this Framework rule.” Those actions require their own authority, preconditions, and user-visible workflow semantics.

### Idempotency

Event delivery is realistically at-least-once.

- same idempotency key + same payload → safe duplicate;
- same idempotency key + different payload → hard conflict.

Do not pretend the network provides magical exactly-once delivery.

## 04 · Bounded handoffs

A handoff transfers only what the worker needs:

```yaml
handoff_id:
source_session_id:
target_worker_class:
resource_id:
task_or_gate:
artifact_refs: []
input_fingerprints: []
instructions:
context_policy:
permissions:
return_contract:
relay_or_native_refs:
```

Default rule: **do not copy the whole manager conversation.**

High-authority permissions such as Canon write, Framework promotion, and durable-taste write remain false unless a separate explicit authority path exists. Most semantic/research workers should never receive them.

## 05 · Leases and attempts

A queued worker atomically claims work for a bounded lease.

The lease establishes:

- current attempt identity;
- current owner;
- claim time;
- expiry/recovery semantics.

Only the active lease owner may complete that attempt. If the lease expires and another worker reclaims the job, the expired worker cannot later overwrite the new owner's valid result.

Lease expiry is infrastructure state, not a semantic judgment.

## 06 · Completion and consumption are different

Worker completion is not the same as applying its result.

```text
worker completes
→ result payload stored
→ deterministic payload hash recorded
→ manager/gate validates job/fingerprint/provenance
→ named logical consumer records receipt
→ downstream workflow effect occurs once
```

This distinction is critical for retries and resume.

An identical duplicate can return “already consumed.” A conflicting result hash for the same logical source/consumer is a hard stop requiring investigation rather than last-write-wins behavior.

## 07 · Exactly-once means logical application

NovelForge uses consume-once semantics for **logical downstream application**, not a claim that every transport message is delivered exactly once.

`feedback.observed` is intentionally multi-consumer. Author Steering and automatic Learning Intake use distinct logical consumer names (for example `author_steering:<session>` and `learning_feedback:<project-or-resource>`), so one receipt cannot globally consume or delete the event for the other path. Each consumer binds the same exact event hash independently. Read-only feedback observability does not consume the event. Arrival or consumption never grants Project Profile, user-taste, Framework, or Canon authority.

This lets the system tolerate:

- duplicate webhook/event delivery;
- worker retry after uncertain acknowledgement;
- process restart;
- manager resume;
- queue reclaim after lease expiry.

The safety condition is that a validated logical result or side effect is not applied twice.

## 08 · Semantic jobs through the Control Plane

A semantic handoff carries a frozen semantic job/fingerprint. The worker returns the typed result contract. The manager then validates:

- job identity;
- semantic fingerprint;
- worker/session/attempt provenance;
- output schema;
- permission boundary.

The Control Plane stores and transports this evidence but does not decide whether the prose is good.

A valid `semantic_reject` is stored as a valid semantic result and routed to the owning repair mechanism.

## 09 · MCP / service transport

The reference local MCP transport may use stdio. Remote service transports should apply normal authentication, origin/session, isolation, and network-security requirements.

MCP tools expose bounded operational capabilities. The existence of an MCP “write” tool does not create Canon authority.

Transport contracts should preserve the same job/handoff/result identity so switching transport does not change semantic meaning.

## 10 · Chat, local agents, CI, and services

Different hosts can participate in the same operational model:

- a chat manager may package a peer relay;
- local Codex/Claude may execute bounded jobs or talk to stdio MCP;
- GitHub/service workers may normalize external events into typed handoffs;
- remote workers may claim leases;
- normal CI may test lifecycle/idempotency/contracts without invoking a paid model.

Host diversity does not change authority semantics.

## 11 · Failure and recovery

Infrastructure failure may lead to:

- attempt failure;
- lease expiry;
- handoff reclaim;
- transport fallback;
- `awaiting_external` / `semantic_pending` when no eligible route exists.

Recovery always revalidates the frozen identity/fingerprint before consuming a returned result.

Do not:

- overwrite a newer lease owner;
- consume a mismatched result because it “looks right”;
- repeat a completed consequential side effect without precondition/receipt evidence;
- treat timeout as semantic rejection.

## 12 · Authority boundary

Control-plane arrival never raises authority.

The following remain non-authoritative by themselves:

- webhook;
- scheduled task;
- MCP request/result;
- worker handoff/result;
- GitHub/service event;
- CI status;
- semantic verdict;
- learning candidate;
- acceptance observation.

An observation that the user accepted something may trigger the settlement workflow. It does not itself execute settlement without the normal project authority/precondition checks.

## 13 · Invariants

1. Operational persistence is separate from story authority.
2. Events are typed and idempotent.
3. Handoffs are bounded; full-manager context is not copied by default.
4. Leases establish attempt ownership and safe reclaim semantics.
5. Completion and logical consumption are separate.
6. Exactly-once refers to logical application, not transport delivery.
7. Result identity/fingerprint/provenance are validated before consumption.
8. Control-plane data never grants Canon/Framework/taste-write authority by itself.

## 14 · Related contracts

- [Session Runtime](../session_runtime/SESSION_RUNTIME.en.md) — session/run/checkpoint identity.
- [Runtime Routing](../session_runtime/RUNTIME_ROUTING.en.md) — selecting eligible execution paths.
- [Semantic Worker Protocol](../semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) — typed semantic jobs/results.
- [Canon & State Model](../../core/CANON_STATE.en.md) — separate settlement transaction and authority.

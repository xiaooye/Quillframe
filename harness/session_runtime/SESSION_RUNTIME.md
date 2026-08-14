# Harness Session Runtime · v2

## Purpose

A session is the durable/continuable execution identity for one manager or worker. A run is one invocation inside that session. A checkpoint is a resumable workflow cursor.

```text
resource/project → session/thread → run/invocation → checkpoint → event/handoff → resume
```

Session lifecycle semantics live here. Durable persistence, event ingress, leases and result-consumption receipts live in `../control_plane/CONTROL_PLANE.md`.

## Identity

Every meaningful participant records:

```yaml
resource_id:
project_id:
session_id:
provider_session_id:
external_session_ref:
parent_session_id:
role: manager|writer|specialist|semantic_reviewer|human_reviewer|other
task_mode:
transport:
backend:
```

Rules:
- resource/project != session;
- session != run;
- provider-native IDs are metadata, not authority;
- a process restart does not create a new project;
- reviewer normally gets a new session for a changed fingerprint.

## Session classes

### Manager
May be long-lived and coordinate user interaction, Context Manifest selection, checkpoints and workers. Chat memory is not Canon.

### Production specialist
Task-bounded worker. Persistent state is allowed only when explicitly useful and never bypasses current authority/context selection.

### Independent semantic reviewer
Default **fresh-per-fingerprint**.

Resume only for transport recovery/clarification against the same frozen fingerprint. Changed artifact/rubric/output contract normally creates a new reviewer session.

### Human / peer-chat reviewer
May use an OS session ID plus opaque external reference/relay nonce when the chat product exposes no native ID.

## Memory policy

- `none`
- `bounded`
- `session`
- `external`
- `checkpoint_only`

Semantic reviewers require `none|bounded`.
Manager chat sessions may use `session`, but each authority-sensitive invocation rebuilds live authority and Context Manifest.

## Context policy

Persistent session state is not automatically model context.

Each worker invocation receives an explicit context policy. Semantic reviewers must exclude writer private reasoning, hidden gold, prior expected judgments and unrelated project data.

## State machine

```text
created → running
running → idle | awaiting_user | awaiting_external | completed | failed | terminated | stale
awaiting_user → running | failed | terminated | stale
awaiting_external → running | failed | terminated | stale
idle → running | completed | terminated | stale
failed → running | terminated | stale
completed → stale
stale → terminated
```

Illegal transitions are deterministic errors.

## Checkpoints

Checkpoint at stable boundaries:
- Context Freeze;
- frozen candidate before independent judgment;
- before `awaiting_user` / `awaiting_external`;
- before consequential writes;
- after a valid external result is bound;
- before SETTLE mutation.

Checkpoint stores at least run ID, workflow step, artifact fingerprints, pending gate/handoff and resume policy.

## Resume

On resume:
1. load session/checkpoint from the durable Control Plane when available;
2. revalidate live project/policy authority;
3. revalidate referenced artifact fingerprints;
4. revalidate approvals/write preconditions;
5. consume returned result exactly once at its logical gate;
6. continue from the saved step;
7. never blindly repeat completed side effects.

## Handoffs

Cross-session work uses `novel_os_handoff_v1` from the Control Plane. Do not clone the manager's entire conversation. Send bounded artifact refs/fingerprints, context policy, permissions, instructions reference and return contract.

Independent semantic work additionally follows `../semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`.

## Chat sessions

Chat is a first-class runtime. The current ChatGPT chat may be a manager session even if platform chat ID is not tool-visible. A separate ordinary chat can be an independent reviewer if it receives a bounded blind packet and returns typed fingerprint-bound evidence.

The OS does not require an API key merely because a runtime is a chat session.

## Local Codex / Claude

Local agent CLIs may run a full Harness manager or bounded worker. Provider-native session IDs may be recorded for resume, but live project authority must still be revalidated. Mandatory semantic review uses a separate invocation/session.

## Persistence boundary

`session_runtime.py` owns deterministic session-object construction and lifecycle validation.

`../control_plane/control_plane.py` owns durable multi-runtime storage, optimistic versions, typed external events, handoff leases and logical exactly-once consumption.

Neither layer grants Canon authority.

> Persist execution identity and resumable state; do not persist accidental authority.

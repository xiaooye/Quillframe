# Session Runtime · v7

## Identity

NovelForge separates:

`project/resource != session/thread != run/invocation != checkpoint`

A session is a resumable execution identity. A run is one invocation inside it. A checkpoint is a validated workflow cursor.

Provider-native chat/thread/session IDs are optional metadata and never project authority.

## Session roles

- `manager`: coordinates one task mode and user interaction.
- `writer`: bounded production worker when separated from manager.
- `specialist`: task-scoped analysis/simulation/research worker.
- `semantic_reviewer`: independent reviewer; normally fresh-per-fingerprint.
- `human_reviewer`: human/peer relay identity.
- `other`: explicit extension only.

## Memory policies

`none | bounded | session | external | checkpoint_only`

Persistent memory is not automatic prompt context. Every invocation still receives an explicit Context Manifest / worker context policy.

Independent reviewers use `none|bounded`; hidden gold, writer private reasoning, prior expected verdicts, and unrelated project state stay out.

## State machine

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

## Checkpoints

Checkpoint stable boundaries such as:
- Context Freeze;
- frozen candidate before independent review;
- external/user wait;
- before consequential write;
- after valid external result binding;
- before Canon settlement.

Checkpoint records run ID, workflow step, relevant fingerprints, pending gate/handoff, resume policy, and timestamp.

## Resume

On resume:
1. load durable session/checkpoint;
2. validate framework/project compatibility;
3. rebuild sparse context against current project authority;
4. verify referenced artifact fingerprints;
5. verify approval/write preconditions;
6. bind pending result if any;
7. ensure logical result/side effects are not re-applied;
8. continue from the saved step.

## Chat sessions

Ordinary chat is a first-class runtime. A current chat can be manager. A separate chat can serve as independent review only when it receives a bounded blind packet and returns typed fingerprint-bound evidence.

No subprocess or API key in the current chat does not automatically mean the overall Harness is blocked.

## Local agent sessions

Codex/Claude/local agents may run full manager sessions or bounded workers. Independent review requires a separate invocation/session even when the same CLI/provider is used.

## Durable persistence

`session_runtime.py` validates session objects/lifecycle. The Control Plane persists shared operational state, events, handoffs, leases, and consumption receipts.

Session state never grants Canon authority.

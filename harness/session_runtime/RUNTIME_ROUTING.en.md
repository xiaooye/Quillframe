# Runtime Routing · v7

## Principle

Select execution backends by required capability, independence, permissions, availability, resumability, user cost preference, and operational friction—not by hard-coded provider preference.

## Runtime classes

| Runtime | Manager | Specialist | Independent semantic review |
|---|---:|---:|---:|
| current chat | yes | bounded | no self-review |
| separate peer chat | no | no | yes |
| local Codex CLI | yes | yes | yes, separate invocation |
| local Claude Code | yes | yes | yes, separate invocation |
| provider API | optional | yes | yes |
| GitHub/service job | no | yes | yes with isolated worker |
| remote MCP worker | yes | yes | yes with isolated session |
| local model | optional | yes | yes with isolated invocation |
| human reviewer | no | no | yes |

## Selection

```text
classify task/gate
→ filter by capability
→ filter by permission/auth/connection
→ filter by independence requirement
→ filter by user usage/cost constraints
→ rank explicit preference, automation, isolation, friction, cost
```

Infrastructure failure may fall through to another eligible transport after checkpointing. A valid semantic rejection is not transport failure.

## Chat manager path

Current chat can remain manager even when it cannot spawn subprocesses. Before declaring `semantic_pending`, probe all eligible connected paths. If a separate peer chat is feasible but requires user relay, state is `awaiting_user`.

## Local agent path

Authenticated Codex/Claude CLI can run the full Harness without NovelForge requiring an additional provider API key. Mandatory review uses a separate invocation/session and blind bounded job.

## Long-running work

Require session ID, durable checkpoint, typed pending handoff/event, lease when queued, resume revalidation, and consume-once result handling.

## Changed artifact

Material change to artifact/rubric/output contract creates a new semantic fingerprint and normally a fresh reviewer session. Retry of infrastructure against unchanged semantic payload can preserve the fingerprint.

## Cost preference

Cost preference can reorder eligible transports; it cannot weaken independence, fingerprint binding, context isolation, authority, or mandatory quality gates.

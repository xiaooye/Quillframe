# Runtime Routing · NovelForge 7.1

## Principle

Select execution backends by **proven capability evidence**, independence, permissions, availability, resumability, user cost preference, and operational friction—not by provider name or historical assumption.

Before routing tool/external work, load or create a typed host capability manifest using `../runtime_capabilities.py` and `RUNTIME_CAPABILITIES.en.md`.

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

The table describes possible runtime classes, not current availability. A current invocation must still prove/declare the capability it needs.

## Selection

```text
classify task/gate
→ derive required capabilities
→ resolve against typed host capability manifest
→ filter by permission/auth/connection
→ filter by independence requirement
→ filter by user interaction/model execution/usage constraints
→ rank explicit preference, automation, isolation, friction, cost
```

Undeclared capability is unavailable. A network primitive is not proof of Web/GitHub/provider authorization.

Infrastructure failure may fall through to another eligible transport after checkpointing and capability re-resolution. A valid semantic rejection is not transport failure.

## Chat manager path

Current chat can remain manager even when it cannot spawn subprocesses. Before declaring `semantic_pending`, re-resolve all required capabilities against actually connected/declared paths. If a separate peer chat is feasible but requires user relay, state is `awaiting_user`.

A capability from an earlier chat/session is not automatically carried forward.

## Local agent path

Authenticated Codex/Claude CLI can run the full Harness without NovelForge requiring an additional provider API key. PATH presence proves only the executable exists; supported authentication/model availability must be resolved by the local runtime when needed. Mandatory review uses a separate invocation/session and blind bounded job.

## Corpus / Research discovery

Corpus Scout emits capability requirements such as `web_search`, `github_search`, `user_files`, `file_library`, or `mcp_client`. `corpus/discovery_runtime.py` only dispatches channels whose requirements are satisfied by the current host manifest.

Discovery result provenance and rights/storage validation remain separate from capability resolution.

## Long-running work

Require session ID, durable checkpoint, typed pending handoff/event, lease when queued, resume revalidation, and consume-once result handling.

On resume, re-resolve pending tool/external capabilities because connections, permissions and cost constraints can change independently of session persistence.

## Changed artifact

Material change to artifact/rubric/output contract creates a new semantic fingerprint and normally a fresh reviewer session. Retry of infrastructure against unchanged semantic payload can preserve the fingerprint.

## Cost preference

Cost preference can reorder eligible transports; it cannot weaken capability evidence, independence, fingerprint binding, context isolation, authority, or mandatory quality gates.

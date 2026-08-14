# Harness Runtime Routing · v2

## Goal

Select execution backends by requirements instead of provider hard-coding.

Classify:
- manager vs bounded specialist vs independent semantic reviewer;
- interactive vs unattended;
- one-shot vs resumable;
- local subprocess/MCP availability;
- connected connector/job availability;
- filesystem/write needs;
- user cost/usage preference;
- human relay tolerance;
- isolation/blindness requirement.

Chat sessions remain first-class.

## Default profiles

| Runtime | Manager | Specialist | Independent semantic | Control Plane | Usage |
|---|---:|---:|---:|---|---|
| current ChatGPT chat | yes | bounded | no self-review | connector/relay | ordinary_chat |
| separate peer chat | no | no | yes | relay | ordinary_chat |
| local Codex CLI | yes | yes | separate invocation | stdio MCP/CLI | codex_agentic |
| local Claude Code | yes | yes | separate invocation | stdio MCP/CLI | claude_plan |
| direct provider API | no | bounded | yes | result/event adapter | api_metered |
| GitHub Actions | no | bounded | yes when provider exists | dispatch/issue | varies |
| remote MCP worker | yes | yes | isolated session | Streamable HTTP | varies |
| local model | optional | yes | isolated invocation | adapter | local_model |
| human reviewer | no | no | yes | relay | human |

Capability does not imply independence from oneself. Independence is per invocation/session boundary.

## Selection algorithm

```text
requirements = classify(task, gate, permissions, cost, automation, isolation)

eligible = registry
  .filter(capability)
  .filter(permission)
  .filter(connection/auth availability)
  .filter(independence when required)
  .filter(user cost/usage constraints)

rank by:
  1. explicit user preference
  2. required automation/session capability
  3. isolation strength
  4. already-authenticated/connected availability
  5. operational friction
  6. cost hint
```

Infrastructure failure may fall through to the next eligible transport after checkpointing.

A completed `semantic_reject` is not infrastructure failure. Repair the owning layer; do not model-shop until something passes.

## Interactive ChatGPT production

1. current chat = manager session;
2. internal creative/simulation roles remain bounded unless true isolation is required;
3. mandatory independent gate probes connected/available runtimes;
4. accessible external worker/connector may run automatically;
5. otherwise peer-chat/human relay → `awaiting_user`;
6. only after all eligible paths fail/unavailable → `semantic_pending`.

No local subprocess in the current chat does not by itself mean the Harness is pending.

## Fully local Codex / Claude

1. local CLI = manager session;
2. attach project/policy checkout explicitly;
3. create/persist OS session through Control Plane;
4. use bounded child workers where useful;
5. mandatory reviewer = separate child invocation/session with blind fingerprint-bound input;
6. checkpoint/lease/result state survives process interruption.

No separate provider API key is required by Novel OS when the chosen local CLI is already authenticated through its supported login mechanism.

## Cost preferences

Avoid separately billed API usage:
1. authenticated local CLI if acceptable;
2. peer chat;
3. human/local model;
4. pending if none.

Preserve Codex usage:
1. Claude/local non-Codex runtime if available;
2. peer chat;
3. separately billed provider only if acceptable;
4. Codex last.

Maximum automation:
1. authenticated local worker;
2. direct provider/service;
3. GitHub/service job;
4. peer/human only if relay acceptable.

## Long-running work

Require:
- OS session ID;
- durable session snapshot;
- checkpoint before wait;
- typed pending handoff/event;
- bounded worker lease if queued;
- resume with live authority/fingerprint revalidation;
- exactly-once logical result consumption.

## Changed draft audit

Changed artifact/rubric/output contract → new fingerprint → normally new reviewer session. Reuse a reviewer session only for transport recovery against the exact same fingerprint.

## Cross-runtime handoff

Use `novel_os_handoff_v1`. Never send a whole manager conversation merely because the destination supports chat history.

Carry only source/target identity, bounded artifact refs/fingerprints, context policy, permission scope, return contract and relay/native references.

## Event transports

Provider webhook, GitHub `repository_dispatch`, Claude hook, MCP call or chat relay is a **transport**. Normalize durable events into `novel_os_event_v1` when they enter the Control Plane.

Transport events never grant Canon or behavior-promotion authority.

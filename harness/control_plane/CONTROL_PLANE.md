# Novel Production OS v6.6 · Runtime Control Plane

## Purpose

The Control Plane is the durable operational substrate under the session-native Harness.

It answers:

> How do ChatGPT chats, local Codex/Claude sessions, provider workers, GitHub jobs and human relays share execution state, hand off work, wait, resume and consume results without inventing authority or repeating side effects?

```text
project/resource
→ session
→ run
→ checkpoint
→ typed event / bounded handoff
→ lease / worker attempt
→ result
→ exactly-once logical consumption
→ resume
```

The Control Plane stores **where work is**. It does not decide story truth.

## Authority boundary

Control-plane data is operational evidence only.

It may persist:
- session snapshots and versions;
- event receipts;
- handoff envelopes;
- worker lease/attempt state;
- returned result payloads/hashes;
- exactly-once consumption receipts.

It may not by itself:
- create Accepted Canon;
- SETTLE a chapter;
- promote Generic OS behavior;
- overwrite durable user taste;
- authorize story-direction changes;
- convert a semantic judgment into Canon.

A webhook, connector, scheduler, MCP call or GitHub event never raises authority.

## Durable store

Reference implementation: `control_plane.py`.

Default backend: stdlib SQLite.

Default local DB: `.novel-os/runtime.db` (must remain uncommitted).

Required storage semantics:
- transactional writes;
- optimistic session version checks where requested;
- event idempotency keys;
- atomic handoff claims;
- bounded worker leases;
- lease expiry permits safe re-claim;
- result payload hashes;
- exactly-once **logical consumption** receipts.

Exactly-once here means downstream consumers record whether the logical result was already applied. It does not pretend distributed delivery itself is magically exactly once.

## Event ingress

Canonical schema: `event_schema.json` / `novel_os_event_v1`.

Allowed v1 external event classes:
- `session.resume_requested`
- `semantic.requested`
- `semantic.result_received`
- `eval.requested`
- `maintenance.requested`
- `research.refresh_requested`
- `feedback.observed`
- `artifact.acceptance_observed`

Notably absent:
- unattended `draft.requested`;
- `settlement.apply`;
- `canon.write`;
- `os.promote`.

Those operations require normal Harness/user authority and cannot be smuggled in through an event transport.

Every event carries:
- `event_id`;
- `event_type`;
- source/provenance;
- `resource_id`;
- optional session/run/handoff binding;
- authority scope (`observation|request|result`);
- idempotency key;
- relevant artifact fingerprints;
- timestamp + bounded payload.

Duplicate delivery with the same idempotency key and exact payload is safe. Reuse of the same key for a different payload is a hard conflict.

## Handoff queue

Canonical schema: `handoff_schema.json` / `novel_os_handoff_v1`.

A handoff is not a copied conversation. It contains only:
- source session;
- target session class;
- resource/task identity;
- artifact refs/fingerprints;
- bounded instructions reference;
- context policy;
- least-privilege permissions;
- return contract;
- optional relay nonce.

Control-plane handoffs forcibly reject `canon_write`, `os_behavior_write` or `durable_user_taste_write` permissions. Higher-authority writes stay in the Harness/Settlement path.

## Lease / worker semantics

Workers claim work through a bounded lease.

Rules:
1. claim is atomic;
2. only one live lease owner may complete the handoff;
3. expired lease may be reclaimed;
4. expired prior worker cannot complete after losing ownership;
5. attempts are tracked;
6. infrastructure retry does not change semantic fingerprint;
7. semantic rejection remains a valid result, not a reason to shop reviewers.

## Result consumption

Completion and consumption are separate operations.

```text
worker completes handoff
→ result stored + hashed
→ manager validates authority/fingerprint/domain contract
→ named gate/consumer consumes result
→ consumption receipt stored
```

If the same result is delivered again, the consumer sees `already_consumed=true` and must not repeat downstream side effects.

If the same logical source/consumer key arrives with a different payload hash, stop as a conflict.

## MCP

Reference local adapter: `mcp_stdio.py`.

The initial supported transport is stdio, following MCP protocol revision `2025-06-18`:
- JSON-RPC 2.0;
- newline-delimited messages;
- initialization before normal operation;
- `tools/list` + `tools/call`;
- structured tool output.

MCP exposes operational tools only. No Canon/SETTLE/write-authority tool is exposed by default.

A future remote deployment should prefer **Streamable HTTP**, with Origin validation, localhost-only binding for local servers, authentication, protocol/session headers, and normal MCP security requirements. Do not add a legacy SSE-only server for new deployments.

## ChatGPT / connector path

Current ChatGPT sessions may not be able to spawn a local stdio subprocess. They remain first-class manager sessions and can reach the same logical Control Plane through eligible connected transports (for example GitHub event/issue bridge or future hosted/remote MCP connector).

Lack of a local subprocess does not invalidate chat-session support.

## Codex / Claude local path

Local Codex/Claude can use:
- CLI operations from `control_plane.py`;
- stdio MCP through `mcp_stdio.py`;
- their own provider-native session IDs as metadata;
- separate child invocation/session for independent semantic review.

A local agent running the full Harness should point to an explicit project checkout/source. Generic OS and project Canon must remain separate authorities.

## GitHub / webhook path

GitHub Actions should use:
- reusable workflows via `workflow_call` for shared deterministic logic;
- `repository_dispatch` as an optional external event ingress;
- typed event validation before any action;
- least-privilege workflow permissions;
- no automatic Canon/SETTLE/behavior promotion.

A generic public HTTP webhook daemon is intentionally not part of v1. Provider/webhook adapters should normalize their payload into `novel_os_event_v1` first.

## Claude hooks

Recommended deterministic hook uses:
- `SessionStart` → attach/refresh session bootstrap;
- `PostToolUse` for Edit/Write → record operational change/checkpoint candidate;
- `Stop` → block only when a deterministic mandatory Harness condition is unresolved;
- `SessionEnd` → flush trace/runtime state.

Do not use prompt/agent hooks as a shortcut for mandatory independent semantic judgment.

## CI contract

Normal CI must validate without paid/model execution:
- SQLite store self-test;
- event idempotency conflict handling;
- handoff authority guard;
- lease claim/completion behavior;
- exactly-once consumption;
- MCP initialize/list/call contract;
- migration/bootstrap authority consistency.

## Design principle

> Persist execution state aggressively; grant authority conservatively.

> Events can wake the Harness. They cannot decide what is Canon.

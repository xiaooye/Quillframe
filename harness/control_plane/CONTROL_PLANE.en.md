# Runtime Control Plane · v7

## Purpose

The Control Plane is NovelForge's durable operational substrate for sessions, events, handoffs, worker leases, result hashes, and logical consume-once receipts.

It answers **where work is and who currently owns a queued attempt**. It does not decide story truth.

```text
project/resource
→ session/run/checkpoint
→ typed event / bounded handoff
→ lease / worker attempt
→ result
→ validation
→ consume-once receipt
→ resume
```

## Authority boundary

Control-plane data is operational evidence only. It cannot by itself:
- create Accepted Canon;
- settle a project state mutation;
- promote framework behavior;
- overwrite durable user taste;
- authorize story direction.

Webhook, MCP, CI, schedule, connector, and queue arrival never raise authority.

## Durable semantics

Reference backend: stdlib SQLite.

Required properties:
- transactional writes;
- optimistic session versions where requested;
- event idempotency keys;
- atomic handoff claims;
- bounded leases and expiry recovery;
- result payload hashes;
- exactly-once **logical consumption** receipts.

Exactly-once refers to downstream application bookkeeping, not magical exactly-once network delivery.

## Typed events

Allowed event classes are deliberately narrow: resume requests, semantic requests/results, eval requests, maintenance requests, research refresh, feedback observations, and acceptance observations.

Unattended Canon write / settlement apply / automatic next-chapter drafting / framework promotion are not generic event types.

Duplicate delivery with the same idempotency key and same payload is safe. Same key with different payload is a hard conflict.

## Handoffs

A handoff contains bounded identity/context:
- source session;
- target worker/session class;
- resource/task identity;
- artifact refs/fingerprints;
- bounded instructions;
- context policy;
- permissions;
- return contract;
- optional native/relay references.

It must not copy the entire manager conversation by default.

High-authority permissions such as Canon/framework-promotion/durable-taste write remain false in generic worker handoffs.

## Leases

Workers atomically claim work for a bounded lease. Only the active lease owner may complete it. Expired work can be reclaimed; the expired worker cannot later overwrite the new owner.

## Result consumption

Completion and application are separate:

```text
worker completes
→ result stored + hashed
→ manager/gate validates binding
→ named consumer records receipt
→ downstream side effect occurs once
```

A duplicate identical result returns already-consumed; a conflicting hash for the same logical source/consumer is a hard stop.

## MCP

Local reference transport is stdio MCP. Future remote services use Streamable HTTP with normal authentication/origin/session protections.

Control-plane MCP tools expose operational capabilities, not unconditional Canon-write tools.

## Chat / local / CI

- Chat sessions can participate through connected/relay transports.
- Local Codex/Claude can use CLI or stdio MCP.
- GitHub/service jobs can normalize external events into the same event/handoff contracts.
- Normal CI validates infrastructure without invoking paid models.

> Persist execution state aggressively; grant authority conservatively.

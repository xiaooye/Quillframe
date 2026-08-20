# Runtime & Integrations

Quillframe 1.0 separates runtime identity, capability, and authority. A provider name does not prove a capability, and a capability never grants story or write authority.

## One launch path

The author-facing entry is:

```bash
quillframe launch [PROJECT]
```

Local mode binds the Studio to a loopback Python Core and project-local SQLite. Cloud mode starts an explicit authentication flow and does not upload a project as a side effect of launch. Repository hooks and host-specific bootstrap commands are not part of product correctness.

## Identity

`project` identifies the work, `session` identifies a durable execution relationship, `run` identifies one bounded attempt, and `checkpoint` identifies an exact recoverable snapshot. Provider history is neither Canon nor Project bootstrap authority.

## Host boundary

Claude Code, Codex, another agent host, or a model API may execute an eligible task. The host runs the agent; Quillframe governs the novel. Hosts provide capability evidence and transport. Core owns workflow state, permissions, fingerprints, budgets, persistence, and typed validation. The Project owns Canon.

## Exact protocols

- Host Bridge version `11` is the only accepted bridge version.
- MCP protocol `2026-07-28` is matched exactly; there is no negotiation or fallback.
- Context assembly accepts only its declared current schema.
- Independent review uses one `independence_receipt` field bound to the frozen candidate fingerprint.

Pre-1.0 requests are rejected rather than translated.

## Resume and cancellation

Resume revalidates the exact checkpoint, Project authority, artifact fingerprints, pending approvals, capabilities, and consume-once state. Run events are cursor-based. Pause, resume, and cancellation occur only at Core safe points.

## Independent semantic execution

Eligible transports include a separate local agent invocation, provider call, MCP worker, GitHub job, peer chat, local model, or human review when current capability evidence supports the route. A transport failure may produce an explicit fallback receipt. A valid semantic rejection routes repair and cannot trigger reviewer shopping.

## Secrets

Credentials remain outside semantic context and Project state. Local credentials use a process lease; Hosted Studio uses the encrypted SessionVault. Receipts and logs contain references and capability evidence, never secret values.

## Control Plane

The Control Plane persists event, handoff, result, and metadata-only receipt lifecycles. It can prove dispatch, validation, consumption, and replay state. It cannot turn operational state or model output into Canon, acceptance, settlement, or publication authority.

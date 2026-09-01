# Runtime & Integrations

Quillframe 1.0 separates runtime identity, capability, and authority. A provider name does not prove a capability, and a capability never grants story or write authority.

## One launch path

The author-facing entry is:

```bash
quillframe launch [PROJECT]
```

Local mode binds the Studio directly to the Rust Core and project-local SQLite. The optional Rust host may expose the same Bridge on loopback for a browser surface. Cloud mode starts an explicit authentication flow and does not upload a project as a side effect of launch. Repository hooks and host-specific bootstrap commands are not part of product correctness.

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

## Local GPT execution for production stages

The opt-in [Codex CLI relay](../harness/integrations/codex_cli_relay.py) consumes the loopback manager queue. It starts a fresh CLI process in a temporary workspace for each request, using an explicitly selected model and no resumed conversation. Authentication stays with the installed CLI. This uses the documented [non-interactive execution interface](https://learn.chatgpt.com/docs/non-interactive-mode); it is not part of ordinary CI.

Select a model whose installed catalog does not force Code Mode. The relay disables Code Mode and its host; catalog-level tool mode takes precedence over feature flags. A model requiring that disabled host will be rejected rather than silently enabling execution or rewriting its metadata. The current local continuation selects GPT-5.5 after checking its installed catalog entry. Only the known experimental-feature notice is suppressed; startup errors remain fatal, with item types and message hashes retained without message text.

An append-only ledger charges an attempt before launch, including failed launches, and carries the total across Core runs. A successful response requires a real CLI thread event, one completed turn, and an exact match between the final message and the saved output. Tool, error, unknown or inconsistent events stop publication of the response. Output bytes are preserved; reasoning text is not kept in evidence logs. No automatic CLI restart or failed-request replay occurs. Provider-internal retries that the CLI does not expose are not claimed as measured model calls.

The default `--round-limit 64` permits at most 63 manager attempts, reserving an invocation for independent review. A higher authorized cap must be explicit: for example, `--round-limit 96 --manager-limit 95`; raising only `--manager-limit` cannot bypass the default. These flags express the operator's authorized budget, not proof of human approval. `--expected-used` verifies existing manager-ledger usage and never resets it. Independent reviewer attempts recorded outside this queue must also be counted by the orchestrator and deducted from the available manager limit while preserving the next required review. The cumulative experiment cap is separate from Core's per-run call budget.

These records describe `codex_cli` manager transport, not native subagent independence or operating-system isolation. Production review still requires its separate frozen packet, eligible independent reviewer and Core-validated receipt. Neither the relay nor a passing review authorizes chapter acceptance or settlement.

## Secrets

Credentials remain outside semantic context and Project state. Local credentials use a process lease; Hosted Studio uses the encrypted SessionVault. Receipts and logs contain references and capability evidence, never secret values.

## Control Plane

The Control Plane persists event, handoff, result, and metadata-only receipt lifecycles. It can prove dispatch, validation, consumption, and replay state. It cannot turn operational state or model output into Canon, acceptance, settlement, or publication authority.

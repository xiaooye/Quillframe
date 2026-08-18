# Semantic Execution Runtime · Preserve one semantic contract across chat, local agents, APIs, MCP, services, and humans

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>TRANSPORT-NEUTRAL</kbd>&nbsp;&nbsp;<kbd>PROVENANCE</kbd>&nbsp;&nbsp;<kbd>VALIDATE BEFORE CONSUME</kbd></p>

The Semantic Execution Runtime is the transport layer between a frozen semantic job and an eligible model/human invocation. It exists so Quillframe can change **how** judgment executes without changing **what judgment was requested**.

> **Core invariant ✦** Transport may change. Semantic identity, bounded input, rubric, output contract, permissions, and fingerprint do not silently change with it.

## 01 · Input contract

Execution begins with a semantic job that has already been built and validated by the generic semantic boundary.

The executor receives:

- job/contract identity;
- exact semantic fingerprint;
- bounded input/context;
- rubric;
- output contract;
- permissions;
- execution constraints such as required independence;
- source/session provenance references.

The executor must not add hidden project context simply because it has access to it.

## 02 · Eligible execution families

A semantic job may execute through:

- a separate chat / peer relay;
- local Codex / Claude / other agent invocation;
- provider API;
- local model endpoint;
- MCP / Control Plane worker;
- GitHub / service job;
- human reviewer.

Eligibility is resolved from current capability evidence and the job's constraints.

The same semantic contract should remain recognizable regardless of transport.

## 03 · Direct versus relayed execution

### Direct execution

A runtime may directly invoke a model/human endpoint and receive the typed result within the same orchestration path.

### Relayed execution

A manager may package a semantic packet for another chat, human, or external system and later receive the typed result back.

Relayed work requires durable identity because the manager cannot rely on conversational continuity to prove which frozen job the result belongs to.

## 04 · Independent-gate execution

When `independent_gate=true` or the owning workflow separately requires independence, execution must prove a separate invocation/session/worker identity.

The executor cannot satisfy the requirement by:

- changing system prompt inside the same manager invocation;
- asking the same hidden reasoning process to “act as critic”;
- copying the manager's entire private context to the reviewer;
- omitting execution provenance.

The same provider/model family may still be valid if the invocation/session is genuinely separate and the packet is bounded/blind.

## 05 · Execution provenance

A result should preserve truthful execution metadata such as:

```yaml
source_session_id:
worker_session_id:
handoff_id:
attempt_id:
provider:
model:
transport:
```

Exact fields depend on the runtime. Provenance should be sufficient to validate required isolation/independence without exposing credentials or private reasoning.

## 06 · Typed-output boundary

The executor asks for the contract's output shape, not arbitrary prose.

A model may internally reason in whatever way its provider/runtime supports, but the persisted result is the typed contract plus concise observable evidence required by that contract.

Do not request or persist private chain-of-thought.

If a model returns prose around JSON, the adapter may normalize only when it can do so deterministically without changing semantic meaning. Otherwise the result is invalid and must be retried/repaired as an execution issue.

## 07 · Binding validation

Before the owning workflow sees the result as valid, deterministic validation checks:

- result schema/output contract;
- exact job/subject identity;
- exact semantic fingerprint;
- required worker/session/attempt provenance;
- permission/result-scope boundary;
- required evidence fields;
- forbidden leakage where applicable.

A high-quality answer to the wrong fingerprint is still invalid.

## 08 · Control Plane integration

For distributed/long-running execution:

```text
manager checkpoint
→ semantic handoff stored
→ eligible worker claims lease
→ worker executes frozen job
→ result + hash stored
→ manager validates semantic binding
→ named gate consumes once
→ workflow resumes
```

Lease/retry/idempotency are infrastructure concerns. They must not alter the semantic verdict.

## 09 · Transport fallback

Fallback is allowed when infrastructure fails and the frozen semantic question has not changed.

```text
adapter unavailable / crash / timeout / expired lease
→ preserve semantic fingerprint
→ re-resolve eligible transport
→ execute same frozen job elsewhere
```

Do not preserve the old fingerprint if bounded input, rubric, candidate, or output contract changes.

## 10 · Semantic rejection is not fallback

A valid typed reject/fail from an eligible worker is a successful semantic execution.

It should be consumed by the owning gate and routed to repair.

Do not classify “the reviewer disliked the artifact” as provider failure and reroute until a different reviewer says PASS.

## 11 · Human / peer-chat execution

Human and peer-chat reviewers use the same conceptual contract:

- receive the frozen subject and bounded context;
- receive the rubric/output format;
- do not receive hidden expected verdict/gold material;
- return the typed result with the required identity/fingerprint;
- preserve enough provenance to prove the separate reviewer identity.

If the user manually relays the packet, the manager may remain `awaiting_user` until the typed result returns.

## 12 · Provider adapter rule

Provider-specific adapters should remain thin. They may translate generic semantic job fields into provider request syntax and normalize provider response metadata.

They must not:

- invent a different rubric;
- broaden context silently;
- grant extra permissions;
- alter the fingerprint meaning;
- treat provider confidence as authority;
- hide which model/runtime actually executed the judgment.

## 13 · Failure taxonomy

### `execution_unavailable`
No current route satisfies the job's capability/independence constraints.

### `execution_failed`
An eligible transport crashed, timed out, or failed before producing a valid result.

### `semantic_invalid`
A returned result fails schema/fingerprint/provenance/leakage validation.

### valid semantic outcome
A typed PASS/FAIL/REJECT/diagnosis/etc. that satisfies the contract.

Only the first three justify infrastructure retry/fallback. A valid negative outcome routes semantic repair.

## 14 · Invariants

1. Transport neutrality preserves semantic identity.
2. Execution does not broaden context or permission silently.
3. Independent gates prove separate execution identity.
4. Provider adapters remain thin.
5. Result binding is deterministic before workflow consumption.
6. Infrastructure fallback preserves the same fingerprint only when the semantic question is unchanged.
7. Valid rejection is not provider failure.
8. Private chain-of-thought is not part of the durable contract.

## 15 · Related contracts

- [Semantic Worker Protocol](SEMANTIC_WORKER_PROTOCOL.en.md) — semantic job/result identity and permissions.
- [Runtime Routing](../session_runtime/RUNTIME_ROUTING.en.md) — eligible route selection.
- [Runtime Capabilities](../session_runtime/RUNTIME_CAPABILITIES.en.md) — capability evidence.
- [Control Plane](../control_plane/CONTROL_PLANE.en.md) — handoff/lease/result persistence.
- [`semantic_worker_runner.py`](semantic_worker_runner.py) — deterministic execution/adapter boundary.

# Specification — Quillframe Model Runtime and Quillframe-owned Agent Loop

Status: implementing  
Primary task mode: `SYSTEM-IMPROVE`  
Baseline: Quillframe 0.9 reconstruction PR #106 head `00422d5dd1787727953a15a03ddc14bbb9996132`  
Target: `0.9.x`

## Goal

Quillframe is the agent runtime. A user connects model inference with exactly two inputs:

```text
API Endpoint
Access Token
```

Provider, protocol, auth strategy, model profile and capability checkboxes are not onboarding inputs. Quillframe Core owns endpoint normalization, authentication attempts, API/model discovery, bounded capability evidence, model eligibility/selection, inference, the tool loop, session/run/checkpoint identity, permission, authority, budgets, provenance and failure truth.

The product mental model is `User → Quillframe → Model API`. Vendor identity is diagnostic metadata at most, never runtime authority.

## Current gap

Quillframe 0.9 already has Harness, sessions/runs/checkpoints, capability routing, Control Plane, Semantic Workers, SQLite and a typed Host Bridge. Direct model execution, however, still centers on Codex/Claude CLI and an OpenAI Responses semantic adapter. Global SQLite also still models `provider_configuration → model_registry`.

Semantic Runtime already correctly owns fingerprints, rubrics, blindness, typed results and independence. General coding/agent jobs must not be forced into fiction semantic contracts.

## Ownership

**Model Runtime** owns endpoint/network policy, secret-reference resolution, model discovery, protocol codecs, capability evidence, request/response/tool-call normalization and exact model execution provenance. It does not own agent authority, tool permission, Canon/Settlement/Framework-write authority or project semantic truth.

**Agent Runtime** owns the bounded Quillframe model→tool→model loop, budgets, cancellation, tool receipts and general AgentJob/AgentResult contracts.

**Semantic Runtime** keeps semantic fingerprints, rubrics, output contracts, blind context, independence and semantic-reject semantics. It may reuse Model Runtime as inference transport but is not replaced by Agent Runtime.

**Tool Runtime** validates registration, schema, grants, authority, scope, budget, before-state and idempotency before executing any tool call.

## Protocol families

v1 supports `openai_chat_completions`, `openai_responses`, and `anthropic_messages`. These are wire codecs, not providers. Different models behind one endpoint may resolve to different protocol families.

OpenCode Go is a mixed-protocol compatibility fixture; Ollama, LM Studio and vLLM are compatibility evidence, not generic architecture entities.

## Discovery and capabilities

Model listing proves only model discovery. Capability state is `verified | detected | manually_configured | unavailable | unknown`, with provenance, timestamp, service/model/protocol binding. Provider/model names never prove capability.

Live harmless inference probes are bounded runtime behavior. Normal CI uses mock HTTP fixtures only and never silently spends model usage.

## Secrets and network

Access tokens exist only in host secret storage or transient transport. Durable state stores credential references only. Secrets are forbidden from prompts, context, AgentJob/SemanticJob, checkpoints, events, receipts, fingerprints, diagnostics and ordinary logs.

Remote endpoints require HTTPS by default; URL userinfo/query/fragment are rejected. Loopback is supported for local model servers. Private/link-local networking is denied unless host policy explicitly allows it.

## Persistence

An ordered migration replaces active `provider_configuration/model_registry` with `model_services`, `discovered_models`, and `model_capability_evidence`. SQLite stores endpoint/snapshot metadata and credential references, never token values.

## Compatibility

Codex CLI, Claude CLI, peer relay, MCP, GitHub jobs and human review remain eligible external runtime routes. Existing users are not forced to migrate to raw endpoints.

## Acceptance

- Model-service connection requires only endpoint + token at the Core boundary.
- One endpoint can expose multiple models with per-model protocol/capability evidence.
- Quillframe executes model→tool→model continuation without a third-party coding-agent runtime.
- Tool grants/authority/before-state/idempotency are enforced.
- Secrets never enter serializable runtime artifacts.
- Normal CI uses deterministic mock transports.
- Mixed-protocol, generic OpenAI-compatible and local-endpoint fixtures pass.
- Semantic fingerprint/independence/consume-once semantics remain intact.

# Quillframe Model Runtime

Hosts run the generic agent loop; Quillframe governs the novel contract. The embedded Model/Agent Runtime is an optional/reference implementation for Studio and local adapters. External model services provide inference only and never receive story, Canon, or Settlement authority.

## Two setup inputs

The ordinary product surface connects a model service with exactly:

```text
API Endpoint
Access Token
```

Provider, protocol, auth strategy, model profile and capability checkboxes are not onboarding inputs. Vendor identity is diagnostic metadata at most.

## Connection flow

```text
endpoint normalization / network policy
→ transient credential resolution
→ model discovery
→ per-model protocol discovery
→ bounded capability evidence
→ automatic eligibility / model selection
→ inference
```

Current wire protocol families are OpenAI Chat Completions, OpenAI Responses and Anthropic Messages. Protocol is a wire codec, not provider identity; different models behind one endpoint may bind to different protocols.

An endpoint may be a host root or may end in an explicit API version segment such as `v1`, `v4`, or `v4.1`. Core adds the default `v1` only when the final segment is not already versioned; otherwise it preserves that base before appending `models`, `chat/completions`, `responses`, or `messages`.

Model listing proves model discovery only. It does not prove tools, vision, structured output or context window. Capability evidence retains state, provenance, timestamp and service/model/protocol binding. Model/vendor names never prove capability.

## Secrets

Access-token values exist only in host secret storage or the current HTTP transport. SQLite, snapshots, prompts, Context, AgentJob, SemanticJob, checkpoints, receipts, fingerprints and ordinary diagnostics never contain the resolved token.

Durable Model Services store a credential reference only. After Core restart, Quillframe can hydrate fingerprint-bound endpoint/model metadata; the credential is resolved just-in-time when inference is actually required.

## Network policy

Remote endpoints require HTTPS by default. URL userinfo/query/fragment are rejected. The direct transport refuses redirects and checks resolved addresses before requests; private/link-local/reserved destinations require explicit host policy. Loopback remains available for local model servers.

## Request deadlines

Ordinary inference defaults to a 180-second request timeout. An explicit finite value may be set up to 86,400 seconds; that larger bound is an admission and single-HTTP-interaction safety envelope, not the lifetime of an already launched durable worker. Transport preparation consumes the same allowance, so an expired request cannot begin a new dispatch.

Only POST requests to a literal loopback address or `localhost` carry `X-Quillframe-Deadline-Unix-Ms`. A production AgentJob also carries a SHA-256 `X-Quillframe-Model-Request-Key`. Remote-provider headers and model message/body semantics remain unchanged.

The v3 local relay freezes one immutable keyed packet and waits only briefly for an interactive response. If the exact worker is still running it returns `202 model_pending`; repeating the identical request polls that packet instead of dispatching again. A changed body with the same key is an idempotency conflict. The production journal marks the request pollable before transport dispatch, so a client crash before the first `202` cannot authorize a second call.

The initial packet deadline still bounds parsing, queue preparation, and pre-launch admission. After a keyed worker has launch evidence, API slowness does not impose an arbitrary process timeout: the CLI entry point defaults to no worker lifetime limit, publishes heartbeats, and records an explicit terminal state. Operators may set a finite emergency worker limit. Ordinary unkeyed/library calls retain bounded behavior.

An ended HTTP waiter is not a model failure and polling does not consume another model call. Exact terminal output may be consumed after the original waiter horizon. Confirmed cancellation, terminal worker failure, changed identity/bytes, invalid output, or semantic rejection remains blocking. A missing or stale heartbeat is unknown state and never permission to retry. See the [durable pending contract](../specs/032-durable-model-pending/spec.en.md); specification 027 remains historical for v2 synchronous packets.

## Persistence

Global SQLite owns `model_services`, `discovered_models` and `model_capability_evidence` through the native 1.0 schema fragment at `persistence/schema/global/002_model_runtime.sql`. Pre-1.0 databases are rejected; there is no migration or fallback read path.

## Deterministic CI and live probes

Normal CI uses a local mock HTTP provider and never executes a live model. Live compatibility is explicit opt-in through Host Bridge v11: register the endpoint with `model.service.add`, store the credential through the OS secret store, then call `model.service.test`. The Rust Core records the exact endpoint, protocol, model catalog and result receipt.

A successful live probe is timestamped endpoint/model-bound evidence, not permanent capability truth.

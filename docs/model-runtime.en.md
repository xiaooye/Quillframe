# Quillframe Model Runtime

Quillframe owns the agent runtime; external model services perform inference only.

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

Model listing proves model discovery only. It does not prove tools, vision, structured output or context window. Capability evidence retains state, provenance, timestamp and service/model/protocol binding. Model/vendor names never prove capability.

## Secrets

Access-token values exist only in host secret storage or the current HTTP transport. SQLite, snapshots, prompts, Context, AgentJob, SemanticJob, checkpoints, receipts, fingerprints and ordinary diagnostics never contain the resolved token.

Durable Model Services store a credential reference only. After Core restart, Quillframe can hydrate fingerprint-bound endpoint/model metadata; the credential is resolved just-in-time when inference is actually required.

## Network policy

Remote endpoints require HTTPS by default. URL userinfo/query/fragment are rejected. The direct transport refuses redirects and checks resolved addresses before requests; private/link-local/reserved destinations require explicit host policy. Loopback remains available for local model servers.

## Persistence

Global SQLite owns `model_services`, `discovered_models` and `model_capability_evidence`. Migration `002_model_runtime.sql` performs a one-shot migration from the 0.9 initial provider-centric schema; it is not a permanent runtime fallback.

## Deterministic CI and live probes

Normal CI uses `MockTransport` and never executes a live model. Live compatibility is explicit opt-in:

```bash
QUILLFRAME_LIVE_MODEL_TEST=1 \
QUILLFRAME_LIVE_MODEL_ENDPOINT=https://.../v1 \
QUILLFRAME_LIVE_MODEL_TOKEN=... \
python tests/live_model_runtime.py
```

A successful live probe is timestamped endpoint/model-bound evidence, not permanent capability truth.

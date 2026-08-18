# Implementation Plan — Quillframe Model Runtime

## Phase 1 — Kernel

Create `model_runtime/` for endpoint/security, secret references, protocol codecs, transport, model discovery, capability evidence and invocation. Create `agent_runtime/` for AgentJob/Result, ToolRuntime, RepositoryToolset and the bounded AgentRunner. Cover all protocol families and a full tool loop with deterministic tests.

## Phase 2 — Persistence and routing

Add `002_model_runtime.sql`; add model-service/snapshot/evidence persistence APIs; replace active provider-name capabilities with `model_api/model_runtime`; register a generic direct-model route.

## Phase 3 — Semantic integration

Add a Model Runtime semantic executor while preserving the existing semantic fingerprint/rubric/output/independence boundary. Reduce the OpenAI Responses adapter to a compatibility wrapper and remove duplicated HTTP semantics when safe.

## Phase 4 — Core/Host surface

Expose model-service connect/list/get/refresh/delete/replace-secret and model/capability projections through operation-specific Core APIs. The UI session may bind the same operations through Host Bridge without ever receiving secret values. Automatic model selection remains default; exact-model selection is preference, never eligibility proof.

## Phase 5 — Coding-agent vertical slice

Ship read-only SYSTEM-IMPROVE planning with repo read/search first, then exact-before-state writes, then explicitly allowlisted subprocess capability.

## Verification

Normal CI uses unittest + mock transports and performs no real model/network usage. Live compatibility is explicit opt-in only. Obtain independent architecture/semantic review before acceptance; do not auto-merge.

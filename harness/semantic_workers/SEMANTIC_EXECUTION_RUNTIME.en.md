# Semantic Execution Runtime · v7

## Execution boundary

```text
validate job
→ checkpoint manager
→ select eligible independent runtime
→ direct execution | queued handoff | peer/human relay
→ receive typed result
→ validate fingerprint/provenance/lineage
→ consume once at semantic gate
→ resume owning workflow
```

The manager coordinates this boundary but never substitutes its own judgment for the independent worker.

## Eligible paths

Typical paths:
1. separate local Codex/Claude invocation;
2. configured provider adapter;
3. Control Plane/MCP worker;
4. GitHub/service job;
5. separate peer chat;
6. isolated local model;
7. human reviewer;
8. otherwise unresolved semantic state.

Runtime selection follows `../session_runtime/RUNTIME_ROUTING.*.md` and user usage/cost constraints.

## Direct runner

`semantic_worker_runner.py` resolves direct adapters. Lack of a direct adapter means **direct-layer unresolved**, not necessarily whole-Harness `semantic_pending`; higher-level MCP/GitHub/peer/human paths may still exist.

## Local agent adapter

`adapters/local_agent_adapter.py` launches a separate local agent process in an isolated temporary workspace and supplies only the bounded blind job.

The broader Harness may itself be running under the same CLI family, but mandatory review still requires a separate invocation/session identity.

## Provider adapter

Provider APIs are optional transports. They must return the same typed result contract and truthful model/provider provenance. API availability is not a framework requirement.

## Peer chat

`peer_chat_relay.py` packages the job with a relay nonce and fingerprint. The reviewer must be a genuinely separate conversation. A user-mediated relay produces `awaiting_user` while outstanding.

## Queued worker

Control Plane handoff flow:

```text
submit handoff
→ worker claims bounded lease
→ independent execution
→ complete handoff with result hash
→ manager validates semantic binding
→ gate records consume-once receipt
```

Lease expiry is infrastructure recovery, not semantic judgment.

## States

Operational/semantic states may include:
- `awaiting_user`
- `awaiting_external`
- `semantic_pending`
- `unsupported`
- `worker_failed`
- `semantic_invalid`
- `semantic_reject`
- `completed`

Only valid completed/rejected worker results are semantic outcomes.

## CI boundary

Normal CI may test job/result contracts, fingerprints, command construction, peer relay, lease/consume behavior, and provider dry-runs. It must not silently invoke paid or login-bound model inference.

# Semantic Execution Runtime · v0.5

## Boundary

```text
validated frozen job
→ checkpoint
→ runtime selection
→ independent reviewer session/invocation
→ direct execution OR queued handoff/relay
→ typed result
→ fingerprint/provenance/lineage validation
→ exactly-once gate consumption
```

Manager self-review is never independent.

## Eligible paths

1. separate local Codex/Claude invocation;
2. direct provider adapter;
3. Control Plane / MCP worker handoff;
4. GitHub Actions/service bridge;
5. separate ordinary peer chat;
6. isolated local model/human/other compliant runtime;
7. otherwise `semantic_pending`.

User usage/cost preferences may reorder eligible paths without weakening independence or binding.

## Direct runner

`semantic_worker_runner.py` resolves:
1. explicit adapter command;
2. configured `NOVEL_OS_SEMANTIC_WORKER_CMD`;
3. auto-detected local Codex/Claude;
4. optional OpenAI adapter if API credential exists;
5. direct-layer unresolved.

A direct-layer `semantic_pending` does not prove the whole Harness is blocked. Higher-level Control Plane, GitHub, peer-chat or human transports may remain eligible.

## Control Plane

For queued/service execution:
1. create `novel_os_handoff_v1` bound to source session/fingerprint;
2. checkpoint manager;
3. submit handoff;
4. worker atomically claims a bounded lease;
5. worker completes with typed result;
6. manager validates semantic binding/lineage;
7. named semantic gate records `consume_once` receipt;
8. manager resumes.

Lease expiry is infrastructure recovery, not semantic judgment.

## Local agents

`adapters/local_agent_adapter.py` launches a separate Codex or Claude process in an isolated temporary working directory. It receives only the bounded blind job and has no project/Canon write authority.

The same CLI may run the broader Harness manager elsewhere, but reviewer independence requires a separate invocation/session.

## Peer chat

`peer_chat_relay.py` packages a frozen job with relay nonce. The reviewer must be a genuinely separate conversation. The manager validates exact fingerprint + nonce/provenance before consumption.

Waiting state is `awaiting_user`, not PASS and not necessarily `semantic_pending`.

## GitHub/service transport

GitHub or remote service workers are infrastructure paths. They normalize request/result identity through the same job/result contract. Missing service credentials or unavailable worker means infrastructure fallback, not semantic PASS/FAIL.

## Result states

- `awaiting_user`
- `awaiting_external`
- `semantic_pending`
- `unsupported`
- `worker_failed`
- `semantic_invalid`
- `semantic_reject`
- `completed`

Only `semantic_reject` and `completed` are semantic outcomes.

## CI

Normal CI may validate schemas, routing, fingerprints, local command construction, peer relay, Control Plane lease/consumption and adapter dry-runs. It must not silently invoke paid/login-bound models.

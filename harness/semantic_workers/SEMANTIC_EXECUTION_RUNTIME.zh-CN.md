# Semantic Execution Runtime · v7 中文版

## Execution Boundary

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

Manager 协调边界，但永远不能用自己的判断替代 independent worker。

## Eligible Paths

常见路径：
1. separate local Codex/Claude invocation；
2. configured provider adapter；
3. Control Plane/MCP worker；
4. GitHub/service job；
5. separate peer chat；
6. isolated local model；
7. human reviewer；
8. 否则进入 unresolved semantic state。

Runtime selection 服从 `../session_runtime/RUNTIME_ROUTING.*.md` 和用户 usage/cost constraints。

## Direct Runner

`semantic_worker_runner.py` 负责 direct adapter。Direct adapter 不存在只说明 **direct layer unresolved**，不等于整个 Harness 必然 `semantic_pending`；MCP/GitHub/peer/human 等高层路径仍可能可用。

## Local Agent Adapter

`adapters/local_agent_adapter.py` 在 isolated temporary workspace 中启动 separate local agent process，只传 bounded blind job。

即使整个 Harness 也运行在同一种 CLI，mandatory review 仍需要 separate invocation/session identity。

## Provider Adapter

Provider API 只是 optional transport。它必须返回相同 typed result contract，并提供 truthful model/provider provenance。API availability 不是 framework requirement。

## Peer Chat

`peer_chat_relay.py` 用 relay nonce + fingerprint 打包 job。Reviewer 必须是真正独立 conversation。需要用户 relay 时，outstanding 状态为 `awaiting_user`。

## Queued Worker

Control Plane handoff：

```text
submit handoff
→ worker claims bounded lease
→ independent execution
→ complete handoff with result hash
→ manager validates semantic binding
→ gate records consume-once receipt
```

Lease expiry 是 infrastructure recovery，不是 semantic judgment。

## States

可出现：
- `awaiting_user`
- `awaiting_external`
- `semantic_pending`
- `unsupported`
- `worker_failed`
- `semantic_invalid`
- `semantic_reject`
- `completed`

只有有效 completed/rejected worker result 才是 semantic outcome。

## CI Boundary

Normal CI 可以测试 job/result contract、fingerprint、command construction、peer relay、lease/consume behavior 和 provider dry-run；不得静默调用付费或 login-bound 模型 inference。

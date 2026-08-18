# Runtime Routing · 根据证据选择执行路径，不根据 provider 传说做假设

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>ELIGIBILITY</kbd>&nbsp;&nbsp;<kbd>INDEPENDENCE</kbd>&nbsp;&nbsp;<kbd>成本感知</kbd></p>

Runtime Routing 在 capability evidence 已经解析以后，决定**某一小块工作应该在哪里执行**。它按 permission、independence、availability、resumability、user interaction、cost preference 与 operational friction 对 eligible path 排序，而不是按 provider 品牌选择。

> **边界 ✦** Routing 可以选择 transport，但不能削弱原本让这项工作具备资格的 semantic、authority、fingerprint 或 context-isolation contract。

## 01 · Routing 从 capability resolution 之后开始

标准序列：

```text
classify task / gate
→ 推导 capability requirements
→ 解析当前 host capabilities
→ 按 permission / auth / connection 过滤
→ 按 semantic independence / isolation 过滤
→ 按 interaction / model-execution / cost constraint 过滤
→ 按 resumability / locality / security 需求过滤
→ 对剩余 eligible path 排序
→ 如果执行离开当前 invocation，则 checkpoint
→ dispatch
```

只要某条路径不满足 mandatory requirement，它就不是“排名较低”，而是**不具备资格**。

## 02 · Runtime class 只是可能性，不是 availability claim

常见执行家族包括：

- 当前 chat；
- 独立 peer chat；
- 本地 Codex / Claude Code / 其他 agent process；
- provider API；
- local model endpoint；
- MCP worker / service；
- GitHub / service job；
- human reviewer。

这些 runtime 只有在当前 invocation 真正证明了所需 capability 后，才能承担 manager、specialist、semantic worker 或 external task。

同一个 runtime family 对一种 role 可能合适，对另一种 role 却无效。例如当前 manager chat 可以写正文，但不能靠内部角色扮演通过自己的 mandatory independent-review gate。

## 03 · Manager path

即使当前 chat / local agent 不能直接执行所有 subtask，它仍然可以继续担任 manager。

Manager 可以：

- freeze work；
- package bounded job；
- checkpoint；
- route 到其他 runtime；
- 等待 user / external relay；
- validate + consume result；
- resume owning workflow。

某一个 direct adapter 不可用，不代表整个 Harness 已 blocked。进入 blocked / `semantic_pending` 前，应重新解析所有当前实际连接 / 声明的 route。

## 04 · Independent semantic path

Gate 要求 independent judgment 时，eligible route 必须提供**真正不同的 invocation / session**，并继续使用相同 bounded semantic contract。

可选路径可能包括：

- 独立 local agent invocation；
- 通过 isolated adapter 调 provider model；
- MCP / Control Plane worker；
- GitHub / service worker；
- 独立 peer chat；
- isolated local-model invocation；
- human reviewer。

Transport 只是载体，真正的不变量是：

- separate execution identity；
- 符合 rubric 的 bounded / blind context；
- exact semantic fingerprint；
- truthful worker provenance；
- typed result；
- consume-once binding；
- 禁止 reviewer shopping。

## 05 · Chat 与 peer relay

当前 chat 即使没有 subprocess capability，也可以继续协调工作。

另一个 peer chat 只要收到冻结的 blind packet，并返回预期 typed result，就可以承担 independent reviewer。如果必须由用户手工转发 packet / result，handoff 未完成期间 workflow 应是 `awaiting_user`。

不要因为 relay 是手工的就误标成 `semantic_pending`；真实状态区分是 runtime truth 的一部分。

## 06 · Local agent path

已经认证的 local Codex / Claude / 其他 Agent，通常可以运行完整 Harness 或受限 semantic job，而不需要 Quillframe 强制再引入一套 provider API key。

但必须注意：

- executable 存在不证明 login / model entitlement；
- independence 需要 manager 与 reviewer 使用不同 invocation / session identity；
- reviewer 默认只拿 bounded job material，不拿 manager 整个 working directory / chat；
- local process crash 是 infrastructure failure，不是 semantic reject。

## 07 · Provider / API path

Provider API 是可选 transport，不是 Framework authority。

Adapter 必须保持：

- job identity 与 semantic fingerprint；
- bounded input / rubric / output contract；
- permission restriction；
- truthful model / provider provenance；
- typed result validation。

Provider-specific convenience 不能改掉 generic semantic job 的意义。

## 08 · MCP / Control Plane / Service Job path

较长或分布式工作可以走 handoff：

```text
manager checkpoint
→ bounded handoff / job
→ worker claim lease / attempt
→ execution
→ result + hash
→ manager validates binding
→ named consumer records receipt
→ owning workflow resumes
```

Lease expiry 与 queue retry 属于 infrastructure behavior，不能被解释成文学判断。

## 09 · Research / Corpus routing

Research 与 corpus discovery 应表达“需要哪种 source capability”，而不是“偏好哪个 provider”。

例如：

- `web_search`；
- `github_search`；
- `user_files`；
- `file_library`；
- `mcp_client`；
- local repository / filesystem access。

Discovery 以后，provenance、rights、storage permission 与 semantic interpretation 仍然是不同检查。

Search 成功不等于获得 ingestion rights，更不等于 Canon authority。

## 10 · Cost 与用户偏好

用户偏好可以重排 eligible path：

- 避免 paid API；
- 优先 local model；
- 优先现有 subscription / CLI usage；
- 尽量不需要人工 relay；
- 优先低 latency；
- 优先更强 isolation；
- 指定某些 gate 使用 human review。

Preference 不能把 ineligible route 变 eligible，也不能削弱 independence、capability proof、permission、context isolation、fingerprint binding、authority 或 mandatory quality gate。

## 11 · Failure 与 fallback

必须区分 transport failure 和 semantic outcome。

```text
infrastructure failure + semantic fingerprint 未变
→ checkpoint / 重新解析 capability / 尝试另一个 eligible transport

invalid / mismatched typed result
→ reject result / 修 transport 或重新执行

valid semantic reject
→ 按 semantic judgment 消费 / 路由 repair
```

不能因为一个有效 reviewer 不喜欢 artifact，就不断换 reviewer。

## 12 · Resume

Resume 时，所有 pending external work 的 routing 都要重新解析 capability。Availability、permission、cost constraint 与 connection 可以独立于 persisted session 发生变化。

已经 completed / consumed 的 result 不会因为现在出现了“更喜欢的新 route”就重新执行。

## 13 · 不变量

1. 只在当前已经证明 eligible 的 capability 之间 routing。
2. Provider family 不决定 role，也不决定 independence。
3. 一个 direct adapter 缺失不等于整个 Harness blocked。
4. Manual peer relay 是真实 route，对应真实 `awaiting_user` 状态。
5. Cost preference 只能重排 eligible path，不能削弱 contract。
6. Infrastructure failure 可以 fallback；semantic reject 不能 reviewer-shop。
7. Resume 重新解析 pending route。

## 14 · 相关契约

- [Runtime Capabilities](RUNTIME_CAPABILITIES.zh-CN.md)：什么让一个 path 真正 eligible。
- [Session Runtime](SESSION_RUNTIME.zh-CN.md)：checkpoint / resume identity。
- [Semantic Execution Runtime](../semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)：semantic-specific execution boundary。
- [Control Plane](../control_plane/CONTROL_PLANE.zh-CN.md)：queued / distributed work。

# Runtime 与集成

Quillframe 1.0 把 runtime identity、capability 与 authority 明确分开。Provider 名称不能证明能力存在，能力也不会自动授予故事或写入权威。

## 唯一启动路径

面向作者的入口只有：

```bash
quillframe launch [PROJECT]
```

Local 模式把 Studio 绑定到 loopback Python Core 与项目本地 SQLite。Cloud 模式只启动显式认证流程，不会因为 launch 就上传项目。仓库 Hook 与 host 专属 bootstrap 命令不参与产品正确性。

## Identity

`project` 标识作品，`session` 标识持久执行关系，`run` 标识一次有边界的尝试，`checkpoint` 标识可精确恢复的快照。Provider history 既不是 Canon，也不能替代 Project bootstrap authority。

## Host 边界

Claude Code、Codex、其他 agent host 或模型 API 可以执行满足条件的任务。Host 运行 agent；Quillframe 治理小说。Host 只提供 capability evidence 与 transport；Core 拥有 workflow state、permission、fingerprint、budget、persistence 与 typed validation；Project 拥有 Canon。

## 精确协议

- 只接受 Host Bridge `11`。
- MCP 必须精确匹配 `2026-07-28`，不协商、不回退。
- Context assembly 只接受当前声明的 schema。
- 独立评审只使用一个 `independence_receipt` 字段，并绑定冻结后的 candidate fingerprint。

任何 1.0 之前的请求都会被拒绝，不会被翻译。

## Resume 与取消

Resume 会重新验证精确 checkpoint、Project authority、artifact fingerprint、待处理授权、capability 与 consume-once 状态。Run event 使用 cursor；pause、resume 与 cancel 只能发生在 Core safe point。

## 独立语义执行

只要当前 capability evidence 支持，可以使用独立本地 agent invocation、provider call、MCP worker、GitHub job、peer chat、本地模型或人工评审。Transport failure 只能生成显式 fallback receipt；有效 semantic reject 必须进入 repair，不能不断更换 reviewer。

## Secrets

Credential 始终位于 semantic context 与 Project state 之外。本地使用进程级 lease；Hosted Studio 使用加密 SessionVault。Receipt 与 log 只能包含引用和能力证据，不能包含 secret value。

## Control Plane

Control Plane 持久化 event、handoff、result 与 metadata-only receipt 生命周期，可以证明 dispatch、validation、consumption 与 replay 状态，但不能把运行状态或模型输出变成 Canon、acceptance、settlement 或 publication authority。

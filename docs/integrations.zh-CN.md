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

## 生产阶段的本地 GPT 执行

需要显式启动的 [Codex CLI 中转驱动](../harness/integrations/codex_cli_relay.py) 消费本机回环地址上的生产请求队列。每个请求都在临时目录中新建 CLI 进程，使用明确选定的模型，不恢复旧会话；认证仍由已安装的 CLI 管理。它使用官方的[非交互执行接口](https://learn.chatgpt.com/docs/non-interactive-mode)，不属于普通 CI。

所选模型在本机模型目录中不能强制要求 Code Mode。中转驱动禁用 Code Mode 及其宿主，而模型目录中的工具模式优先于功能开关。若模型要求这一被禁用的宿主，驱动会拒绝提交，不会悄悄启用执行能力或改写模型元数据。当前本地续跑在核对目录后选用 GPT-5.5。仅关闭已识别的实验功能告知；启动错误仍会阻止提交，并保留事件类型及消息哈希，不保存消息正文。

调用账本只追加记录，启动前即扣除一次尝试，启动失败也计入；新建 Core 运行不会重置总数。只有取得真实 CLI 会话事件、完成单次执行，并确认最终消息与保存的输出完全一致，才会提交响应。工具调用、错误、未知事件或证据不一致都会阻止提交。输出字节保持原样，证据日志不保留推理正文，也不会自动重启 CLI 或重发失败请求。对于 CLI 未暴露的服务商内部重试，不声称已统计其模型调用次数。

默认 `--round-limit 64` 最多允许 63 次生产尝试，为独立审稿保留一次调用。提高已授权上限必须显式传参，例如 `--round-limit 96 --manager-limit 95`；仅提高 `--manager-limit` 不能越过默认限制。这些参数表达操作者获准使用的预算，本身不能证明用户已批准。`--expected-used` 核对已有生产账本用量，不会重置计数。独立审稿若记录在队列之外，编排器还必须将其计入累计消耗、相应下调生产限额，并继续预留下一次必需审稿。整个实验的累计上限与 Core 单次运行的调用预算分开管理。

这些记录证明的是 `codex_cli` 生产传输，不是原生子任务的独立性或操作系统隔离。生产审阅仍须另行冻结输入包，由满足条件的独立审稿者执行，并通过 Core 的回执校验。中转驱动和审阅通过都不能代替作者对章节采纳与结算的决定。

## Secrets

Credential 始终位于 semantic context 与 Project state 之外。本地使用进程级 lease；Hosted Studio 使用加密 SessionVault。Receipt 与 log 只能包含引用和能力证据，不能包含 secret value。

## Control Plane

Control Plane 持久化 event、handoff、result 与 metadata-only receipt 生命周期，可以证明 dispatch、validation、consumption 与 replay 状态，但不能把运行状态或模型输出变成 Canon、acceptance、settlement 或 publication authority。

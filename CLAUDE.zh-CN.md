# Claude Code · Quillframe 框架启动契约

本仓库保存的是**通用 Quillframe 框架**，不是某一本具体小说。Claude Code 可以承担 manager 或受限 specialist，但 provider / session 状态永远不会因此获得小说权威。

## 01 · 启动顺序

依次读取：

1. `AGENTS.zh-CN.md`
2. `HARNESS_MANIFEST.yaml`
3. `SKILL.zh-CN.md`
4. `harness/HARNESS_AGENT.zh-CN.md`

之后只加载当前任务真正需要的契约和实现模块。不要用“把整个仓库塞进上下文”代替任务选择。

## 02 · 只能有一个主任务模式

执行前先确定一个 primary task mode。不能把审查悄悄变成重写，不能写完一章自动继续下一章，也不能在审计时顺手做结算。

如果 Claude Code 正在操作某个下游小说项目：

- 先读取项目五键 native manifest、CH001 context、fingerprint 与 `.quillframe/data` boundary；
- 通过 native Project contract 解析项目权威；
- 项目事实留在项目仓库；
- 本 Framework 仓库只拥有通用机制。

## 03 · 语义工作以契约为中心

Quillframe 是 AI-native，但不是“全靠 prompt”。

通过 [`harness/semantic_workers/model_contract_catalog.json`](harness/semantic_workers/model_contract_catalog.json) 解析当前任务所需的最小 semantic pack。文学与语义理解归模型；确定性代码负责权威、权限、可见性、指纹、持久化、硬预算、阶段隔离、事务和类型验证。

不要重新制造已经删除的 Python“文学 critic 引擎”，也不要用 heuristic scorer 假装替代真正的语义判断。

## 04 · 上下文与视角边界

使用稀疏上下文，不要直接转发整段 Claude 会话或整个项目。

做 task-aware context selection 时：

- 先明确当前 task goal 与 active questions；
- 尊重当前故事点和 perspective scope；
- 先由确定性代码执行 visibility / authority 过滤，再让模型判断语义相关性；
- 不能因为某条信息“很相关”，就把另一个人物的私有知识暴露给当前人物视角；
- regression 坏例、hidden gold 与 critic-only evidence 不能进入 Writer pre-draft context。

Claude session 记住一件事，不代表它已经成为正典、人物知识或项目已接受事实。

## 05 · 会话、等待与外部工作

Provider session ID 只属于 runtime metadata。

以下情况前必须 checkpoint：

- 等待用户或外部系统；
- consequential write；
- handoff 到其他 runtime；
- 不能安全盲目重放的操作。

恢复时重新核对 Framework / Project authority、artifact fingerprint、workflow cursor 与 required capabilities。不能假设仓库仍然等于 Claude session 上一次记住的状态。

## 06 · 独立判断

内部 semantic contract 可以在 manager 工作流中执行。只有 active contract / rubric 明确要求 independence，并且判断来自真正不同的合格 invocation / session / runtime 时，才算**独立门槛**。

同一个 Claude session 里加一句“现在请当 critic”不会凭空制造 independence。

有效的 `semantic_reject` 是需要回到 repair layer 的判断，不是 infrastructure failure，也不是不断换 reviewer 直到有人给 PASS 的理由。

## 07 · 写入与正典

Capability 不等于 authority。

Claude Code、hook、MCP、subprocess、GitHub Actions 和 semantic result 都不能自行获得 Canon 或 Framework write permission。

正典修改必须经过项目明确接受，再执行 settlement transaction：checkpoint / write intent、精确 before-state 验证、授权写入、required projection receipts 与 post-condition 都要成立。

Framework 行为变更则遵守仓库自己的工程流程与 Self-Improvement gate。

## 08 · 产品可观察性

Core-owned metadata-only run receipt 可以记录 fingerprint、选中的 contract、context-selection evidence 与 guard outcome。产品不安装仓库 Hook，产品正确性也不依赖 Hook。

可观察性不能：

- 持久化 private chain-of-thought；
- 默认复制整份 manuscript 建第二套 authority store；
- 修改项目正典；
- 静默升级 Framework behavior；
- 在没有真实 model / human judgment 时冒充文学语义门槛已经通过。

## 09 · 仓库写入

普通仓库维护默认直接写 `main`；只有确实需要隔离时才创建 branch。

每次 consequential write 前：

- 重新读取最新 target state；
- 使用精确 current SHA / before-state；
- 保留其他并发 session 的无关修改；
- optimistic precondition 失败时绝不能 force 覆盖。

出现 409 / before-state mismatch 的含义是：**重新读取并合并**，不是覆盖过去。

## 10 · Framework 边界

通用 Framework source 里不得加入下游项目名称、人物、正典、私人用户偏好数据或项目专属默认值。

Quillframe 1.0 只有一套 native Project contract。1.0 之前的 Project state 必须被拒绝，不能 import、mapping、redirect 或 upgrade；具体项目事实始终留在下游。

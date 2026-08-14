# Agent 框架机制采用 · 借运行时机制，但小说语义必须由 NovelForge 自己拥有

NovelForge 不是某个 Agent SDK 外面套一层小说提示词。它会研究成熟 Agent / Runtime 系统里的**执行机制**，再按照长篇小说生产真正需要的边界决定：采用、改造，还是拒绝。

> **范围 ✦** 这是一份“实现影响”文档，不是产品竞品页。通用 Agent 框架解决的问题与 NovelForge 不同，不应该被摆成主要客户替代品。

**研究快照：2026-08-14。** 上游框架变化很快；任何准备进入架构或依赖层的结论，都必须重新核对第一方资料。

---

## 01 · 怎么判断一个机制值不值得采用

如果某个机制能明显改善以下能力，就值得研究：

- 可恢复执行；
- 有边界的任务委派；
- 权限与能力可证明；
- 状态隔离；
- 类型化交接与输出；
- 可观察性；
- 人类 / 外部等待；
- 可重复的软件工程流程。

如果它会模糊以下边界，就必须改造甚至拒绝：

- 运行时记忆 vs. 故事权威；
- 执行能力 vs. 写权限；
- shared conversation vs. 独立判断；
- long-term memory vs. Canon；
- 编排方便 vs. 稀疏上下文纪律。

Story、Character、Relationship、Canon、Reader Engagement、Surface Fundamentals、质量失败路由、Settlement 与证据化学习，属于 NovelForge 自己的小说语义，不从通用 Agent 框架外包。

---

## 02 · OpenAI Agents SDK

**当前第一方资料显示：** Agents SDK 刻意保持少量 primitive，核心包括 Agent、agents-as-tools / handoff、guardrail、session、tracing、MCP、human-in-the-loop，以及隔离 workspace 的 sandbox agent。Handoff 默认可以带入此前会话，但提供 input filter；Session 管理持久工作上下文；Runner 也支持恢复被中断的 run state。

### 采用

- 少量清晰 runtime primitive，而不是发明几十种“编辑部角色”；
- manager-style specialist / agent-as-tool 做受限子任务；
- 类型化 handoff 输入与结构化结果；
- model / tool 边界的 guardrail；
- resumable run state 与 persistent session；
- tracing / observability；
- MCP interoperability；
- 专家确实需要真实文件或工具时使用隔离 workspace。

### 改造

- NovelForge 默认传递**任务级受限上下文**，而不是整段历史会话；
- provider/session memory 永远只是执行状态，不是项目正典；
- observability 默认记录 metadata / fingerprint，而不是复制整份 manuscript 到第二套 tracing authority；
- mandatory independent gate 要求真正不同的 invocation / session 与 artifact binding，不是同一个 run 里再 new 一个 agent object。

### 拒绝

- 把 provider conversation state 当故事事实；
- 任何任务都用 handoff，哪怕一个 model contract 或 deterministic step 就够；
- 把小说语义绑死在单一 provider 上。

第一方资料：
- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/handoffs/
- https://openai.github.io/openai-agents-python/sessions/
- https://openai.github.io/openai-agents-python/running_agents/

---

## 03 · LangGraph

**当前第一方资料显示：** LangGraph 的强项是 thread + checkpoint、durable interrupt、replay / time travel、故障恢复、thread-scoped short-term memory、跨 thread store，以及不同粒度的 subgraph persistence。官方文档对很多“subagent-as-tool”场景明确推荐 per-invocation isolation。

### 采用

- 外部等待与关键状态转换前的 durable checkpoint；
- 显式 thread / session identity；
- interrupt / resume 是正常运行状态，而不是异常补丁；
- 从最后一个成功持久状态恢复；
- thread-scoped execution memory 与 cross-thread store 分离；
- 不需要长期共享状态的 specialist 使用 per-invocation isolation；
- replay / fork 思想用于调试与 scenario exploration。

### 改造

NovelForge 至少明确区分三类持久域：

```text
runtime / session state
learning / evidence state
project authority / Canon state
```

Scenario fork、run receipt、checkpoint、memory overlay 与 generic graph state 都保持无权威，除非项目自己的显式事务改变 Canon。

### 拒绝

- 把整本小说权威塞进 generic graph state；
- 从旧 checkpoint 恢复时不重新验证 project authority、artifact fingerprint 与 required capabilities；
- 为了 graph 编排方便而绕过 character / perspective visibility boundary。

第一方资料：
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/concepts/memory
- https://docs.langchain.com/oss/python/langgraph/use-subgraphs

---

## 04 · Google ADK / agents-cli

**当前第一方资料显示：** ADK 把 session / event / state 做成显式服务；agents-cli 则把 Agent 项目开发明确组织成 scaffold、build、evaluate、deploy、publish、observe，并提供 coding-agent skills 与结构化 eval dataset。

### 采用

- 标准项目 scaffold 与 lifecycle commands；
- session / event 作为可检查的运行时概念；
- tests / evals 成为项目正常组成，而不是最后才想起来；
- coding-agent skills 与仓库 guidance 作为正式基础设施；
- scaffold upgrade 与可重复项目 metadata；
- change validation 中加入 trace / eval comparison。

### 改造

- NovelForge Project SDK scaffold 的是**小说工程**，包含 authority classes、Canon/state、plans、manuscripts、research、corpus 与 regression evidence；
- Framework upgrade 是 exact-lock dependency migration，不是工具链自动升级；
- deployment / observability 思想可以借，但小说生产仍保持 provider-neutral、hosting-neutral。

### 拒绝

- 把小说项目模型绑定到一个 cloud deployment target；
- 自动生成 eval scenario 或 LLM grade 没经过 NovelForge blindness / evidence rule 就获得权威。

第一方资料：
- https://google.github.io/adk-docs/
- https://google.github.io/agents-cli/guide/quickstart-tutorial/
- https://google.github.io/agents-cli/guide/evaluation/
- https://google.github.io/agents-cli/reference/skills/

---

## 05 · Microsoft AutoGen

**当前第一方资料显示：** AgentChat 支持 single agent、多种 team、human-in-the-loop，以及 agent/team 的显式 save/load state。值得注意的是，它当前的 team 文档自己也强调：简单任务先从 single agent 开始，只有确实需要 collaboration / diverse expertise 时才升级到 team。

### 采用

- 显式 save/load state；
- 可观察 agent / team state；
- human feedback 是一等工作流；
- 只有 distinct capability / collaboration 真有价值时才引入 team；
- termination / resume，而不是无限 group chat。

### 改造

- NovelForge 默认 **single manager + bounded specialists**；
- independent reviewer 收到隔离 packet，而不是共享 group-chat history；
- worker/team state 是 runtime evidence，不是 Canon；
- saved state 恢复时必须重新绑定当前 project authority。

### 拒绝

- Round-robin discussion 作为默认质量策略；
- mandatory blind / independent review 共享 group-chat context；
- 多个 stateful agent 并发修改同一份 authoritative story state。

第一方资料：
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/index.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html

---

## 06 · Claude Code

**当前第一方资料显示：** Claude Code 支持项目级 instruction memory、按 session ID 恢复、programmatic print mode、permission mode、MCP 与仓库级工作指导。

### 采用

- repo-scoped agent instructions；
- 子目录 scoped / nested guidance；
- 可恢复 local session；
- CLI 作为真实 bounded runtime；
- MCP interoperability；
- deterministic hook / telemetry 记录运行生命周期证据。

### 改造

- `CLAUDE.md` 只是 bootstrap / instruction state，不拥有 Canon；
- resume 后重新检查当前 Project / Framework state；
- hook 可以记录 operational facts，但不能偷偷代替 literary semantic gate。

### 拒绝

- 把聊天里的临时解释持久化成项目事实；
- 同一个 session 里做 prompt-only self-review，冒充 mandatory independence。

第一方资料：
- https://docs.anthropic.com/en/docs/claude-code/cli-usage
- https://docs.anthropic.com/en/docs/claude-code/memory
- https://docs.anthropic.com/en/docs/mcp

---

## 07 · Model Context Protocol

**当前第一方资料显示：** MCP 2025-06-18 specification 使用 JSON-RPC，标准 transport 为 stdio 与 Streamable HTTP。Streamable HTTP 规范明确要求关注 Origin validation 与认证；transport authorization 解决的是连接权限，不是应用领域 authority。

### 采用

- 标准 JSON-RPC lifecycle / capability negotiation；
- 本地 runtime / tool integration 优先 stdio；
- 合格远程服务使用 Streamable HTTP；
- stdio 严格 stdout discipline；
- 标准 tool schema，而不是每个 provider 自造协议；
- remote HTTP 的 Origin / auth protection；
- transport 支持时使用标准 session / resumability mechanism。

### 改造

- NovelForge 默认暴露 operational / project-safe capability，而不是 raw Canon-write power；
- MCP authorization 证明的是 transport access，**不是 story authority**；
- 高权威写入仍然必须走 Harness / Settlement transaction 与项目 precondition。

### 拒绝

- webhook / MCP message 到达就等于获得权限；
- MCP 已经能解决时还为每家 provider 发明一套 resume / idempotency protocol。

第一方资料：
- https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization

---

## 08 · 普通软件工程同样是重要来源

NovelForge 还借用一套并不属于 Agent 框架的纪律：

```text
spec → plan → tasks → implementation → verification → acceptance
```

### 采用

- 精确 target path / object；
- precondition 与 before-state；
- phase checkpoint；
- behavior / authority compatibility check；
- deterministic test 与 reproducible build；
- dependency / migration planning；
- rollback 与 post-condition verification。

### 改造

- 普通正文 micro edit 不制造假 feature ticket；
- structural fiction change、schema migration、Framework upgrade、Canon migration 才使用更强工程流程；
- 章节生产使用 plan、Scene Card、semantic contract 与 quality evidence，不把每个 paragraph 假装成 software task。

### 拒绝

- 为流程而流程；
- 假装 deterministic unit test 能完全替代艺术 / 语义判断。

---

## 09 · NovelForge 最终综合

```text
one manager
→ 当前问题需要的最小 semantic / deterministic mechanism
→ 只有 capability / isolation 真需要时才 dispatch bounded specialist
→ durable session / checkpoint / control-plane state
→ sparse perspective-safe context
→ typed fingerprint-bound evidence
→ explicit repair owner
→ user-visible gate
→ separate acceptance + settlement authority
```

治理原则：

1. 默认一个 manager；只有 capability、isolation、independence 或真实 parallelism 才增加 worker。
2. 分开 runtime memory、learning evidence、derived memory 与 Canon authority。
3. specialist 之间传 bounded、perspective-safe context，不复制整段历史。
4. wait / resume 必须 durable、显式，并重新验证。
5. connector / transport 只是 capability，永远不是 authority。
6. 语义智能放 model-readable contract；可精确定义的不变量放 deterministic code。
7. observability 优先记录 metadata / fingerprint，不复制 private reasoning 或整份 manuscript 建第二 authority store。
8. 小说项目应当是可重复的软件工程制品：manifest、test、build、migration、exact lock 都能独立工作。
9. Learning 依赖 evidence + counterexample，不依赖模型反复同意自己。

---

## 10 · 维护规则

上游框架研究只是 evidence，不是自动 dependency update。

当某个上游机制发生变化：

```text
重新核对第一方资料
→ 记录 adopt / adapt / reject 假设
→ 找到受影响的 NovelForge contract
→ 跑 capability + regression impact
→ 只有确实合理时才改实现
→ 更新本页日期与来源
```

**NovelForge 应该不断变得更懂 runtime engineering，但不能退化成“通用 Agent 框架 + 小说提示词”。**

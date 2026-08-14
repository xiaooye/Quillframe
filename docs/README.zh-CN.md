<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="600" />
  <p><strong>面向需要小说原生状态、质量体系与智能体执行能力的开发者。</strong></p>
  <p><kbd>开始使用</kbd>&nbsp;&nbsp;<kbd>理解原理</kbd>&nbsp;&nbsp;<kbd>构建项目</kbd>&nbsp;&nbsp;<kbd>质量验证</kbd>&nbsp;&nbsp;<kbd>运行维护</kbd></p>
  <p><a href="README.en.md">English</a> · <strong>简体中文</strong></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge 文档中心

> 🌸 **NovelForge 不是“带几个小说示例的通用智能体 SDK”。它从小说生产本身出发，把故事状态、正典、人物、读者体验、质量门槛、长期学习和运行时一起设计。**

把本页当作面向用户的总导航。需要精确实现细节时，再进入底层协议与机器契约。

---

## 01 · 按你的目标开始 ✨

| 你现在想做什么 | 从这里开始 | 然后阅读 |
|---|---|---|
| **先理解 NovelForge 是什么** | [为什么是 NovelForge](why-novelforge.zh-CN.md) | [总体架构](architecture.zh-CN.md) |
| **判断技术选型是否合适** | [为什么是 NovelForge](why-novelforge.zh-CN.md) | [架构图谱](architecture-atlas.zh-CN.md) |
| **理解一章正文如何生产出来** | [生产流水线](production-pipeline.zh-CN.md) | [质量保障与 QA](quality-assurance.zh-CN.md) |
| **把现有小说接入框架** | [项目 SDK](project-sdk.zh-CN.md) | [项目适配器](project-adapters.zh-CN.md) |
| **在聊天 / CLI / MCP / API 上运行** | [运行时与集成](integrations.zh-CN.md) | [会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md) |
| **理解偏好学习和语料体系** | [自适应学习](adaptive-learning.zh-CN.md) | [语料智能](../corpus/README.zh-CN.md) |
| **审核框架质量与发布门槛** | [质量保障与 QA](quality-assurance.zh-CN.md) | [评测参考](../evals/README.zh-CN.md) |

---

## 02 · 产品逻辑 🪄

### 为什么需要一个小说专用框架

通用智能体框架很擅长编排、工具调用、持久工作流、多智能体协作与自动化。NovelForge 从更高一层的问题开始：**如果最终产物是一部长时间演化的小说，那么“什么是真的、人物知道什么、这一章是否好看、失败后从哪里修、用户口味如何学习”应该由谁负责？**

[为什么是 NovelForge](why-novelforge.zh-CN.md) 会直接比较 LangGraph、CrewAI、AutoGen 和 OpenAI Agents SDK，也会明确说明哪些场景使用它们反而更简单。

### 三类状态必须分开

NovelForge 明确区分：

1. **项目状态** —— 已接受正典、当前状态、计划、研究资料；
2. **运行状态** —— 会话、检查点、交接、租约、结果回执；
3. **学习状态** —— 证据、偏好假设、语料缺口、升级候选。

三者可以互相引用，但权威不会隐式流动。

阅读 [总体架构](architecture.zh-CN.md) 获取系统视图，阅读 [架构图谱](architecture-atlas.zh-CN.md) 查看每个子系统的职责与深入入口。

---

## 03 · 构建与运行 📖

### 项目工程化

NovelForge 把一本小说视为可复现的工程项目，而不是一堆提示词文件。项目锁定精确框架版本，并独立维护自己的故事事实、状态、计划、稿件、研究资料、评测和迁移。

- [项目 SDK](project-sdk.zh-CN.md)
- [项目适配器](project-adapters.zh-CN.md)
- [项目适配器协议](../harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md)

### 调度与运行时

NovelForge 默认只使用一个管理器。只有在确实需要不同能力、上下文隔离、独立判断或有效并行时，才增加专门执行器。聊天会话、本地智能体、提供商 API、MCP、GitHub 任务、本地模型和人工审阅者都只是运行方式，不是权威来源。

- [运行时与集成](integrations.zh-CN.md)
- [调度管理器](../harness/HARNESS_AGENT.zh-CN.md)
- [编排协议](../harness/ORCHESTRATION_PROTOCOL.zh-CN.md)
- [运行时路由](../harness/session_runtime/RUNTIME_ROUTING.zh-CN.md)

---

## 04 · 小说原生系统 🌸

这些能力通常需要通用智能体框架的应用层自己实现，而 NovelForge 把它们作为框架的一等机制：

| 系统 | 它回答什么问题 | 深入文档 |
|---|---|---|
| **故事系统** | 当前处于哪个故事层级，哪些压力发生变化，下一步必须推动什么？ | [故事系统](../core/STORY_SYSTEM.zh-CN.md) |
| **人物系统** | 每个角色知道什么、想要什么、承担什么风险、独立追求什么？ | [人物系统](../core/CHARACTER_SYSTEM.zh-CN.md) |
| **正典状态** | 什么只是计划，什么是审阅稿，什么已经接受或锁定？ | [正典状态](../core/CANON_STATE.zh-CN.md) |
| **表层质量规则** | 哪些反复出现的 AI 文本失败机制必须直接拦截？ | [表层质量规则](../surface/FUNDAMENTALS.zh-CN.md) |
| **读者吸引力** | 这一章是否真正有推进、有回报、有因果、有继续读下去的动力？ | [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md) |

---

## 05 · 质量保障、QA 与发布门槛 ✅

NovelForge 刻意把**确定性正确性**和**文学语义判断**分开。

- Schema、生命周期、权限、内容指纹、依赖完整性、幂等性、构建发布不变量和项目泄漏由确定性检查负责；
- 文本质量、读者吸引力、人物与场景行为等无法诚实压缩成正则规则的问题，交给语义审查；
- 强制独立审查必须来自不同会话或调用，并绑定候选稿内容指纹；
- 评测中的隐藏预期值会在交给审阅者之前从盲评队列中移除；
- 普通 CI 不会偷偷调用付费模型消耗额度。

阅读 [质量保障与 QA](quality-assurance.zh-CN.md) 查看完整门槛体系，[评测参考](../evals/README.zh-CN.md) 查看运行器与评测案例格式。

---

## 06 · 学习与语料智能 🔎

NovelForge 可以从用户反馈和外部证据中学习，但不会把模型自己的猜测偷偷固化成永久规则。

- [自适应学习](adaptive-learning.zh-CN.md)
- [语料智能](../corpus/README.zh-CN.md)
- [语料政策](../corpus/CORPUS_POLICY.zh-CN.md)
- [语料入库协议](../corpus/CORPUS_INGEST_PROTOCOL.zh-CN.md)
- [自我改进协议](../harness/SELF_IMPROVEMENT_PROTOCOL.zh-CN.md)

---

## 07 · 精确参考层 ⚙️

下面这些文档主要用于实现、调试和审计，而不是新用户入门：

| 领域 | 精确参考 |
|---|---|
| 调度执行 | [调度管理器](../harness/HARNESS_AGENT.zh-CN.md) |
| 会话身份与恢复 | [会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md) |
| 运行能力路由 | [运行时能力](../harness/session_runtime/RUNTIME_CAPABILITIES.zh-CN.md) |
| 持久控制平面 | [控制平面](../harness/control_plane/CONTROL_PLANE.zh-CN.md) |
| 语义执行器契约 | [语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md) |
| 语义任务执行 | [语义执行运行时](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md) |
| 框架发布包 | [框架发布包](../release/FRAMEWORK_BUNDLE.zh-CN.md) |
| 评测实现 | [评测参考](../evals/README.zh-CN.md) |

---

## 08 · 文档分层原则 ✦

面向用户的页面负责回答 **为什么、什么时候用、怎么用、有什么取舍**；底层协议负责定义 **精确不变量、状态迁移和机器契约**；机器 Schema 则继续保持单一来源。

这样既能让第一次来到仓库的人迅速理解价值，也不会为了“好懂”而牺牲框架的工程严谨性。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <br />
  <sub>先理解产品，再深入契约；需要多深，就读多深。🌸</sub>
</div>

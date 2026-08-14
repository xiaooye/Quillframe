<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="580" />
  <p><strong>先建立产品心智模型；只有在需要精确执行语义时，再深入底层契约。</strong></p>
  <p><kbd>理解</kbd>&nbsp;&nbsp;<kbd>接入</kbd>&nbsp;&nbsp;<kbd>写作</kbd>&nbsp;&nbsp;<kbd>验证</kbd>&nbsp;&nbsp;<kbd>运行</kbd></p>
  <p><a href="README.en.md">English</a> · <strong>简体中文</strong></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge 文档中心

NovelForge 的文档按**读者要完成的任务**组织，而不是照着源码目录逐层解释。

当前 7.3 实现采用 AI-native、contract-first 架构：需要理解小说的语义判断交给模型；权威、权限、内容指纹、持久化、路由、类型校验、事务、硬预算与可复现性由确定性系统负责。

文档本身也遵循同样的分层。产品页负责建立心智模型和说明取舍；指南负责告诉你怎样使用一个子系统；深层协议负责定义精确不变量与执行边界。

---

## 01 · 如果你正在判断 NovelForge 是否适合自己 ✦

先读这四页：

**[为什么是 NovelForge](why-novelforge.zh-CN.md)** —— 产品判断、直接小说智能体 / 框架对比、成熟作者工具、真实取舍，以及哪些场景并不适合 NovelForge。

**[总体架构](architecture.zh-CN.md)** —— 项目权威、模型语义智能、确定性运行外壳、状态分离与写入边界。

**[生产流水线](production-pipeline.zh-CN.md)** —— 为什么 `DRAFT` / `REVISE` 是一轮可诊断、可修复的生产运行，而不是一次模型调用。

**[质量保障](quality-assurance.zh-CN.md)** —— 确定性 QA、语义契约、独立判断、质量发现、候选稿演化与发布门槛。

如果需要继续追到每个子系统具体负责什么，再进入 **[架构图谱](architecture-atlas.zh-CN.md)**。

---

## 02 · 如果你要把一本小说接入 NovelForge ⚙️

先读 **[项目 SDK](project-sdk.zh-CN.md)**。它定义一个完整下游项目必须自己拥有的内容：项目清单、精确 Framework lock、项目自己的正典与当前状态、计划、稿件、研究资料、回归样本、测试与构建产物。

如果现有小说已经有成熟目录结构，不需要为了接入框架重排整个仓库。继续读 **[项目适配器](project-adapters.zh-CN.md)** 与精确的 **[项目适配器协议](../harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md)**。

最重要的边界始终不变：Generic Framework 不是某一本小说的数据库；依赖方向只能是 **Project → pinned NovelForge**。

---

## 03 · 如果你正在写作或修改正文 📖

小说机制层建议按这个顺序理解：

**[故事系统](../core/STORY_SYSTEM.zh-CN.md)** —— 故事层级、压力、因果推进，以及问题应该由哪一层负责。

**[人物与关系系统](../core/CHARACTER_SYSTEM.zh-CN.md)** —— 人物议程、信念、知识边界、独立行动与长期关系状态。

**[正典与状态](../core/CANON_STATE.zh-CN.md)** —— 什么已经锁定或接受，什么只是计划、审阅稿或提案。

**[表层质量基础](../surface/FUNDAMENTALS.zh-CN.md)** —— 常见 AI 文本失败机制，以及它们真正应该回到哪里修。

**[读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)** —— 读者压力、回报、因果、继续阅读动力、预期与章节体验。

把这些机制组合成一轮生产运行的完整流程，见 **[生产流水线](production-pipeline.zh-CN.md)**。

---

## 04 · 如果你在处理上下文或记忆 🧠

读 **[上下文与记忆](context-and-memory.zh-CN.md)**。

核心原则很简单：**持久存储不等于自动塞进提示词，记住了也不等于是真的。** 项目权威、派生记忆、运行状态与模型推断始终是不同的东西。

上下文检查器负责解释当前工作集为什么包含某些信息；记忆分层与可编辑 Memory Bank 提供作者可见的控制面。受保护的 `accepted` / `locked` 内容不能通过记忆编辑器被静默改写。

真正需要理解“此刻什么相关”时，由模型作语义判断；确定性代码负责硬预算、来源、生命周期、权威等级与显式控制，而不是用伪文学分数替代阅读理解。

---

## 05 · 如果你在运行 NovelForge 🔌

实践入口是 **[运行时与集成](integrations.zh-CN.md)**。

需要精确语义时，再按问题进入对应协议：

- **[Harness 管理器](../harness/HARNESS_AGENT.zh-CN.md)** —— manager 拥有什么职责；
- **[编排协议](../harness/ORCHESTRATION_PROTOCOL.zh-CN.md)** —— 一轮任务怎样推进；
- **[会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md)** —— session / run / checkpoint 身份与恢复；
- **[运行时能力](../harness/session_runtime/RUNTIME_CAPABILITIES.zh-CN.md)** —— 当前宿主究竟具备什么能力；
- **[运行时路由](../harness/session_runtime/RUNTIME_ROUTING.zh-CN.md)** —— 怎样选择符合条件的执行路径；
- **[控制平面](../harness/control_plane/CONTROL_PLANE.zh-CN.md)** —— 外部任务、租约、结果与一次性消费；
- **[语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)** —— 受限语义任务和类型化结果；
- **[语义执行运行时](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)** —— transport、校验、回执与结果消费。

一个运行时技术上“做得到”，从来不代表它因此获得故事写入权威。

---

## 06 · 如果你要理解 7.3 的模型语义契约 ✦

NovelForge 7.3 使用**按需渐进加载**的语义契约体系。

唯一的确定性目录索引是：

`harness/semantic_workers/model_contract_catalog.json`

具体契约包位于：

`harness/semantic_workers/contracts/`

管理器先选择当前任务真正需要的最小契约包，运行时再把精确 contract ID 解析到唯一 pack。任务只封装必要输入、rubric 与 output contract，计算语义指纹，并验证类型化结果。

这使文学理解继续属于模型，同时又不允许模型输出绕过项目权威、权限、持久化或结算规则。

---

## 07 · 如果你在审核质量或组织修改 ✅

从 **[质量保障](quality-assurance.zh-CN.md)** 开始，再读 **[质量演化](quality-evolution.zh-CN.md)** 与 **[评测参考](../evals/README.zh-CN.md)**。

可以把这一层理解成六件不同的事：

**确定性 QA** —— 证明机器可以证明的不变量。

**语义契约** —— 回答真正需要理解文本的问题。

**质量发现（findings）** —— 把问题、证据和归属明确记录下来。

**失败路由** —— 把问题送回真正拥有它的故事、人物、场景、表层或上下文机制。

**候选稿演化** —— 记录谱系、比较现稿与挑战稿，并允许在收益平台期停止修改。

**独立判断** —— 当任务明确要求独立性时，必须来自真正不同的调用 / 会话，并返回绑定精确稿件指纹的类型化结果。

---

## 08 · 如果你在做长期学习或使用语料证据 🔎

偏好 / 创作机制学习从 **[自适应学习](adaptive-learning.zh-CN.md)** 开始；外部作品与研究证据从 **[语料智能](../corpus/README.zh-CN.md)** 开始。

需要精确政策时继续读：

- [语料政策](../corpus/CORPUS_POLICY.zh-CN.md)
- [语料入库协议](../corpus/CORPUS_INGEST_PROTOCOL.zh-CN.md)
- [自我改进协议](../harness/SELF_IMPROVEMENT_PROTOCOL.zh-CN.md)
- [持续维护](../harness/CONTINUOUS_MAINTENANCE.zh-CN.md)

发现、访问、版权判断、存储、语义分析、学习与升级是不同的门槛。语料不是正典；模型推断不是持久用户口味；通用创作机制的升级必须有证据、反例或适用边界、评测覆盖、版本与回滚，以及通过确定性验证。

---

## 09 · 如果你在比较产品、框架或运行时 🧭

请把两个问题分开。

**产品定位：** [为什么是 NovelForge](why-novelforge.zh-CN.md) 主要比较直接小说智能体 / 小说框架，并单独说明成熟作者产品与 NovelForge 的不同目标。

**实现思想：** [智能体框架采用分析](../knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md) 才讨论 LangGraph、OpenAI Agents SDK、CrewAI、AutoGen、coding-agent runtime、MCP 等通用工程体系。

不要把这两类比较重新塞回一张首页大表。它们回答的不是同一个问题。

---

## 10 · 文档的三层结构 🌸

**Tier A · 产品入口** —— README、Docs Home、Why、Architecture、Pipeline、QA。第一次来仓库的人应该不读源码也能理解，文字与视觉都执行最严格的 QA。

**Tier B · 使用指南** —— Project SDK、Integrations、Learning、Corpus、Evals、Context/Memory、Quality Evolution。重点是“什么时候用、怎么用、会得到什么、失败后怎么办”。

**Tier C · 契约与工程记录** —— Harness、Runtime、Semantic Worker、Story / Character / Canon、Surface / Reader、Corpus Policy 以及历史 specs。这里优先保证边界和语义精确，不为了“好看”牺牲协议清晰度。

历史 spec 与 changelog 保留历史语义；文档重建不能把旧设计记录偷偷改写成当前产品事实。

仓库级写作规范与 QA gate 分别见 **[文档规范](DOCUMENTATION_STANDARD.zh-CN.md)** 与 **[文档质量门槛](DOCUMENTATION_QA.zh-CN.md)**。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <br />
  <sub>当前任务需要读多深，就只读到多深。🌸</sub>
</div>

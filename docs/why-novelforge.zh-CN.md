<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="580" />
  <p><strong>为什么是 NovelForge —— 以及什么时候其他小说系统更合适。</strong></p>
  <p><kbd>直接竞品</kbd>&nbsp;&nbsp;<kbd>取舍</kbd>&nbsp;&nbsp;<kbd>研究版图</kbd></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# 为什么是 NovelForge

> 🌸 **NovelForge 不争“最好用的 AI 写作软件”，它解决的是更窄、更工程化的问题：如何让长篇小说生产具备明确权威、可恢复执行、独立质量门槛和有证据的长期学习。**

因此，真正直接的比较对象应该是其他小说创作产品与小说智能体，而不是通用智能体编排 SDK。

> **对比快照：** 2026-08-14。产品能力会快速变化；本页记录的是当前适用性对比，不是永久排名。

<img src="../assets/ui/home-comparison.zh-CN.svg" alt="NovelForge 与 Sudowrite、NovelCrafter、NovelClaw、Novel OS、AuthorAgent 和 autonovel 的对比" width="100%" />

---

## 01 · 一句话怎么选 ✨

**选 Sudowrite**：你更需要成熟的创意陪写体验、快速起草、改写扩写和 Story Bible，而不是一套严格的运行时与正典治理系统。

**选 NovelCrafter**：你更看重成熟的结构化写作工作台、Codex、世界观与系列管理、协作和灵活模型选择。

**选 NovelClaw**：你希望拥有可视化的长篇写作控制台，可直接查看和编辑记忆、稿件、故事板、人物、世界和运行结果。

**选 Novel OS**：你喜欢固定的“编辑团队”模式，希望 Architect → Scribe → Editor → Guardian → Curator 这类明确角色流水线帮你自动推进。

**选 AuthorAgent**：你希望本地优先，并且一套工具覆盖研究、规划、写作、修订、格式化乃至出版工作流。

**选 autonovel**：你更想探索高度自动化的“从种子概念直接生成完整小说及发布资产”的流水线。

**选 NovelForge**：你最难的问题是权威边界、长篇连贯性、失败回路、真正独立的语义 QA、多运行时恢复、项目可复现性，以及长期偏好 / 语料学习。

---

## 02 · NovelForge 真正不同在哪里 🌸

### 正典不是“记忆区”，而是一笔受控事务

NovelForge 明确区分 `locked > accepted > active_plan > review > proposal`。计划、会话记忆、审阅结论、语料事实和模型推断都不能因为“系统看见过”就自动变成故事事实。

这比常见的“Story Bible / Codex / memory bank 就是 source of truth”更严格。代价是流程更重，但在多章节、多会话、多模型、多人协作的长期项目里，这种严格会直接降低故事事实被悄悄污染的风险。

### 人物独立性属于状态模型，不只是人物卡

重要人物拥有自己的目标、声线、知识边界、任务、空间位置、利益和情绪余波。管理器知道的事情，不代表人物知道；计划里写过的反应，也不代表角色在场景中一定会照做。

### 质量不是“一个 Editor Agent”

NovelForge 把质量拆成不同机制：

- 表层质量规则；
- 读者吸引力；
- 故事与人物模拟；
- 连贯性 / 状态审计；
- 独立语义审查；
- 确定性契约检查。

局部表层失败可以局部改写；表层问题成簇应整场景重生；安全但平淡要回到读者压力与场景模拟；人物失真回人物模拟；故事失败回 Story / Plan。它不允许所有问题都被“润色一下句子”掩盖。

### 独立审查必须真的独立

管理器不能把自己的提示词切成“现在你是批评家”就算通过强制审查。默认 reviewer fresh-per-fingerprint，接收有界包，返回绑定候选稿指纹的类型化结果；有效拒绝后也禁止不断换审阅者直到有人说通过。

### 运行状态不等于故事权威

聊天会话、本地 Codex / Claude、MCP 执行器、提供商 API、GitHub 任务、本地模型和人工审阅者都可以承载工作，但它们的 session/thread ID 只是运行时元数据，不是正典来源。

### 学习必须有证据，而且能撤回

用户口味以偏好假设存在，同时记录证据、冲突、适用范围、评测、版本与回滚。语料检索与入库分开；语料证据与用户口味分开；用户口味与通用写作机制升级再次分开。

---

## 03 · 直接竞品在哪些地方更强 ⚠️

### Sudowrite / NovelCrafter 的作者 UX 明显更成熟

它们是成熟的创作产品，有完整编辑器、引导流程、项目界面和作者社群。NovelForge 当前首先是框架与项目运行系统，不是一个完成度同等级的消费级写作 Studio。

### NovelClaw 的可视化控制面更完整

NovelClaw 把稿件、故事板、人物、世界、风格、记忆、运行日志和下载结果都直接做成可操作界面。NovelForge 目前的优势更多在权威、运行时和质量契约，而不是作者端可视化产品体验。

### Novel OS 的固定编辑角色更容易理解

Architect → Scribe → Editor → Guardian → Curator 的隐喻非常直观。NovelForge 刻意不假设“多 Agent / 固定角色越多越专业”，因此更灵活、更严格，但第一眼没有那么戏剧化。

### AuthorAgent / autonovel 覆盖更完整的出版生命周期

NovelForge 当前集中于故事生产、QA、正典、学习、运行时和项目工程化，并不试图同时成为最佳排版工具、有声书生成器、营销智能体或广告优化器。

### NovelForge 的流程确实更重

内容指纹、检查点、权威等级、独立门槛、before/after settlement 和精确框架锁，对短篇或随手写作来说可能是过度工程。

---

## 04 · 值得持续关注的研究系统 🔬

商业产品和开源工程还不是全部。研究型系统可以提供机制证据，但不应该和成熟产品放在同一张“谁更好用”的表里。

### StoryWriter

StoryWriter 采用大纲智能体、规划智能体和写作智能体；写作阶段会围绕当前事件动态压缩历史上下文，主要针对长篇的一致性和叙事复杂度问题。

### MAGNET + ATLAS

MAGNET 让基于人物设定的角色智能体根据共享世界状态和持续变化的故事目标提出行动；ATLAS 再用图结构检查跨场景世界状态。2026 年 7 月论文报告，在 100 页尺度上，相比单模型提示和 IBSEN，标注问题与 hallucination 明显下降。

### GOAT Storytelling Agent

GOAT 采用从全书设定 → 章节 → 场景 → 场景正文的自顶向下流水线，并能挂在普通文本生成后端上运行。

> **研究边界 ✦** 一篇论文证明某个机制有效，不等于该系统已经适合与成熟产品或生产框架做同一维度的工程比较。

---

## 05 · 通用 Agent 框架依然重要，但属于更底层 🔧

LangGraph、OpenAI Agents SDK、AutoGen、CrewAI、Google ADK、Claude Code 和 MCP 对 NovelForge 仍然非常重要，因为它们提供了持久执行、会话、交接、guardrail、MCP、项目脚手架、保存 / 恢复状态等成熟机制。

但这些应该放在“实现思想来源 / adopt-adapt-reject”层，而不是首页的主要市场竞品。详见 [Agent Framework Adoption Matrix](../knowledge/AGENT_FRAMEWORK_ADOPTION.en.md)。

---

## 06 · 一个简单的选择规则 🧭

当下面多条同时成立时，NovelForge 更有价值：

- 小说会跨越很多章节、会话或模型；
- 计划与已接受故事事实必须严格分离；
- 人物知识越界、角色失真是严重风险；
- “文字没有明显错误”远远不够，还要独立衡量读者抓力；
- 编辑 / 审阅者必须真正独立于写作调用；
- 失败应该回到拥有问题的机制，而不是不断打补丁；
- 项目要能跨等待、重启、提供商变化和外部 worker 恢复；
- 用户口味需要靠证据演化，而不是不断往 prompt 里堆规则；
- 一本小说应该可以像软件项目一样被版本化、验证和迁移。

如果这些大多都不成立，那么更轻量的写作产品或小说 Agent 可能更合适。

---

## 07 · 对比来源 🔗

### 作者产品
- Sudowrite Story Bible: https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/what-is-story-bible/jmWepHcQdJetNrE991fjJC
- Sudowrite 概览: https://docs.sudowrite.com/getting-started/dQph1snuwbfMWG9wRjsNug/what-is-sudowrite/iwppfTjfffZTFaa7eBzJoQ
- NovelCrafter: https://www.novelcrafter.com/

### 开源小说系统
- NovelClaw: https://github.com/iLearn-Lab/NovelClaw
- Novel OS: https://github.com/mrigankad/Novel-OS
- AuthorAgent: https://github.com/Ckokoski/AuthorAgent
- autonovel: https://github.com/NousResearch/autonovel
- GOAT Storytelling Agent: https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent
- StoryWriter: https://github.com/THU-KEG/StoryWriter

### 研究论文
- StoryWriter: https://arxiv.org/abs/2506.16445
- MAGNET / ATLAS: https://arxiv.org/abs/2607.00918

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="52" />
  <br />
  <sub>专用不是天然优势；只有当“小说本身”就是最难的问题时，它才有价值。✦</sub>
</div>

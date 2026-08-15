<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="580" />
  <p><strong>为什么是 NovelForge · 先看你的项目最难治理的到底是什么</strong></p>
  <p><kbd>直接小说系统</kbd>&nbsp;&nbsp;<kbd>作者产品</kbd>&nbsp;&nbsp;<kbd>架构差异</kbd>&nbsp;&nbsp;<kbd>真实取舍</kbd></p>
  <p><a href="why-novelforge.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# 为什么是 NovelForge

NovelForge 并不想证明“别的小说系统没有记忆、没有 QA、没有读者模拟、没有多 Agent、没有长期一致性”。到了 2026 年，这些能力已经广泛出现在成熟作者产品和开源小说系统里。

它真正提出的是一个更窄的架构判断：

> **当一本小说跨越很多章节、会话、模型和修改轮次时，故事权威、模型语义判断、可恢复执行、质量证据，以及最终正典写入，应该始终是彼此分开的东西。**

本页比较快照：**2026 年 8 月 14 日**。产品能力变化很快；“公开资料暂未确认”只表示这次没有从已检查的第一方材料确认，绝不等于“产品没有”。

<img src="../assets/ui/home-comparison.zh-CN.svg" alt="NovelForge、NovelClaw、Novel OS、AuthorAgent 与 autonovel 的公开机制证据对比" width="100%" />

---

## 01 · 最快的选择方法

不要先数功能，先看哪个产品最擅长解决你的主要瓶颈。

**Sudowrite** 更适合把重点放在成熟作者体验的人：构思、规划、写作、改写、整理项目，以及用持久 Story Bible 让作者与 AI 共同参考同一套故事资料。

**NovelCrafter** 更适合需要结构化作者工作区的人：多种 planning view、Codex、系列间共享资料、协作，以及由作者决定 AI 要参与多少。

**NovelClaw** 更适合希望把长篇写作做成“可见工作台”的人：持续 session、run inspection、manuscript / storyboard、人物 / 世界 / style surface，以及可以直接查看和编辑的 memory bank。

**Novel OS** 更适合喜欢明确编辑团队模型的人：central StoryState、Architect → Scribe → Editor → Guardian → Curator 五角色、确定性 continuity pre-check + LLM Guardian、多 provider，以及比较完整的 browser writing studio / export。

**AuthorAgent** 更适合想要本地优先、一站式 author application 的人：从 planning / writing 到 evidence-chained quality check、人物 critic、candidate evolution、长期记忆、出版与导出都在同一套系统里。

**autonovel** 更适合想实验高度自动化全链路的人：seed → world / characters / outline / canon → sequential drafting → evaluation → reader-panel revision → plateau stopping → PDF / ePub / audiobook / landing。

**NovelForge** 更适合这样的项目：真正难的不是“再生成一版文字”，而是**什么是真的、模型可以根据什么推断、什么状态应该跨 run 保留、哪类证据可以改变哪类状态、失败后应该回哪一层修，以及用户接受的正文什么时候才允许真正修改 Canon。**

---

## 02 · NovelForge 真正不同的地方

NovelForge 最重要的差异不是某一个孤立 feature，而是 feature 之间的边界。

### Story authority 明确分级

NovelForge 明确区分 `locked`、`accepted`、`active_plan`、`review` 与 `proposal`，而不是把所有持久故事资料都装进一个统一“source of truth bucket”。

Session memory、model inference、review result、Corpus evidence、scenario branch 和 active plan 都是不同 authority class。

一本书只写几章时，这种严格程度可能显得麻烦；一本书跨几十、上百章之后，这种差异会越来越重要。

### Canon mutation 是 transaction，不是“保存成功”

通过 QA 不会自动写正典；用户说“这一版可以”也不等于 write transaction 已经完成。

`SETTLE` 要求明确 accepted-artifact evidence、write authorization、before-state verification、精确 mutation intent、required projection receipt 与 postcondition。before-state mismatch 或 required projection failure 会得到 `settlement_incomplete`，而不是“差不多成功”。

这比把“保存进 memory / story bible”与“已经成为 Canon”当成同一回事更严格。

### 语义智能与确定性运行时故意分开

当前开发架构把文学 / 叙事理解明确交给 model-readable semantic contracts，并按需渐进加载。

模型负责真正需要阅读理解的问题：人物行动、scene resolution、reader reaction、character integrity、revision diagnosis、long-horizon reconciliation、candidate comparison。

确定性代码负责真正应该精确的东西：permissions、fingerprints、persistence、session / checkpoint、result binding、consume-once、hard budget、rights gate、transaction 与 reproducible build。

Framework 因此不需要让一个 Python heuristic 假装自己是文学批评家。

### 人物行动先于“剧情方便”

`story-simulation` contract 可以先根据人物的 agenda、belief、knowledge、relationship 与 scene evidence 提出人物真正可能做什么，再解析人物行动之间的 scene-level collision。

目标不是让 AI 随机跑角色，而是避免 outline / manager 通过每个人物的嘴完成预定剧情。

### Context 是稀疏、可检查、可控制的

NovelForge 把 Project storage 与 prompt context 分开。Context / Memory 层确定性负责硬预算、provenance、authority class 与作者可见控制；真正需要解释“现在什么相关”时，可以由 semantic contract 判断。

Persistent memory 被当作受治理的 derived view，而不是“系统见过的东西以后就一直偷偷塞进 prompt”。

### Quality 的核心是 failure routing，不是 critic 数量

Surface、Reader、Character、Story、Continuity、Context / Memory、Research 与 Runtime failure 有不同 repair owner。

场景语言很漂亮但完全没劲，可以回 Reader Pressure + Scene Simulation；人物失真回 Character Simulation；场景前提因果错误回 Story / Plan；reviewer 审错 fingerprint 回 runtime validation。

核心不是“多安排几个 critic”，而是**把问题修在真正拥有它的机制上**。

### Revision 可以承认“这一版并没有更好”

Quality Evolution 记录 candidate fingerprint 与 lineage。Model-owned comparison 可以保留 incumbent、接受 challenger，也可以返回 tie。Plateau stopping 允许系统在继续改已经没有真实收益时停止。

### 独立判断不是角色扮演

Semantic judgment 与 independent judgment 是两回事。

只有 rubric 真正要求 independence 时，才要求 separate invocation / session、bounded packet、exact fingerprint binding、typed result，以及稿件实质变化后的 fresh review。有效的 semantic rejection 进入 repair，而不是换 reviewer 直到有人给 PASS。

### 多运行时，但 capability 永远不等于 authority

Current chat、peer chat、本地 Codex / Claude、provider API、MCP worker、GitHub job、本地模型或人工都可以成为 eligible execution route，只要当前 host 真正具备所需 capability。

但技术上“做得到”，永远不等于“有权写 Canon”。

### Learning 必须一直受 evidence 约束

Preference hypothesis、Corpus observation、eval evidence 与 General Craft candidate 彼此分开。Learning 可以被反证、限定作用域、版本化、评测、通过明确 promotion gate 升级，也可以 rollback。

模型不能只猜一次“用户喜欢 X”，就把这个判断永久写进用户口味。

---

## 03 · 别的系统在哪些方面更强

NovelForge 并不是所有维度都领先。

### 成熟作者体验：Sudowrite / NovelCrafter

这两者首先是完整 author product，而不是 engineering framework。

Sudowrite 官方文档把 Story Bible 作为持久故事组织与 AI reference 的核心之一；NovelCrafter 提供 planning mode、Codex、series sharing、collaboration，以及作者自己控制 AI 参与程度。

NovelForge 当前仍然要求用户更接近 Project / runtime system，本身的 author-facing UI 明显没有这些成熟产品完整。

### 可见的长篇工作区：NovelClaw

NovelClaw 把长篇工作的很多状态直接放在 UI 上：sessions、run inspection、manuscript review、storyboard、world / character / style surface、editable memory bank、logs、chapter output 与 downloads。

NovelForge 目前更强调整套 authority / execution contract，而不是提供一个已经非常成熟的作者控制台。

### 一眼就能理解的编辑工作室：Novel OS

Novel OS 的 Architect → Scribe → Editor → Guardian → Curator 很直观，browser studio 也直接覆盖 plan / write / revise、continuity finding 与 export，同时公开支持很广的 provider layer。

NovelForge 刻意不把固定角色团队当作核心架构。好处是 failure routing 和 runtime 更灵活，代价是第一次看上去没有那么“像一个现成的写作工作室”。

### Author / publishing 全链路：AuthorAgent

AuthorAgent 公开描述了 contradiction detection、per-character critic、specialist revision、Prose Evolution、reader panel、durable lesson、long-book memory、KDP-ready DOCX / EPUB3、audiobook preparation、cover 与 publishing / launch tooling。

NovelForge 今天并不打算把整个作者商业 / 出版工作流全部收进 Framework。

### 高自治 artifact production：autonovel

autonovel 明确把 foundation generation、sequential chapter evaluation、automated revision、reader panel、plateau detection、full-manuscript review、typesetting、illustration、audiobook、ePub 与 landing page 连成完整流水线。

NovelForge 在 authority / Project state 上更保守，但在 downstream artifact production 上明显更窄。

---

## 04 · 现在更值得比较的是“机制边界”，不是 feature count

当前小说系统已经普遍开始拥有曾经看起来很稀有的能力：

- persistent story state；
- memory system；
- deterministic continuity check；
- character-focused critic；
- reader panel；
- candidate evolution / stopping condition；
- multi-provider / local model；
- inspectable run；
- long-form workspace。

所以“我们有 memory”“我们有 agents”已经不能构成真正产品差异。

更有意义的问题是：**这份状态到底有什么 authority；模型 interpretation 与 deterministic machinery 如何分开；failure 怎么 route；review result 怎样绑定它实际审的 artifact；中断之后怎样恢复；故事事实改变之前究竟必须发生什么。**

NovelForge 最强的设计下注就在这一层。

---

## 05 · Author product、open fiction studio 与 engineering substrate 不是同一种东西

Sudowrite / NovelCrafter 的中心是作者体验：编辑器、project organization、planning surface、AI assistance、协作与方便。

NovelClaw / Novel OS 越来越接近 open fiction studio：既有较强的小说系统，也有明显可见的作者 workspace。

AuthorAgent / autonovel 则向更宽的 autonomous book pipeline 推进，包括出版产物。

NovelForge 更接近**受治理小说生产的 engineering substrate**：中心是 Project authority、semantic contract、recoverable execution、QA provenance、settlement、learning boundary，以及 Framework / Project reproducibility。

这些类别有交集，但如果硬说它们都在做同一个产品，就会得到很差的比较结论。

---

## 06 · 通用 Agent Framework 放在更深一层比较

LangGraph、OpenAI Agents SDK、AutoGen、CrewAI、Google ADK、MCP ecosystem 与 coding-agent runtime 对 NovelForge 很重要，但主要属于 engineering reference。

它们影响的是：

- durable execution；
- sessions / state；
- typed handoff；
- tool / guardrail contract；
- MCP integration；
- local coding-agent execution；
- resumable workflow；
- multi-runtime capability routing。

但用户在问“我应该用哪个系统运营一部长篇小说”时，它们不应该占据首页主要竞争位。

深入看：[智能体框架采用分析](../knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md)。

---

## 07 · 当这些条件同时出现时，NovelForge 会越来越值

- 小说会跨很多章节、session、model 或 contributor；
- plan、review、accepted fact 与 proposal 的区别很重要；
- character knowledge / agenda drift 是严重风险；
- context 必须可检查、可预算，而不是不断累积；
- 正文生成前应该先解决 scene causality；
- 不同 quality failure 必须回不同 repair owner；
- revision 应该被比较，而不是默认“改了就更好”；
- 某些 judgment 真正需要 fresh independent execution；
- 工作必须跨 external wait、provider change 与 process restart 恢复；
- Accepted Canon mutation 需要 exact before→after transaction；
- 用户口味 / craft learning 需要 evidence、scope、eval 与 rollback；
- 整本小说需要像一个有版本的软件工程项目一样可复现。

---

## 08 · 当这些才是主要需求时，NovelForge 很可能太重

- 快速 brainstorm 一个点子；
- 一两个 session 写完短篇；
- 生成几个不同表达；
- 给已有章节 line edit / polish；
- 希望打开一个成熟 consumer editor 就直接写；
- 主要任务是出版 / 格式化，而不需要额外 authority model；
- 想快速实验，不准备维护 Project contract 与 runtime state。

Exact lock、checkpoint、fingerprint、semantic receipt、authority class 与 settlement transaction 都是 overhead。只有它们真正防住项目关心的失败时，才应该存在。

---

## 09 · NovelForge 当前真实代价

**流程更重。** 显式 authority、checkpoint、fingerprint、contract 与 settlement 比 memory-first assistant 麻烦。

**语义判断有延迟和 usage cost。** 把 model output 套上 typed schema 并不会让文学判断突然免费。

**真正独立的 gate 更贵。** 可能需要另一个 session、provider route、本地 agent 或 human。

**生态与 author UI 更小。** 相比成熟商业写作产品，NovelForge 作为 consumer author application 还很不成熟；相比一些新的开源 fiction studio，可视化工作区也没有那么完整。

**Publishing 不是中心。** DOCX / EPUB、cover、audiobook、launch workflow 目前都不是 NovelForge 的比较强项。

**需要工程纪律。** Multi-runtime 架构只有在 Project authority、capability evidence 与 result binding 始终明确时才真正安全。

这些都是实打实的成本，不是脚注。

---

## 10 · 本页比较的证据规则

比较优先使用当前可访问的第一方产品文档与项目仓库。

主页机制矩阵里的符号定义为：

**● 明确描述** —— 第一方公开材料明确写出了这类机制。

**◐ 邻近机制 / 范围更窄** —— 存在很接近的机制，但公开范围与比较项有实质差别。

**○ 暂未确认** —— 本次检查的公开资料里没有确认。**绝不等于“产品没有”。**

矩阵刻意保守，因为 README / 产品文档本来就不是完整 specification。

### 当前第一方来源

- Sudowrite 文档：`https://docs.sudowrite.com/`
- NovelCrafter：`https://www.novelcrafter.com/`
- NovelClaw：`https://github.com/iLearn-Lab/NovelClaw`
- Novel OS：`https://github.com/mrigankad/Novel-OS`
- AuthorAgent：`https://github.com/Ckokoski/AuthorAgent`
- autonovel：`https://github.com/NousResearch/autonovel`

NovelForge 自己的能力声明仍然以本仓库当前 machine contracts / implementation 为准，本页只是产品解释层，不是第二份 Framework authority。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="52" />
  <br />
  <sub>专用系统只有在它真正匹配你的核心失败模式时，才比更轻的工具更有价值。✦</sub>
</div>

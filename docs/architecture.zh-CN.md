<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="560" />
  <p><strong>架构总览 · 模型负责理解小说，确定性系统负责绑定权威与执行</strong></p>
  <p><kbd>项目权威</kbd>&nbsp;&nbsp;<kbd>语义契约</kbd>&nbsp;&nbsp;<kbd>运行外壳</kbd>&nbsp;&nbsp;<kbd>证据</kbd>&nbsp;&nbsp;<kbd>结算</kbd></p>
  <p><a href="architecture.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge 架构总览

NovelForge 的核心架构选择，是拒绝把**故事事实、模型判断、运行状态与证据**混在一个巨大提示词、一份万能 memory 或一个“全能 Agent”里。

真正需要理解小说的事情交给 AI；必须保持精确、可恢复、可验证的事情交给确定性系统。

<img src="../assets/ui/home-architecture.zh-CN.svg" alt="NovelForge 架构：项目权威、模型语义契约、确定性运行外壳与证据演化彼此分离" width="100%" />

---

## 01 · 用一句话理解整套架构

> **项目拥有故事事实；模型拥有语义解释；确定性运行时拥有执行不变量；证据可以影响判断，但不会因为“已经存在”就自动获得权威。**

这句话几乎解释了仓库里所有重要设计。

会话记住一件事，不代表它进入正典；模型指出人物失真，不代表模型获得写入权限；语料证据可以改变学习假设，却不会自动变成人物知识；Review Draft 即使质量很好，也不会因此直接升级成 Accepted Canon。

---

## 02 · 最高边界是 Project authority

NovelForge 是 Generic Framework。真正消费它的小说 Project 才拥有那本小说的实例与事实。

项目按需要拥有：

- 项目身份与 manifest；
- 锁定的精确 NovelForge revision；
- 项目配置与 prose profile；
- 故事圣经与研究决策；
- Accepted Canon 与当前状态；
- active plan 与 review artifact；
- 人物 / 关系实例；
- manuscripts；
- 项目自己的 regressions 与 tests；
- 明确 acceptance 与 Canon change evidence。

NovelForge 只拥有操作这些结构的通用机制，不能把某个下游项目的剧情、人物或用户私有口味反向吸收到 Generic Framework 里。

因此依赖方向永远只有：

**小说 Project → 精确锁定的 NovelForge**

不能反过来。

深入参考：[项目 SDK](project-sdk.zh-CN.md) · [项目适配器](project-adapters.zh-CN.md) · [正典与状态](../core/CANON_STATE.zh-CN.md)

---

## 03 · 小说机制决定系统必须保存哪些概念

Story、Character / Relationship、Canon / State、Surface 与 Reader 构成 fiction-native 的语义地基。

Story System 负责结构层级、因果压力、开放线索与 story-level failure ownership。

Character / Relationship System 负责人物议程、信念、知识边界、独立行动、关系位置、义务、空间状态与事件余波。

Canon / State 负责区分哪些事实已经 locked / accepted，哪些仍只是 active plan、review 或 proposal。

Surface Fundamentals 与 Reader Engagement 则分别处理**文本实现质量**和**真实阅读体验**，二者不是同一层。

这些是语义 / 结构契约，并不意味着“小说的一切都可以被 Python 确定性计算”。

深入参考：[故事系统](../core/STORY_SYSTEM.zh-CN.md) · [人物与关系](../core/CHARACTER_SYSTEM.zh-CN.md) · [正典与状态](../core/CANON_STATE.zh-CN.md) · [表层质量基础](../surface/FUNDAMENTALS.zh-CN.md) · [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)

---

## 04 · 语义智能采用 contract-first + progressive disclosure

NovelForge 不把所有文学问题塞进一条万能 critic prompt，也不维护一个巨大的 semantic registry。

确定性 catalog 位于：

`harness/semantic_workers/model_contract_catalog.json`

Catalog 只告诉管理器有哪些高层 contract pack，以及什么时候值得加载。Manager / model 先选择最小相关 pack，确定性 runtime 再把**精确 contract ID**解析到唯一 pack。

当前语义域包括：

**Quality** —— 读者反应 / 比较、人物完整性、修改诊断。

**Narrative memory** —— 派生叙事状态、读者预期、记忆整合。

**Learning** —— 创作机制分析与 blind evaluation。

**Context / research** —— 语义上下文选择与 Corpus discovery planning。

**Story simulation** —— 人物行动提案与场景级因果求解。

**Long horizon** —— active plan 协调、relationship memory 协调、narrative commitment audit。

**Creative evolution** —— 场景分叉，以及 incumbent / challenger 的证据比较。

Catalog 故意保持很小。Runtime 不应该代替模型用关键词猜“用户现在属于哪种文学问题”，也不应该默认把所有 pack 全部加载。

深入参考：[语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)

---

## 05 · Semantic result 是受限证据，不是权威升级

每个 semantic job 都有受限输入、rubric、output contract、permissions 与精确 semantic fingerprint。

Fingerprint 描述的是：**对哪份证据提出了哪个语义问题。** 至于任务通过哪个 worker session、provider attempt 或 handoff 执行，则属于单独的 execution lineage。

这种分离可以保证：

- artifact 实质变化后，旧 review binding 自动失效；
- transport retry 不会悄悄改变原来的 semantic question；
- typed validator 可以拒绝 malformed 或错误绑定的 output；
- result 可以按 consume-once 逻辑使用，而不是成为隐藏状态；
- 模型判断可以非常有用，却仍然没有 Canon / Framework write / durable user taste authority。

当某个 gate 明确要求独立性时，semantic execution 还必须来自真正不同的 invocation / session。**independence 是 gate 的额外属性，不是每个 semantic contract 自动拥有的称号。**

深入参考：[语义执行运行时](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)

---

## 06 · 确定性外壳负责执行不变量

Harness 与 runtime code 故意“不聪明”一些，因为它们负责的是需要精确规则的部分。

包括：

- task mode 身份；
- Project / Framework compatibility；
- session、run、checkpoint、event、handoff 身份；
- runtime capability discovery；
- routing constraints；
- artifact / job fingerprints；
- permission checks；
- 生命周期与 consume-once；
- leases、idempotency 与 resume safety；
- hard context / memory budgets；
- typed validation；
- durable Control Plane state；
- rights / provenance gates；
- 可复现 Project / Framework build；
- settlement transaction 与 postcondition。

确定性外壳负责**运输和约束智能**，而不是拿启发式分数冒充文学理解。

深入参考：[Harness](../harness/HARNESS_AGENT.zh-CN.md) · [会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md) · [运行时能力](../harness/session_runtime/RUNTIME_CAPABILITIES.zh-CN.md) · [控制平面](../harness/control_plane/CONTROL_PLANE.zh-CN.md)

---

## 07 · Runtime identity 与 Project identity 必须分开

NovelForge 明确区分四个经常被混在一起的概念：

**Resource / Project** —— 真正长期存在、被操作的项目资源。

**Session / Thread** —— 持续协作或执行上下文。

**Run / Invocation** —— 一次有边界的具体任务尝试。

**Checkpoint** —— 可以恢复的 before-state 与 pending-work 记录。

provider conversation ID、本地进程、GitHub job、MCP handoff 或 human-review session 都可以参与这套模型，但它们都不是 Project，更不会因此获得 story authority。

这就是为什么外部等待、中断与 provider 切换可以恢复，而 provider history 仍然不会被误当成 Canon。

---

## 08 · Capability 要先证明；Authority 必须另外授予

NovelForge 可以运行在当前聊天、peer chat、本地 Codex / Claude、provider API、MCP worker、GitHub job、本地模型或人工 reviewer 上。

但“运行时叫什么名字”不是 capability proof。当前 host 必须在实际权限、availability 与 usage constraints 下真正提供所需能力。

即便如此：

> **capability ≠ authority**

一个工具技术上能写文件，不代表它有 Canon-write 权限；模型能联网，不代表它有权抓取并存储版权全文；reviewer 能评价文本，也不代表它能执行 SETTLE。

深入参考：[运行时路由](../harness/session_runtime/RUNTIME_ROUTING.zh-CN.md)

---

## 09 · Context 是选择出来的，不是从历史里继承出来的

NovelForge 使用：**完整 Schema，稀疏注入。**

Project storage 可以非常丰富，但每一次 invocation 只接收当前 contract 真正需要的部分。

上下文可能包含 Accepted state、active plan、相关人物 / 关系状态、研究证据、长程承诺与派生记忆，但只有当前工作需要时才进入工作集。

如果“哪些信息现在最相关”本身需要语义理解，则由 `context.select` 这样的 model contract 判断。确定性 Context runtime 仍然负责预算、来源、authority class 与封装约束。

Persistent memory 也遵守同样边界。Memory Bank 与 memory tiers 是作者可见的 derived control layer，不是第二份 Canon database。受保护的 `accepted` / `locked` 内容不能被 memory tooling 静默改写。

深入指南：[上下文与记忆](context-and-memory.zh-CN.md)

---

## 10 · 持久状态按 authority domain 分开

跨 run 持久保存的状态不止一种，但它们不能混成同一锅。

**Project state** 保存 Canon、current state、plans、研究决策、manuscripts 等项目权威记录。

**Runtime state** 保存 sessions、checkpoints、waits、events、handoffs、leases 与 result receipts。

**Learning state** 保存 preference evidence、可修订假设、Corpus gaps、learning candidates、evaluation evidence、promotion history 与 rollback 信息。

**Derived narrative / memory state** 可以压缩或协调证据供以后使用，但默认不具权威，除非 Project 通过允许的边界明确升级。

Domain 可以互相引用；authority 不能隐式跨域。

---

## 11 · Quality architecture = evidence + repair ownership + evolution

NovelForge 的质量系统不是“多跑几个 critic”。

Deterministic QA 证明机器可以证明的不变量。

Surface / Reader 机制定义通用质量问题。

Model-readable quality contracts 产生 reader、character 与 revision evidence。

Typed findings 让问题可以跨候选稿和跨 session 追踪。

Repair ownership 把缺陷送回真正的 Story、Plan、Scene、Character、Reader Pressure、Surface、Continuity、Context / Memory、Research、Runtime 或 Human escalation。

Quality Evolution 保存 candidate fingerprint 与 lineage，让 incumbent 和 challenger 可以被显式比较；修改可以出现 tie，也可以在 plateau 停止，而不是假设每一轮都在进步。

深入参考：[质量保障](quality-assurance.zh-CN.md) · [质量演化](quality-evolution.zh-CN.md)

---

## 12 · 长程状态是可重建证据，不是第二套 Canon

连载小说需要跨很多章节记住变化，但“长期记忆”如果只是不断堆模型 summary，很容易变成另一份未经授权的事实库。

NovelForge 因此把 long-horizon view 当作 source-bound derived evidence。

Semantic contracts 可以：

- 因果自然演化后协调 active plan；
- 用证据协调冲突的 relationship memories；
- 审核明确 narrative commitments；
- 从 reader-visible text 解释当前读者预期；
- 整合可重建的派生 memory。

确定性 state graph / ledger 可以保存结构与 provenance，但这些 derived view 默认都没有 Canon authority。

---

## 13 · Evidence、Corpus 与 Learning 永远在故事事实之外

Corpus Intelligence 与 Adaptive Learning 构成的是证据域，而不是一条暗中的内容注入管道。

Corpus 工作把 discovery、access、rights classification、storage、semantic analysis、learning 与 promotion 分成不同门槛。能搜到一个来源，不等于有权保存或再分发它。

Learning 则把 evidence 与 hypothesis 分开，又把 hypothesis 与 promotion 分开。单纯 model inference 不能自动成为 durable user taste 或 General Craft。

General Craft 需要更强证据，例如跨作品支持、反例或 profile boundary、eval coverage、provenance、versioning、rollback 与 green deterministic validation。

Corpus evidence 和 learning output 都不会自动成为 Canon 或 character knowledge。

深入参考：[语料智能](../corpus/README.zh-CN.md) · [自适应学习](adaptive-learning.zh-CN.md)

---

## 14 · Settlement 是唯一的高权威写入路径

Generation、semantic review、quality gate 和 user acceptance 本身都不会直接写 Canon。

`SETTLE` 使用确定性 transaction runtime，要求明确 accepted-artifact evidence 与明确 write authorization。Runtime 负责 compare-and-swap before-state、精确写入、rollback、required projection receipts、postconditions、idempotency，以及 `complete` / `settlement_incomplete` 生命周期。

它明确**不会**自己推断文学意义、用户是否接受、State Delta 是什么。

这些语义 / Project 逻辑必须在进入 transaction 之前已经产生精确 before→after intent。

因此：

**候选稿生成 → 用户审阅 → 明确接受 → Canon mutation**

始终是不同 authority transition。

---

## 15 · Release 与文档也遵守同一条 source-of-truth 原则

面向人的图与说明只是 presentation / explanation layer，不能变成第二套架构权威。

产品页可以用 Story Loom branded visual 帮助理解，但真正的 machine contract 仍然保存在 JSON / YAML / Python 与 deep protocol 中。

当 implementation、manifest 与 human docs 不一致时，这是一项需要暴露和修复的 release-quality drift，而不是由文档作者自行“挑一个看起来最新的说法”掩盖过去。

历史 specs 与 changelog 也因此必须保留历史语义，不能为了当前产品叙事被改写。

---

## 16 · 最值得记住的架构不变量

整套系统可以浓缩成几条：

**Project → pinned Framework，不能反向依赖。**

**Storage ≠ prompt context。**

**Memory ≠ Canon。**

**Model judgment ≠ write authority。**

**Capability ≠ authority。**

**Review ≠ acceptance。**

**Acceptance ≠ settlement complete。**

**Corpus evidence ≠ story truth。**

**Learning hypothesis ≠ durable rule。**

**Deterministic runtime ≠ literary intelligence。**

如果需要按子系统查看 ownership、边界和 exact reference，继续阅读 [架构图谱](architecture-atlas.zh-CN.md)。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <br />
  <sub>权威保持显式，智能保持有界，让小说本身自由地鲜活起来。✦</sub>
</div>

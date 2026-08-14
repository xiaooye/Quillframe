<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="560" />
  <p><strong>架构图谱 · 不翻源码目录，也能知道每个子系统到底负责什么</strong></p>
  <p><kbd>PROJECT</kbd>&nbsp;&nbsp;<kbd>小说机制</kbd>&nbsp;&nbsp;<kbd>语义智能</kbd>&nbsp;&nbsp;<kbd>运行时</kbd>&nbsp;&nbsp;<kbd>质量</kbd>&nbsp;&nbsp;<kbd>证据</kbd></p>
  <p><a href="architecture-atlas.en.md">English</a> · <a href="architecture.zh-CN.md">架构总览</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# 架构图谱

[架构总览](architecture.zh-CN.md) 解释 NovelForge 的几个大权威域怎样协作。本页回答更具体的问题：**某一个真实问题到底归哪个 subsystem 管，它明确拒绝管什么，精确契约又在哪里？**

<img src="../assets/ui/home-architecture.zh-CN.svg" alt="NovelForge 系统图：项目权威、语义契约、确定性运行外壳与证据域彼此分离" width="100%" />

---

## 01 · Project SDK 与 Project Adapter

**负责：** 下游小说项目的工程契约，包括项目身份、`novelforge.toml`、精确 dependency lock、standard / mapped layout、校验、deterministic project build，以及逻辑 Project path 的解析。

**明确不负责：** Generic Framework 不能变成某一本小说的数据库；Adapter 即使能够解析某个文件，也不能因此悄悄改变该文件的 authority。

新建 / 校验 Project 时看 SDK；现有成熟仓库想保留原目录结构时看 Adapter。

参考：[项目 SDK](project-sdk.zh-CN.md) · [项目适配器](project-adapters.zh-CN.md) · [项目适配器协议](../harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md)

---

## 02 · Canon / State 与 Settlement Runtime

**负责：** authority class，以及从“用户明确接受的 artifact”进入“授权 Project write”的高权威事务。

Canon / State 区分 `locked`、`accepted`、`active_plan`、`review` 与 `proposal`；具体 precedence 仍由下游 Project 自己定义。

Settlement Runtime 只负责事务机制：明确 acceptance receipt、accepted-artifact fingerprint、checkpoint / write authorization、精确 create / update / delete intent、before-state compare-and-swap、rollback、required projection receipt、idempotency 与 postcondition verification。

**明确不负责：** settlement 不会自己推断用户是否接受、State Delta 是什么、哪句话应该变成 Canon。Review result、memory、semantic verdict、Corpus evidence 或 scenario branch 都不能自动把自己写进正典。

参考：[正典与状态](../core/CANON_STATE.zh-CN.md) · `harness/settlement_runtime.py`

---

## 03 · Story System

**负责：** 故事结构层级、story-level pressure、因果推进、open loops、dependencies 与 story-level repair ownership。

NovelForge 可以表达 `BOOK → VOLUME → ARC → UNIT → CHAPTER → SCENE`，但这只是通用结构能力，不代表每个项目必须采用同一种叙事风格。

**明确不负责：** 人物私有知识、最终文本 realization 或自动 Canon settlement。

如果场景前提本身因果不成立，问题应该回 Story / Plan，而不是在句子层继续修。

参考：[故事系统](../core/STORY_SYSTEM.zh-CN.md)

---

## 04 · Character & Relationship System

**负责：** 人物议程、信念、知识边界、独立行动、声线归属、空间 / task state、利益、义务、关系位置，以及情绪 / 事件余波。

**明确不负责：** manager knowledge、reader knowledge、author intent，或者“因为 outline 里这样写了，所以人物就应该这样反应”。

这套系统存在的意义，就是让重要人物可以拒绝、误解、临场改变、追求自己的利益，而不是成为计划的执行函数。

参考：[人物与关系系统](../core/CHARACTER_SYSTEM.zh-CN.md)

---

## 05 · Story-Simulation 语义契约包

**负责的语义判断：** 写正文前的人物行动与场景级因果求解。

当前 pack 包含：

- `character.action_propose` —— 根据 typed character / relationship / scene evidence 提出真正属于人物的可能行动；
- `scene.resolve_actions` —— 把这些行动和世界约束彼此碰撞，解析成因果事件轨迹。

**明确不负责：** deterministic routing、Project authority 或 Canon mutation。模型负责提出语义结果；manager / runtime 负责封装有界任务并验证结果。

来源：`harness/semantic_workers/contracts/story-simulation.json`

---

## 06 · Context Inspector、Memory Tiers 与 Memory Bank

**确定性负责：** 上下文来源、硬预算、memory authority class、显式 pin / reprioritize / invalidate 控制，以及 protected-memory edit 边界。

如果“什么内容现在最相关”本身需要理解文本，则语义选择属于 `context-research` pack 的 `context.select`。

**明确不负责：** 伪文学 relevance score、黑盒自动 prompt injection 或 Canon mutation。对受保护 `accepted` / `locked` 内容的编辑，必须降级成无权威 proposal，而不是直接改故事事实。

指南：[上下文与记忆](context-and-memory.zh-CN.md)

实现：`harness/context_inspector.py` · `harness/memory_tiers.py` · `harness/memory_bank.py`

---

## 07 · Semantic Contract Catalog

**负责：** 发现 semantic contract pack 所需的最小确定性索引。

`harness/semantic_workers/model_contract_catalog.json` 是**唯一 registry index**。它只描述 pack、contract IDs 与 load condition。Manager / model 选择最小相关 pack；runtime 再把 exact contract ID 解析到唯一 pack。

当前 pack family 包括：

- quality；
- narrative-memory；
- learning；
- context-research；
- story-simulation；
- long-horizon；
- creative-evolution。

**明确不负责：** 用关键词替模型猜文学意图、默认加载全部 contract，或者由 runtime 自己决定语义意义。

参考：[语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)

---

## 08 · Semantic Worker Router 与 Execution Runtime

**确定性负责：** exact contract resolution、有界 semantic job packaging、permissions、semantic fingerprint、typed result validation、provider-neutral execution lineage，以及 consume-once result handling。

Adapter 可以把任务送往本地 agent、provider API、peer-chat relay、MCP / service path 或其他 eligible transport。

**明确不负责：** literary judgment。Runtime 只验证契约与结果形状；真正理解小说的是模型。

它也不假装每一次 semantic call 都天然独立。只有当前 gate 真正要求 independence 时，才强制不同 invocation / session。

参考：[语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md) · [语义执行运行时](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)

---

## 09 · Harness Manager 与 Orchestration

**负责：** 一个 primary `task_mode`、Framework / Project bootstrap、稀疏上下文、capability resolution、checkpoint 时机、bounded specialist、semantic-pack selection、external wait、failure routing、gate ordering、result validation，以及真实 user-visible completion state。

**明确不负责：** Project story facts 或伪造 independent judgment。Manager 是协调器，不是第二份 Canon database，也不能在同一 invocation 里换个角色就自证 independent gate。

参考：[Harness 管理器](../harness/HARNESS_AGENT.zh-CN.md) · [编排协议](../harness/ORCHESTRATION_PROTOCOL.zh-CN.md)

---

## 10 · Session Runtime

**负责：** `resource / project`、`session / thread`、`run / invocation` 与 `checkpoint` 的持久身份和恢复语义。

它保存 workflow cursor、wait、before-state、handoff binding 与 resume 所需 evidence，让长任务可以跨进程 / provider 边界继续。

**明确不负责：** Canon。Provider conversation ID 或长期 chat session 仍然只是 runtime metadata。

参考：[会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md)

---

## 11 · Runtime Capabilities 与 Routing

**负责：** 当前 host 到底真正具备哪些能力，以及每个能力的 permission、availability、user-interaction requirement、model-execution capability 与 usage constraints。

Runtime Routing 只能在这些能力被证明之后，选择 eligible execution path。

**明确不负责：** authority。Provider 名称不是 capability proof；capability 也不是 Canon-write permission。

参考：[运行时能力](../harness/session_runtime/RUNTIME_CAPABILITIES.zh-CN.md) · [运行时路由](../harness/session_runtime/RUNTIME_ROUTING.zh-CN.md)

---

## 12 · Durable Control Plane

**负责：** 外部 / 并行工作的 operational state：events、handoffs、bounded leases、result receipts、idempotency、lifecycle、provenance 与 logical consume-once。

**明确不负责：** semantic validity、Project authority 或 story direction。Worker result 回来后，仍然必须经过真正拥有它的 semantic / authority contract。

参考：[控制平面](../harness/control_plane/CONTROL_PLANE.zh-CN.md)

---

## 13 · Surface Fundamentals 与 Reader Engagement

这是两层不同的 generic quality mechanism。

**Surface Fundamentals 负责：** 反复出现的 prose-realization failure，以及“局部修”还是“整场重做”的边界。

**Reader Engagement 负责：** 压力、回报、因果运动、反差、reader reward、关系移动、forward pull 与 SAFE-BUT-FLAT。

**它们明确不负责：** story authority 或 deterministic runtime invariant。Reader problem 可以回到 scene design；一份 surface-clean candidate 仍然可能是很差的小说。

参考：[表层质量基础](../surface/FUNDAMENTALS.zh-CN.md) · [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)

---

## 14 · Quality Semantic Pack 与 Findings

`quality` pack 当前提供：

- `reader.reaction`；
- `reader.compare`；
- `character.integrity`；
- `revision.diagnose`。

Typed findings 把语义诊断变成可追踪 evidence，并绑定到精确 artifact / evidence context。

**明确不负责：** 自动 repair、自动 independent-gate status 或 Canon authority。Reader simulation 默认是诊断证据；只有另外的 workflow 明确要求 independence 时，才额外满足独立门槛。

参考：[质量保障](quality-assurance.zh-CN.md) · `harness/semantic_workers/contracts/quality.json` · `quality/findings.py`

---

## 15 · Quality Evolution 与 Creative Evolution

**Quality Evolution ledger 确定性负责：** candidate fingerprint、parent lineage、repair owner、comparison identity、result binding、当前 incumbent 与 plateau counter。

**Creative Evolution pack 负责的语义判断：**

- `scene.diverge` —— 真正不同的因果场景探索；
- `quality.compare` —— incumbent / challenger 比较，可以选择任一方，也可以返回 tie。

**明确不负责：** deterministic ledger 不会自己判断文学质量；comparison winner 也不会获得 Canon authority。

指南：[质量演化](quality-evolution.zh-CN.md)

实现：`quality/quality_evolution.py` · `harness/semantic_workers/contracts/creative-evolution.json`

---

## 16 · Narrative Memory 与 Long-Horizon Pack

这两组契约负责解释长期叙事证据，但不会创建第二套 Canon。

**Narrative Memory** 可以处理 source-bound narrative interpretation、`reader.expectations` 与可重建 memory consolidation。

**Long Horizon** 可以处理 `plan.reconcile`、`relationship.memory_reconcile` 与 `continuity.commitment_audit`。

**明确不负责：** derived narrative state、reader expectations、relationship memory、scenario branch 与 state-graph result 默认都没有 Canon authority；只有 Project 通过明确授权边界才能真正升级事实。

来源：`harness/semantic_workers/contracts/narrative-memory.json` · `harness/semantic_workers/contracts/long-horizon.json`

---

## 17 · Adaptive Learning

**负责：** durable evidence、可修订 preference hypothesis、contradictions、applicability boundary、Corpus gap、learning candidate、evaluation evidence、promotion history 与 rollback。

语义学习工作位于 `learning` pack；deterministic learning store / cycle 负责状态迁移和 promotion precondition。

**明确不负责：** 单纯 model inference 不能自动变成 durable user taste；promotion evidence 也不会自己获得 Framework-write authority。

参考：[自适应学习](adaptive-learning.zh-CN.md) · [自我改进协议](../harness/SELF_IMPROVEMENT_PROTOCOL.zh-CN.md)

---

## 18 · Corpus Intelligence

**负责：** evidence discovery planning、source provenance、rights classification、有界 storage / analysis、mechanism observation、counterexample 与 cross-work benchmark。

`context-research` pack 的 `corpus.discovery_plan` 可以提出语义 discovery plan；真正能不能执行、以什么方式执行，仍由 deterministic capability / rights layer 决定。

**明确不负责：** 搜得到不等于可以 ingest；Corpus 不是 Canon；现实事实不会自动变成人物知识；named-author imitation profile 不在允许范围内。

参考：[语料智能](../corpus/README.zh-CN.md) · [语料政策](../corpus/CORPUS_POLICY.zh-CN.md) · [语料入库协议](../corpus/CORPUS_INGEST_PROTOCOL.zh-CN.md)

---

## 19 · Evals

**负责：** deterministic / rubric / hybrid eval case、blind semantic queue、scoring、baseline / release logic，以及真实 judgment 与 `PENDING_MODEL` 的区别。

**明确不负责：** 普通 CI 不能伪造 semantic PASS，也不能静默消耗付费 / 登录态模型额度。

参考：[评测参考](../evals/README.zh-CN.md) · [质量保障](quality-assurance.zh-CN.md)

---

## 20 · Framework Bundle 与 Release Engineering

**负责：** deterministic Framework materialization、exact bundle fingerprint、compatibility evidence、可复现 artifact 与下游 pinning。

**明确不负责：** bundle 不会创建第二份 story database，derived output 也不会因为被打进包里就获得 authority。

参考：[Framework Bundle](../release/FRAMEWORK_BUNDLE.zh-CN.md)

---

## 21 · 用一个问题检查架构有没有开始变糊

如果团队已经回答不出“这个失败到底应该回哪个 subsystem”，架构边界就正在退化。

几个例子：

**人物知道了 future-plan 信息** → Character / Context，必要时继续回 Story / Plan。

**场景语言很顺但完全没劲** → Reader Pressure + Scene Simulation。

**Reviewer 实际审的是旧 fingerprint** → Semantic Runtime / validation。

**修复稿只是不同，没有证据说明更好** → Quality Evolution / `quality.compare`。

**Relationship memory 与 Accepted evidence 冲突** → Long Horizon reconciliation；不能从 memory 反写 Canon。

**一个来源可以搜到，但 rights 不清楚** → Corpus rights / provenance gate。

**用户已经接受正文，但写入前 before-state 变了** → Settlement Runtime → `settlement_incomplete`。

这种明确的 failure routing，才是整套架构真正有价值的地方。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="52" />
  <br />
  <sub>每个 subsystem 只拥有一小块明确职责；真正的安全来自这些职责不会偷偷混在一起。✦</sub>
</div>

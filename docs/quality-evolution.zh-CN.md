<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><kbd>语义判断归模型</kbd>&nbsp;&nbsp;<kbd>证据绑定修复</kbd>&nbsp;&nbsp;<kbd>平台期停止</kbd></p>
</div>

# 质量演进 · 改进候选稿，但不假装“改得越多越好”

NovelForge 明确拆开**文学语义判断**与**质量状态机器**。模型通过受限、可读的语义契约完成需要理解正文的判断；确定性代码负责可见性、权威、指纹、预算、类型验证、持久化、单次消费与修订状态。

> **核心不变量 ✦** Python 可以约束、持久化、路由、验证和执行事务；它不会因为质量工作流需要判断文学效果，就自动变成文学评论家。

---

## 01 · 质量是一组不同问题，不是一个总分

NovelForge 把这些问题分别处理：

- **确定性正确性**：Schema、生命周期、权限、权威、指纹、幂等性；
- **上下文落地**：当前任务是否拿到了真正相关的证据，同时没有越过视角边界；
- **表层实现**：正文是否出现已知的结构性 / 模型失败机制；
- **读者吸引力**：压力、回报、因果、人物投入、清晰度和继续阅读动力；
- **人物完整性**：目标、知识、声线、关系位置、任务与空间一致性；
- **连续性 / 长程完整性**：候选稿是否尊重权威状态与仍然活跃的承诺；
- **独立判断**：只有工作流明确要求独立性时，才需要真正不同的调用 / 会话。

任何单一分数都不能把这些维度压成“客观文学真理”。

---

## 02 · 语义智能属于契约包

[`harness/semantic_workers/model_contract_catalog.json`](../harness/semantic_workers/model_contract_catalog.json) 负责解析按需披露的语义契约包。运行时只暴露当前步骤真正需要的受限输入、rubric、权限、指纹和类型化输出契约。

直接服务质量系统的契约包括：

- `reader.reaction`：一种阅读行为 persona 对单个候选稿的即时体验；
- `reader.compare`：两个候选稿的读者体验比较，可配合交换 A/B 顺序检查位置偏差；
- `character.integrity`：人物目标、知识、声线、关系与任务 / 空间完整性；
- `revision.diagnose`：带证据的失败诊断与 repair owner 归因；
- `reader.expectations`：当前读者问题、承诺、setup 与未偿义务；
- `context.select`：在已经通过可见性过滤的证据块中，按当前任务问题做语义选择。

语义结果只是证据。它不会因为“判断很有说服力”就获得正典写入、框架行为写入或持久用户口味写入权限。

---

## 03 · 上下文是否落地，本身就是质量问题

如果模型看到了错误的证据，再精细的质量判断也不可靠。当前上下文选择因此把**语义相关性**和**确定性可见性**拆开。

[`harness/memory_tiers.py`](../harness/memory_tiers.py) 要求当前任务明确声明：

- `task_mode` 与 `task_goal`；
- 适用时的当前故事点；
- 当前视角类型与视角身份；
- 明确的活跃问题列表。

模型看到候选记忆块之前，确定性代码先剔除与当前视角不兼容的材料。人物视角任务不能因为某条信息“很相关”，就拿到另一个人物的私有知识。即使某条记忆被 pin，只要违反当前视角边界，也会直接失败，而不是偷偷塞进去。

只有完成这一步以后，`context.select` 才判断哪些可见证据真正支持当前问题。确定性打包器只负责硬预算与整块装载，不自行发明文学相关性分数。

责任边界因此很清楚：

```text
可见性 / 权威 / 预算  → 确定性运行时
语义相关性 / 问题支持 → 模型契约
故事事实               → 项目权威
```

上下文支持仍然只是观察，不是正典。

---

## 04 · 读者诊断是证据，不会自动变成门槛

Reader persona 描述的是**阅读行为**，不是人口标签。有效信号可以包括继续阅读意愿、紧张感、节奏、困惑、情绪反应、喜欢 / 卡住的 beat 与弃读原因。

相比伪装成“万能总分”，`reader.compare` 更适合比较候选稿。需要检查位置偏差时，应交换 A/B 顺序再次比较。

必须继续保持这些边界：

- Reader diagnostics 不是正典；
- 单个分数不能独自决定保留 / 丢弃；
- persona 之间的分歧本身是有效证据，而不是应该被平均掉的噪音；
- Reader diagnostics 不会自动满足 mandatory independent gate。

---

## 05 · 人物完整性必须受知识边界约束

`character.integrity` 只接收当前候选稿与已经建立的类型化人物状态，检查目标、知识、声线、关系位置、空间 / 任务状态，以及“一致性中的意外”。

管理器、叙述者、读者、研究材料和模型本身知道的内容，都不能自动变成人物知识。人物发生有意变化完全可以成立，但必须有足够的 transition evidence。

结果是一条 finding，不是人物状态写入。

---

## 06 · 先诊断，再修订

`revision.diagnose` 的目的就是阻止无目标的“整体 polish”。它先找出真正的失败，再把问题送回拥有修复责任的机制。

典型 ownership：

- 单个 surface defect → 局部表层重写；
- Surface failure 成簇 → 更大范围的 Surface Realization 重生成；
- SAFE-BUT-FLAT / reader pressure 弱 → Reader Pressure + Scene Simulation；
- character failure → Character Simulation / 人物状态推理；
- story / plan failure → Story / Plan；
- continuity / state failure → 连续性或权威状态修复；
- context failure → 重建稀疏、按问题落地的上下文；
- memory failure → invalidate / rebuild 派生记忆；
- research failure → Research resolution；
- runtime / capability failure → transport / capability 层；
- 无法自动决定的艺术方向 → 用户 / 人类决定。

修原因，不要继续抛光症状。

---

## 07 · 类型化 finding 提供共同证据语言

[`quality/findings.py`](../quality/findings.py) 负责归一化带证据的质量 finding，但它本身不做文学判断。

一条有效 finding 至少应说明：

- 类别与严重度；
- 对象与候选稿；
- repair owner；
- candidate-side evidence；
- 必要时的 authority / state-side evidence；
- source references；
- confidence；
- 不直接修改权威状态的修复 proposal。

Surface、Reader、Character、Continuity、Context、Memory 和 Research 可以共享传输语义，但不会因此被混成同一种失败。

---

## 08 · 候选稿演进是可持久、非单调的

[`quality/quality_evolution.py`](../quality/quality_evolution.py) 负责修订状态持久化，不负责文学判断。

一次典型循环是：

```text
incumbent
→ 定向修复
→ challenger
→ 语义比较
→ validate + consume once
→ challenger 晋级或记录 no-gain
→ 只有仍然有收益时才继续
```

每个候选稿都有内容指纹与父级谱系；每份比较结果都绑定指纹，并且只能被逻辑消费一次。Challenger 必须从当前 incumbent 派生，被声明为 winner 的稿件也必须真的是本次实际比较的 candidate。

真正胜出会重置 no-gain 计数；连续没有收益达到配置阈值以后，循环进入 plateau 并停止。

**修订不是单调变好的。知道什么时候停，本身就是质量控制。**

---

## 09 · Reader Expectation Ledger 保存长程阅读压力

[`quality/reader_expectation.py`](../quality/reader_expectation.py) 保存持久、无权威的读者侧 expectation。语义解释来自 `reader.expectations`，确定性代码只负责身份、持久化、状态转移与证据引用。

一条 expectation 可以表示仍然活跃的：

- 问题；
- 承诺；
- setup / payoff 期待；
- 关系期待；
- 目标；
- mystery 或其他读者侧未偿义务。

未来计划里的 payoff 不代表读者现在已经拥有这个 expectation。Ledger 必须区分当前读者体验与未来意图。

---

## 10 · 质量工作必须既可恢复，也可观察

[`quality/state_graph.py`](../quality/state_graph.py) 保存无权威的质量工作流进度，使中断后能够知道哪些步骤已经完成，而不是靠聊天记忆猜。

Control Plane 还通过 [`harness/control_plane/run_receipt.py`](../harness/control_plane/run_receipt.py) 支持**仅元数据的运行回执**。一份 receipt 可以记录：

- artifact fingerprints；
- context-selection fingerprint；
- 哪些证据块被加载或因视角边界被排除；
- question → evidence 的加载状态；
- semantic job ID、contract ID 与 result fingerprint；
- 确定性 guard 的结果。

它明确**不保存候选正文、private reasoning 或 hidden gold**，也没有正典或记忆权威。

这样可以让质量工作可追踪，同时不制造第二套故事数据库，也不复制整份稿件做“监控副本”。

---

## 11 · 独立审查是条件性的，而且必须真的独立

内部 semantic contract 可以在 manager 工作流里运行。只有 active rubric 明确要求 independence 时，它才成为**独立门槛**。

一旦 independence 是 mandatory，判断必须来自真正不同的合格 invocation / session / runtime，并返回绑定精确 artifact fingerprint 的类型化结果。

有效的 `semantic_reject` 应该触发 repair。它不是 transport failure，也不是不断换 reviewer 直到有人说 PASS 的许可证。

---

## 12 · 它在生产流水线中的位置

证据准备可以发生在草稿之前：解析权威、过滤可见性、定义 active questions、选择稀疏上下文，都会影响后续候选稿是否真正有根据。

**Candidate evolution 本身只有在候选稿已经存在以后才开始。** Regression 坏例与 critic-only evidence 继续保持生成后隔离。语义契约读取受限 packet，确定性基础设施验证并持久化结果，repair 回到 owning mechanism，随后 comparison 再判断修复稿是否真的优于 incumbent。

用户可见产物仍然必须通过当前工作流要求的门槛。用户接受正文以后，正典结算依然是另一笔独立事务。

---

## 13 · 为什么要这样拆

这套拆分同时避免两种常见失败：

**Fake determinism**：用 heuristic 假装判断其实需要文学理解的问题。

**Unbounded model authority**：模型因为判断听起来很合理，就顺手获得 durable truth 写权限。

NovelForge 把边界固定为：

```text
model       → 语义解释
runtime     → 可见性 + packet + 权限 + fingerprint + budget
validator   → 类型与绑定检查
ledgers     → 持久、无权威的证据 / 状态
project     → 正典权威与结算
```

---

## 14 · 相关契约

- [质量保障与 QA](quality-assurance.zh-CN.md)：完整质量栈与发布门槛。
- [生产流水线](production-pipeline.zh-CN.md)：诊断、修复与候选演进在全流程中的位置。
- [上下文与记忆](context-and-memory.zh-CN.md)：稀疏选择、视角可见性与可编辑派生记忆。
- [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)：正向读者质量模型。
- [人物与关系系统](../core/CHARACTER_SYSTEM.zh-CN.md)：人物状态与知识边界。
- [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)：provider-neutral 语义 job/result 契约。
- [Control Plane](../harness/control_plane/CONTROL_PLANE.zh-CN.md)：持久运行时协调与回执。

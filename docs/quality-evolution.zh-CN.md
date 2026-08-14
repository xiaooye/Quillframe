<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><kbd>语义判断归模型</kbd>&nbsp;&nbsp;<kbd>类型化证据</kbd>&nbsp;&nbsp;<kbd>平台期停止</kbd></p>
</div>

# 质量演进 · 模型负责文学判断，确定性代码负责让质量状态可追踪、可恢复

NovelForge 把**文学语义判断**与**质量状态机器**明确拆开。模型通过受限、可读的 semantic contract 阅读正文并作判断；确定性代码只负责打包上下文与权限、验证类型化输出、保存证据和候选稿谱系、执行 fingerprint / consume-once 规则，以及在连续没有收益时停止修订循环。

> **核心不变量 ✦** Python 可以持久化、路由、做指纹、控制预算、验证类型和执行事务；它不会因为质量工作流需要“文学判断”就自动变成文学评论家。

## 01 · 质量是一组不同问题，不是一个总分

NovelForge 把这些问题分别处理：

- **确定性正确性**：Schema、生命周期、指纹、权威、权限、单次消费、幂等性；
- **表层实现**：正文是否出现已知结构性 / 模型失败机制；
- **读者吸引力**：注意力、压力、回报、因果、人物投入与继续阅读动力；
- **人物完整性**：目标、知识、声线、关系位置、任务 / 空间一致性；
- **连续性 / 状态完整性**：候选稿是否与相关权威状态一致；
- **独立语义判断**：工作流明确要求独立门槛时，由真正不同的调用 / 会话完成。

一个 absolute score 不能把这些不同维度压成“客观文学真理”。

## 02 · 语义智能属于 model contract

[`harness/semantic_workers/model_contracts.json`](../harness/semantic_workers/model_contracts.json) 定义受限的语义任务。运行时只提供候选稿、允许使用的上下文、rubric、权限、fingerprint 与类型化输出契约。

当前直接服务质量系统的 contract 包括：

- `reader.reaction`：某一种阅读行为 persona 对单个候选稿的即时阅读体验；
- `reader.compare`：两个候选稿的读者体验对比，可配合交换 A/B 顺序检查位置偏差；
- `character.integrity`：人物目标、知识、声线、关系位置、任务 / 空间状态，以及一致性中的意外；
- `revision.diagnose`：只在指定质量维度上诊断，并把每个失败送回真正拥有修复责任的机制；
- `reader.expectations`：解释当前活跃的读者问题、承诺、setup、关系期待、目标与 mystery。

这些 contract 都明确禁止 Canon write、framework behavior write 和 durable user-taste write。

## 03 · Reader diagnostics 是证据，不会自己变成门槛

模拟读者 persona 描述的是**阅读行为**，不是人口标签。默认行为维度包括：追更 / 前推力敏感、类型熟悉度、移动端注意力、人物投入、回报敏感度。

一次 `reader.reaction` 判断可以报告 continue desire、tension、pacing、confusion、情绪反应、favorite / stumble beat、drop-off point，以及具体原因。

一次 `reader.compare` 会比较 A/B 候选稿的整体偏好、forward pull、character investment 与 reward。需要检查位置偏差时，应交换候选稿可见顺序重复判断，而不是默认第一稿占优是“真实质量”。

必须继续保持这些边界：

- reader diagnostic 不是 Canon；
- 单个 absolute score 不能独自决定 keep / discard；
- persona 之间的分歧本身是有价值的证据，不是应该被平均掉的噪音；
- Reader diagnostics 不会自动满足 mandatory independent semantic gate。

## 04 · Character Integrity 必须保持受限

`character.integrity` contract 只能收到当前 scene excerpt 和已经建立的类型化人物状态。Rubric 明确检查：

`目标一致性 · 知识边界 · 声线 · 关系位置 · 空间/任务状态 · 一致性中的意外`

它不能把 manager、narrator、reader、research 或模型本身知道的东西自动当成人物知识。

如果候选稿提供了足够的 transition evidence，人物有意发生变化完全可以成立。任何 finding 都应同时引用候选稿侧证据与 established-state 证据。

结果只是一条 observation，不会直接修改人物状态。

## 05 · 先诊断，再修订

`revision.diagnose` 的存在就是为了阻止无目标的“整体 polish”。它先判断失败属于哪里，再指定 repair owner。

模型可以区分：

- story；
- plan；
- scene；
- character；
- reader pressure / engagement；
- surface realization；
- continuity / state；
- context / memory；
- research / fact support。

Contract 明确规定：SAFE-BUT-FLAT 不是 line-edit 问题；Surface failure 成簇时也可能需要 scene-level regeneration，而不是继续逐句补丁。

输出包含带证据链的 findings 与 repair sequence，但仍然没有 Canon mutation 权限。

## 06 · 类型化 finding 让不同审查使用同一种证据语言

[`quality/findings.py`](../quality/findings.py) 负责确定性地归一化 evidence-backed quality finding。一个有效 finding 至少应该说明：

- 问题类别与严重度；
- 对象 / candidate；
- repair owner；
- candidate-side evidence；
- 必要时的 authority / state-side evidence；
- source references；
- confidence；
- 不直接修改权威状态的修复 proposal。

这样 Surface、Reader、Character、Continuity、Context、Memory 和 Research diagnosis 可以共用 transport format，同时仍然保持“它们不是同一种失败”。

## 07 · 修真正拥有问题的机制

Quality finding 应回到真正拥有原因的最小修复层：

- 单个 surface issue → 局部 surface rewrite；
- Surface issue 反复成簇 → paragraph / block 或整场景 Surface Realization；
- SAFE-BUT-FLAT / reader-grip failure → Reader Pressure + Scene Simulation；
- character failure → Character Simulation / character-state reasoning；
- story / plan failure → Story / Plan；
- continuity / state failure → 连续性或权威状态修复；
- context failure → 重建稀疏 Context Manifest；
- memory failure → invalidate / rebuild derived memory；
- research failure → Research resolution；
- runtime / capability failure → transport / capability 层；
- 无法自动决定的艺术方向 → human / user decision。

修原因，不要继续抛光症状。

## 08 · 可恢复的候选稿演进

[`quality/quality_evolution.py`](../quality/quality_evolution.py) 负责确定性的 revision-state persistence，不负责文学判断。

一次典型演进是：

```text
baseline candidate
→ challenger
→ model / semantic comparison result
→ validate + consume result once
→ incumbent 更新或 no-gain
→ 下一 challenger
→ plateau / complete
```

每个 candidate 都有 content fingerprint 与 parent lineage；每份 comparison result 也有 fingerprint，并且只能被逻辑消费一次。完全相同的 replay 是幂等的。

Challenger 必须从当前 incumbent 派生。被声明为 winner 的稿件必须真的是本次参与比较的 candidate 之一，或者明确 tie / no-decision。Ledger 不能在判断完成后偷偷替换“到底比的是哪两稿”。

挑战稿真正胜出时，它成为新的 incumbent，no-gain counter 清零；连续没有收益达到配置阈值以后，演进进入 plateau 并停止。

**修订不是单调变好的。能够主动停在平台期，本身就是质量机制。**

## 09 · Reader Expectation Ledger 保存长程读者状态

[`quality/reader_expectation.py`](../quality/reader_expectation.py) 保存持久、无权威的 reader-facing expectation。语义解释来自 `reader.expectations` contract；确定性代码只负责 identity、persistence、state transition 和 evidence refs。

一条 expectation 可以表示仍然活跃的：

- 问题；
- 承诺；
- setup / payoff 期待；
- 关系期待；
- 目标；
- mystery 或其他读者侧未偿义务。

语义 contract 必须区分“读者体验中现在已经存在的 expectation”和“未来 active plan 里准备安排的 payoff”。因此 ledger 不能因为计划里写了一个未来回报，就把它提前当成读者当前事实。

有证据时，expectation 可以被 reinforcement、partial reward、payoff、abandonment 或 dormancy。这个 ledger 没有 Canon authority。

## 10 · State Graph 让质量工作可以恢复

[`quality/state_graph.py`](../quality/state_graph.py) 持久保存无权威的质量工作状态，使中断后的 run 能知道哪些分析 / 修订步骤已经完成，而不是靠聊天记忆猜。

它记录的是工作流进度，不会获得 Canon write authority，也不能替代下游项目自己的 acceptance / settlement。

## 11 · Independent review 仍然是另一份契约

`reader.reaction`、`character.integrity`、`revision.diagnose` 之类内部 semantic contract 即使很有价值，也可能仍然运行在 manager 工作流内部。

当 Harness 明确要求 **mandatory independent semantic gate** 时，判断仍必须来自真正不同的合格 invocation / session / runtime，并返回绑定精确 artifact fingerprint 的 typed result。

Semantic rejection 是有效结果。它应该触发 repair，而不是成为不断换 reviewer 直到有人给 PASS 的理由。

## 12 · 它在生产流水线中的位置

Quality Evolution 只能在候选稿已经存在后开始。

Regression 坏例与 critic-only evidence 继续保持生成后隔离。Semantic contract 读取受限 candidate / context packet，返回 typed judgment；确定性 infrastructure 验证并持久化结果；repair 回到 owning mechanism；candidate evolution 再记录修复稿是否真的击败当前 incumbent。

只有必须的 Surface、Reader、Continuity 与 Independent gate 全部解决后，artifact 才能越过 user-visible gate。用户接受正文以后，Canon settlement 仍然是另一笔独立事务。

## 13 · 为什么要这样拆

把 semantic intelligence 放进 model-readable contract，可以同时避免两个常见失败：

**Fake determinism**：Python heuristic 假装能决定其实需要文学理解的质量问题。

**Unbounded model authority**：模型因为判断听起来很有道理，就顺手获得 durable truth 的写权限。

NovelForge 把边界明确成：

```text
model      → semantic judgment
runtime    → bounded packet + permissions + fingerprint
validator  → typed-result checks
ledgers    → durable non-authoritative state
project    → Canon authority + settlement
```

## 14 · 相关契约

- [质量保障与 QA](quality-assurance.zh-CN.md)：完整质量栈与 release gate。
- [生产流水线](production-pipeline.zh-CN.md)：diagnostics 与 repair 在全流程中的位置。
- [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)：通用正向 reader-quality model。
- [人物与关系系统](../core/CHARACTER_SYSTEM.zh-CN.md)：Character Integrity 判断所依据的人物状态与知识边界。
- [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)：provider-neutral semantic job/result contract。
- [`model_contracts.json`](../harness/semantic_workers/model_contracts.json)：当前 model-readable semantic registry。

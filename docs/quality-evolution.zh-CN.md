<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><kbd>读者证据</kbd>&nbsp;&nbsp;<kbd>回到问题所属机制</kbd>&nbsp;&nbsp;<kbd>平台期停止</kbd></p>
</div>

# 质量演进 · 让候选稿真正变好，而不是无限“再改一版”

NovelForge 7.2 把修订从一串松散的“critic prompt”升级成可检查的质量演进系统。不同机制可以提供诊断，但最终都落到统一的类型化 finding；修复必须回到真正拥有问题的机制；候选稿比较可以恢复、可以追踪；连续没有收益时，系统能够主动停止。

> **核心不变量 ✦** 质量信号可以诊断、反对甚至拒绝一个候选稿，但它不会因此获得正典权威；换一个 persona 跑同一个模型，也不会凭空变成“独立审查”。

## 01 · 质量是一组不同问题，不是一个总分

NovelForge 把这些问题明确分开：

- **确定性正确性**：Schema、生命周期、指纹、权威、幂等性；
- **表层实现**：正文是否出现已知结构性 / AI 化失败机制；
- **读者吸引力**：压力、回报、因果、人物投入与继续阅读动力；
- **人物完整性**：目标、知识、声线、关系位置、空间与任务状态；
- **连续性 / 状态完整性**：候选稿是否与相关已接受事实和当前状态一致；
- **独立语义判断**：工作流明确要求独立门槛时，由真正不同的调用 / 会话完成。

因此，一个“8.4 / 10”不能假装把这些不同维度压成客观真理。

## 02 · 模拟读者面板是诊断证据

`quality/reader_panel.py` 负责打包受限的模拟读者任务。默认 persona 描述的是**阅读行为**，而不是人口属性标签，例如：追更型、类型熟悉型、移动端轻阅读型、人物投入型、回报敏感型。

面板既可以观察单个候选稿，也可以做 A/B 对比。信号包括：

继续阅读意愿、紧张度、节奏、困惑、情绪反应、最喜欢 / 最卡顿的段落、前推力、人物投入、回报感、可能弃读的位置。

A/B 比较会交换候选稿的可见顺序，以便发现 first-position bias，而不是让先展示的一稿天然占便宜。

聚合层还会检查不同 persona 的分歧，以及理由是否异常模板化。共识有价值；分歧同样有价值，因为它能指出**不同阅读目标从哪里开始分叉**。

**重要：** Reader Panel 只提供诊断证据。它既不是正典门槛，也不能单独满足强制独立语义审查。

## 03 · 类型化 finding 让不同审查说同一种“工程语言”

不同质量机制最终都会把观察归一成带证据链的 finding。每条 finding 至少说明：

- 问题类别与严重度；
- 对象；
- 修复应该归谁负责；
- 候选稿侧证据；
- 必要时的权威 / 状态侧证据；
- 来源引用；
- 置信度；
- 不直接修改权威状态的修复建议。

这样，连续性、人物、读者、表层、研究、上下文和记忆问题可以汇入一个修订层，同时仍然保留“它们根本不是同一种失败”的区别。

## 04 · 人物完整性审查只拿真正需要的上下文

`quality/character_integrity.py` 只打包当前场景片段和类型化人物状态。它明确拒绝 private reasoning、chain-of-thought、hidden gold、writer scratchpad 和 regression 坏例。

审查维度包括：

`目标一致性 · 知识边界 · 声线漂移 · 关系位置 · 空间/任务状态 · 意外反应的一致性`

结果只是带证据的观察，不会直接修改人物状态，也不会自动冒充独立审查。

## 05 · Revision Orchestrator 负责窄范围审查与归因

`quality/revision_orchestrator.py` 是确定性编排层，不是文学裁判。只有具备对应前置证据时，它才安排这些窄范围 pass：

`连续性 · 人物 · 读者 · 表层 · 研究/事实`

某个 pass 缺前置条件时，只跳过那个 pass，不让无关审查一起失败。

完成后的 finding 会去重，并按照 **repair owner / 问题所属机制** 分组。核心修复规则是：

- 单个表层问题 → 局部改写；
- 表层问题成簇 → 整场景重新生成；
- 读者抓力不足 / SAFE-BUT-FLAT → 回到 Reader Pressure + Scene Simulation；
- 人物失败 → 回到 Character Simulation；
- 故事 / 计划失败 → 回到 Story 或 Plan；
- 连续性 / 状态失败 → 修复连续性或状态；
- 上下文失败 → 重新构建稀疏上下文；
- 记忆失败 → 让派生记忆失效并重建；
- 研究失败 → 回到研究解析；
- 运行时失败 → 修复 transport / capability；
- 方向本身无法自动决定 → 交给人。

系统修的是原因，而不是继续打磨症状。

## 06 · 可恢复的候选稿演进

`quality/quality_evolution.py` 用确定性的 SQLite ledger 保存修订过程：

**基线候选稿 → 挑战稿 → 对比 → 当前最优稿 → 下一挑战稿 → 平台期 / 完成**

每个候选稿都有内容指纹和父子谱系；每次比较结果也有指纹，并且只能被逻辑消费一次。完全相同的重放是幂等的。

挑战稿必须从当前 incumbent 派生；胜者只能是本次真正参与比较的候选稿之一，或者明确的平局 / 无决定。这样就不能在比较完成后偷偷换掉“到底比的是哪两稿”。

挑战稿真正获胜时，它成为新的 incumbent，并清零无收益计数。连续无收益达到阈值以后，演进状态进入 `plateau` 并停止。

这很重要，因为修订并不是单调变好的。“让模型继续改，直到它自己觉得够了”不是质量策略。

## 07 · 独立审查仍然必须真的独立

Reader persona、人物完整性审查、内部 critic pass 都可以很有价值，但它们仍然属于 manager 工作流的一部分。

如果 Harness 当前任务要求强制独立语义门槛，判断仍然必须来自真正不同的合格调用 / 会话 / 运行时，并返回绑定精确 artifact fingerprint 的类型化结果。

`semantic_reject` 是有效结论。它应该触发修复，而不是成为不断换 reviewer 直到有人给 PASS 的理由。

## 08 · State Graph 与可恢复性

`quality/state_graph.py` 为质量工作流提供显式、无权威的状态图，让中断后的工作能够知道哪些分析 / 修订步骤已经完成，而不是靠聊天记忆猜。

这类 durable state 只记录“流程走到哪里”，不会获得正典写权限，也不会替代下游项目自己的接受与结算规则。

## 09 · 它在生产流水线中的位置

Quality Evolution 只能在候选稿已经存在后开始。Regression 坏例和只供 critic 使用的证据继续保持生成后隔离。随后，模拟读者、人物完整性和其他受限审查产生 findings；Revision Orchestrator 决定问题应该回哪一层修；candidate evolution 再记录这次修复是否真的打败当前 incumbent。

只有必须的质量、连续性和独立门槛都解决以后，稿件才可以越过用户可见门槛。用户接受正文之后，是否写入正典仍然是另一笔独立的结算事务。

## 10 · 继续阅读

- [质量保障与 QA](quality-assurance.zh-CN.md)：完整质量栈与发布门槛。
- [生产流水线](production-pipeline.zh-CN.md)：诊断与修订在全流程中的位置。
- [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)：通用 Reader Engagement 机制。
- [`reader.reaction` / `reader.compare` model contracts](../harness/semantic_workers/model_contracts.json)：模拟读者诊断语义。
- [`revision.diagnose` model contract](../harness/semantic_workers/model_contracts.json)：诊断与修复归因语义。
- [`quality/quality_evolution.py`](../quality/quality_evolution.py)：持久候选稿演进 ledger。
- [`character.integrity` model contract](../harness/semantic_workers/model_contracts.json)：受限人物完整性语义。

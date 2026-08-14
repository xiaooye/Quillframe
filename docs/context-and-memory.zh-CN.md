<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><strong>上下文与记忆 · 让作者看得见工作集，也让“记住了”永远不会冒充“发生了”</strong></p>
  <p><kbd>语义选择</kbd>&nbsp;&nbsp;<kbd>权威检查</kbd>&nbsp;&nbsp;<kbd>硬预算</kbd>&nbsp;&nbsp;<kbd>作者控制</kbd>&nbsp;&nbsp;<kbd>可重建记忆</kbd></p>
  <p><a href="context-and-memory.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 上下文与记忆

NovelForge 明确区分四件经常被混在一起的东西：**项目里存了什么、这次运行允许看到什么、模型认为当前什么最相关、哪些内容只是可重建的派生记忆。**

当前实现故意把语义选择与确定性控制拆开：

> **“什么对当前任务真正相关”由模型通过 `context.select` 判断；权威等级、阶段隔离、作者显式控制、来源绑定、硬预算、整项装载与受保护编辑规则由确定性代码负责。**

这样可以避免一个旧摘要、会话笔记或启发式“相关度分数”悄悄变成 prompt truth，更不会让它升级成 Canon。

---

## 01 · 先分清四层

**项目权威**回答：这本小说里什么是真的？`accepted` / `locked` 事实仍然由 Project 拥有。

**Context Manifest**回答：哪些材料在当前 run、当前 stage 下具备进入上下文的资格？

**语义选择**回答：在这些合法候选里，哪些内容对当前任务真正有用？这属于模型解释，通过 `context.select` 完成。

**Memory Bank**保存运行时、派生或 proposal 型记忆，并记录 provenance 与版本；它可以引用 Canon，却不是第二份 Canon database。

最简单的心智模型是：

**存储 → 合法候选 → 语义选择 → 硬预算装载 → 模型工作上下文**

每一个箭头都有不同 owner。

---

## 02 · Context Inspector 检查权威与资格，不判断文学相关度

`harness/context_inspector.py` 实现 `novelforge_context_inspector_v2`。

每条 Context Manifest item 会被规范化为可检查字段，例如：

- 稳定 ID 与内容类别；
- source reference 与 source fingerprint；
- authority class；
- inclusion reason；
- 允许进入的 stages；
- 显式 numeric priority；
- pinned 状态；
- 是否为 derived view；
- hidden / invalidated 状态；
- 调用方附带的 metadata。

Inspector **明确拒绝 `relevance` 字段**。语义相关性不是一项确定性 manifest 属性。

确定性排序只遵守：

**pinned → explicit priority → stable ID**

这代表作者 / runtime 的显式控制，不代表系统声称“这条信息在文学上比另一条更重要”。

---

## 03 · Stage isolation 防止错误证据污染 Writer

Context item 可以声明允许进入的 stage：

`writer_pre_draft` —— 可以影响首轮正文生成；

`post_draft_critic` —— 只有候选稿出现以后才合法，例如相关 regression evidence；

`independent_reviewer` —— 可以封装进真正独立审查的 bounded packet；

`never` —— 可以持久保存，但不得自动注入。

Regression、hidden gold、expected verdict、answer key 等 sensitive class 如果被放进 `writer_pre_draft`，Inspector 会直接拒绝。

这是一条确定性 contamination boundary，不需要靠模型“自觉不要偷看”。

---

## 04 · 真正的语义筛选属于 `context.select`

当合法候选材料多于当前任务真正应该接收的内容时，NovelForge 会准备一个受限的 `context.select` semantic job。

`harness/memory_tiers.py` 只把 task context 与 typed memory blocks 交给模型。模型返回 hot / working / archive 的有序 ID；确定性 runtime 再用 exact semantic-job fingerprint 验证结果。

这意味着：

- 模型可以解释“现在什么最相关”；
- runtime 只允许模型选择已知、未失效的候选 item；
- stale 或错误绑定的 semantic result 会被拒绝；
- 某条 memory 被选中，并不会因此获得更高 authority。

该 contract 通过 `context-research` semantic pack 按需解析。

---

## 05 · 硬预算装载仍然由确定性代码负责

语义选择完成后，`memory_tiers.py` 才执行 deterministic packing。

它负责：

- `hot_budget` 与 `working_budget`；
- pinned item override；
- derived-memory `authority=false` 检查；
- source refs / source fingerprints；
- whole-item-or-skip 装载；
- invalidated item 排除；
- archive 输出。

它**不会**自己总结 Canon、给故事相关性打分，也不会为了塞进预算而把一个有完整语义边界的 memory block 截成模糊残片。

Pinned item 如果连 hot budget 都放不下，运行应该失败并暴露控制冲突，而不是悄悄丢掉作者明确固定的内容。

实现返回值直接写明：

- `selection_owner = model`
- `budget_owner = deterministic_runtime`

---

## 06 · 作者控制是 overlay，不是 Canon write

Context Inspector 支持的低权威控制包括：

- pin / unpin；
- 调整显式 priority；
- 隐藏 derived view；
- invalidation derived view，要求以后重建。

这些操作只改变**选择和呈现行为**。

Hide / invalidate 只允许作用于 derived view。调用方不能靠 overlay 让 Project authoritative fact “从现实里消失”。

Overlay 本身也有 fingerprint，方便追踪控制变化。

---

## 07 · 修改受保护事实时，只能生成 proposal

如果用户通过 Context / Memory 控制面要求修改 `locked` 或 `accepted` item，`context_inspector.py` 不会直接改 source。

它会创建 proposal，并记录：

- proposal ID；
- source item ID；
- 原 authority；
- requested patch；
- `proposal_required`；
- `direct_mutation_performed = false`；
- `canon_write = false`。

这允许作者表达“我想改这个事实”，同时不会让 UI 假装“这个事实已经改进正典”。

真正的 Canon mutation 仍然必须经过 Project 明确接受与 Settlement。

---

## 08 · Memory Bank 是持久工作记忆，不是影子正典

`harness/memory_bank.py` 可以保存 context、character、relationship、thread、style、learning、runtime、corpus、derived 等不同 memory domain。

记录会保留 provenance、fingerprint、version、authority metadata、显式控制与 edit history。

两种编辑路径必须分开：

**运行时 / 派生记忆**可以在 version / fingerprint precondition 下编辑。

**受保护 Canon reference** 仍然是只读引用；修改请求只能形成 proposal，不能原地写回 authoritative source。

只要条件允许，derived memory 都应该能够从 source evidence 重建。

---

## 09 · Memory 永远不能证明故事事实或人物知识

Memory 很有用，但它不是证据终点。

它不能证明：

- 某个事件已经发生；
- 某个人物已经知道某个事实；
- 某段关系已经正式改变；
- 某个计划已经被接受；
- 某条 research claim 已经成为 Project truth；
- 某个 Corpus observation 应该自动进入下一章；
- 某个 model inference 已经成为持久用户口味。

这些结论仍然属于真正拥有该状态的 Project mechanism。

Memory 可以被 invalidated、重建甚至丢弃，正是因为它的 authority 应该低于 Canon。

---

## 10 · 一次典型 DRAFT / REVISE 怎样使用上下文

**解析 Project authority。** 确认 Canon cutoff、active plan、参与人物、长程承诺与任务证据。

**建立合法候选集。** 用 authority、provenance 与 stage boundary 构建稀疏 Context Manifest。

**应用显式作者控制。** 处理 pin / priority / derived-view overlay，并拦截 sensitive-stage 泄漏。

**必要时做语义选择。** 只有真正需要解释“此刻什么相关”时才调用 `context.select`。

**在硬预算下装载。** 验证 semantic result，保留 pin，并以 whole block 方式确定性装载。

**执行真正目标任务。** Writer 或其他 semantic contract 只看到这份 bounded working set，而不是整个 Project。

**只持久化合适的派生观察。** 新 memory 仍然保持 source-bound、non-authoritative。

任何 Canon change proposal 仍然等待用户接受与 Settlement。

---

## 11 · Failure routing

上下文 / 记忆失败应该回本层修，不应伪装成 prose failure。

**模型漏选了真正关键的合法证据** → 修正 bounded evidence / 重跑 `context.select`。

**Pinned memory 超出 hard budget** → 处理作者控制与预算冲突，不能静默取消 pin。

**Regression / hidden gold 进入 Writer context** → deterministic stage-isolation failure。

**Derived memory 指向旧 source fingerprint** → invalidate + rebuild。

**受保护 Canon fact 真正需要改** → proposal → Project acceptance → Settlement。

**人物根据自己并不知道的 memory 行动** → Character / knowledge-boundary failure，而不是全局删除那条 memory。

---

## 12 · 精确参考

- [架构总览](architecture.zh-CN.md) —— authority domain 与 semantic / deterministic ownership。
- [生产流水线](production-pipeline.zh-CN.md) —— DRAFT / REVISE 中上下文选择出现在哪里。
- [项目 SDK](project-sdk.zh-CN.md) —— Project authority 与精确 dependency lock。
- [`harness/context_inspector.py`](../harness/context_inspector.py) —— deterministic inspector / overlay。
- [`harness/memory_tiers.py`](../harness/memory_tiers.py) —— model-selected + deterministic-budget context packer。
- [`harness/memory_bank.py`](../harness/memory_bank.py) —— durable editable memory。
- [`harness/semantic_workers/contracts/context-research.json`](../harness/semantic_workers/contracts/context-research.json) —— `context.select` contract。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="48" />
  <br />
  <sub>让模型判断意义，让运行时守住边界，让 Project 决定什么是真的。🌸</sub>
</div>

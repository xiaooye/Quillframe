# 随纲选法 · 候选创作方法库

这套方法库帮助 Writer 决定怎样把已获授权的场景写成正文。它不是题材分类器，不生成新的剧情事实，也不充当质量裁判或 Canon 来源。现有生产指导仍是默认基线。

当前登记版本为 5。第四版退出仍在生效的 Raw Draft→Surface 指令，改由一个直接 Surface Writer 实现场景合同。第五版保持这套架构，同时要求连续叙事单位、清楚的说话人与空间归属、自然中文连接，以及真正承担现场作用的环境和侧面反应；它还替换了与这些原则冲突的碎片化对白正例。这仍是待作者逐篇验证的候选机制，不是文学质量提升结论。

## 基础层与可组合方法

当前 Rust-native DRAFT／REVISE 每次写作都把[网文章节的现场、人物与推进](cards/core.zh-CN.md)基础层冻结进生产指导快照，并只把这份正向指导投影给 Writer。以下专项卡仍是登记候选；当前 native 运行时尚未提供专项卡选择，不得把文档中的历史 `outline_driven` 设计当成已启用能力：

- [升级与对抗](cards/confrontation.zh-CN.md)。
- [关系与情绪](cards/relationship.zh-CN.md)。
- [信息、疑问与揭示](cards/mystery.zh-CN.md)。
- [日常与职业体验](cards/everyday.zh-CN.md)。
- [喜剧与轻松感](cards/comedy.zh-CN.md)。
- [设定与奇观](cards/wonder.zh-CN.md)。

一场平静的职业戏，也可能兼有关系推进或奇观体验。选择依据是当前可用的总纲、章纲、细纲与已解析场景表达的实际功能，不按书名或题材关键词分配卡片。不选附加方法也是有效选择。示例不是必填格式、数量指标或经过验证的标准答案。

## 启用、冻结与回退

基础层是当前 native 生产的 Framework 默认指导，不再依赖 `craft_guidance_mode`。Core 会通过原生句柄物化已批准 Book Setup 中明确标注为行文／声口／文风／校准且指纹一致的项目指导；`author.run.start` 也可以显式提交同一批准来源的精确正文。Core 把它们与基础层、完整 Surface Fundamentals 和登记审计 rubric 一起冻结，恢复只读取快照，不重新读取磁盘。

`outline_driven`、`outline_plus_style_contract`、`ProductionRunExecutor` 与 `craft_selection` 属于历史 Python 方案和候选规格，不是当前 Rust Bridge 能力。专项卡只有在后续 native 合同、权限、快照与评测完整落地后才能重新开放；未知字段不会成为启用证明。

直接 Surface Writer 随单一 Scene Realization Contract 收到基础层和已批准项目指导。完整 HF 诊断规则只交给生成后的 Surface Auditor，避免 Writer 围着负面检查表防守；Blind Reader 和独立评审也不接收方法投影或私有计划。修订继承来源快照，不能用局部修订要求替换基础层。第一、二版历史资源继续只用于核对旧证据，不能当作当前派发权限。

源码与完整框架包均携带同一份资源目录，不维护第二份副本。

## 来源与证据边界

[单篇章节审阅流程](../../evals/CRAFT_CHAPTER_REVIEW.zh-CN.md)是当前作者评审方式：每轮只交一篇完整新章节，必须走包含 Character Simulation 与 Reader Pressure 的完整生产运行，作者反馈绑定前不得准备下一篇。若本篇被要求修改或退回，同一创作快照不得换题重试。

[六组配对实验流程](../../evals/OUTLINE_CRAFT_ABLATION.zh-CN.md)继续保留，用于核对已经产生的历史制品或另行授权的工程实验；它不再是当前作者审稿流程，也不会自动派发模型。

[来源登记](sources.json)固定了九个一手仓库的版本、许可证、借鉴点与明确不采纳的配方。其中受非商业许可证约束的来源仅作分析，不复制其文字或代码。没有导入外部代码、安装外部 skill 或复制来源正文。短例均为新写的通用微型片段，不含消费项目内容，也不模仿指定作者。

[生成后诊断](diagnostics.zh-CN.md)解释失效机制和合理例外，只在正文生成后用于分析；Writer 的资源加载器不会读取或选择这些例子。

[第一版实施规格](../../specs/028-outline-driven-craft/spec.zh-CN.md)、[第二版克制修订规格](../../specs/029-prose-restraint-candidate/spec.zh-CN.md)、[第三版网文现场候选规格](../../specs/030-web-serial-immediacy-candidate/spec.zh-CN.md)及各自验证记录区分工程检查和文学证据。测试通过、模型自信或一次单篇偏好，都不能证明普遍提升；局部评测也不会自动授予推广权限。

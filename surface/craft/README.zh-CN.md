# 随纲选法 · 候选创作方法库

这套方法库帮助 Writer 决定怎样把已获授权的场景写成正文。它不是题材分类器，不生成新的剧情事实，也不充当质量裁判或 Canon 来源。现有生产指导仍是默认基线。

当前登记版本为 5。第四版退出仍在生效的 Raw Draft→Surface 指令，改由一个直接 Surface Writer 实现场景合同。第五版保持这套架构，同时要求连续叙事单位、清楚的说话人与空间归属、自然中文连接，以及真正承担现场作用的环境和侧面反应；它还替换了与这些原则冲突的碎片化对白正例。这仍是待作者逐篇验证的候选机制，不是文学质量提升结论。

## 基础层与可组合方法

启用后，每次写作都包含[网文章节的现场、人物与推进](cards/core.zh-CN.md)基础层。AI 在已有的场景投影调用中，可以按当前需要组合：

- [升级与对抗](cards/confrontation.zh-CN.md)。
- [关系与情绪](cards/relationship.zh-CN.md)。
- [信息、疑问与揭示](cards/mystery.zh-CN.md)。
- [日常与职业体验](cards/everyday.zh-CN.md)。
- [喜剧与轻松感](cards/comedy.zh-CN.md)。
- [设定与奇观](cards/wonder.zh-CN.md)。

一场平静的职业戏，也可能兼有关系推进或奇观体验。选择依据是当前可用的总纲、章纲、细纲与已解析场景表达的实际功能，不按书名或题材关键词分配卡片。不选附加方法也是有效选择。示例不是必填格式、数量指标或经过验证的标准答案。

## 启用、冻结与回退

调用 `ProductionRunExecutor.execute` 时传入 `craft_guidance_mode="outline_driven"`，或在 `author.run.execute` 中传入同名字段，即可显式启用。新建 DRAFT 时省略该字段，保持 `baseline`；REVISE 省略或保持原模式时，继承来源运行的完整快照。在新运行中明确选择不同模式，才冻结该模式的资源；这不授权修改修订任务的原有故事目标。

当一次明确授权的运行需要让注册 Craft V4 与 source-free Corpus 候选合作时，使用 `outline_plus_style_contract` 并提供本次运行的候选 pack。组合快照始终保留 V4 `core`，再由同一个注册场景投影从登记 methods 与 Corpus 机制中选择适用项；Corpus 最多四条。候选 pack 只冻结进该次不可变请求，不修改默认模式、registry、Framework promotion 或 publication 状态。

运行时在派发模型前，把方法目录身份和正向卡片全文冻结进不可变执行请求。已有的 `scene.realization_project` 调用只增加目录简介和当前已选中的计划依据。模型返回的 `craft_selection` 必须引用准确的来源标识。Python 只校验身份、哈希与权限，不判断文学适用性。

直接 Surface Writer 随 Scene Realization Contract 收到基础层和选中正文。选卡理由、计划引用、未选中的卡片、诊断示例、评测隐藏标签不进入这份创作投影；Blind Reader 和独立评审不接收方法投影、选卡结果或私有计划。系统不再先生成完整中间正文供后续清洗；原有发布关卡不变。

恢复运行使用原快照，即使磁盘资源已经更新；同次执行不能替换模式。第一、二版登记和基础层分别逐字节保存在 `history/v1/` 与 `history/v2/`，只用于核对旧证据；旧运行仍以自身冻结快照为准，历史文件不能当作当前派发权限。早于快照机制的历史执行需要新建运行。回退时，在新运行中指定 `baseline`。候选方法不能自行变成默认规则。

源码、Python 安装包和完整框架包均携带同一份资源目录，不维护第二份副本。

## 来源与证据边界

[单篇章节审阅流程](../../evals/CRAFT_CHAPTER_REVIEW.zh-CN.md)是当前作者评审方式：每轮只交一篇完整新章节，必须走包含 Character Simulation 与 Reader Pressure 的完整生产运行，作者反馈绑定前不得准备下一篇。若本篇被要求修改或退回，同一创作快照不得换题重试。

[六组配对实验流程](../../evals/OUTLINE_CRAFT_ABLATION.zh-CN.md)继续保留，用于核对已经产生的历史制品或另行授权的工程实验；它不再是当前作者审稿流程，也不会自动派发模型。

[来源登记](sources.json)固定了九个一手仓库的版本、许可证、借鉴点与明确不采纳的配方。其中受非商业许可证约束的来源仅作分析，不复制其文字或代码。没有导入外部代码、安装外部 skill 或复制来源正文。短例均为新写的通用微型片段，不含消费项目内容，也不模仿指定作者。

[生成后诊断](diagnostics.zh-CN.md)解释失效机制和合理例外，只在正文生成后用于分析；Writer 的资源加载器不会读取或选择这些例子。

[第一版实施规格](../../specs/028-outline-driven-craft/spec.zh-CN.md)、[第二版克制修订规格](../../specs/029-prose-restraint-candidate/spec.zh-CN.md)、[第三版网文现场候选规格](../../specs/030-web-serial-immediacy-candidate/spec.zh-CN.md)及各自验证记录区分工程检查和文学证据。测试通过、模型自信或一次单篇偏好，都不能证明普遍提升；局部评测也不会自动授予推广权限。

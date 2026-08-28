# 中文网文研究与采用边界

状态：实施研究，不是读者留存实验结果。仓库观察固定在[研究登记](research-register.yaml)的具体提交；未安装外部技能，未导入外部代码。受关注程度用于发现项目，不作为质量分数。

## 已影响本次实现的决策

| 来源 | 可借鉴机制 | Quillframe 的边界 |
| --- | --- | --- |
| [webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer/tree/2041abad78211e29a67a2f0c64b2a97a747dce57) | 阶段账本和章节状态投影 | 精确候选审查、作者明确接受、原子结算分别执行；未复制 GPL 代码。 |
| [chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill/tree/3db1e3be88343ca531924b0dc6516710f1b11779) | 逐步询问题材与文风 | Plan 使用简短且可编辑的输入；不无人值守地接受整本书；检查版本未发现许可证。 |
| [ani-book-skill](https://github.com/ExplosiveCoderflome/ani-book-skill/tree/44a0eb216eee234101af1984df20726713b7690e) | 目标、阻力、回报、净变化与滚动计划 | 阅读意图字段可选，平静章节也可以有价值；单引擎里的角色名称不证明独立审查。 |
| [chinese-webnovel-skills](https://github.com/tance-mang/chinese-webnovel-skills/tree/ecf552f6930e769d8bbf17818ad3d5a864a7a70b) | 模块化写作指导与读者预测 | 按需加载；模型反应仅作建议，不能充当真实读者数据。 |
| [webnovel-handbook](https://github.com/miserylee/webnovel-handbook/tree/700b2a718c9d3c79f946b35abc7b037088532bac) | 反馈与记忆流程 | 区分作者、真实读者、模型来源；项目偏好需要评估和明确启用。 |
| [novel-architect](https://github.com/zhougz520/novel-architect/tree/8be80352257f98151921d89200e63464759a329f) | 读者承诺记录 | 期待绑定已接受的来源章节；关键词压力计数不能判定吸引力。 |

## 修正论文归因

[Learning to Reason for Long-Form Story Generation](https://arxiv.org/abs/2503.22828)研究下一章预测与强化学习，不是人物模拟。本次实现不训练模型权重。

[From Personas to Plot](https://arxiv.org/abs/2607.00918)提出 MAGNET 人物行动与 ATLAS 场景／世界图，可启发因果场景状态，不能据此声称任意批评循环会改善读者留存。

[ConWriter](https://arxiv.org/abs/2608.05169)使用演进状态、转移检查和局部修复；[Lost in Stories](https://aclanthology.org/2026.findings-acl.410/)提供 ConStory-Bench 和矛盾检测。它们支持有来源的一致性证据，不提供通用文学总分。

[Agents' Room](https://proceedings.iclr.cc/paper_files/paper/2025/file/0fbc8a83d93dd8021a4dd8d2d34138eb-Paper-Conference.pdf)以共享草稿板分离规划与写作，其短篇实验不能证明长篇连载规模。Quillframe 还要求未来计划与人物私密状态不能进入盲读包。

## 尚待测量的内容

产品目标是读者吸引力：值得追问的问题、人物投入、有意义的选择、可感知的回报与继续读的理由。模型判断只是诊断预测；真人阅读与作者决定保留为不同类型的证据。

使用四个开发案例和六个留出案例，每轮最多六十四次实际调用，包含上下文选择、审查和修复。未完成的轮次如实记录。单章、连续三章、十二章链路须逐章取得作者确认；确定性测试与新建章节记录不能替代这些验收。不声称已验证商业留存或百万字一致性。

## 后续叙事研究

[2026-08-28：中文网文叙事与读者校准](prose-quality-research.zh-CN.md)补充具体技能文件、官方公开首章和实际提示词接线的核查。这是尚未实施的研究提案，不改变上述历史采用记录，也不代表质量提升已获验证。

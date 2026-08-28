# 中文网文叙事与读者校准研究

2026-08-28 · 主模式 `RESEARCH` · **研究提案，尚未实施或验证质量改善。** 本文不包含下游作品、作者私有偏好或小说正文。没有安装外部技能、导入外部代码、运行新的生产模型调用，也没有改变既有候选的审查结果。

研究问题：为什么事件连贯、状态一致的章节，仍可能缺乏人物感和阅读吸引力？调查分开检查具体写作指导、公开作品的实际呈现，以及 Quillframe 真正发给模型的任务。来源和版本见[来源登记](prose-quality-sources.yaml)。

## 值得细读的技能文件

| 来源 | 可借鉴之处 | 不能直接照搬的部分 |
| --- | --- | --- |
| [oh-story 写作技法，第 1、8 节](https://github.com/zenstory-ai/oh-story-claudecode/blob/66d61809084ec4c5902b659af24ce2acdfa2ed42/skills/story-long-write/references/writing-craft.md) | 细纲不决定正文形状；关键处详写，过场略写；情绪不必默认译成身体动作。 | 同一文件中的开篇事件数、物件次数和固定视角，不宜作为全题材硬门。 |
| [Chinese Webnovel Skills：正文扩写](https://github.com/tance-mang/chinese-webnovel-skills/blob/ecf552f6930e769d8bbf17818ad3d5a864a7a70b/skills/expand/SKILL.md)、[对话](https://github.com/tance-mang/chinese-webnovel-skills/blob/ecf552f6930e769d8bbf17818ad3d5a864a7a70b/skills/dialogue/SKILL.md) | 让对话体现人物身份、目的、关系和不同声口。 | 默认第一人称、固定爽点套路不能代替项目定位。 |
| [Ani Book：中文小说反模板化二稿](https://github.com/ExplosiveCoderflome/ani-book-skill/blob/44a0eb216eee234101af1984df20726713b7690e/references/chinese-novel-humanization.md) | 修复成簇的解释旁白和均质对白，可重组原稿句序；保留事实边界。 | 不把检测器分数当成文学质量；方法文件本身不是效果证据。 |
| [Webnovel Writer：写作技法](https://github.com/lingfengQAQ/webnovel-writer/blob/2041abad78211e29a67a2f0c64b2a97a747dce57/webnovel-writer/references/csv/%E5%86%99%E4%BD%9C%E6%8A%80%E6%B3%95.csv) | 场景目的与对白诉求可以帮助选择呈现重点。 | 每次发言绑定动作、情绪拆成连续动作，可能增加无功能反应。 |

另查阅了 [Novel Architect 的章节流程](https://github.com/zhougz520/novel-architect/blob/8be80352257f98151921d89200e63464759a329f/docs/guides/chapter-workflow.md)。承诺与兑现的记录有参考价值，但不能从关键词或标点加权推导真实追读效果。

技能库也需要审稿。例如 [Human Texture](https://github.com/tance-mang/chinese-webnovel-skills/blob/ecf552f6930e769d8bbf17818ad3d5a864a7a70b/references/human-texture.md)指出情绪平均的问题，但不能据此把非理性或不闭环设成“人味”的必要条件。

[oh-story 的固定身体反应实验](https://github.com/zenstory-ai/oh-story-claudecode/blob/66d61809084ec4c5902b659af24ce2acdfa2ed42/demo/craft-stock-reaction-eval/README.md)报告：单加自检问题未稳定改善，修改上游生成规则后出现方向性改善。其范围是单章、单模型、每组三次，同家族模型评审；完整输出未公开。本次只核实报告内容，未独立复验，不将它视为留存或普适质量证明。

## 公开首章对照

本次阅读了以下官方公开首章，另查阅官方作者课堂。只保存链接和概括，不镜像原文，不把原作句式或人物写入生成上下文。

- [三九音域《我在精神病院学斩神》第一章](https://fanqienovel.com/reader/6982735801973113351)：旁观者的疑问、家庭日常和复查谈话交替推进，首章没有战斗。可观察悬疑与温情怎样相互加强。
- [竹已《难哄》第一章](https://www.jjwxc.net/onebook.php?novelid=4001734&chapterid=1)：日常困扰、朋友通话与重逢承载不同的应对方式。可观察语气和回避怎样改变关系，而不只记录活动。
- [番茄《开篇五步走（上）》](https://fanqienovel.com/writer/zone/article/7480087779494346776)将人物处境、行动和作品核心联系起来，并注明经验的适用范围；[《告别工具人》](https://fanqienovel.com/writer/zone/article/7651510334422777881)强调配角自己的诉求与行动理由。

以上是有限范围的文本观察，不代表全部网文，也不证明某种写法能提高平台留存。安静日常、档案体、专业操作与克制叙述都可能有阅读价值；不能把“多事件、多冲突、多身体反应”设成统一目标。

## 当前实现的具体缺口

以下核查针对代码提交 `2053e854049c00780c4fc2027657a7ec6c7fbd5f`，归类为 `DOCUMENTATION_DISCOVERED_IMPLEMENTATION_GAP`，不是已经完成的修复。

1. **写作要求没有充分进入实际输入。** [运行时](../../production_runtime/runtime.py)的 `_stage_instruction` 对初稿和正文实现的专属要求很短；[场景投影](../../harness/semantic_workers/contracts/production-loop.json)主要提供因果轨迹。它们没有清楚区分事件清单与正文的详略、视角及叙事节奏。这个缺口可能影响生成，但仍需消融实验确认。
2. **预期回报不等于实际阅读体验。** `reader.pressure` 在正文前运行；来源核验只能证明提案来自哪里，不能证明正文已经让读者感到。盲读需要依据实际正文判断，不能获得预期答案。
3. **文档判准和生产审稿判准不一致。** [读者基本法 RG-15](../../surface/READER_ENGAGEMENT.zh-CN.md)允许安全但平淡的正文失败。[实际 Reader 与独立审稿合约](../../harness/semantic_workers/contracts/quality.json)没有同等明确的正向质量门槛；[任务包装](../../production_runtime/semantic.py)只发送登记的任务，不会自动加载这份文档。
4. **阅读定位传递不完整。** Reader 和独立合约支持 `genre_profile`、`platform_profile`、`chapter_position`，但当前实际构造没有传入；`reader_grip` 也没有作为明确参数一致送入 Writer 与压力阶段。修复应冻结并明确各阶段所需的定位。盲读者与独立审稿只能获得读者可知的信息，不能获得未来计划、创作者解释、旧评语或隐藏答案；写作者与压力阶段保留各自授权的创作输入，同时遵守人物私密状态的权限边界。
5. **接线测试不是文学质量校准。** [平淡样本](../../evals/cases/reader_safe_but_flat_reject.json)使用英文摘要、专用判准，且 `blocks_release=false`；[生产测试](../../tests/test_quillframe_production_runtime.py)里的模拟 Reader 固定通过。这些测试有工程价值，但不能证明真实合约能识别完整中文章节的误放行。

## 建议的验证顺序

1. **先测实际输入。** 捕获真实构造的任务，验证相关写作指导和明确阅读定位进入相应的冻结输入。用负向测试验证盲读者与独立审稿仍无法获得未来计划、创作者解释、旧评语和隐藏答案；写作阶段保留授权的计划与修复约束，但不扩大人物私密状态的访问权限。
2. **分开测生成与审稿。** 生成实验固定故事任务、模型和预算，分别比较现有指令、增加叙事实现指导、再加入明确项目定位。审稿实验使用另一套固定完整中文样本，通过真正登记的合约比较误放行和误拒绝，不能把两个变量混成一次胜负。
3. **同时准备反例。** 配对样本覆盖按序汇报但平淡、事件相同而人物与感受有变化、安静但有回报、专业流程本身好看；隐藏人工标签，随机编号并交换成对顺序，留下不同评审的分歧。
4. **最后由作者读。** 模型报告不能替代作者判断。记录作者实际选择及理由，按最窄范围形成待评估假设；不自动激活偏好、推广通用规则、接受稿件或结算。

本次只完成资料研究、代码核查和验证方案。上述行为变更、完整中文盲测和质量改善均未完成；不得用新增文档或通过文档检查替代它们。

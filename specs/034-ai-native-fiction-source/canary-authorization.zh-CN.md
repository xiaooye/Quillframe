# 中文小说 Canary 授权单

2026-08-31 · 仅为提案 · 尚未授权、尚未派发。

## 目的与纯 AI 素材边界

Canary 只回答一个小问题：两种当前受支持的模型族中，是否至少有一种能从同一份新 Writer Pack 实现一场中文场景，并获得作者接受？它不会修订、接受、结算或覆盖冻结的失败候选。

本次测试的是 100% AI-generated candidate prose，而不是作者声线学习。固定输入只包含抽象作者目标、项目中立的角色／关系／世界事实、同一份 Scene Realization Contract 与版本化通用创作指令。两篇候选正文从第一个字到最后一个字均由各自 Writer 生成。

不提供或召回任何正面中文正文样本，不编译 Author Voice Sheet，不使用 accepted prose tail，不使用被否决正文、Reviewer 分析、Repair 解释或私有 Character Enactment 状态。运行必须标明 `source_free_voice_baseline=true`，并且不得声称系统已经学会作者文风。

## 拟议调用

| 阶段 | 模型 ID | 计划调用 | 用途 |
| --- | --- | ---: | --- |
| Writer A | `gpt-5.6-sol` | 1 | 从同一份 source-free Writer Pack 直接生成完整候选正文 |
| Writer B | `claude-opus-5` | 1 | 从同一份 source-free Writer Pack 直接生成完整候选正文 |
| A/B 交换顺序取证 | `gpt-5.6-terra` | 2 | 分别审查 A→B 与 B→A |
| A/B 交换顺序取证 | `claude-sonnet-5` | 2 | 分别审查 A→B 与 B→A |

基线实验计划为 6 次调用；这是调用图，不是 token 或费用预算。禁止 tools、网页搜索和自动替代调用，避免让两篇候选获得不同的外部信息。结果未知时停止并报告，不用额外调用把不确定性刷成 PASS。

派发前，必须把每个 provider model ID、protocol 与 provider 可见 metadata 冻结为 Quillframe 模型版本指纹。服务缺失、ID 或价格变化、fiction-audition receipt 无法验证时，在第一次付费 Writer 调用前停止，并重新提交授权单。

## Token 与费用策略

作者不设置 Canary 的 token 上限或 provider 费用上限，也不要求 `run_cost_budget` 在派发前截停。每次请求只受所选模型／协议本身的上下文窗口、输出能力、Provider 账户状态和 Quillframe 防止无效或重复派发的执行边界约束。实际输入、输出、计费与模型版本仍写入 receipt，供事后对账；记录费用不等于限制费用。

## 权利与确认门

本方案不摄入第三方正文，也不要求用户提供正文样本；因此没有声线样本授权门。抽象场景事实与作者目标仍须绑定到本次 Canary receipt，且只能用于本次测试。任何后续 Author Voice 学习实验必须另行提交素材来源、权利与作者确认授权单，不能沿用本次批准。

## 盲评决策规则

1. 两个 Writer 接收同一份带指纹 Writer Pack 和对称的非价格设置；不为制造相同 token 数而截断任一候选。
2. 导出标签与模型身份隐藏，A/B 映射密封。
3. 每位 Reviewer 分别比较 A→B 与 B→A，对每个当前作者目标输出 `met`、`not_met` 或 `uncertain`、精确证据与修订范围。顺序改变导致冲突时记为 `uncertain`，不得用平均分选赢家。
4. 作者只看到随机顺序的两篇正文，不看到模型身份或 Reviewer verdict，并选择 A、B 或“两者都不接受”。
5. 只有作者明确接受，才可激活选中模型的 fiction-writing receipt；“两者都不接受”会停止继续叠 Prompt，并记录模型能力边界。

## 等待授权

在用户明确要求启动上述纯 AI Canary 前，任何调用都不得开始。不存在额外的 token 或费用上限确认门；本文件的规则修正本身不等于启动命令。

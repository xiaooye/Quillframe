# 中文小说 Canary 授权单

2026-08-31 · 已授权并派发一组 source-free A/B · 等待作者选择。

## 目的与纯 AI 素材边界

Canary 只回答一个小问题：相对普通 Writer 基线，新的近生成端指令能否把同一个中文场景改善到作者更愿意选择？它不会修订、接受、结算或覆盖冻结的失败候选。

本次测试的是 100% AI-generated candidate prose，而不是作者声线学习。固定输入只包含抽象作者目标、项目中立的角色／关系／世界事实、同一份 Scene Realization Contract 与版本化通用创作指令。两篇候选正文从第一个字到最后一个字均由各自 Writer 生成。

不提供或召回任何正面中文正文样本，不编译 Author Voice Sheet，不使用 accepted prose tail，不使用被否决正文、Reviewer 分析、Repair 解释或私有 Character Enactment 状态。运行必须标明 `source_free_voice_baseline=true`，并且不得声称系统已经学会作者文风。

## 已授权调用

| 阶段 | 模型 ID | 计划调用 | 用途 |
| --- | --- | ---: | --- |
| 普通 Writer 基线 | `gpt-5.6-sol` | 1 | 从共享 source-free 场景合同与普通 Writer 指令生成完整候选 |
| AI-native treatment | `gpt-5.6-sol` | 1 | 从同一场景合同与新的近生成端指令生成完整候选 |

本次实验只授权两次正文调用。没有模型 Reviewer、交换顺序模型审查、额外样本或自动替代调用。禁止 tools 与网页搜索，避免两篇候选获得不同外部信息。唯一的文学比较由作者完成，不交给另一个模型。

派发前，必须把 provider model ID、protocol 与可用的 provider 可见 metadata 冻结到执行回执。服务缺失、ID 变化或 request identity 无法验证时，在第一次 Writer 调用前停止，并重新提交授权单。

## Token 与费用策略

作者不设置 Canary 的 token 上限或 provider 费用上限，也不要求 `run_cost_budget` 在派发前截停。每次请求只受所选模型／协议本身的上下文窗口、输出能力、Provider 账户状态和 Quillframe 防止无效或重复派发的执行边界约束。实际输入、输出、计费与模型版本仍写入 receipt，供事后对账；记录费用不等于限制费用。

## 权利与确认门

本方案不摄入第三方正文，也不要求用户提供正文样本；因此没有声线样本授权门。抽象场景事实与作者目标仍须绑定到本次 Canary receipt，且只能用于本次测试。任何后续 Author Voice 学习实验必须另行提交素材来源、权利与作者确认授权单，不能沿用本次批准。

## 盲评决策规则

1. 两个 Writer 接收同一份带指纹 Writer Pack 和对称的非价格设置；不为制造相同 token 数而截断任一候选。
2. 导出标签与模型身份隐藏，A/B 映射密封。
3. 作者只看到随机顺序的两篇正文，不看到模型或指令身份，并选择 A、B 或“两者都不接受”。
4. 这次选择只是一条一次性指令证据，不能自动提升 General Craft、写入 Canon、授予模型资格或单独证明文学成功。
5. “两者都不接受”表示本次指令 treatment 没有通过作者 canary，不会触发更多调用。

## 执行记录

用户已于 2026-08-31 明确授权一个 sample 的 A/B。两次 Writer 调用均已完成；第一次 relay 校验停止后复用了 checkpoint，没有重复派发。匿名顺序中的两份输出分别为 3,720 与 2,560 个中文字符。实际记录合计为 27,936 input tokens、6,894 output tokens 与 1,393 reasoning-output tokens；provider 没有暴露货币价格回执。

两次 Codex CLI 0.151 调用都以退出码 0 返回一份精确 final message 与 usage，但同时产生了经脱敏保存的 error-type lifecycle items，v3 relay 将其记录为 `forbidden_cli_item` / `invalid_cli_item`。正文可以交给作者盲评，但不能声称 transport validation 完全干净。没有运行 Reviewer 或任何额外模型调用。

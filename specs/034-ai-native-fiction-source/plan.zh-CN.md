# AI 原生小说生成源头实施计划

2026-08-31 · SYSTEM-IMPROVE · 本计划不授权付费 canary。

## 阶段 1 · 保全失败证据

还原失败修订的精确模型调用图、Writer payload 和事件时间线。保持历史候选未接受、未结算且不变。把已证、只能给边界和未知的耗时分开记录。

可见结果：字段级污染图，以及有证据的墙钟耗时解释。

## 阶段 2 · 版本化语义合同

加入 Author Voice Sheet 编译合同，扩展 Character Enactment 与 Scene Realization，并让场景投影同时选择 Writer 上下文和 Director Note。修改当前派发前先保存旧合同版本。

可见结果：文学选择归模型，来源与 schema 边界归 Core。

## 阶段 3 · 替换 Raw Draft 改写

从 DRAFT 与 REVISE 移除 event-first 完整正文阶段。用紧凑上下文只派发一次 Surface Writer。局部修订严格限制窗口，fresh realization 隐藏旧稿。

可见结果：被否决正文和规划解释不能再为 fresh Writer 播种。

## 阶段 4 · 让作者目标贯穿审稿

把当前目标 envelope 送入 candidate self-audit 与独立审稿。要求逐目标证据，并让硬目标以合取方式控制 readiness。

可见结果：泛化的流畅或完整不能覆盖作者未满足的要求。

## 阶段 5 · 小说模型路由与受治理声线资产

持久化默认关闭、作者确认的 Voice Sheet 与合格正面锚点，并绑定权利和指纹。要求小说写作 route，并记录模型精确版本。

可见结果：Quillframe 可以说明使用了什么声线证据和模型能力；没有时也会诚实说明。

## 阶段 6 · 修复预算与自动推进

拆分 context、output 与 cost 预算；保留有效返回；绑定通用 checkpoint；结果确认后入队 coordinator wake；恢复 wake 时不重复请求；run 绑定唯一 Framework build。

可见结果：模型完成后无需人工轮询即可推进，且不会丢失已付费结果。

## 阶段 7 · 证明机制边界

补齐 Writer 可见性、局部／fresh 修订、作者硬目标、模型／结果指纹、事后预算、重启恢复、重复计费和脚本禁用测试。运行针对性与完整的无模型测试和文档检查。

可见结果：可复现的工程证据，同时明确文学质量仍待验证。

## 阶段 8 · 准备但不运行 canary

列出候选模型、source-free 同场景输入、arm 顺序与交换顺序盲比；明确本次 canary 不设置作者级 token 或 provider 费用上限。任何真实调用前等待用户明确下达启动命令。

可见结果：显式、可审查的 source-free canary 派发包，而非隐式模型调用。

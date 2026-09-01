# AI 原生小说生成源头验证

2026-08-31 · 无模型费用的工程验证已完成 · 未获授权运行真实或付费小说调用。

## 已验证的工程主张

当前 Quillframe 不再用完整的被否决稿或助手式初稿为 fresh fiction 播种。当前作者目标 envelope 会贯穿直接 Surface Writer、self-audit 与独立审稿；有效的模型返回也不会再因软预算越界或 coordinator 恢复而被丢弃。

本文只验证代码路径、schema、来源与恢复行为，不声称生成的中文小说已经自然、生动、幽默、没有“AI 腔”或获得作者认可。

## 冻结的改造前失败基线

- 当前修订目标进入了 Repair Editor 与 Surface Writer，却没有进入 candidate self-audit 和独立审稿。
- Surface Writer 收到完整旧候选、Repair 解释、重复规划材料和大体量上下文，因此局部保守改写延续了系统性声线污染。
- 第一次修订返回完整 Writer 响应后，被重新标成 `token_budget_exhausted_after_response`。
- 独立 reviewer 在没有逐目标证据的情况下以 0.94 置信度给出 PASS；该判断继续作为失败证据，而不是文学成功证据。
- 11 次有记录的 manager 调用墙钟合计 918.271 秒：queue 104.746 秒、worker／model 408.597 秒、response-confirm／resume 404.741 秒。事件中可见的单次 database handoff 约 20–170 ms；没有足以支持 database 或 validation 总量的独立计时。
- 从请求到可见约 7 小时 09 分，从注册到可见约 4 小时 03 分。最大开销不是模型，而是三次 build 之间的人工轮询／续跑、测试、规范、snapshot、hotfix 与重新派发空档。历史事件不足以把所有剩余时间精确拆成五类，因此未知余量继续标未知。

## 已完成的确定性证据

2026-08-31 通过以下无模型测试：

- `tests.test_quillframe_production_runtime`：96／96，445.145 秒。
- `tests.test_quillframe_author_revision_source`：14／14，100.657 秒。
- `tests/test_quillframe_craft_guidance.py`：27／27，55.057 秒。
- checkpoint、Writer context、persistence、Agent runtime、Model runtime、host bridge、fiction audition、Author Voice、prose contract 与 semantic-context 模块：154／154，6.247 秒。
- `tests.test_quillframe_ai_native_architecture`：4／4，0.100 秒。
- `scripts/docs_quality.py`：0 个错误；仍有 21 条此前已有的建议性 warning。

另一次全仓 discovery 共执行 1,152 个测试，用时 848.260 秒；修复前结果为 79 个失败、252 个错误、2 个跳过。绝大多数来自既有的 Windows no-follow 目录能力限制、缺少 Node 与 Unix 进程组设施，以及已退役 CLI 表面的历史预期。该轮发现的两处当前契约 fixture 偏差已经修复并单独复跑通过：recorded qualification 14／14，style-corpus ablation 18／18。全仓 discovery 未再次执行，且仍受平台结构性条件阻塞，因此本记录不会把全仓测试描述为全部通过。

这些结果共同证明：

1. 当前只有一个直接 Surface Writer，没有 Raw Draft 正文阶段；
2. fresh Writer 上下文不含被否决正文、Reviewer 分析和人物私有推演；
3. 上下文受出场人物、模型选中的相关 Lore 与作者已选偏好边界约束；
4. Voice Sheet、声线锚点与 accepted prose tail 绑定权利、适用范围、版本、指纹和作者确认；
5. 当前作者目标原样进入 Writer、self-audit 和独立审稿；
6. 系统性污染走 fresh realization，孤立错误只暴露精确编辑窗口；
7. 硬目标使用合取门，`not_met` 或 `uncertain` 不能被平均成 PASS；
8. optional prose telemetry 不被生产决策模块导入，当前 schema 不暴露英文计数、禁词、长度、比例、AIGC 或聚合文学分数门；
9. 有效返回在软费用或时间预算越界后仍保持 confirmed，缺失计费另行对账；
10. 精确节点 checkpoint、durable wake 与 billing receipt 防止重启后重复派发和重复计费；
11. 模型 protocol、身份与版本指纹在派发前捕获，并在恢复时重新验证；
12. 跨 build 续跑要求 typed migration、已对账计费、精确持久化 offline-regression receipt 与显式授权；
13. 当前 Framework 决策模块与合同不含消费项目身份；
14. DRAFT／REVISE 决策模块既不生成也不执行一次性质量程序。

## 性能状态

- 已验证：八个 model waiter 阻塞时，第九个 ready wake 仍能被调度；推进不需要人工另开 Session 轮询。
- 已验证：可轮询 lease 过期后 30 秒内重新 ready。
- 已验证：返回结果先原子确认，再处理后续预算停止；重启不会重复 provider 计费。
- 部分有计时：queue、provider／model、durable result、billing 与 wake transition 已记录；历史 validation、database 与 orchestration 总区间没有全部独立计时。
- 待完整端到端 benchmark：串行墙钟 ≤ 实际模型时间总和 + 3 分钟；并行墙钟 ≤ 模型关键路径 + 3 分钟。单元时钟和 coordinator 测试验证了机制，但不能替代带完整计时的真实 canary。

## 迁移与回滚证据

当前注册使用 production-loop v10 与 craft guidance v4。production-loop v9 和 craft v3 以精确 hash 保留，供审计与回滚取证。迁移采用 clean graph cut：没有 adapter 或 dual dispatch 重建已退役的 Raw Draft 阶段。

历史 run 保持冻结、可读。Project open 只能原子应用由 Core 拥有、按序排列的 known-prefix schema migration。跨 build 恢复缺少上述 typed migration 与精确 regression／billing 证据时 fail closed。禁用当前注册仍保留 Voice Sheet receipt、checkpoint、模型结果与审稿证据；回滚不得让被否决正文重新合格，也不得恢复 Raw Draft 生成。

## Canary 门

真实小说调用前，授权包必须列出精确模型与调用图、匿名作者决策规则，并明确每个正面样本的权利或声明完全无正文样本。已执行的授权包为 source-free，且作者不设置 token 或 provider 费用上限：不使用 Author Voice Sheet、正文锚点或 accepted prose tail。用户把范围缩到同场景严格两次 Writer 调用，不调用模型 Reviewer。

授权包已执行，当前等待作者匿名选择。状态只能是 `engineering_verified / canary_awaiting_author_decision`，不能是 `literary_success`。

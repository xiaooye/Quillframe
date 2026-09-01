# AI 原生小说生成源头任务

2026-08-31 · 任务台账。

## 证据与合同

- [x] 冻结并审计失败修订，不修改其候选。
- [x] 记录一手研究与采用／改造／拒绝边界。
- [x] 定义 Author Voice Sheet、Character Enactment、Scene Realization 与 Context Composer 合同。
- [x] 定义直接 Surface Writer 与修订范围语义。
- [x] 定义作者目标绑定审稿与模型能力边界。
- [x] 定义预算、checkpoint、事件驱动 coordinator 与 build 绑定要求。

## 实施

- [x] 版本化并更新语义合同。
- [x] 增加带权利、作者确认的 Voice Sheet 存储与快照。
- [x] 根据模型选择的合格标识组合最小 Writer 上下文。
- [x] 从当前 DRAFT 与 REVISE 移除完整 Raw Draft 阶段。
- [x] 在不泄漏正文的前提下路由 local、scene、fresh 与 mixed 修订。
- [x] 把当前作者目标带入 Writer、self-audit 与独立审稿。
- [x] 让硬目标失败使用合取门。
- [x] 要求 fiction-writing 路由证据并持久化模型／版本指纹。
- [x] 拆分 model context、output 与 run cost 预算。
- [x] 保留软预算越界后已返回的有效响应。
- [x] 增加 checkpoint 回执、run wake coordinator 与不可变 build 绑定。
- [x] 让脚本式正文判断退出所有生产决策路径。
- [x] 禁止 DRAFT 与 REVISE 生成一次性质量程序。

## 验证

- [x] Writer payload 不含被否决正文、Reviewer 分析和人物私有推演。
- [x] Writer payload 只含出场人物与模型选择的相关 Lore。
- [x] 声线与 prose tail 来源绑定权利、版本、作者确认和指纹。
- [x] 当前作者目标进入最终 Writer 与两层审稿。
- [x] 系统性污染选择 fresh realization 并隐藏旧稿。
- [x] 孤立错误只暴露目标范围。
- [x] 有效返回不因软预算耗尽而作废。
- [x] coordinator 重启不重复派发或计费。
- [x] 每个语义节点都能从精确 checkpoint 恢复。
- [x] 通用 Framework 不含消费项目实体或私有偏好。
- [x] DRAFT／REVISE 不生成临时质量脚本。
- [x] 针对性无模型测试与文档检查通过。

## 文学与真实调用门

- [x] 用户明确要求启动一组 source-free A/B；不要求 token 或 provider 费用上限。
- [x] 当前 canary 已明确为 source-free，不使用正面声线样本；未来声线学习 canary 必须另走权利门。
- [x] 同场景中文 arms 严格只生成两份，并以随机匿名顺序交给作者，不调用模型 Reviewer。
- [ ] 作者接受至少一个 canary arm。

这些真实调用项保持 pending，不能由工程完成暗示。

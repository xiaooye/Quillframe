# Durable Model Pending 验证记录

2026-08-31 · 已记录确定性证据；真实生产证据刻意分开。

## 被验证的契约

本记录只证明：keyed 本地模型 worker 可以比 HTTP waiter 活得更久，同时不重复派发、计费或消费结果。它不声称模型结果文学质量合格、已经独立审稿或已经 release。

## 确定性证据

Focused suites 覆盖：

- loopback request-key 稳定哈希且 body 不变；
- `202 model_pending` 归一化与终态 worker failure；
- 同 key packet 复用、改变 body 冲突、并发首次发布；
- worker 的 running／finalizing／completed／failed 与心跳；
- keyed 进程跨过原 deadline 后仍无默认进程超时；
- pollable stage 跨过旧 deadline 后继续存在；
- 首个 202 前崩溃与瞬时轮询故障；
- resume 使用同一 stage-call 身份且只有一行；
- native pending 投影不泄露正文；
- 上下文未变的 author revision 精确复用，只需八次新主调用。

最终 no-timeout 改动前，完整 author-revision 与 production-runtime 回归为 `107/107`。改动完成后还必须记录最终 focused 与 combined suite 结果。

## 仍需真实证据

- 最终源码快照指纹与部署 commit；
- REVISE run ID 与一次性 pack 指纹；
- 每次主调用的 stage 身份与 confirmed／pending 历史；
- 轮询没有增加行或计费的证据；
- 全新独立审稿 invocation 与精确 judgment 绑定；
- 最终 candidate／revision 指纹；
- 新 Epoch 使用量、历史 ledger offset 与剩余预算；
- 明确证明未执行 acceptance 与 settlement。

## 完成规则

确定性 suites 与文档全部通过才算工程完成；已授权 REVISE 和独立审稿通过 Core 才算真实执行完成；文学接受仍由用户决定。

# Durable Model Pending 任务

2026-08-31 · 真实任务状态。

## 工程

- [x] 为每个冻结模型调用序号绑定稳定 request key。
- [x] 在 loopback 派发前持久化 pollable 状态。
- [x] HTTP 短暂等待后返回 `202 model_pending`。
- [x] 相同并发发布加入同一 packet，改变 body 则拒绝。
- [x] 发布 worker 心跳与终态状态。
- [x] 移除 keyed durable worker 的默认任意进程超时。
- [x] 旧 deadline 已过时仍保留同一 pending stage，不新增调用。
- [x] 让 `NativeStyleRunner` 安全传递无正文 pending 字段。
- [x] 为崩溃、轮询、终态、过期与去重增加确定性测试。

## 文档

- [x] 新增双语 032 spec、plan、tasks 与 verification。
- [x] 更新双语 Model Runtime 与 Agent Runtime 指南。
- [x] 记录 v2→v3 前向取代边界，不改写规格 027。

## 真实生产

- [ ] 冻结最终源码快照并部署到隔离 WSL runtime。
- [ ] 构建并绑定 CH001 REVISE 专用一次性 pack。
- [ ] 通过 Core 注册精确授权的 REVISE。
- [ ] 主图在 12 次调用内完成；pending 只轮询原请求。
- [ ] 从 packet-only 上下文完成一次全新独立审稿。
- [ ] 分开核对新 Epoch 与历史 manager ledger。
- [ ] 读取 Core 释放、未接受、未结算的 Review Draft。

# Durable Model Pending 实施计划

2026-08-31 · 先执行 `SYSTEM-IMPROVE`，再执行已授权的 CH001 `REVISE`。

## 阶段 1 · 冻结当前状态

记录源码快照、活动 run／worker、manager ledger、新计费 Epoch、revision request 与候选指纹；不修改历史行。

回滚点：尚未发生 runtime 或生产写入。

## 阶段 2 · 分开 waiter 与 worker 寿命

加入稳定 request key、v3 durable packet、短 HTTP pending 响应、进程心跳和终态 worker state；普通无 key 调用仍保持有限边界。

回滚点：任何 v3 packet 启动前关闭 v3 路线。

## 阶段 3 · 生产 resume 只消费一次

派发前持久化 pollable 状态；跨 executor lease 和旧 waiter deadline 保留同一 pending stage；只能恢复精确冻结 job；通过 native runner 暴露无正文的安全 pending metadata。

回滚点：先 drain/reconcile 所有 v3 worker，再恢复 confirmed-only 同步 resume。

## 阶段 4 · 验证确定性边界

运行 Model、Agent、relay、journal、author-revision、native-runner 与 production-runtime 测试，证明没有重复 packet、启动、行、计费或结果消费。

回滚点：保留证据，不启动真实 run。

## 阶段 5 · 同步契约与操作文档

发布双语 spec、plan、tasks、verification，以及 Model Runtime 与 Agent Runtime 文档；规格 027 作为历史证据保留，只记录前向取代关系。

回滚点：代码与文档一起回滚，绝不改写历史 ledger。

## 阶段 6 · 执行已授权 REVISE

创建 REVISE 专用一次性 craft pack，通过 Core 注册精确 author-revision source；主调用上限 12，另留 1 次独立审稿；只轮询同一 pending request，直至 manager graph 到达外部审稿。

回滚点：注册前停止，或显式取消新 run；不得复用已消费的 DRAFT pack。

## 阶段 7 · 全新独立审稿与 release

只凭冻结 packet 启动一个全新 reviewer，原样保存 judgment bytes，完成 Core 审稿关卡，只读取释放的未接受 Review Draft；不 accept、不 settle。

回滚点：把 run 留在 `awaiting_external`，不得伪造或复用旧审稿证据。

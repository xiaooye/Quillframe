# Quillframe Model Runtime

宿主运行通用 Agent loop，Quillframe 管理小说契约。内置 Model / Agent Runtime 是 Studio 与本地 adapter 使用的 optional/reference implementation。外部模型服务只提供 inference，永远不会获得故事、Canon 或 Settlement authority。

## 两个输入

普通产品接入模型服务时只需要：

```text
API Endpoint
Access Token
```

Provider、Protocol、Auth Strategy、Model Profile、Capability checkbox 都不是 onboarding 输入。Vendor identity 最多是诊断 metadata。

## 连接流程

```text
Endpoint normalization / network policy
→ transient credential resolution
→ model discovery
→ per-model protocol discovery
→ bounded capability evidence
→ automatic eligibility / model selection
→ inference
```

当前 wire protocol family：

- OpenAI Chat Completions；
- OpenAI Responses；
- Anthropic Messages。

Protocol 是 wire codec，不是 Provider identity。同一 endpoint 的不同 model 可以绑定不同 protocol。

Endpoint 可以是主机根路径，也可以明确停在 `v1`、`v4`、`v4.1` 等版本段。Core 只在末段不是版本标识时补入默认 `v1`；明确版本段会原样保留，再追加 `models`、`chat/completions`、`responses` 或 `messages`，避免静默改写 Provider 的 API 基址。

Quillframe 当前的 OpenAI Chat 生产调用全部要求结构化 JSON，因此请求体显式发送 `response_format: {"type":"json_object"}`。系统仍验证返回的精确 Rust 类型；只声明 JSON 模式不会授予语义正确性或权威。

`GET /models` 只证明模型发现；它不证明 tools、vision、structured output 或 context window。

Capability evidence 保留状态、provenance、timestamp、service/model/protocol binding。Model/vendor 名字永远不是 capability proof。

## Secrets

Access Token 只存在于 host secret store 或当前 HTTP transport。SQLite、snapshot、prompt、Context、AgentJob、SemanticJob、checkpoint、receipt、fingerprint 与普通 diagnostics 都不得包含 resolved token。

Durable Model Service 只保存 `credential_ref`。Core restart 后可以 hydrate fingerprint-bound endpoint/model metadata；真正 inference 时才向 host SecretStore 解析 credential。

## Network policy

Remote endpoint 默认要求 HTTPS；URL userinfo/query/fragment 被拒绝。Direct transport 默认拒绝 redirect，并在请求前检查 DNS 解析结果，private/link-local/reserved 地址除非 host policy 显式允许。Loopback 保持可用，以支持 Ollama/LM Studio 等本地服务。

## 请求截止时间

普通推理请求默认时限为 180 秒；可显式指定最多 86,400 秒的有限正数。这个更大的值只约束准入与单次 HTTP 交互，不是已经启动的 durable worker 寿命。传输准备消耗同一额度，因此已过期请求不能开始新的派发。

只有向字面回环地址或 `localhost` 发起的 POST 才携带 `X-Quillframe-Deadline-Unix-Ms`。生产 AgentJob 还携带 SHA-256 形式的 `X-Quillframe-Model-Request-Key`。远端提供商的 header、模型消息和请求 body 语义保持不变。

v3 本地 relay 为 keyed 请求冻结一个不可变 packet，只做很短的交互等待。如果精确 worker 仍在运行，就返回 `202 model_pending`；重复发送完全相同的请求只轮询该 packet，不会再次派发。同 key 但 body 改变会触发幂等冲突。生产 journal 会在 transport 派发前把请求标记为 pollable，所以首个 `202` 前客户端崩溃也不能授权第二次调用。

初始 packet deadline 仍限制解析、队列准备和启动前准入。一旦 keyed worker 已有启动证据，API 慢不再形成任意进程超时：CLI 入口默认不设 worker 寿命上限，持续发布心跳并记录显式终态；操作者仍可配置有限紧急上限。普通无 key／library 调用继续保持有限边界。

HTTP waiter 结束不是模型失败，轮询也不增加模型调用。相同请求的精确终态输出可以在原 waiter 时间窗之后消费。已确认取消、终态 worker failure、身份／字节变化、无效输出或语义拒绝仍然阻断。心跳丢失或陈旧属于未知状态，绝不授权重试。详见 [durable pending 契约](../specs/032-durable-model-pending/spec.zh-CN.md)；规格 027 继续作为 v2 同步 packet 的历史记录。

## Persistence

Global SQLite 使用：

- `model_services`
- `discovered_models`
- `model_capability_evidence`

这些表由原生 1.0 schema fragment `persistence/schema/global/002_model_runtime.sql` 建立。Pre-1.0 数据库会被拒绝；不存在迁移或 fallback 读取路径。

## Normal CI / Live probe

Normal CI 使用本机 mock HTTP provider，禁止真实模型执行。真实兼容性验证只能通过 Host Bridge v11 显式启动：先用 `model.service.add` 登记 endpoint，通过 OS secret store 保存凭据，再调用 `model.service.test`。Rust Core 会记录精确 endpoint、protocol、model catalog 与 result receipt。

Live probe 的成功只是带时间和 endpoint/model binding 的 evidence，不是永久 capability truth。

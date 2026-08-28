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

`GET /models` 只证明模型发现；它不证明 tools、vision、structured output 或 context window。

Capability evidence 保留状态、provenance、timestamp、service/model/protocol binding。Model/vendor 名字永远不是 capability proof。

## Secrets

Access Token 只存在于 host secret store 或当前 HTTP transport。SQLite、snapshot、prompt、Context、AgentJob、SemanticJob、checkpoint、receipt、fingerprint 与普通 diagnostics 都不得包含 resolved token。

Durable Model Service 只保存 `credential_ref`。Core restart 后可以 hydrate fingerprint-bound endpoint/model metadata；真正 inference 时才向 host SecretStore 解析 credential。

## Network policy

Remote endpoint 默认要求 HTTPS；URL userinfo/query/fragment 被拒绝。Direct transport 默认拒绝 redirect，并在请求前检查 DNS 解析结果，private/link-local/reserved 地址除非 host policy 显式允许。Loopback 保持可用，以支持 Ollama/LM Studio 等本地服务。

## 请求截止时间

推理请求默认时限为 180 秒，可显式指定最多 600 秒的有限正数。传输准备消耗同一请求的时间额度；过期请求不得派发，迟到响应不得接受。这不会加入重试，也不会放宽外层 Agent 与生产 journal 的截止时间。

只有向字面回环地址或 `localhost` 发起的 POST 才携带 `X-Quillframe-Deadline-Unix-Ms`。它表示本次 HTTP 请求预算，时间原点不等同于更早的 journal 起点。远端提供商的请求头以及模型消息和请求体语义保持不变。版本 2 的本地 relay 将有效到期时间冻结到 packet；发布前若单调时钟剩余额度更短，只能据此收窄到期时间。CLI 按该时间执行并预留发布余量。默认调用方、relay、worker 时限仍为 180/170/150 秒；长正文可显式配置 600/590/570 秒。即使 worker 扩大了上限，短请求仍受调用方截止时间限制。这些属于宿主执行设置，不增加作者首次连接模型时的输入项。

直接 HTTP 传输会拒绝过期派发和迟到结果，但不提供操作系统级看门狗，不能主动打断阻塞中的 DNS 查询或持续缓慢读取的 socket。CLI 子进程另有终止截止时间；Core 仍会拒绝超过阶段期限的结果。单调时钟证据只在各自进程内有效，无法重建 packet 发布到另一进程准入之间的墙钟变化；本实现不承诺共享的跨进程时钟，上游请求仍独立检查并拒绝迟到结果。

## Persistence

Global SQLite 使用：

- `model_services`
- `discovered_models`
- `model_capability_evidence`

这些表由原生 1.0 schema fragment `persistence/schema/global/002_model_runtime.sql` 建立。Pre-1.0 数据库会被拒绝；不存在迁移或 fallback 读取路径。

## Normal CI / Live probe

Normal CI 使用 `MockTransport`，禁止真实模型执行。真实兼容性验证只能显式运行：

```bash
QUILLFRAME_LIVE_MODEL_TEST=1 \
QUILLFRAME_LIVE_MODEL_ENDPOINT=https://.../v1 \
QUILLFRAME_LIVE_MODEL_TOKEN=... \
python tests/live_model_runtime.py
```

Live probe 的成功只是带时间和 endpoint/model binding 的 evidence，不是永久 capability truth。

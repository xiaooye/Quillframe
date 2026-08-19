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

## Persistence

Global SQLite 使用：

- `model_services`
- `discovered_models`
- `model_capability_evidence`

Migration `002_model_runtime.sql` 从 0.9 初始 provider-centric schema 一次性迁移；它不会建立永久 runtime fallback。

## Normal CI / Live probe

Normal CI 使用 `MockTransport`，禁止真实模型执行。真实兼容性验证只能显式运行：

```bash
QUILLFRAME_LIVE_MODEL_TEST=1 \
QUILLFRAME_LIVE_MODEL_ENDPOINT=https://.../v1 \
QUILLFRAME_LIVE_MODEL_TOKEN=... \
python tests/live_model_runtime.py
```

Live probe 的成功只是带时间和 endpoint/model binding 的 evidence，不是永久 capability truth。

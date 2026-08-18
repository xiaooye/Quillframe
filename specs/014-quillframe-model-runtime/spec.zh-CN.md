# 规格说明 — Quillframe Model Runtime 与自有 Agent Loop

状态：实施中  
主任务模式：`SYSTEM-IMPROVE`  
基线：Quillframe 0.9 重构 PR #106 head `00422d5dd1787727953a15a03ddc14bbb9996132`  
目标版本：`0.9.x`

## 目标

Quillframe 自己是 Agent Runtime。用户连接模型服务时只提供两个输入：

```text
API Endpoint
Access Token
```

用户不选择 Provider、Protocol、Auth Strategy、Model Profile 或 capability checkbox。Quillframe Core 负责 endpoint 归一化、认证尝试、API surface/model discovery、bounded capability evidence、模型 eligibility/selection、模型请求、工具调用循环、session/run/checkpoint、permission、authority、budget、provenance 与失败语义。

产品心智模型固定为：

```text
User → Quillframe → Model API
```

Provider/vendor identity 最多是诊断 metadata，不是 runtime authority 或配置实体。

## 现状缺口

0.9 已有 Harness、Session/Run/Checkpoint、Runtime Capability、Control Plane、Semantic Worker、SQLite 与 typed Host Bridge，但 direct model execution 仍主要依赖 Codex/Claude CLI 与 OpenAI Responses semantic adapter。全局 SQLite 仍保存 `provider_configuration → model_registry`，与当前 Model Service 心智不一致。

Semantic Runtime 已经正确拥有 fingerprint/rubric/blindness/typed result/independence；本 feature 不把 coding/general agent job 塞进文学 semantic contract。

## 核心边界

### Model Runtime

拥有：
- Endpoint normalization / network policy；
- Secret reference resolution；
- model discovery；
- protocol-family codec；
- capability evidence；
- request/response/tool-call normalization；
- exact model execution provenance。

不拥有：
- Agent authority；
- Tool permission；
- Canon/Settlement/Framework-write authority；
- Project semantic truth。

### Agent Runtime

拥有 Quillframe 自己的 bounded model→tool→model loop、step/model/tool budget、cancellation、tool receipts 和 general `AgentJob/AgentResult`。

### Semantic Runtime

继续独立拥有 semantic fingerprint、rubric、output contract、blind context、independence 与 `semantic_reject` 语义。它可以复用 Model Runtime 做 inference transport，但不能被 Agent Runtime 取代。

### Tool Runtime

所有 tool call 先经过注册、schema、grant、authority、scope、budget、before-state/idempotency 检查，再执行。Model 不能自行授予 filesystem/subprocess/Canon/Framework 权限。

## Protocol family

v1 至少支持：

- `openai_chat_completions`
- `openai_responses`
- `anthropic_messages`

它们只是 wire protocol codec，不是 provider identity。一个 endpoint 内不同 model 可以解析到不同 protocol。

OpenCode Go 是 mixed-protocol compatibility fixture：当前官方 API 同一个 Go `/v1` 下同时有 `/chat/completions`、`/responses`、`/messages` 与 `/models`。Ollama/LM Studio/vLLM 等只作为 compatibility evidence，不进入 generic contract。

## Discovery / capability

`GET /models` 或等价 discovery 只证明 model listing。它不证明 tool calling、vision、structured output 或 context window。

Capability evidence state：

```text
verified | detected | manually_configured | unavailable | unknown
```

Provenance 与 timestamp/service/model/protocol binding 必须保留。Provider/model 名称永远不是 capability proof。

Live harmless inference probes 是 bounded runtime behavior；Normal CI 只运行 mock HTTP fixtures，禁止静默调用付费模型。

## Secrets / network

Access Token 只进入 host secret store / transient transport。Durable data 只保存 `credential_ref`。Token 禁止进入 prompt、Context、AgentJob、SemanticJob、checkpoint、event、receipt、fingerprint、diagnostic JSON 或普通 log。

Remote endpoint 默认要求 HTTPS；URL userinfo/query/fragment 被拒绝。Loopback 可用于 Ollama/LM Studio。Private/link-local 网络默认拒绝，除非 host policy 显式允许。

## Persistence

新增 ordered migration，把 `provider_configuration/model_registry` 迁到：

- `model_services`
- `discovered_models`
- `model_capability_evidence`

迁移后不保留 active Provider authority。`model_services` 保存 endpoint、credential_ref、snapshot/probe metadata；secret value 不进入 SQLite。

## Agent Job

`quillframe_agent_job_v1` 至少绑定：job/session/run/task_mode/runtime_role/model service、instruction/context、tool grants、required model capabilities、authority snapshot、budgets、idempotency 与 input fingerprint。

`quillframe_agent_result_v1` 返回 exact model/protocol、steps/model requests/tool calls、tool receipts、usage 与 truthful failure state，并始终 `authority=false`。

## Compatibility

保留现有 Codex CLI、Claude CLI、peer relay、MCP、GitHub job、human reviewer。它们仍是 eligible external runtime route，不强迫迁移到 endpoint API。

OpenAI-specific semantic adapter 应逐步变为 Model Runtime compatibility wrapper，而不是继续拥有第二套 HTTP/model execution semantics。

## 验收

- 用户连接 model service 时 Core API 只要求 Endpoint + Token。
- 一个 endpoint 可发现多个 model，且每个 model 可有独立 protocol/capability evidence。
- Quillframe 能完成 model→tool→model continuation，不依赖第三方 coding-agent runtime。
- repo read/search/write tool obey grant/authority/before-state/idempotency。
- secrets 不出现在任何可序列化 runtime artifact。
- Normal CI 的 protocol/agent tests 全部使用 mock transport。
- mixed OpenCode-style protocol fixture、generic OpenAI-compatible fixture、local endpoint fixture 通过。
- Semantic Runtime 的 fingerprint/independence/consume-once 语义不被改变。

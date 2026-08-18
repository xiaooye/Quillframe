# Frontend Contract Handoff · Host Bridge v7

并行 consumer：Studio PR #129。

## Ownership
UI 负责 SolidJS/Tauri 展示层、路由、AI/Models UX、Writer/Review/Inspector UX 与 BridgeClient transport；Core 负责 operation 语义、authority、persistence 与 typed error state。UI 不得直接读取 SQLite、复制 Python production runtime，或建立 UI 私有的 authority model。

本 Core workstream 不修改 Studio visual design、frontend composition、CSS、navigation 或 Writer UX。

## Production 状态机

### `author.run.start`
输入：`project_id`、唯一 `task_mode`、`payload`，可选 `target_ref/session_id/idempotency_key`。
输出：durable run，初始状态 `awaiting_semantic`；不会产生 Candidate。

### `author.run.status`
输入：`project_id`、`run_id`。
输出：当前 run status、持久化 typed runtime events、result fingerprint，以及存在时的 latest Candidate projection。

### `author.run.execute`
必需输入：
- `project_id`
- `run_id`
- `service_id`
- `instruction`
- `reader_grip`
- `rule_material`
- `independent_provenance`，其中包含 `project_id`、`project_repo`、`framework_repo`、`framework_commit`

可选输入：`document_id`、`model_id`、`stage_budgets`、`reader_visible_context`、`repair_preservation`。

DRAFT/REVISE 路径：

`Context profiles → eligibility/Decision/Greenlights → deterministic packing → Context Freeze + immutable payload bundle → Story/Canon Preflight → Scene Simulation → Character Simulation → Reader Pressure → Event-first Raw Draft → Surface Realization → registered Blind Reader (reader.engagement_audit) → Continuity → registered manager self-audit (quality.candidate_self_audit) → pre-independent qualification → external quality.production_review handoff`。

本地/manager 侧正常执行完成后通常返回 `status=awaiting_external`，并带有 fingerprint-bound `independent_review_request.peer_packet`。此时：
- Raw Draft 不返回；
- Review Draft Candidate 尚不存在；
- 同一 Writer / manager / Model Service invocation 不能冒充 independent review；
- peer packet 明确要求 fresh independent conversation/worker。

重要 typed state/error 包括：`awaiting_external`、`completed`、`stale_conflict`、`failed_gate`、`semantic_pending`、`run_in_progress`、`failed_gate_requires_fresh_run`、`target_document_required`、`not_qualified_for_independent`，以及 Model Runtime typed errors。

### `author.run.independent.submit`
必需输入：
- `project_id`
- `run_id`
- exact frozen `peer_packet`
- peer semantic `result`
- Project-owned `bridge_receipt`

Core 验证 exact registered `quality.production_review` job、peer relay nonce/result binding、`quillframe_project_peer_validation_receipt_v1`、candidate fingerprint、pre-independent qualification，以及仍然有效的 frozen Context boundary。只有合法的 independent PASS 才可能通过 `quality.production_readiness` 并创建一个 user-visible Review Draft Candidate。Independent FAIL 返回 `failed_gate`；禁止在同一 run 上 reviewer-shopping 直到出现 PASS。

Review Draft 仍然不等于 Accepted，更不等于 Settled。

### `author.run.context.refresh`
Project source 改变后显式创建新的 fingerprint-bound Context bundle。绝不静默修改旧 freeze。返回新的 bundle/freeze fingerprint 与 supersession linkage。在继续 production 或提交 independent result 前发现任何 source/project mutation，都必须返回 `stale_conflict`，不能静默继续。

## Production 消费的 Context 契约
每个 production mechanism 只接收当前 run 的 frozen stage context 与上游 artifact。Stage packet 明确携带 `context_fingerprint`、`stage_context_fingerprint`、source fingerprints 与 selector provenance。Stage materialization 没有 SQLite/store access path，并明确报告 `db_fetch_performed=false`。

Worker 不得自行扩大 candidate universe，也不得 hidden DB fetch。补充 Context 必须走 explicit refresh/extension semantics，并产生新的 fingerprint。

## Model Service operations
产品层 setup mental model 仍然只有 **Endpoint + Access Token**。Provider/protocol 名称只是 runtime discovery/compatibility evidence，不是用户必须先选的配置项，更不是 authority。

- `model.service.add(endpoint, access_token)`：连接/发现并持久化 public service/model metadata；secret value 只进入 host 注入的 SecretStore。
- `model.service.list()` / `model.service.get(service_id)`：只返回 public metadata。
- `model.service.discover(service_id)`：通过 host credential reference 刷新 discovery。
- `model.service.test(service_id, model_id?, verify_tools?)`：受限的真实 protocol/text/tool probe。
- `model.capabilities(service_id)`：public per-model capability evidence matrix；unknown 保持 unknown；capability 不产生 authority。
- `model.service.token.replace/remove` 与 `model.service.delete`：显式 lifecycle commands。

底层 Generic Model Runtime 根据 endpoint 证据发现兼容 protocol/model，不要求用户先选 vendor。兼容路径包括 OpenAI-style model listing、Responses-compatible、Chat-Completions-compatible、在客观可发现时的 Anthropic-compatible Messages，以及 local/custom compatible endpoints。Tool capability 只有在要求验证时通过 probe 确认，不从 vendor branding 推断。

失败保持 typed Model Runtime errors，例如 invalid endpoint、authentication/discovery failure、network failure、unresolved/unsupported protocol、credential unavailable、no eligible model。

## Credential boundary
Bridge request fingerprint 会对 `access_token` 等 credential value 做 redaction；Candidate Acceptance 的 business `authorization` 仍必须进入 fingerprint。Token value 不进入 Canon、project semantic state、Context、Context Freeze、AgentJob、semantic-worker input、receipts、logs、exports 或 `.qfproject` 数据。

Host integration requirement：
- Desktop：通过 `configure_secret_store` 注入 Tauri/OS-keychain `SecretStore`；
- Hosted Web：注入 server-side secure secret/session facility；
- `MemorySecretStore` 只是 process-local fallback，不得宣称为 durable credential persistence；
- Generic Core 不依赖 Cloudflare。

## 其他稳定 Core operations
当前可用 operation 包括 project create/open/inspect/search/backup/restore；document create/open/save/revisions/compare；Candidate Accept；Settlement apply；publication preview/build；feedback capture；以及 sessions、runs、checkpoints、Context、receipts、Candidates、learning、Context Runtime 的 Inspector projections。

## 明确 deferred
以下能力不得伪造正常成功状态：
- `project.delete`：在 Core-owned reversible delete transaction 出现前为 `unsupported`；
- `project.export` / `project.import`：portable transport contract 出现前为 `awaiting_external`；
- `candidate.review.request`：不提供 free-floating authority path；mandatory review 属于上述 production state machine。

## Stream/event behavior
Host Bridge v7 operation 当前是 request/response。Durable `runtime_events`、run status 与 checkpoints 是 canonical progress surface。以后可以增加 WebSocket/Tauri event transport，但 transport 不得改变 Core semantics，也不得创建第二套状态机。

## UI integration sequence
Core PR review/merge 后，UI PR #129 应从 fresh main rebase，并处理其与 Core 重叠的 `studio/host_bridge.py` / `host_bridge_contract.json`，以 Core v7 semantics 为 authority。BridgeClient 随后接入：
1. run start/status；
2. execute → `awaiting_external` handoff；
3. host/project peer-review transport；
4. `author.run.independent.submit`；
5. Review Draft / Candidate acceptance / Settlement；
6. Model Service Endpoint + Token setup/discovery/test/capability views。

Rebase 后执行 Web + Tauri E2E。不得把 Python runtime logic 复制进 frontend。

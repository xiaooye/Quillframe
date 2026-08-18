# Frontend Contract Handoff · Host Bridge v6

并行 consumer：Studio PR #129。

## Ownership
UI 负责 SolidJS/Tauri presentation 与 BridgeClient transport；Core 负责以下 operation 的语义、authority、persistence 与 error state。UI 不得直接读 SQLite，也不得创建替代性的 semantic truth。

## Production operations
### `author.run.start`
输入：`project_id`、唯一 `task_mode`、`payload`，可选 `target_ref/session_id/idempotency_key`。
输出：durable run，初始状态 `awaiting_semantic`；不会产生 Candidate。

### `author.run.status`
输入：`project_id`、`run_id`。
输出：当前 run status、persisted events、存在时的 latest candidate projection。

### `author.run.execute`
输入：`project_id`、`run_id`、`service_id`、`instruction`，可选 `document_id/model_id/stage_budgets`。
DRAFT/REVISE 正常路径：Context profiles/Decision/Greenlights/Freeze → frozen payload bundle → mandatory production mechanisms → independent semantic gate → user-visible gate → Review Draft Candidate。
可能状态/错误：`completed`、`stale_conflict`、`failed_gate`、`semantic_pending`、`run_in_progress`、`failed_gate_requires_fresh_run`、`target_document_required` 与 Model Runtime typed errors。Raw Draft 永不返回。
Authority=false；completed Candidate 仍不等于 Accepted 或 Settled。
Streaming：v6 是 request/response；进度通过 durable typed `runtime_events` 表达。客户端可刷新 `author.run.status`，未来也可加 host event transport，但不得改变 Core semantics。

### `author.run.context.refresh`
当 Project source 改变时显式创建新的 fingerprint-bound Context bundle。绝不静默修改旧 freeze。返回新 bundle/freeze fingerprint 与 supersession linkage。

## Model Service operations
用户 mental model 仍然只有 Endpoint + Access Token。

- `model.service.add(endpoint, access_token)`：discover 并持久化公开 service/model metadata；secret value 只进入 injected host SecretStore。
- `model.service.list()` / `model.service.get(service_id)`：只返回 public metadata。
- `model.service.discover(service_id)`：使用 host credential reference 刷新 discovery。
- `model.service.test(service_id, model_id?, verify_tools?)`：受限 real protocol/text/tool probe。
- `model.capabilities(service_id)`：public capability evidence matrix；unknown 保持 unknown；capability 不产生 authority。
- `model.service.token.replace/remove` 与 `model.service.delete`：显式 lifecycle commands。

失败保持 Model Runtime typed errors，例如 invalid endpoint、discovery failure、network failure、unresolved protocol、credential unavailable、no eligible model。

## Credential boundary
Bridge request fingerprint 只对 credential value（如 `access_token`）做 redaction；Candidate Acceptance 的 business `authorization` 仍必须进入 fingerprint。Token value 不进入 SQLite、Context、AgentJob、receipt、export 或 semantic worker payload。

Host integration requirement：
- Desktop：通过 `configure_secret_store` 注入 Tauri/OS-keychain `SecretStore`。
- Hosted Web：注入 server-side secure secret/session store。
- MemorySecretStore 只是 process-local fallback，不得在产品上宣称为 durable credential persistence。
- Contract 不依赖 Cloudflare API/binding。

## 新增 document/project operations
- `project.open`（与 inspect 使用同一 Core projection）
- `project.restore`（仅 CLI/local_app；hosted file-upload transport 另行处理）
- `document.open`
- `document.revisions.list`

既有 backup、revision save/compare、Candidate Accept、Settlement、publication、Inspector operations 保持兼容。

## 明确 deferred
以下能力不得伪造正常成功状态：
- `project.delete`：在 reversible Core delete transaction 出现前为 unsupported。
- `project.export` / `project.import`：等待 portable transport contract。
- `candidate.review.request`：不提供 free-floating review；mandatory review 属于 production execution。

## UI integration sequence
Core PR review/merge 后，UI PR #129 从 fresh main rebase，处理其与 Core 重叠的 `studio/host_bridge.py` / `host_bridge_contract.json`，以 v6 Core semantics 为 authority；然后 BridgeClient 接真实 operations，并执行 Web + Tauri E2E。不得把 Python runtime logic 复制进 frontend。

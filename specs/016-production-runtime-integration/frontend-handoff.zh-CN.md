# Frontend Contract Handoff · Host Bridge v8

当前 consumer：Studio PR #130。

## Ownership
UI 负责 SolidJS/Tauri 展示层、路由、Writer/Review/Inspector UX 与 BridgeClient transport；Core 负责 operation 语义、authority、persistence 与 typed error。UI 不得直接读取 SQLite、复制 Python production logic，或建立 browser-owned semantic/authority truth。

本 Core workstream 不修改任何 `studio/app/**` visual/frontend composition 文件。

## Production 状态机
`author.run.start` durable 注册且只注册一个 authoring task mode。`author.run.execute` 消费 frozen Context 并运行 mandatory production graph，通过 registered Reader/manager qualification 后，正常返回 `awaiting_external` 与 fingerprint-bound peer packet。Raw Draft 永不返回；此时 Review Draft Candidate 仍不存在。

同一 manager/Writer/Model Service 不能满足 independent gate。`author.run.independent.submit` 必须收到 exact peer packet、external semantic result 与 Project-owned `quillframe_project_peer_validation_receipt_v1`。只有合法 independent PASS 且 `quality.production_readiness` 通过，才能创建 user-visible Review Draft。Independent FAIL 是 `failed_gate`，禁止在同一 run reviewer-shopping。

Freeze 后任何 tracked source/project change 都返回 `stale_conflict`。`author.run.context.refresh` 是显式 supersession 路径；Core 不会静默修改旧 freeze。

## Context boundary
每个 production mechanism 只能收到自己的 frozen stage Context 与受限 upstream artifacts。Stage materialization 没有 SQLite/store access path，并报告 `db_fetch_performed=false`。Worker 不得扩大 candidate universe，也不得 hidden Project retrieval。

## v8 新增 Authoring primitives
以下六个 primitive 正式关闭 Studio PR #130 报告的 Core blocker：

### `project.list`
只读 canonical global Project registry projection。Browser storage 不具 authority。

### `document.list`
一个 Project 的只读 canonical Binder/document list；包含 latest revision identity/fingerprint/authority metadata。

### `candidate.review.get`
Exact Candidate-bound Review projection。Missing/stale independent evidence 必须 fail closed。返回 Review Draft revision、incumbent parent revision、unified diff，以及安全的 Reader/Character/Continuity/Independent/production-readiness/user-visible-gate evidence；`private_reasoning_exposed=false`。

### `candidate.reject`
Explicit user-authorized、exact-fingerprint、idempotent Reject。把可操作的 Review Draft 置为 `rejected`，写入可审计 receipt/event，不修改 Canon 或 Settlement。

### `candidate.revision.request`
Explicit user-authorized、exact-fingerprint、idempotent durable Request Revision。Physical Candidate status 保持既有 schema 值；Core projection 的 effective status 为 `revision_requested`，并阻止旧 Candidate 后续 Accept/Reject。返回指向 `author.run.start` + `task_mode=REVISE` 的 explicit next-action descriptor，**绝不自动启动 REVISE**。

### `settlement.preflight`
只读 authoritative Acceptance/Candidate/source-revision/current-Canon validation。返回供单独 user-authorized `settlement.apply` 使用的 exact `expected_before_fingerprint`；目标不存在时为 `absent`。Preflight 不执行 mutation。

## Model Service
用户 setup 仍只有 **Endpoint + Access Token**。Core 自行发现 protocol/model/capability evidence，并提供 `model.service.add/list/get/discover/test`、token lifecycle、delete 与 `model.capabilities`。Unknown 保持 unknown；capability 不产生 semantic、Canon 或 Settlement authority。

## Credential boundary
Credential value 只留在 host 注入的 SecretStore；durable Core 只保存 `credential_ref` 与公开 metadata。Bridge request fingerprint 对 credential 做 redaction；若 upstream provider 把 secret echo 到 nested result/error string，public projection 也会 scrub exact secret value。Candidate action 的 business authorization 仍必须 fingerprint-bound，不能被误当成 credential。

Desktop 应注入 Tauri/OS-keychain storage；Hosted Web 应注入 server-side secure secret/session storage。`MemorySecretStore` 仅为 process-local fallback。Generic Core 不依赖 Cloudflare。

## Deferred，不伪造
- `project.delete`：在 reversible Core transaction 出现前为 `unsupported`；
- portable `project.export/import`：在 transport contract 出现前为 `awaiting_external`；
- free-floating `candidate.review.request`：`unsupported`；mandatory semantic review 属于 production execution。

## Studio PR #130 integration sequence
Core PR #131 merge 后，从 fresh main rebase/integrate PR #130，并让 BridgeClient 以 v8 operation 为 authority：
1. 用 `project.list` 替换 browser-owned Project registry；
2. 用 `document.list` 替换 fixture Binder/document truth；
3. 用 `candidate.review.get` hydrate Review；
4. 将 Accept / `candidate.reject` / `candidate.revision.request` 接成 explicit typed command；
5. 在 `settlement.apply` 前立即调用 `settlement.preflight`，传入它返回的 exact before fingerprint；
6. 保留 execute → `awaiting_external` → independent transport → `author.run.independent.submit`；
7. Endpoint+Token Model Service UX 继续只通过 typed bridge。

随后运行 Studio typecheck/tests/build 与真实 browser smoke，并验证可用的 Tauri contract surface。不得把 Python runtime logic 复制进 frontend。

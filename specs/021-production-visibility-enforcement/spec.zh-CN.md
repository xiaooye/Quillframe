# Spec 021 · Production Visibility Enforcement / 生产可见性强制

## 状态

`SYSTEM-IMPROVE` 实施合同。冻结基线：`c6832365be6c4e3816b9c779dd0c2aa88b42cab9`。

## 问题

Quillframe Core 已经会隐藏 Raw Draft，并在 production gate pending/fail 时返回 `candidate_visible=false`。但 agent host 仍可能只读取 Framework 文档，然后绕过 Core 自己生成并展示正文。与此同时，ChatGPT 一类临时 Linux sandbox 在无法直接 clone GitHub 时，需要一种可验证地 materialize exact Framework runtime 的方式。

本次真实集成测试还暴露出三个相关缺口：

- pre-release qualified checkpoint 内含 `candidate_text`，若 agent surface 能枚举原始 checkpoint，会形成 visibility 旁路；
- Project peer bridge 的 `validate-result` 调用了不存在的 `peer_bridge_receipt.py build` CLI；
- `author.run.execute` 对 `rule_material` 只做浅层 list 检查，错误 schema 会在昂贵 production stages 完成后才被 registered self-audit 拒绝。

## 强制不变量

1. `DRAFT` / `REVISE` 中，Host 在没有 Core 对 exact candidate 签发 fingerprint-bound production release 前，绝不能展示 manuscript 正文。
2. Host 自己声称 PASS、prompt 文本、session memory、或未验证 payload 中的 boolean 都不是 release evidence。
3. Production candidate 的公开正文读取只能经过一个受控出口；它必须验证 run completed、candidate identity、candidate fingerprint、持久化 user-visible gate、readiness/release evidence 与 revision fingerprint。
4. pending / fail / stale / missing / mismatch 必须 fail closed，且响应对象中不得包含 manuscript content 字段。
5. Raw Draft 与 pre-release qualified candidate text 均不得通过 agent-facing inspector/query 旁路读取。
6. `quality.production_release` 必须成为最终 structural release aggregator，不能继续作为未接入主链的平行合同。
7. Ephemeral conversational host 可以在本地运行 Quillframe，但 runtime 源码必须来自可验证 exact Git commit；临时 SQLite 只属于 execution state，不构成第二套 durable Canon authority。
8. Chat host 的 manager-stage relay 只能是 loopback transport，必须使用原子 request/response materialization，并明确 `independent_review_evidence=false`；它不能充当 independent gate。
9. Independent semantic review 必须来自真正不同的 invocation/provider。历史 GitHub Models 路径不是已发布 provider；支持的远端兼容路径是 `github_copilot_actions`。它只拥有 semantic judgment，job/fingerprint/nonce/provenance/receipt 仍由确定性 bridge 绑定并再次验证。
10. `rule_material` 必须在 production graph 开始前用 registered `quality.candidate_self_audit` input contract 做 deterministic schema preflight。该 preflight 不做文学判断，也不得把 regression bad examples 提前注入 Writer。
11. 若 consumer Project adapter 规定 Git repo 为持久权威，则 Git 仍是 durable source/authority；Canon 修改只能通过 Settlement。

## Ephemeral runtime bundle

CI 必须为被测试的 source commit 发布 exact-source runtime bundle。Pull Request 场景必须绑定 PR head SHA，而不是 GitHub synthetic merge SHA。Bundle 必须保留足够的 `.git` metadata，使 Framework authority verifier 能证明 `HEAD == declared source SHA`，并附 source commit 文件与 SHA-256 digest。

## Chat host relay

Framework 提供 loopback OpenAI-compatible relay，使无法直接提供 Model API credential 的聊天 sandbox 仍可运行真实 Quillframe Model Runtime：

`ProductionRunExecutor → Model Runtime → localhost relay → current manager host → typed response → Core`

relay 只负责 transport，不重解释 semantic contract，不获得写权限，不可作为 independent review evidence。

## Project-owned independent review

`project-peer-semantic` action 支持显式的 `github_copilot_actions` 兼容 review mode；不宣称 GitHub Models 或 `models: read`。Consumer Project repo 继续拥有 issue/runtime trace。Reviewer 只看到 bounded peer packet，不看到 writer conversation 或 Project checkout。返回 judgment 后，Framework 必须重新验证 exact job、candidate fingerprint、relay nonce、registered contract、Project/Framework provenance 与 runtime trace，才能生成 peer validation receipt。

人工/另一聊天的 `prepare → validate-result` 路径继续保留，并必须真实可执行。

## Host Bridge 合同

新增 query operation：`candidate.visible.get`。它接受 `project_id`、`candidate_id`，并且：

- 只有全部不变量通过时，返回 `quillframe_user_visible_candidate_v1`，包含 exact candidate content 与 release evidence；
- release 无法证明时必须 fail closed，且不返回 content。

`candidate.review.get` 可以继续作为 Studio review projection，但 agent host 获取 production manuscript 必须使用 `candidate.visible.get`。`agent_package` 不得枚举包含 pre-release manuscript 的原始 production checkpoints。

## Release 组合

`ProductionRunExecutor.submit_independent` 必须将最终 `quality.production_readiness` 送入 `quality.production_release` 聚合。Structural receipts 至少需要覆盖当前 Context Freeze / production execution binding，以及 runtime 合同要求的 user-visible gate binding。持久化 candidate 必须绑定最终 release fingerprint。

## 验收

只有以下全部成立才算完成：

- 现有 Quillframe tests 全部通过；
- 新 negative tests 证明 no release / stale release / fingerprint mismatch / pending gate / raw checkpoint bypass 均拿不到 content；
- positive test 证明 fully released candidate 能由 `candidate.visible.get` 获取；
- exact PR-head runtime artifact 可下载到隔离 Linux 目录，通过 authority verification，并能运行 Core test suite；
- malformed `rule_material` 在任何 semantic generation 前 fail-fast；
- localhost manager relay 能把真实 DRAFT 推进到独立 handoff，且过程中 candidate/raw draft 不可见；
- Project-owned independent provider 能返回 fingerprint/nonce-bound valid receipt；
- 一次真实 DRAFT integration run 通过最终 production release，且只有 released candidate 才向用户展示。

本 spec 不包含 consumer Project repin，也不修改 Canon。

# Spec 021 · Production Visibility Enforcement / 生产可见性强制

## 状态

`SYSTEM-IMPROVE` 实施合同。冻结基线：`c6832365be6c4e3816b9c779dd0c2aa88b42cab9`。

## 问题

Quillframe Core 已经会隐藏 Raw Draft，并在 production gate pending/fail 时返回 `candidate_visible=false`。但 agent host 仍可能只读取 Framework 文档，然后绕过 Core 自己生成并展示正文。与此同时，ChatGPT 一类临时 Linux sandbox 在无法直接 clone GitHub 时，需要一种可验证地 materialize exact Framework runtime 的方式。

## 强制不变量

1. `DRAFT` / `REVISE` 中，Host 在没有 Core 对 exact candidate 签发 fingerprint-bound production release 前，绝不能展示 manuscript 正文。
2. Host 自己声称 PASS、prompt 文本、session memory、或未验证 payload 中的 boolean 都不是 release evidence。
3. Production candidate 的公开正文读取只能经过一个受控出口；它必须验证 run completed、candidate identity、candidate fingerprint、持久化 user-visible gate、readiness/release evidence 与 revision fingerprint。
4. pending / fail / stale / missing / mismatch 必须 fail closed，返回 typed blocked error，且响应对象中不得包含 manuscript content 字段。
5. Raw Draft 永远不能通过公开 visibility operation 读取。
6. `quality.production_release` 必须成为最终 structural release aggregator，不能继续作为未接入主链的平行合同。
7. Ephemeral agent host 可以在本地运行 Quillframe，但 runtime 源码必须来自可验证 exact Git commit；临时 SQLite 只属于 execution state，不构成第二套 durable Canon authority。
8. 若 consumer Project adapter 规定 Git repo 为持久权威，则 Git 仍是 durable source/authority；Canon 修改只能通过 Settlement。
9. Independent semantic review 必须继续是真正独立、fingerprint-bound；visibility 修复不能弱化或模拟独立审查。

## Ephemeral runtime bundle

CI 必须为被测试的 source commit 发布 exact-source runtime bundle。Pull Request 场景必须绑定 PR head SHA，而不是 GitHub synthetic merge SHA。Bundle 必须保留足够的 `.git` metadata，使 Framework authority verifier 能证明 `HEAD == declared source SHA`，并附 source commit 文件与 SHA-256 digest。

## Host Bridge 合同

新增 query operation：`candidate.visible.get`。它接受 `project_id`、`candidate_id`，并且：

- 只有全部不变量通过时，返回 `quillframe_user_visible_candidate_v1`，包含 exact candidate content 与 release evidence；
- release 无法证明时必须 fail closed，且不返回 content。

`candidate.review.get` 可以继续作为 Studio review projection，但 agent host 获取 production manuscript 必须使用 `candidate.visible.get`。

## Release 组合

`ProductionRunExecutor.submit_independent` 必须将最终 `quality.production_readiness` 送入 `quality.production_release` 聚合。Structural receipts 至少需要覆盖当前 Context Freeze / production execution binding，以及 runtime 合同要求的 user-visible gate binding。持久化 candidate 必须绑定最终 release fingerprint。

## 验收

只有以下全部成立才算完成：

- 现有 Quillframe tests 全部通过；
- 新 negative tests 证明 no release / stale release / fingerprint mismatch / pending gate 均拿不到 content；
- positive test 证明 fully released candidate 能由 `candidate.visible.get` 获取；
- exact PR-head runtime artifact 可下载到隔离 Linux 目录，通过 authority verification，并能运行 Core test suite；
- 一次真实 DRAFT integration run 到达正确 gate 状态，并且只有 released candidate 才能展示给用户。

本 spec 不包含 consumer Project repin，也不修改 Canon。
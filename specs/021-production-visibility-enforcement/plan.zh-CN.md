# Plan 021 · Production Visibility Enforcement / 生产可见性强制

## 顺序

1. 修正 CI runtime materialization：PR artifact 必须绑定 exact PR head SHA，并保留 shallow `.git` metadata。
2. 将 artifact 下载到隔离 Linux 目录，验证 declared SHA、archive digest、`git rev-parse HEAD`、Framework authority bootstrap，以及现有 Core test suite。
3. 新增 Core-owned production visibility projection，验证 candidate/run/revision/review/readiness/release binding；任一前置条件失败都不得返回 content。
4. 将 `quality.production_release.aggregate` 接入最终 production path，并为 candidate 持久化 fingerprint-bound release receipt。
5. 在 `studio/host_bridge.py` 与 `host_bridge_contract.json` 暴露 `candidate.visible.get`；保留 `candidate.review.get` 给 Studio 的完整 review projection，但不再把它当 agent manuscript release boundary。
6. 更新 host bootstrap/HARNESS 合同：DRAFT/REVISE 的 agent host 必须具备 production runtime capability；runtime/release 不可用时禁止自行合成 Quillframe 正文。
7. 增加 unit/integration regression tests：missing release、pending/fail、stale candidate、fingerprint mismatch、host fabricated boolean、Raw Draft 不泄漏，以及 valid release success。
8. 跑完整 CI，下载最终 exact-head artifact，在当前 chat Linux container 重跑测试，再执行一次真实 DRAFT 流程给用户做人类质量 review。

## 设计约束

- Prompt 或 host code 里不得出现第二套 production engine。
- Ephemeral SQLite 不成为第二套 Canon authority。
- 不削弱 independent semantic review。
- Release/visibility 只做确定性的授权与组合；文学判断继续由 registered semantic contracts 负责。
- Framework merge 前，不进行 consumer Project repin。
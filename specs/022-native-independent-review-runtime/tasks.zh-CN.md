# 任务 022 · 原生独立审查运行时

- [x] 冻结基线 `05efed31d37a27e901ab777fa3d544e078d65305`。
- [x] 创建隔离分支并记录 116-test/v9 基线。
- [x] 任务 1：冻结 packet、持久 lease/attempt、通用 receipt、Host Bridge v10、readiness（`a0f0a15` 及后续恢复/ fencing 修复）。
- [x] 任务 2：native agent/hook、exact-packet local runner、修复 GitHub adapter（`2bb6068`）。
- [x] 任务 3：mapped manifest、projection preview/apply/status、早期 preflight（`9480b06` 至 `ee70d2d`，含 migration 兼容修复）。
- [x] 任务 4：成对文档、完整回归、确定性构建、最终审查（`ccd3cd5` 至 `0775147`；Framework clean suite 181/181）。
- [x] 任务 5：重置并重新执行本地 Project 设计/CH001 链路、Codex native review 与仅 visibility 读取。当前链路证据在 consumer overlay 的 `runtime/evidence/CH-001.v0.9.1-local-chain.current.evidence.json`；reset 前材料均保留在可恢复的 `/tmp` quarantine。
- [x] 证明 `accepted=false`、`settled=false` 并记录所有 exact fingerprint。当前 released candidate 只通过 `candidate.visible.get` 读取；handoff 为 `runtime/evidence/CH-001.v0.9.1-local-chain.current.human-review.md`。

## 任务 5 证据 · 当前 reset 链路

- Fresh Project 与 runtime data 记录在外部、机器可读的 CH001 evidence JSON 中；Framework 仓库不保存 consumer Project 数据库。
- exact Framework commit 在执行时由 consumer lock 解析，并在外部 CH001 evidence JSON 中重复记录。
- Framework bundle：`sha256:3fd739b14b6c9ef9e0493cf186f4ca6eb4a7092e9c6180234eeccc300a5074d3`。
- Projection：`sha256:5143ee28e8e1ef1bd43d2ba9c04026d57ca94db5df8c1b901f8c49ac85170a7e`；manifest：`sha256:a3cfb21678401cc7def3d92a8c18948764654fbf9d498ec426e3866d85c317c8`。
- Context bundle、run ID、candidate ID 及全部 lifecycle fingerprint 以外部 CH001 evidence JSON 为准。
- Candidate：`sha256:27604cafbab04b5e4cf2dacb25cbcad8f3f3db8c1f59b7d4f096cabbf7955145`。
- Native reviewer：恰好一次 `codex_native_subagent` lifecycle，具有独立 reviewer session、exact packet/result/receipt 绑定及工具拒绝；Claude 没有评审这个 candidate。exact identity 以外部 evidence JSON 为准。
- Review Draft、handoff 与 evidence 保存在 Framework 仓库之外、用户指定的 consumer overlay 中。
- 没有 projection、Context、draft 或 review CH002/CH003；`accepted=false`、`settled=false`，Frostloom remote 未触碰。

此前的 9668aef 链路只作为历史证据，不是当前 Review Draft，也不得当作 release-chain 结果。

# 任务 022 · 原生独立审查运行时

- [x] 冻结基线 `05efed31d37a27e901ab777fa3d544e078d65305`。
- [x] 创建隔离分支并记录 116-test/v9 基线。
- [x] 任务 1：冻结 packet、持久 lease/attempt、通用 receipt、Host Bridge v10、readiness（`a0f0a15` 及后续恢复/ fencing 修复）。
- [x] 任务 2：native agent/hook、exact-packet local runner、修复 GitHub adapter（`2bb6068`）。
- [x] 任务 3：mapped manifest、projection preview/apply/status、早期 preflight（`9480b06` 至 `ee70d2d`，含 migration 兼容修复）。
- [x] 任务 4：成对文档、完整回归、确定性构建、最终审查（`ccd3cd5` 至 `0775147`；Framework clean suite 181/181）。
- [x] 任务 5：本地 Project 设计、CH001、Codex native review、仅 visibility 读取。新的本地链路证据记录在 `runtime/evidence/CH-001.v0.9.1-local-chain.evidence.json`；reset 前的材料已隔离在 active overlay 之外。
- [x] 证明 `accepted=false`、`settled=false` 并记录所有 exact fingerprint。发布 candidate 只通过 `candidate.visible.get` 读取；handoff 为 `runtime/evidence/CH-001.v0.9.1-local-chain.human-review.md`。

## 任务 5 证据

- Framework commit：`9668aefa1dfc7cbdd1be01b7b0b990cd585a7b21`。
- Framework bundle：`sha256:38cf2ed4b8ec62704c5522a25fc54a251148b900397d1619941d2da56dd81ad7`。
- Projection：`sha256:d7e26adf0cb1752bdaa8f8d300e04b4bf51a2547857c11d956ae21835f031fb9`。
- Projection manifest：`sha256:a2ab5c2bd75bca410472bfe0cfa1a53dd77fccd1f48b33832248eee76308a581`。
- CH001 run：`run_4f4aa5346081460c9cb2db67bc88f65d`；candidate：`cand_0c8dfacc021449959da57d643f8a072f`。
- Candidate：`sha256:a7d4ca13a245c5c6d3d0e5c2b6ea32c25d7350241d335d1f8f7eb4918bcf6d9b`。
- Native reviewer：恰好一次 `codex_native_subagent` invocation，通过隔离 exact-packet local adapter 完成；Claude 没有评审这个 candidate。
- Overlay 只保留本次 CH001 review evidence 与 handoff；没有 projection、Context、draft 或 review CH002/CH003。

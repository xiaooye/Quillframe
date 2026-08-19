# 任务 022 · 原生独立审查运行时

- [x] 冻结基线 `05efed31d37a27e901ab777fa3d544e078d65305`。
- [x] 创建隔离分支并记录 116-test/v9 基线。
- [x] 任务 1：冻结 packet、持久 lease/attempt、通用 receipt、Host Bridge v10、readiness（`a0f0a15` 及后续恢复/ fencing 修复）。
- [x] 任务 2：native agent/hook、exact-packet local runner、修复 GitHub adapter（`2bb6068`）。
- [x] 任务 3：mapped manifest、projection preview/apply/status、早期 preflight（`9480b06` 至 `ee70d2d`，含 migration 兼容修复）。
- [x] 任务 4：成对文档、完整回归、确定性构建、最终审查（`ccd3cd5` 至 `0775147`；Framework clean suite 181/181）。
- [ ] 任务 5：本地 Project 设计、CH001、Codex native review、仅 visibility 读取。
- [ ] 证明 `accepted=false`、`settled=false` 并记录所有 exact fingerprint。

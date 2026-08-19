# Plan 021 · Production Visibility Enforcement / 生产可见性强制

## 顺序

1. 修正 CI runtime materialization：PR artifact 绑定 exact PR head SHA，保留 shallow `.git` metadata，并提供 source SHA + archive digest。
2. 下载 artifact 到隔离 Linux 目录，验证 declared SHA、digest、`git rev-parse HEAD`、Framework authority bootstrap 和完整 Core test suite。
3. 将 `quality.production_release.aggregate` 接入 production final path，并持久化 fingerprint-bound release receipt。
4. 新增 Core `candidate_visible_get`：严格验证 candidate/run/revision/readiness/release binding；任一条件失败都不得返回 content。
5. 在 Host Bridge 暴露 `candidate.visible.get`，并关闭 `agent_package → raw production checkpoints` 的 pre-release manuscript 旁路。
6. 将聊天 sandbox 的 manager execution 收口到 loopback OpenAI-compatible relay；relay 采用原子 request/response 文件，只负责 transport，并显式不能作为 independent evidence。
7. 修复 Project peer receipt CLI 的 `build/validate` 命令，使既有 manual peer workflow 真正可执行。
8. 将 GitHub Models 设计记录标为 superseded；已发布的兼容 mode 是 `github_copilot_actions`：模型只输出 semantic judgment，deterministic bridge 负责 exact job/fingerprint/nonce/provider/runtime receipt binding。
9. 对 `rule_material` 增加 registered-contract dry preflight，在任何 Context/Story/Raw Draft semantic execution 前拒绝错误 schema。
10. 增加 regression tests：missing/tampered/mismatched release、checkpoint leak、host fabricated boolean、relay atomicity、unsupported-provider rejection、peer receipt CLI、rule-material fail-fast 与 valid release success。
11. 跑完整 Framework CI；下载最终 exact-head artifact，在当前 ChatGPT Linux container 重跑完整 tests。
12. 用 localhost manager relay 执行真实 DRAFT 到 independent handoff；再用 Project-owned independent provider 完成 peer review、submit、production release 与 `candidate.visible.get`。
13. 只有最终 release 后，才向用户展示新的校园剧 candidate 做人工质量 review。

## 设计约束

- Prompt 或 host code 里不得出现第二套 production engine。
- ChatGPT host 使用本地 `cli` transport 驱动 exact Core；不得靠扩大 `agent_package` semantic 权限实现。
- Ephemeral SQLite 不成为第二套 Canon authority。
- Manager relay 永远不满足 independent gate。
- Independent provider 不得查看 writer conversation/private Project context，只能收到 bounded peer packet。
- Release/visibility 只做确定性的授权与组合；文学判断继续由 registered semantic contracts 负责。
- Framework merge 前不进行 consumer Project repin；consumer repin 必须作为独立工程 run。

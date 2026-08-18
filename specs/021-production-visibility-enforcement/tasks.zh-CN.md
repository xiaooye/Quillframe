# Tasks 021 · Production Visibility Enforcement / 生产可见性强制

- [x] 将 SYSTEM-IMPROVE 基线冻结在 `c6832365be6c4e3816b9c779dd0c2aa88b42cab9`。
- [x] 建立隔离实现分支与 Draft PR。
- [x] 用本地 smoke harness 证明最小 visibility invariant：未 release candidate 响应中没有 content。
- [ ] 修正 runtime artifact：绑定 PR head SHA，并保留可验证的 shallow Git identity。
- [ ] 将 exact-head artifact 下载进隔离 Linux runtime，并通过 authority/bootstrap tests。
- [ ] 将 `quality.production_release` 接入最终 production execution，并持久化 release receipt。
- [ ] 新增 Core `candidate_visible_get` projection，所有失败条件都 fail closed 且隐藏 content。
- [ ] 新增 Host Bridge `candidate.visible.get`，更新 contract version。
- [ ] 更新 host/HARNESS：DRAFT/REVISE 禁止在 released production runtime 之外自行合成 manuscript。
- [ ] 增加 missing/stale/mismatched/pending/failing/fabricated release evidence 以及 valid release success 的 regression tests。
- [ ] 跑完整 Python/Core/Host Bridge/Studio/site CI。
- [ ] 下载最终 exact-head artifact，并在 ChatGPT Linux container 重跑测试。
- [ ] 执行一次真实 gated DRAFT，只在 release 后向用户展示 candidate 做质量 review。
- [ ] 将验证证据写入 PR，所有验收项通过后才标记 ready。
- [ ] 本任务不 repin consumer Project，不修改 Canon。
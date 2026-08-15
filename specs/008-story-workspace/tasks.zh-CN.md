# Tasks · Story Workspace & Narrative Runtime

> 当前 `feature/008-story-workspace` 已重新建立在 current main 上，只保留不会覆盖主线 shared registry 的 Core-safe slice。之前完整 integration 尝试保存在 backup branch，**不是 release candidate**；下列状态以当前 feature branch 为准。

- [x] T1 · 建立 `spec / plan / tasks`，冻结 authority / non-goal / acceptance 边界。
- [x] T2 · 定义 `novelforge_story_workspace_v1` schema 与 Core projector；覆盖 standard + mapped synthetic Project。
- [x] T3 · 定义 `novelforge_context_trace_v1`，串联 Inspector / `context.select` / memory-tier packing provenance。
- [x] T4 · 定义 `novelforge_event_ir_v1` schema、validator 与 synthetic event fixtures。
- [x] T5 · 定义 `novelforge_scene_simulation_run_v1`，绑定 base-state / semantic results / Event IR / branch fingerprints。
- [x] T6 · 定义 `novelforge_candidate_state_delta_v1`，表达 candidate `before -> after + evidence` 且保持 non-authoritative。
- [x] T7 · 定义 `narrative.verify` semantic contract 与 `novelforge_narrative_verification_v1` layered report；semantic issues 与 transport failure 分离。
- [x] T8 · 增加 stale fingerprint / future knowledge / authority flattening / selected-branch-is-not-Canon / semantic-reject-is-not-transport-failure deterministic guards；增加三条 generic narrative eval fixtures。
- [ ] T9 · 将新 schemas / tools / semantic contract 增量合并进 current-main `HARNESS_MANIFEST.yaml`、semantic catalog、top-level CLI 与 model-free CI；禁止用旧 feature blob 覆盖 shared registry。
- [ ] T10 · 在 current-main Studio Host Bridge 上增量加入 read-only `story.workspace` / `context.trace` / `scene.simulation.inspect` / `state.candidate.inspect` / `continuity.verify`，并保留现有 Publication/runtime operations。
- [ ] T11 · 将已实现的 `NarrativeWorkspace.tsx` 接入 current-main Studio route / product shell，保留 Inspector / Control / Architecture / Publication 与原 execution playground；不得建立 parallel Canon store。
- [ ] T12 · 将已完成的双语 `docs/story-workspace.*` 与 008 spec/plan/tasks 增量登记到 current-main documentation manifest，并更新相关 architecture / context / pipeline / Studio references。
- [ ] T13 · 在完成 shared integration 后跑 deterministic contract / syntax / schema / bundle / Studio typecheck/build / documentation quality tests，修复 regressions。
- [ ] T14 · 使用 blind narrative fixtures 获得独立 semantic capability / regression evidence；fixture 存在本身不等于 semantic acceptance。
- [ ] T15 · 基于 current main 建立新的 Draft PR，review exact diff、authority boundary、rollback path、base drift 与 CI status；旧 PR #80 因 clean-reset 已关闭，不作为当前 acceptance target。
- [ ] T16 · 合并后生成新的 exact Framework commit + deterministic bundle fingerprint / attestation evidence。
- [ ] T17 · 仅在 release evidence 完整后，由 consuming Project 单独执行 `novelforge.lock.json` / attestation dependency migration；旧 production session 不普通 resume。

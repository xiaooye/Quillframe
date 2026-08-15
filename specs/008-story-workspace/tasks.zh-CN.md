# Tasks · Story Workspace & Narrative Runtime

> 当前 `feature/008-story-workspace` 已完成对 current main 的增量 integration。Shared registry、CLI、Host Bridge、Studio routes 与 documentation 均以 current-main 为底合并，因此 Publication、Inspector、runtime control 与 authorized local `session.resume` 行为保持完整。早期 integration 尝试仅保存在 backup branch 用于 forensic rollback，**不是 release candidate**。

- [x] T1 · 建立 `spec / plan / tasks`，冻结 authority / non-goal / acceptance 边界。
- [x] T2 · 定义 `novelforge_story_workspace_v1` schema 与 Core projector；覆盖 standard + mapped synthetic Project。
- [x] T3 · 定义 `novelforge_context_trace_v1`，串联 Inspector / `context.select` / memory-tier packing provenance。
- [x] T4 · 定义 `novelforge_event_ir_v1` schema、validator 与 synthetic event fixtures。
- [x] T5 · 定义 `novelforge_scene_simulation_run_v1`，绑定 base-state / semantic results / Event IR / branch fingerprints。
- [x] T6 · 定义 `novelforge_candidate_state_delta_v1`，表达 candidate `before -> after + evidence` 且保持 non-authoritative。
- [x] T7 · 定义 `narrative.verify` semantic contract 与 `novelforge_narrative_verification_v1` layered report；semantic issues 与 transport failure 分离。
- [x] T8 · 增加 stale fingerprint / future knowledge / authority flattening / selected-branch-is-not-Canon / semantic-reject-is-not-transport-failure deterministic guards；增加三条 generic narrative eval fixtures。
- [x] T9 · 将新 schemas / tools / semantic contract 增量合并进 current-main `HARNESS_MANIFEST.yaml`、semantic catalog、top-level CLI 与 model-free CI；未使用旧 feature blob 覆盖 shared registry。
- [x] T10 · 在 current-main Studio Host Bridge 上增量加入 read-only `story.workspace` / `context.trace` / `scene.simulation.inspect` / `state.candidate.inspect` / `continuity.verify`，并保留 Publication/runtime operations 与 authorized local runtime-command surface。
- [x] T11 · 将 `NarrativeWorkspace.tsx` 接入 current-main Studio route / product shell，保留 Inspector / Control / Architecture / Publication 与原 execution playground；未建立 parallel Canon store。
- [x] T12 · 将双语 `docs/story-workspace.*` 与 008 spec/plan/tasks 登记到 current-main documentation manifest，并更新相关 architecture / context / pipeline / Studio references。
- [x] T13 · 完成 deterministic contract / syntax / schema / bundle / Studio typecheck-build / documentation quality 验证并修复 feature regression。Integrated branch 上 Story Workspace reusable CI、semantic contract packs、quality gate、Studio App、generic semantic kernel、bundle 与 eval stages 均通过；剩余 `session-terminate-command` 与 aggregate Host Bridge dispatch failure 在 current `main` 同样可复现，作为 upstream blocker 记录，不计为 008 regression。
- [ ] T14 · 使用 blind narrative fixtures 获得独立 semantic capability / regression evidence；fixture 存在与 hidden-label isolation 本身不等于 semantic acceptance。当前 live gate 因 repository 未配置 `OPENAI_API_KEY` provider credential，在任何模型执行前 fail closed。
- [ ] T15 · Review Draft PR #81 的 exact diff、authority boundary、rollback path、base drift 与最终 CI status；旧 PR #80 保持关闭，不作为 acceptance target。
- [ ] T16 · 合并后生成新的 exact Framework commit + deterministic bundle fingerprint / attestation evidence。
- [ ] T17 · 仅在 release evidence 完整后，由 consuming Project 单独执行 `novelforge.lock.json` / attestation dependency migration；旧 production session 不普通 resume。

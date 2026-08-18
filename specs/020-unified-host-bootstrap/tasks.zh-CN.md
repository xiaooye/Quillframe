# 任务 · Claude Code 与 Codex 统一 Project Bootstrap

格式：`[ID] [P?] [Phase] exact target + 完成标准`

## Phase 1 · Authority / Research Freeze

- [x] T001 Freeze live `main` at `e353fd506ae047b22c43442ceba0fda0a73c032d`，创建隔离 implementation branch。
- [x] T002 重新读取 HARNESS manifest、Skill、Harness Agent、Project SDK、host code、session runtime 与 Control Plane contracts。
- [x] T003 核对当前 Claude Code / Codex 官方 instruction/hook 行为，并记录 Codex trust constraint。
- [x] T004 写入中英文 spec/plan/tasks，明确 non-goals 与 overreach audit。

## Phase 2 · Unified Host Runtime

- [ ] T010 新增 `harness/integrations/host_bootstrap.py`，统一 scope/authority/session state。
- [ ] T011 通过 Control Plane 持久化完整 `quillframe_agent_session_v1`，替代临时 host session payload。
- [ ] T012 派生真实 `blocked | awaiting_task_mode | running` host states。
- [ ] T013 将 `claude_hook.py` 降为统一 runtime 的 compatibility wrapper。
- [ ] T014 增加 Codex wrapper/dispatch 与 Codex tool alias normalize。

## Phase 3 · Task Mode / Run Gate

- [ ] T020 新增 `quillframe host-run status|begin` deterministic CLI。
- [ ] T021 验证 exactly one 合法 task mode，并启动 exactly one manager run。
- [ ] T022 没有 valid authority + active task mode/run 时拒绝 consequential writes。
- [ ] T023 mode 未解析前只允许严格匹配 Quillframe bootstrap command，拒绝 lookalike shell command。
- [ ] T024 把 Codex `apply_patch` 视为 consequential edit。

## Phase 4 · Host Scaffolding

- [ ] T030 将根 router-only `AGENTS.md` 改成 compact direct Quillframe bootstrap instructions。
- [ ] T031 更新 generated consumer `AGENTS.md`，直接包含 exact-authority/session/run bootstrap。
- [ ] T032 生成 consumer `.codex/hooks.json`，并保持 Claude host scaffold compatibility。
- [ ] T033 增加 Framework `.codex/hooks.json`；trusted Codex session 可调用，但 static instruction correctness 不依赖 package install。
- [ ] T034 增加显式、幂等 `quillframe host-install` repair path，以安全 precondition 升级旧 supported Project。

## Phase 5 · Verification

- [ ] T040 增加 deterministic unified-host regression tests，覆盖 Claude/Codex parity、typed session、task mode、run、write gate、stale authority、hook alias 与 retrofit。
- [ ] T041 确认既有 Project SDK/bootstrap tests 保持 green。
- [ ] T042 确认 normal CI 不执行 live model/API。
- [ ] T043 跑 docs/site/Studio CI，并区分 candidate-owned failure 与 unrelated debt。

## Phase 6 · Documentation / Acceptance

- [ ] T050 同步 Project SDK/integration 中英文文档，包括 Codex hook trust 指引。
- [ ] T051 审查 exact diff，确认无 Framework/Project/Canon/provider overreach。
- [ ] T052 deterministic candidate checks ready 后开 review PR；CI 与 explicit acceptance 通过后再 merge。

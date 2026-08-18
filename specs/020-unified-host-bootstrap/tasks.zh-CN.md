# 任务 · Claude Code 与 Codex 统一 Project Bootstrap

格式：`[ID] [P?] [Phase] exact target + 完成标准`

## Phase 1 · Authority / Research Freeze

- [x] T001 Freeze live `main` at `e353fd506ae047b22c43442ceba0fda0a73c032d`，创建隔离 implementation branch。
- [x] T002 重新读取 HARNESS manifest、Skill、Harness Agent、Project SDK、host code、session runtime 与 Control Plane contracts。
- [x] T003 核对当前 Claude Code / Codex 官方 instruction/hook 行为，并记录 Codex trust constraint。
- [x] T004 写入中英文 spec/plan/tasks，明确 non-goals 与 overreach audit。

## Phase 2 · Unified Host Runtime

- [x] T010 新增 `harness/integrations/host_bootstrap.py`，统一 scope/authority/session state。
- [x] T011 通过 Control Plane 持久化完整 `quillframe_agent_session_v1`，替代临时 host session payload。
- [x] T012 派生真实 `blocked | awaiting_task_mode | running` host states。
- [x] T013 将 `claude_hook.py` 降为统一 runtime 的 compatibility wrapper。
- [x] T014 增加 Codex wrapper/dispatch 与 Codex tool alias normalize。

## Phase 3 · Task Mode / Run Gate

- [x] T020 新增 `quillframe host-run status|begin` deterministic CLI。
- [x] T021 验证 exactly one 合法 task mode，并启动 exactly one manager run。
- [x] T022 没有 valid authority + active task mode/run 时拒绝 consequential writes。
- [x] T023 mode 未解析前只允许严格匹配 Quillframe run-bootstrap command，拒绝 shell-chained lookalike。
- [x] T024 把 Codex `apply_patch` 视为 consequential edit。
- [x] T025 修复 Generic Framework → fiction Project bootstrap deadlock：pre-mode 只额外允许外部 target + id/title 的严格 `init` escape，不允许 `--force` / shell chaining，继续服从宿主正常 approval，创建后必须从新 Project 重启宿主。

## Phase 4 · Host Scaffolding

- [x] T030 将根 router-only `AGENTS.md` 改成 compact direct Quillframe bootstrap instructions。
- [x] T031 让正式 `quillframe init` / `host-install` 安装 generated consumer `AGENTS.md`，直接包含 exact-authority/session/run bootstrap。
- [x] T032 通过正式 CLI scaffold path 生成 consumer `.codex/hooks.json`，并保持 Claude host scaffold compatibility。
- [x] T033 增加 Framework `.codex/hooks.json`；trusted Codex session 可调用，但 static instruction correctness 不依赖 package install。
- [x] T034 增加显式、幂等 `quillframe host-install` repair path，以安全 precondition 升级旧 supported Project。

## Phase 5 · Verification

- [x] T040 增加 deterministic unified-host regression tests，覆盖 Claude/Codex parity、typed session、task mode、run、write gate、stale authority、hook alias、retrofit 与 Framework→consumer init escape。
- [x] T041 compatibility repair 后确认既有 Project SDK/bootstrap tests 保持 green。
- [x] T042 确认 normal CI 不执行 live model/API。
- [x] T043 跑 Core/SQLite/authority、docs/site 与 Studio CI；run 705 在最终 init-escape hardening 前已全绿，最终 candidate 仍须再次全绿才能验收。

## Phase 6 · Documentation / Acceptance

- [x] T050 同步 Project SDK/integration 中英文文档，包括 Codex hook trust 指引。
- [x] T051 审查 exact changed-file set：变更只落在 host/runtime/CLI/tests/docs/spec surfaces；没有修改 Project Canon、Settlement、provider secret 或 Studio UI 路径。
- [x] T052 已打开隔离于 `main` 的 draft review PR #141。
- [ ] T053 只有最终 candidate CI 全绿且用户明确接受后才 mark ready / merge；在此之前保持 candidate 可审查，不修改 `main`。

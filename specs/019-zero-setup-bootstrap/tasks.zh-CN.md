# 任务 · 零配置启动与 Claude Code 宿主守卫

格式：`[ID] [P?] [Phase/Story] 精确 target + 完成标准`

## Phase 1 · Foundation

- [x] T001 冻结 current `main`，检查 open PR / branches，并记录当前 Claude / Project SDK gap。
- [x] T002 调研当前 Claude Code 官方 CLAUDE import 与 hook contract。
- [x] T003 写入 spec / plan / tasks，明确 non-goals 与 rollback。

## Phase 2 · Project Authority

- [x] T010 在 `project_sdk.py` 增加 clean-checkout exact Framework identity helper。
- [x] T011 新 Project init 写入 exact lock + 匹配的 `framework.attestation.json`。
- [x] T012 增加显式 `pin` operation 与 `authority_ready` validation，不静默迁移 legacy Project。

## Phase 3 · Host Entry

- [x] T020 增加 `quillframe` console entrypoint 与 CLI delegation。
- [x] T021 把根 Claude router-only 行为改为官方支持的 static imports。
- [x] T022 把 Claude hook 从 telemetry-only 升级为 bootstrap context + cached authority snapshot。
- [x] T023 consumer authority verification 失败时，对 consequential tools fail closed。
- [x] T024 新 Project scaffold 生成使用已安装 host bridge 的 `.claude/settings.json`。

## Phase 4 · Verification

- [x] T030 增加 deterministic bootstrap / host regression tests。
- [x] T031 运行 core/unit/docs quality CI，并修复 candidate-owned failure。
- [x] T032 确认 normal CI 没有引入 model / live API execution。

## Phase 5 · Documentation / Acceptance

- [x] T040 同步中英文 Quick Start 与 Project SDK docs。
- [x] T041 审查 exact diff，确认 Framework / Project / Canon boundary没有 overreach。
- [ ] T042 仅在 CI green 后 merge，并删除临时 branch。

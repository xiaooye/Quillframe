# 实施计划 · Claude Code 与 Codex 统一 Project Bootstrap

## 选定架构

新增统一的 `harness/integrations/host_bootstrap.py`。Claude Code 与 Codex wrapper 只负责 normalize host event / tool name，然后委托同一个 core，禁止形成两套 workflow。

Core 只拥有 deterministic host bootstrap facts：

`discover scope → verify Project/Framework authority → load/create typed manager session → expose bootstrap state → validate task-mode transition → start/resume manager run → gate consequential tools`

`task_mode` 的语义选择仍由模型/用户负责。确定性代码只验证它属于 Framework 允许的 mode，并阻止 active run 中静默切换第二个 mode。

## Runtime State

通过 Control Plane `put_session` 持久化完整既有 `quillframe_agent_session_v1` payload。Host-native session id 确定性映射为 Quillframe session id。Session 内真实保存 task mode、runs、checkpoints、events、context policy 与 provenance，不再维护一套临时拼装 schema。

由 authority + typed session 派生 host state：

- `blocked`：consumer exact authority 无效；
- `awaiting_task_mode`：authority 有效，但没有 active Quillframe mode/run；
- `running`：存在且只存在一个 active run，session task mode 合法；
- Generic Framework scope 同样要求先有明确 mode/run 才允许 consequential Framework edits。

## Host Adapters

### Claude Code

保留 `harness/integrations/claude_hook.py` 作为薄 wrapper；既有 `.claude/settings.json` 继续支持，并调用 installed CLI。

### Codex

增加 Codex wrapper/common dispatch。新 Project 生成 `.codex/hooks.json`，覆盖 SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/SessionEnd；编辑 matcher 覆盖 `Bash|Edit|Write|apply_patch`。

由于 Codex project hook 需要用户 trust，`AGENTS.md` 必须是第一等 static bootstrap surface，而不是指向其他文档的 router。

## Task-mode / Run Command

新增薄 CLI：

```text
quillframe host-run status [--session-id ...] [--project .]
quillframe host-run begin --session-id ... --mode DESIGN-BOOK [--project .]
```

`begin` 验证 authority、session identity、合法 mode 与当前 active-run state，再调用 `session_runtime.start_run` 更新 typed session。Run id 每次 begin 唯一并明确绑定 execution identity。

Host injected context 必须包含 exact Quillframe session id，以及模型在完成语义 mode 选择后可以执行的 exact command shape。

## Write Gate

只有 derived bootstrap state 为 `running` 且 exact authority 仍 fresh 时，consequential tool 才可执行。

Mode 未解析前，Bash 默认拒绝；唯一例外是严格 parser 识别的 Quillframe 自身 `quillframe host-run status|begin ...` bootstrap command，禁止 substring allowlist。Codex `apply_patch` normalize 为 edit。

Framework scope edit 同样需要 active run。若当前工作属于 Framework engineering，应显式使用 `SYSTEM-IMPROVE`；fiction mode 不得导致具体 Project facts 被写入 generic Framework repo。

## Static Instructions

把根 `AGENTS.md` 从 router 改成 compact direct contract，至少直接说明：Generic Framework boundary、manifest/Skill/HARNESS bootstrap、exactly one task mode、session/run requirement、Framework 不保存 Project facts/Canon、consequential edit 前启动 host-run。

Consumer `AGENTS.md` 写入等价的 Project-specific exact-authority rules；Claude 的 `CLAUDE.md` 仍可 import 它。

## Existing Project Repair

新增 `quillframe host-install <project>`。

它补齐 `.claude/settings.json` / `.codex/hooks.json`，并只在 `CLAUDE.md` / `AGENTS.md` 与已知 generated scaffold 匹配时自动升级；未知自定义内容返回 `manual_merge_required`，不得直接覆盖。Lock、attestation、manifest、profiles、plans、manuscripts 与 Canon 全部不动。

## 影响路径

- `harness/integrations/host_bootstrap.py`（新增）
- `harness/integrations/claude_hook.py`
- Codex wrapper（新增）
- `quillframe/cli.py`
- `project_sdk.py`
- `AGENTS.md`
- `.codex/hooks.json`
- consumer scaffold generators
- `tests/test_quillframe_unified_host_bootstrap.py`（新增）
- Project SDK / integration 中英文文档

## Migration Strategy

不自动迁移 Framework 或 Project schema。新 scaffold 同时获得两个 host。旧 supported Project 通过显式 `quillframe host-install` 修复。未知自定义 host files 永不静默替换。

## Test Strategy

Deterministic unit/subprocess tests 覆盖 typed session persistence、host parity、Codex tool alias、task-mode/run transition、pre-mode write denial、严格 bootstrap-command allowlist、stale authority denial、generated scaffold、host-install idempotency 与 static instruction fallback。Normal CI 不调用模型。

## Phases / Checkpoints

1. Freeze spec/plan/tasks 与当前 host contracts。
2. 实现 host-neutral typed session/bootstrap core。
3. 增加 task-mode/run CLI 与 write gate。
4. 增加 Codex adapter/scaffold 与 root static instructions。
5. 增加 existing-Project host-install repair path。
6. 增加 regression tests 与中英文 docs。
7. 跑 CI、security/authority boundary review，进入 human-review readiness。

## Rollback

Revert spec 020 implementation。既有 `quillframe` CLI 与 Project lock/attestation 保持不变；不执行 Canon 或 Project authority migration。

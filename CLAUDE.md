# Quillframe · Claude Code Bootstrap

@AGENTS.en.md
@SKILL.md
@CLAUDE.en.md
@harness/HARNESS_AGENT.en.md

This stable path is Claude Code's project entry. The imports above are intentional: Claude Code loads them at session start, so Quillframe authority/task-mode boundaries apply before the first user prompt instead of relying on the model to discover linked files later.

简体中文权威版本仍保留在 `AGENTS.zh-CN.md`、`CLAUDE.zh-CN.md`、`SKILL.zh-CN.md` 与 `harness/HARNESS_AGENT.zh-CN.md`；需要中文解释时按需读取，不重复注入整套双语上下文。

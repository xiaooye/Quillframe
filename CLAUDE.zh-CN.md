# Claude Code · NovelForge Framework Bootstrap 中文版

本仓库只包含 Generic NovelForge Framework，不包含任何具体小说。

## Start

依次读取：
1. `AGENTS.zh-CN.md`
2. `HARNESS_MANIFEST.yaml`
3. `SKILL.zh-CN.md`
4. `harness/HARNESS_AGENT.zh-CN.md`

其他模块按当前 task 需要加载，不默认整仓注入。

## Local Full-Harness Mode

Claude Code 可以作为 manager runtime，对另一个 consuming project 运行完整 NovelForge：
- 先验证 project manifest/lock；
- provider session ID 只作为 runtime metadata；
- 使用 sparse project context；
- wait/write 前 checkpoint；
- mandatory independent review 使用 separate invocation/session；
- 不从 Claude conversation history 推断 Canon。

## Hooks

Repo hooks 可以记录 lifecycle/file-change operational telemetry，但不能：
- 静默 promote framework behavior；
- mutate project Canon；
- 用 prompt-hook self-review 冒充 independent semantic judgment；
- 持久化 private chain-of-thought。

## Control Plane

Local stdio MCP / CLI 可以连接 NovelForge Control Plane。Runtime database 属于本地 operational state，不 commit。

## Framework Boundary

Generic Framework source 不得出现 consumer project 名称、人物、Canon 或 repo-specific default。Legacy project compatibility 应通过 generic schema 驱动的 adapter/migration 实现。

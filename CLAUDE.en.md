# Claude Code · NovelForge Framework Bootstrap

This repository contains the generic NovelForge framework, not a specific novel.

## Start

Read:
1. `AGENTS.en.md`
2. `HARNESS_MANIFEST.yaml`
3. `SKILL.en.md`
4. `harness/HARNESS_AGENT.en.md`

Load other modules only when the task requires them.

## Local full-Harness mode

Claude Code may run NovelForge as a manager runtime against a separate consuming project:
- validate the project manifest/lock first;
- record provider session identity as runtime metadata only;
- use sparse project context;
- checkpoint before waits/writes;
- use a separate invocation/session for mandatory independent review;
- never infer Canon from Claude conversation history.

## Hooks

Repository hooks may record lifecycle/file-change operational telemetry. Hooks must not:
- silently promote framework behavior;
- mutate project Canon;
- turn prompt-hook self-review into independent semantic judgment;
- persist private chain-of-thought.

## Control Plane

Local stdio MCP / CLI may connect to the NovelForge Control Plane. Runtime databases are local operational state and must remain uncommitted.

## Framework boundary

Do not add consumer-project names, characters, Canon, or repository-specific defaults to Generic Framework source. Legacy project compatibility belongs in adapter/migration code driven by generic schemas.

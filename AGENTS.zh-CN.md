# AGENTS · NovelForge 仓库 Agent 指南

## Scope

本文件约束 **Generic NovelForge Framework Repo** 内的 coding/agent 工作。

任何 consumer novel 的人物、剧情、Canon、repo path 或用户 private preference data 都不能进入这里。

## Bootstrap

1. 读取 `HARNESS_MANIFEST.yaml`；
2. 读取 `SKILL.zh-CN.md`；
3. 读取 `harness/HARNESS_AGENT.zh-CN.md`；
4. Structural framework change 读取 `harness/SELF_IMPROVEMENT_PROTOCOL.zh-CN.md`；
5. Project Engineering 读取 `docs/project-sdk.zh-CN.md`；
6. Learning/Corpus 读取 `docs/adaptive-learning.zh-CN.md` 与 Corpus policy；
7. 确定 exactly one primary task_mode。

## Engineering Rules

- 用户已授权的 maintenance 默认直接改 `main`，除非用户明确要求 branch/PR；
- Generic Framework 与 consumer project 永远单向依赖：Project → Framework；
- Framework code/test/doc 不得包含 project-specific import/default；
- Normal CI 不得静默消耗 API/Codex/Claude/model usage；
- Material behavior change 必须有 mechanism evidence、tests/evals、version/rollback 与 green CI；
- Identity、state、schema、fingerprint、permission、idempotency、算术、release invariant 尽量由 deterministic code 负责；
- 只有真正需要判断时才使用 independent semantic worker；
- Runtime state、learning state、project Canon 分离持久化；
- 不 commit credential、local runtime/learning DB、private chat、chain-of-thought。

## Documentation

Human-facing authoritative docs 必须成对发布 `.en.md / .zh-CN.md`。只有外部工具要求固定 path 时，允许保留一个精简 bilingual router。

Machine schema 保持单份 JSON/YAML/TOML-compatible contract，配套 human explanation 必须双语。

架构图优先 Mermaid。Static visual asset 必须原创或有清晰 license/provenance。

## Project SDK Principle

每一本小说 project 都是完整 engineering artifact：manifest、lockfile、authority/state、plans、manuscripts、research、tests/evals、build bundle、migration、rollback history 都应存在。

Generic Framework 不 hard-code 某个 legacy project 的目录；旧项目通过 adapter/migration 兼容。

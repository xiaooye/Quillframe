# Project Adapter Protocol · 项目适配协议

## 目的

NovelForge Project 是 Generic Framework 的 consumer。Adapter 告诉 Harness：如何解析这个项目自己的 identity、profiles、Canon/state、plans、research、manuscripts、tests 与 project-only regressions。

Framework 永远不能把具体项目事实反向 import 进自己的 source tree。

## Required Project Identity

标准项目使用：

```text
novelforge.toml
novelforge.lock.json
```

`novelforge.toml` 声明 project identity、logical authority paths、profiles 与 build settings。

`novelforge.lock.json` 锁定 framework compatibility/version/commit/bundle fingerprint。

可以支持 alternative adapter，但必须暴露同一 logical contract。

## Dependency Direction

```text
Project → Framework
Framework -X→ Project-specific data
```

Framework 可以定义 schema 与 validator；不能 hard-code 任何 consumer project 的路径、人物、BOOK ID、剧情事实或 repo 名。

## Project-owned Domains

Project 自己拥有：
- project identity / release version；
- genre/platform/project profiles；
- framework 允许范围内的用户明确 project override；
- BOOK/VOL/ARC/UNIT/CH/SCN 实例；
- character / relationship / world / organization / research 对象；
- current structured state；
- Accepted Canon artifact；
- active plans；
- project regression/capability fixtures；
- project corpus refs/benchmarks；
- project assets/manuscripts；
- settlement migrations / derived views。

Framework 拥有 generic mechanism 与 quality contract。

## Adapter Output

Bootstrap 时至少解析：

```yaml
project_id:
project_version:
project_root:
framework_lock:
authority_paths:
profile_paths:
canon_cutoff:
active_plan_paths:
research_paths:
eval_paths:
bundle_ref:
```

这些只是 resolution metadata，不等于 model context。

## Sparse Context Manifest

Adapter 找到项目后，Context Curator 仍只选择当前任务真正需要的 object。

不能因为 Adapter 能定位整个 bible/state/manuscript history，就默认把它们全部注入模型。

## Framework Bundle

为避免每次任务跨 repo 反复读 engine，Project 可以把 lockfile 锁定的 framework release materialize 到：

```text
.novelforge/framework/
```

这是 read-only dependency cache，默认 gitignore。

规则：
- 验证 lockfile fingerprint/commit；
- 不能把 cache 当 project behavior 直接修改；
- framework upgrade 是显式 dependency change；
- compatibility test 失败则 upgrade 不得完成。

## Compatibility

Project 声明 project schema version 与 minimum/locked framework version。

非平凡 framework upgrade 应走 structural-change spec：

```text
spec → plan → tasks → sync/upgrade → validate → project tests/evals → acceptance
```

Framework schema 变化时，不得静默 reinterpret 旧 Canon。

## Legacy Project Adapter

已有小说可以保留旧物理目录，再通过 adapter/migration 层逐步映射到标准逻辑边界。

Migration 可以逐步完成：
- old project entry → `novelforge.toml`；
- old Canon/state table → standard authority path 或 adapter mapping；
- old prose/project rules → framework fundamentals + 真正 project override；
- old runtime files → framework lock dependency；
- old generated/derived files → 显式 lifecycle class。

具体项目 migration 可以作为 Project SDK 的设计证据，但人物、剧情、Canon 等 concrete facts 永远不能复制到 framework。

## Authority Invariant

> Framework 提供“如何生产小说”的语言；Project 提供“这一本小说到底是什么”的事实。

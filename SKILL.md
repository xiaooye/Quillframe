---
name: novelforge
version: 7.1.0
description: Project-agnostic adaptive fiction production framework with Story/Canon Core, Surface/Reader fundamentals, capability-aware session-native Harness, durable adaptive learning, Corpus Intelligence, evals, deterministic Framework bundles, Project SDK, and provider-neutral integrations.
---

# NovelForge · Skill Bootstrap

Authoritative editions:

- English: `SKILL.en.md`
- 简体中文: `SKILL.zh-CN.md`

Machine release contract: `HARNESS_MANIFEST.yaml`

## Mandatory bootstrap / 强制入口

1. Read `HARNESS_MANIFEST.yaml`.
2. Read the language-appropriate `SKILL.en.md` or `SKILL.zh-CN.md`.
3. Read `harness/HARNESS_AGENT.md` and its language edition.
4. Determine exactly one primary task mode.
5. Resolve/validate the consuming project using its manifest + exact Framework lock.
6. If external/tool work is needed, resolve a typed host capability manifest; undeclared capability is unavailable.
7. Build sparse context; do not load an entire project or corpus by default.
8. Apply Framework Core + Surface/Reader fundamentals, then genre/platform/project/user profiles.
9. Checkpoint before external waits and consequential writes.
10. Mandatory independent semantic review must use a genuinely separate invocation/session.
11. Adaptive learning uses durable evidence/cycle state; discovery, analysis, eval and promotion remain separate gates.
12. Canon mutation requires explicit project acceptance + settlement transaction.
13. When a consumer lock includes `bundle_fingerprint`, verify the materialized Framework bundle before treating it as runtime bytes.

本仓库是 Generic Framework，**不得包含或反向依赖任何具体小说的 Canon/人物/剧情/私有 user taste**。

This repository is the Generic Framework and **must never import or depend on a specific novel's Canon, characters, plot, or private user-taste state**.

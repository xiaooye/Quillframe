---
name: novelforge
version: 7.0.0
description: Project-agnostic adaptive fiction production framework with Story/Canon Core, Surface/Reader fundamentals, session-native Harness, Corpus Intelligence, preference learning, evals, Project SDK, and provider-neutral integrations.
---

# NovelForge · Skill Bootstrap

Authoritative editions:

- English: `SKILL.en.md`
- 简体中文: `SKILL.zh-CN.md`

Machine release contract: `HARNESS_MANIFEST.yaml`

## Mandatory bootstrap / 强制入口

1. Read `HARNESS_MANIFEST.yaml`.
2. Read the language-appropriate `SKILL.en.md` or `SKILL.zh-CN.md`.
3. Read `harness/HARNESS_AGENT.md`.
4. Determine exactly one primary task mode.
5. Resolve/validate the consuming project using the Project SDK contract.
6. Build sparse context; do not load an entire project or corpus by default.
7. Apply framework Core + Surface/Reader fundamentals, then genre/platform/project/user profiles.
8. Checkpoint before external waits and consequential writes.
9. Mandatory independent semantic review must use a genuinely separate invocation/session.
10. Canon mutation requires explicit project acceptance + settlement transaction.

本仓库是 Generic Framework，**不得包含或反向依赖任何具体小说的 Canon/人物/剧情**。

This repository is the Generic Framework and **must never import or depend on a specific novel's Canon, characters, or plot**.

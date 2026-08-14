# AGENTS · NovelForge Repository Guidance

## Scope

This file governs coding/agent work inside the **generic NovelForge framework repository**.

No consuming novel's characters, plot, Canon, repository path, or private user preference data belongs here.

## Bootstrap

1. Read `HARNESS_MANIFEST.yaml`.
2. Read `SKILL.en.md`.
3. Read `harness/HARNESS_AGENT.en.md`.
4. For structural framework changes, read `harness/SELF_IMPROVEMENT_PROTOCOL.en.md`.
5. For project-engineering work, read `docs/project-sdk.en.md`.
6. For learning/corpus work, read `docs/adaptive-learning.en.md` and Corpus policy.
7. Determine exactly one primary task mode.

## Engineering rules

- Work directly on `main` for user-authorized maintenance unless explicitly asked for a branch/PR.
- Keep Generic Framework and consumer projects strictly one-way: Project → Framework.
- No project-specific imports/defaults in framework code/tests/docs.
- Normal CI must not silently spend API/Codex/Claude/model usage.
- Material behavior changes require mechanism evidence, tests/evals, version/rollback, and green CI.
- Use deterministic code for identity, state, schemas, fingerprints, permissions, idempotency, arithmetic, and release invariants.
- Use independent semantic workers only where model/human judgment is genuinely required.
- Persist runtime state, learning state, and project Canon in separate domains.
- Never commit credentials, local runtime/learning databases, private chats, or chain-of-thought.

## Documentation

Human-facing authoritative docs are paired `.en.md` / `.zh-CN.md`. Stable router files may remain bilingual single-page entry points only when external tooling requires a fixed path.

Machine schemas remain single-source JSON/YAML/TOML-compatible contracts; their human explanations are bilingual.

Use Mermaid for version-controlled diagrams. Static visual assets must be original or clearly licensed/provenanced.

## Project SDK principle

A novel project is a complete engineering artifact with manifest, lockfile, authority/state, plans, manuscripts, research, tests/evals, build bundle, migrations, and rollback history.

Do not hard-code the layout of one legacy project into the generic framework; support legacy structures through adapters/migrations.

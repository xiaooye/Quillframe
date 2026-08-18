# AGENTS · Quillframe Repository Guidance

## Scope

This file governs coding/agent work inside the **generic Quillframe framework repository**.

No consuming novel's characters, plot, Canon, repository path, or private user preference data belongs here.

## Bootstrap

1. Read `HARNESS_MANIFEST.yaml`.
2. Read `SKILL.en.md`.
3. Read `harness/HARNESS_AGENT.en.md`.
4. Determine exactly one primary task mode.
5. For structural framework changes, read `harness/SELF_IMPROVEMENT_PROTOCOL.en.md`.
6. For project-engineering work, read `docs/project-sdk.en.md`.
7. For learning/corpus work, read `docs/adaptive-learning.en.md` and Corpus policy.
8. **For any human-facing documentation, README, diagram, comparison, docs information architecture, or visual-identity work, read and follow `docs/DOCUMENTATION_STANDARD.en.md`, `docs/DOCUMENTATION_QA.en.md`, and `assets/DESIGN_SYSTEM.en.md` before editing.**

## Engineering rules

- **Work directly on `main` for user-authorized routine maintenance by default. Do not create a branch merely because the task is large.** Use a branch/PR only when the user requests it, repository protection requires it, the change genuinely needs isolated review/migration, multiple contributors need a coordination boundary, or an external workflow specifically depends on a PR.
- **Branch budget:** outside `main`, keep the normal active working set to **at most one general/agent branch and at most one UI/product/visual branch**. Zero branches is preferred when direct `main` work is appropriate. This is a repository-hygiene target, not permission to bypass required isolation or review.
- Before creating any branch, inspect current branches and open PRs. Reuse the existing branch for that category when its scope is compatible; do not create one branch per task, per coding agent, or per chat/session.
- A new coding-agent/session should normally continue on `main` or the existing category working branch. If a genuinely incompatible change needs a new branch while that category slot is occupied, first merge/close/delete or explicitly supersede the old branch. Keep parallel branches in the same category only when the user explicitly authorizes the exception or an external workflow requires it.
- Branches are working state, not archives. Preserve historical context in commits, merged/closed PRs, issues, release artifacts, or tags; delete stale/superseded branch refs after their useful work is preserved.
- Before consequential writes, re-read current `main` when another session/contributor may be active and preserve unrelated concurrent work.
- Temporary branches created exceptionally should be merged/closed and deleted when no longer needed.
- Keep Generic Framework and consumer projects strictly one-way: Project → Framework.
- No project-specific imports/defaults in framework code/tests/docs.
- Normal CI must not silently spend API/Codex/Claude/model usage.
- Material behavior changes require mechanism evidence, tests/evals, version/rollback, and green CI.
- Use deterministic code for identity, state, schemas, fingerprints, permissions, idempotency, arithmetic, and release invariants.
- Use independent semantic workers only where model/human judgment is genuinely required.
- Persist runtime state, learning state, and project Canon in separate domains.
- Never commit credentials, local runtime/learning databases, private chats, or chain-of-thought.

## Documentation rules

The repository-wide human-facing documentation contract is `docs/DOCUMENTATION_STANDARD.en.md`; the visual source of truth is `assets/DESIGN_SYSTEM.en.md` plus `assets/brand/tokens.json`; the mandatory authoring self-check is `docs/DOCUMENTATION_QA.en.md`.

Mandatory summary:

- Documentation is a product surface, not source-tree decoration.
- Root landing pages must explain what Quillframe is, why it differs, how it works, why QA is credible, its tradeoffs, and how to start.
- Tier-A landing pages use coherent Story Loom presentation modules for core product concepts. Do **not** represent a primary architecture, production pipeline, QA stack, or competitor comparison with a raw `A → B → C` arrow list, generic placeholder Mermaid, low-information card stack, or oversized native Markdown table when a branded high-density visual is more appropriate.
- **A generated SVG is not approved by source generation alone.** New/materially changed Tier-A visuals must pass deterministic docs lint, be rendered and visually inspected at real GitHub-like widths, have copy reviewed independently of layout, and pass bilingual parity when paired. If the environment cannot inspect the render, keep the asset WIP and do not integrate it into a Tier-A page.
- Do not solve overflow by shrinking type until it fits. Reduce/restructure copy or repair layout.
- Run `python scripts/docs_quality.py` before completing customer-facing docs work. Normal CI runs the same deterministic checker and must not invoke model APIs.
- The homepage's primary comparison class is **direct novel-writing agents/frameworks**. General agent runtimes belong in implementation-influence/adoption docs; author SaaS/editor products are discussed separately when category differences matter.
- Comparisons describe verifiable mechanisms rather than star scores or marketing grades, and current competitor claims must be freshly verified before material updates.
- English and Simplified Chinese human-facing editions are parallel **native-quality** authoritative versions, not literal translations. Chinese prose and diagrams should use natural Chinese terminology except for exact identifiers/product names; English should read as native professional technical English.
- Customer-facing docs must state meaningful limitations and tradeoffs rather than presenting Quillframe as universally superior.
- Branded SVG/UI modules are the preferred Tier-A presentation layer; Mermaid remains the inspectable/diffable technical source/reference layer.
- Static visual assets must be original or clearly licensed/provenanced, accessible, and semantically backed by nearby text/reference docs.
- Story Loom targets roughly `70% professional technical / 30% anime-editorial warmth`; emoji may add editorial warmth but never replace structural/status semantics.
- A page is not done merely because it is visually clean: information density, hierarchy, native bilingual quality, accuracy, authority boundaries, links, accessibility, honest positioning, and render QA must all pass.

Human-facing authoritative docs are paired `.en.md` / `.zh-CN.md`. Stable router files may remain bilingual single-page entry points only when external tooling requires a fixed path.

Machine schemas remain single-source JSON/YAML/TOML-compatible contracts; their human explanations are bilingual.

## Project SDK principle

A novel project is a complete engineering artifact with manifest, lockfile, authority/state, plans, manuscripts, research, tests/evals, build bundle, migrations, and rollback history.

Do not hard-code the layout of one legacy project into the generic framework; support legacy structures through adapters/migrations.

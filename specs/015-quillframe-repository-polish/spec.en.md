# Specification · Quillframe Repository Polish

Status: Implementation candidate
Primary mode: `SYSTEM-IMPROVE`
Frozen starting `main`: `e49304bde7fb0c5ba0822deb3823f960c6425804`

## Problem / Context

The repository contains a strong Quillframe 0.9 framework and product surface, but the GitHub landing experience still reads like an internal engineering repository. The root README is only a language router, contributor/security/community entry points are missing, GitHub metadata is empty, and the Starlight landing still exposes current-facing NovelForge copy and a retired Studio domain.

## Current-state Audit

- Product identity: Quillframe; technical namespace: `quillframe`; version: `0.9.0`.
- Current runtime truth comes from `HARNESS_MANIFEST.yaml`, `SKILL*`, `harness/HARNESS_AGENT*`, implementation, tests, and the frozen `main` SHA.
- Canon, Context, Learning, independent review, and Settlement have explicit authority boundaries.
- SQLite is canonical durable product state in `persistence/quillframe_sqlite.py`.
- Current Studio is a SolidJS + TypeScript + Vite shell behind a typed Python Host Bridge/local server. Tauri 2 is the desktop-host direction, not a shipped wrapper on the frozen baseline.
- Model-runtime work is active in draft PR #108 and must not be presented as merged capability.
- UI/UX work is active on `ui/homepage-product-language-unification`; its owned implementation must not be overwritten.
- The repository license is proprietary source-available and explicitly not an OSI open-source license. Presentation must say this plainly unless a separate relicensing decision is made.

## User / Editorial Value

A first-time visitor should understand Quillframe in 30 seconds, understand its authority/runtime model within five minutes, reach a truthful setup path within ten minutes, and know how to contribute without opening internal contracts first.

## Requirements

1. Reconstruct `README.md` as a full GitHub landing page, with synchronized English and native Chinese editions.
2. Translate the Borderless Kawaii Editorial identity into GitHub-native composition: generous whitespace, restrained marks, real brand assets, small status labels, diagrams, and progressive disclosure.
3. Explain why long-form fiction needs explicit Canon, Context, state, independent semantic review, Learning governance, and Settlement rather than one prompt → model → text loop.
4. Explain product architecture without making the Model API the authority chain.
5. Separate implemented, active-development, and planned surfaces.
6. Provide commands that exist on the frozen baseline only.
7. Add concise contributor, security, conduct, issue, and PR entry points consistent with the repository license and authority model.
8. Repair current-facing NovelForge copy/dead domains in public documentation entry points without rewriting historical records or legal text.
9. Preserve other-session ownership; no Core, Agent Runtime, Model Runtime, SQLite schema, Studio behavior, or CSS changes.
10. Create a Draft PR only; do not merge.

## Non-goals

- Runtime or schema migration.
- Agent/Model Service implementation.
- Studio component/CSS redesign.
- Relicensing the repository.
- Global replacement of historical `NovelForge` strings.
- Pretending draft PR work or planned Tauri packaging is released.

## Authority / Canon Impact

None. Documentation and GitHub presentation cannot grant Canon, acceptance, Settlement, Learning promotion, or Framework write authority.

## Compatibility Constraints

- `Quillframe` is current product identity; `quillframe` is the active technical namespace.
- `0.9.x` remains pre-1.0 and may break before 1.0.
- Historical specifications and the current license preserve their original naming where provenance/legal meaning would change.
- Public URLs must match current deployment workflows and be independently rechecked when possible.

## Acceptance Scenarios

- A visitor can answer: what Quillframe is, what it owns, what the model owns, where project truth lives, how state persists, how to run current surfaces, and where to contribute.
- README does not claim Model Runtime capabilities from PR #108 as merged.
- README does not claim a shipped Tauri wrapper on the frozen baseline.
- README does not call the current license open source.
- Current Starlight navigation contains no active NovelForge branding or retired NovelForge Studio URL.
- CI/docs build and repository link checks pass or limitations are reported precisely.

## Risks

- Parallel UI/UX or Agent branches may merge after the initial freeze; perform late truth reconciliation before review.
- README screenshots can become stale while Studio is actively changing; prefer stable brand/architecture assets and defer volatile Studio screenshots.
- GitHub rendered light/dark visual QA cannot be declared passed without actual rendered evidence.

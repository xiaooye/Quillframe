# Specification · Quillframe Repository Polish

Status: implementation + verification candidate
Primary mode: `SYSTEM-IMPROVE`
Frozen starting `main`: `e49304bde7fb0c5ba0822deb3823f960c6425804`

## Problem / Context

Quillframe 0.9 already has a substantial framework, product site, Studio, and documentation corpus, but the repository itself must read like a coherent product rather than an internal source tree. The public surface must also be legible to both people and current AI discovery systems without inventing protocols or authority that Quillframe does not expose.

## Reconciled implementation truth

- Product identity: **Quillframe**; technical namespace: `quillframe`; version line: `0.9.x`.
- Agent/Model Runtime work from PR #108 is merged: ordinary model setup is `API Endpoint + Access Token`; Quillframe owns discovery, capability evidence, model selection, tools, sessions/checkpoints, authority, and the agent loop.
- Product-language / UI work from PR #109 and later consistency/layout fixes has merged and must be preserved rather than reimplemented here.
- SQLite remains canonical durable product state.
- SolidJS + TypeScript + Vite is the current web/Studio stack; Tauri 2 remains the thin desktop-host direction rather than a shipped wrapper.
- The repository remains proprietary source-available, not OSI open source. The legal product name is now Quillframe; license permissions/restrictions are unchanged.

## User / Editorial Value

A first-time visitor should understand the category and central distinction within seconds, reach a real setup path quickly, understand why long-form work needs explicit state/authority, and find deeper runtime/docs material without reading the entire framework.

## Requirements

1. Make `README.md` a complete product landing page with synchronized native English and Simplified Chinese editions.
2. Follow current high-performing GitHub README patterns: immediate category clarity, a memorable product statement, a near-top Quick Start, one clear mental model, progressive disclosure, explicit status/security/license, and no inventory-first wall of text.
3. Translate Borderless Kawaii Editorial into GitHub-native presentation: whitespace, restrained marks, real badges, stable brand assets, theme-aware diagrams, and no dashboard/card soup.
4. Explain Canon, bounded Context, Character/Relationship state, independent semantic review, Learning governance, SQLite persistence, and Settlement without making Model API/provider identity authoritative.
5. Describe the merged Model Runtime and Agent Runtime truthfully and register their paired docs in documentation governance/Starlight.
6. Make `python scripts/docs_quality.py` a standalone deterministic gate and execute it in normal CI without model/API spending.
7. Add/maintain contributor, security, conduct, issue, and PR entry points consistent with the current authority model and source-available license.
8. Add bounded AI-readable discovery surfaces (`robots.txt`, XML + Markdown sitemaps, `llms.txt`, fuller agent guidance, discovery catalog, Agent Skills index, content-use signals) without claiming unsupported MCP/A2A/OAuth/API services.
9. Rename the legal product identifier in `LICENSE` from NovelForge to Quillframe without changing the substantive license grant/restrictions.
10. Produce actual GitHub-rendered README light/dark/narrow QA evidence where the environment can safely execute it; never substitute a local Markdown mock while calling it GitHub-rendered.
11. Reconcile concurrent merged `main` changes before consequential writes and preserve their ownership.
12. Keep this work in Draft PR #110; do not merge from this session.

## Non-goals

- Runtime, Canon, Settlement, Learning, or SQLite behavior changes.
- Provider gateway or third-party agent-runtime authority.
- Relicensing to an OSI license.
- Global rewriting of historical product names where provenance matters.
- Fabricating repository metadata writes, public APIs, agent protocols, or visual QA evidence.

## Authority / Canon Impact

None. Repository presentation, discovery metadata, documentation registration, and QA tooling do not grant Canon, acceptance, Settlement, Project-write, Learning-promotion, or Framework-write authority.

## Compatibility Constraints

- Historical records remain historical; current-facing guidance uses Quillframe.
- Pre-1.0 consumers pin the exact Framework revision/bundle required by their project lock.
- Model tokens remain host secrets and must not enter prompts, Context, SQLite, receipts, fingerprints, or client bundles.
- Public AI discovery is metadata only; public crawlability does not expand license rights.

## Acceptance Scenarios

- README answers what Quillframe is, what it owns, what models own, where truth/state live, how to start, and what is still pre-1.0.
- English/Chinese README assets remain readable in GitHub light/dark themes and do not horizontally overflow at narrow width.
- Model/Agent Runtime docs are registered and reachable through Starlight navigation.
- `python scripts/docs_quality.py` runs in normal CI and blocks deterministic documentation defects.
- AI discovery files are internally consistent and explicitly deny unsupported authority/service claims.
- LICENSE says Quillframe while preserving the existing legal terms.
- Repository Description/Homepage/Topics are written only if an authorized connected action exists; otherwise exact desired values are reported as an external settings step.
- Final PR remains Draft and reconciled with current `main`.

## Risks

- Concurrent sessions may continue moving `main`; late reconciliation is mandatory.
- GitHub Actions security/event semantics may prevent a newly introduced visual-QA workflow from running before that workflow exists on the default branch; this must be reported as a tooling boundary rather than converted into a fake PASS.
- AI crawler/content-signal conventions are evolving; discovery files must remain narrow, descriptive, and subordinate to the license/security contracts.

<p align="center">
  <img src="assets/brand/quillframe-mark.svg" width="96" alt="Quillframe mark" />
</p>

<h1 align="center">Quillframe</h1>

<p align="center"><strong>Let the story grow. Keep the system aware of what it is doing.</strong></p>
<p align="center">An AI-native long-form fiction framework and authoring environment with explicit Canon, bounded Context, a Quillframe-owned agent runtime, and SQLite-native state.</p>

<p align="center">
  <a href="https://quillframe.wei-dev.com/">Website</a> ·
  <a href="https://studio.quillframe.wei-dev.com/">Studio</a> ·
  <a href="https://quillframe.wei-dev.com/docs/">Docs</a> ·
  <a href="#quick-start">Quick Start</a>
</p>

<p align="center">
  <a href="https://github.com/xiaooye/cn_webnovel_agent/actions/workflows/quillframe-ci.yml"><img alt="Quillframe 0.9 CI" src="https://github.com/xiaooye/cn_webnovel_agent/actions/workflows/quillframe-ci.yml/badge.svg?branch=main" /></a>
  <img alt="Version 0.9.0" src="https://img.shields.io/badge/version-0.9.0-796BC4" />
  <a href="LICENSE"><img alt="Quillframe source-available license" src="https://img.shields.io/badge/license-source--available-C985A4" /></a>
</p>

<p align="center"><sub>0.9.x · pre-1.0 · active development</sub></p>
<p align="center"><a href="README.zh-CN.md">简体中文</a> · <strong>English</strong></p>

---

> **Quillframe runs the agent. Your model endpoint supplies inference.** Bring an API endpoint and an access token; Quillframe keeps ownership of context, tools, sessions, checkpoints, quality gates, authority, and durable state.

## Quick Start

**Requirements:** Python 3.11+; Node.js 24 for the web surfaces; pnpm 10.33.0 for `studio/app`.

```bash
git clone https://github.com/xiaooye/cn_webnovel_agent.git
cd cn_webnovel_agent
python -m pip install -e .

python project_sdk.py self-test
python persistence/cli.py doctor
python studio/host_bridge.py self-test
```

Run the local Studio:

```bash
cd studio/app
corepack enable
pnpm install --frozen-lockfile
pnpm build
cd ../..
python studio/local_server.py
```

The basic authoring/inspection shell does not require a model endpoint. When inference is needed, ordinary model setup is deliberately small:

```text
API Endpoint
Access Token
```

The token may be empty for an unauthenticated local model server. Quillframe discovers models/protocols, records capability evidence, selects eligible models, and executes the model → tool → model loop itself. Provider identity is provenance, not runtime authority.

> Quillframe is pre-1.0. A consuming fiction project should pin the exact Framework revision/bundle required by its project lock instead of assuming that latest `main` is compatible.

## Why Quillframe exists

A one-shot writing assistant can be modeled as **prompt → model → text**. Long-form fiction cannot. After dozens or hundreds of scenes, the hard problems are state and authority:

- Which facts are Canon, and which are only plans, proposals, research, or review notes?
- What did this exact model invocation actually see?
- What does each character know, want, remember, and still carry from previous scenes?
- Does a review belong to this exact candidate, or to an earlier draft?
- If the author accepts a change, was it durably applied to the right project state?

Quillframe makes those questions explicit system contracts rather than reconstructing them from chat history.

**The practical result:** models remain flexible where judgment is useful; deterministic code owns identity, permissions, fingerprints, persistence, and write boundaries.

## The product model

<img src="docs/assets/architecture/framework-mental-model.en.svg" alt="Quillframe framework mental model: project authority, semantic execution and verification, then authorized Settlement" width="100%" />

Quillframe separates four kinds of truth that ordinary AI-writing loops tend to blur:

- **Story truth** — Story, Character, Relationship, Canon, timeline, plans, research, and current narrative state.
- **Context truth** — what is stored is larger than what is injected; a sparse Context Manifest bounds each operation.
- **Execution truth** — Session, Run, Checkpoint, tool receipt, candidate fingerprint, and semantic result provenance are explicit.
- **Authority truth** — generation, review, persistence, acceptance, and Settlement are different operations with different permissions.

A consuming Project owns its characters, plot, manuscript, research, plans, Accepted Canon, and current state. Quillframe owns the generic mechanisms. The dependency direction is **Project → Quillframe**.

## Model Runtime + Agent Runtime

Quillframe does not use Codex, Claude Code, OpenCode, or another provider-specific coding-agent product as its agent-runtime authority.

The Model Runtime turns an endpoint into bounded inference capability: endpoint/network policy → transient credential resolution → model/protocol discovery → capability evidence → eligibility → inference. Current wire codecs cover OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages; those are protocol families, not provider identities.

The Agent Runtime owns `AgentJob`, model selection, hard budgets, normalized tool calls, capability/authority checks, consequential-write checkpoints, receipts, post-conditions, and `AgentResult`. Side effects fail closed when the required durable execution boundary cannot be established.

Resolved access-token values are host secrets. They are not persisted into SQLite, prompts, Context, AgentJob/Result, checkpoints, receipts, or fingerprints.

Read more: [Model Runtime](docs/model-runtime.en.md) · [Agent Runtime](docs/agent-runtime.en.md) · [Integrations](docs/integrations.en.md)

## Production is a lifecycle, not a generation call

<img src="docs/assets/architecture/production-graph.en.svg" alt="Quillframe long-form fiction production lifecycle" width="100%" />

Current DRAFT / REVISE production is built around bounded Context, Story/Canon preflight, scene and character simulation, reader pressure, event-first drafting, surface realization, candidate qualification, independent semantic review when required, repair/challenger generation, reader engagement, continuity, and a user-visible gate.

**Raw Draft is internal. Review is not Accepted. Accepted is not Settled.**

That distinction is central to the system:

`stored ≠ injected` · `Plan ≠ Canon` · `Review ≠ Accepted` · `Accepted ≠ Settled` · `autosave ≠ Accepted` · `revision ≠ Canon` · `Corpus ≠ Canon` · `persistence ≠ authority`

When the author explicitly accepts a consequential change, **Settlement** is the authorized transaction that validates the exact before-state, applies the intended after-state, updates required projections, and checks post-conditions. A mismatch is `settlement_incomplete`, not a guessed success.

## Writer-first Studio

Quillframe Studio is a **SolidJS + TypeScript + Vite** authoring surface backed by typed Core/Host Bridge contracts. The product-language and visual unification work is now merged into `main`; the interface follows the same Borderless Kawaii Editorial language across the product site, docs, and Studio.

Writer-facing work stays primary. Runtime detail belongs in progressively disclosed inspection surfaces rather than turning the application into a framework dashboard. The UI cannot manufacture Canon, acceptance, Settlement, or direct SQLite authority that the Core has not granted.

A **Tauri 2 thin desktop host** remains the desktop architecture direction; a finished Tauri wrapper is not part of the current `0.9.0` checkout.

## SQLite-native durable state

Canonical product state is SQLite-native:

```text
~/.quillframe/
├─ quillframe.sqlite
├─ projects/<project-id>/project.sqlite
├─ projects/<project-id>/blobs/
└─ backups/
```

The Core enables foreign keys, WAL, a busy timeout, explicit durability policy, ordered/checksummed migrations, backup/restore, integrity checks, and `quillframe doctor`-style diagnostics. Markdown, DOCX, EPUB, and other document formats are import/export artifacts—not a second live authority.

The UI boundary is intentionally one-way: **Solid/Tauri → typed Bridge/API → Python Core → SQLite**.

## Learning without silent promotion

Meaningful user feedback can enter learning intake automatically:

`capture → interpret → scope → evidence → candidate → validation`

Automatic capture is not automatic promotion. `one_off`, `project`, `user_taste`, and `general_craft` remain separate scopes; inferred preference does not silently become Canon, permanent user taste, Project policy, or Framework behavior.

## AI-readable by design

The public site now exposes small, explicit discovery surfaces for AI clients without pretending that the website itself is an authority-bearing agent server:

- [`llms.txt`](site/public/llms.txt) — concise product/context guide.
- [`llms-full.txt`](site/public/llms-full.txt) — fuller machine-oriented architecture and authority guide.
- [`ai-catalog.json`](site/public/.well-known/ai-catalog.json) — machine-readable public-surface catalog.
- [`agent-skills/index.json`](site/public/.well-known/agent-skills/index.json) — discoverability for the real portable Quillframe Agent Skill.
- [`agent-skills/quillframe/SKILL.md`](agent-skills/quillframe/SKILL.md) — read-only Host Bridge skill for external agent packages.

These files grant **no** Canon, Project-write, Framework-write, Settlement, MCP, A2A, OAuth, or hosted-model-gateway authority. Public discovery is metadata; capability and authority remain explicit contracts.

## Documentation

Start with the path closest to your task:

- [Why Quillframe](docs/why-quillframe.en.md) — product fit, tradeoffs, and alternatives.
- [Architecture](docs/architecture.en.md) — system ownership and authority boundaries.
- [Production Pipeline](docs/production-pipeline.en.md) — DRAFT / REVISE lifecycle.
- [Quality Assurance](docs/quality-assurance.en.md) — exact-fingerprint gates and independent review.
- [Context & Memory](docs/context-and-memory.en.md) — sparse Context, visibility, persistence, and memory boundaries.
- [Model Runtime](docs/model-runtime.en.md) / [Agent Runtime](docs/agent-runtime.en.md) — provider-neutral inference and Quillframe-owned agent execution.
- [Project SDK](docs/project-sdk.en.md) — reproducible fiction-project integration.
- [Studio](studio/README.en.md) — authoring surface and Host Bridge behavior.
- [Architecture Atlas](docs/architecture-atlas.en.md) — subsystem ownership and deep contract links.

The published documentation is built with **Astro + Starlight**. Documentation governance is executable through `docs/documentation_manifest.json` and `python scripts/docs_quality.py`.

## Repository map

```text
quillframe/       public Python façade
model_runtime/    endpoint, discovery, capability evidence, inference transport
agent_runtime/    AgentJob, tools, budgets, checkpoints, receipts, agent loop
core/             Story / Character / Canon contracts
harness/          sessions, semantic execution, control plane, Settlement
quality/          readiness, findings, repair, candidate evolution
learning/         feedback evidence and governed promotion
corpus/           governed craft/research evidence
persistence/      canonical SQLite durable state
publication/      Accepted-text publication IR/compiler
studio/           Host Bridge, local server, SolidJS Studio
site/             product site + Astro/Starlight docs
```

## Current status · 0.9.x

Quillframe is **pre-1.0 and actively developed**. Current `main` includes the embeddable Python façade, Model Runtime, Agent Runtime, fiction Core/authority contracts, SQLite persistence, typed Host Bridge, SolidJS Studio, product site, and Starlight docs. Normal CI is deterministic and does not silently call a configured paid/live Model API.

Still intentionally incomplete: pre-1.0 compatibility is not frozen, the authoring UX continues to evolve, and the Tauri 2 desktop wrapper is not yet shipped.

## Development and contribution

```bash
python scripts/docs_quality.py
python -m unittest discover -s tests -p 'test_quillframe_*.py' -v

cd site && npm install --no-audit --no-fund && npm run quality && npm run build && npm run docs:build
cd ../studio/app && corepack enable && pnpm install --frozen-lockfile && pnpm typecheck && pnpm build
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [Roadmap](ROADMAP.md), [Security](SECURITY.md), [Code of Conduct](CODE_OF_CONDUCT.md), and [Changelog](CHANGELOG.en.md).

## Security

Never paste model access tokens, private manuscript text, or project databases into public issues. Hosted secrets belong server-side; resolved tokens must not enter browser bundles, prompts, Context, SQLite, receipts, or fingerprints. See [SECURITY.md](SECURITY.md).

## License

Quillframe is distributed under the **Quillframe Proprietary Source-Available License**. This repository is public and source-available, but the license is **not** an OSI open-source license and restricts redistribution, deployment, and commercial use unless separate written permission is granted.

Read the exact terms in [LICENSE](LICENSE).

---

<p align="center"><sub>✦ Creative judgment stays flexible. Execution truth stays explicit. ♡</sub></p>

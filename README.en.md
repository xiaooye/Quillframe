<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/quillframe-mark-dark.svg" />
    <img src="assets/brand/quillframe-mark.svg" width="104" alt="Quillframe mark" />
  </picture>
</p>

<h1 align="center">Quillframe</h1>

<p align="center"><strong>AI-native long-form fiction framework and authoring environment.</strong></p>
<p align="center">Let the story grow without losing track of what is true, what the model saw, what changed, or who is allowed to make it real.</p>

<p align="center">
  <a href="https://quillframe.wei-dev.com/">Website</a> ·
  <a href="https://studio.quillframe.wei-dev.com/">Studio</a> ·
  <a href="https://quillframe.wei-dev.com/docs/">Docs</a> ·
  <a href="docs/why-quillframe.en.md">Why Quillframe</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/xiaooye/Quillframe/actions/workflows/quillframe-ci.yml"><img alt="Quillframe CI" src="https://github.com/xiaooye/Quillframe/actions/workflows/quillframe-ci.yml/badge.svg?branch=main" /></a>
  <img alt="Version 1.0.0-dev.0" src="https://img.shields.io/badge/version-1.0.0--dev.0-796BC4" />
  <a href="SECURITY.md"><img alt="Tokens stay host-local" src="https://img.shields.io/badge/security-tokens%20stay%20host--local-4D9B7D" /></a>
  <a href="LICENSE"><img alt="Quillframe source-available license" src="https://img.shields.io/badge/license-source--available-C985A4" /></a>
</p>

<p align="center"><sub>1.0.0-dev.0 · acceptance in progress · active development</sub></p>

<img src="assets/brand/story-thread.svg" width="100%" alt="Quillframe story thread divider" />

> [!IMPORTANT]
> **The host runs the agent. Quillframe governs the novel.** Codex, Claude Code, Cursor, or another declared host owns the generic session, model → tool → model loop, sandbox, and subagent lifecycle. Quillframe owns the novel contract: Project resolution, Story / Character / Relationship / Canon boundaries, bounded Context, candidate lifecycle, quality gates, independent review, visibility, and Acceptance / Settlement. The embedded runtime remains an optional/reference implementation for Studio, local adapters, and deterministic tests.
>
> **Tokens stay host-local.** Resolved access-token values are transient host secrets. Quillframe never writes them to repository files, SQLite, prompts, Context, AgentJob / AgentResult, checkpoints, receipts, fingerprints, logs, or client bundles; the host uses a credential only transiently when authenticating to the model endpoint you configured.

## Quick Start

**Requirements:** Python 3.11+. Node.js 24 and pnpm 10.33.0 are only needed for the web/Studio surfaces.

Install the Framework from a clean source checkout and verify the local runtime:

```bash
git clone https://github.com/xiaooye/Quillframe.git
cd Quillframe
python -m pip install -e .
quillframe doctor
```

Create a fiction Project **outside** the generic Framework repository and open the local-first Studio with the one native command:

```bash
quillframe launch ../my-novel \
  --new \
  --id MY-NOVEL \
  --title "My Novel" \
  --language en
```

The command creates the exact native four-key manifest (`schema`, `id`, `title`, `language`) for a complete novel, exposes top-level `scope: "novel"` in Project context, and seeds `CH001` with manuscript `DOC-CH001` as the initial chapter. Runtime state stays under `.quillframe/data`, and Studio binds to loopback only. Reopen an existing Project with `quillframe launch ../my-novel`; opening does not migrate, repair or reseed old development state. If you also use Claude Code or another coding agent, start that host from the Project directory; no repository hook or host-specific configuration is part of Quillframe correctness. The host runs the agent, while Quillframe retains novel and Canon authority.

The authoring/inspection shell can work without a model connection. When inference is needed, ordinary setup is deliberately small:

```text
API Endpoint
Access Token
```

The token may be empty for an unauthenticated local model server. Provider/vendor identity is diagnostic provenance only; it does not become runtime authority.

<details>
<summary><strong>Run the Studio locally</strong></summary>

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @quillframe/studio-app build
quillframe launch ../my-novel
```

</details>

## Why Quillframe

A one-shot writing assistant can be approximated as **prompt → model → text**. A long novel cannot. After dozens or hundreds of scenes, the difficult part becomes preserving story truth, character continuity, bounded context, review provenance, durable state, and explicit write authority.

| Long-story failure mode | Quillframe mechanism |
| --- | --- |
| Facts, plans, and drafts blur together | **Canon + Settlement** keep story truth and authorized state changes distinct |
| Prompts become giant memory dumps | **Context** is sparse and task-bounded: stored ≠ injected |
| Characters flatten or forget their own agendas | **Story + Character + Relationship** maintain causal state and knowledge boundaries |
| A manager “reviews itself” and calls that independent | **Quality** binds real independent semantic judgment to the exact candidate fingerprint |
| Agent state lives only in chat history | **Runtime + SQLite** make Session, Run, Checkpoint, receipts, and durable state explicit |
| One piece of feedback silently becomes a permanent rule | **Learning** captures evidence without automatic promotion |

Quillframe's generic system spans **Story · Character · Relationship · Canon · Context · Runtime · Quality · Learning · Settlement**. A consuming fiction Project owns its characters, plot, manuscript, research, plans, Accepted Canon, and current story state. The dependency direction is **Project → Quillframe**.

## How it fits together

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/architecture/framework-mental-model.en.dark.svg" />
  <img src="docs/assets/architecture/framework-mental-model.en.svg" alt="Quillframe framework mental model" width="100%" />
</picture>

The boundary is intentional:

- **Models own semantic fiction judgment.** They can reason about story, character, reader experience, relevance, and repair.
- **Quillframe owns execution truth.** Deterministic code owns identity, permissions, fingerprints, routing, budgets, transactions, persistence, and reproducibility.
- **Independent means independent.** A required independent semantic judgment must come from a genuinely separate invocation/session/worker and be bound to the exact artifact fingerprint; manager self-roleplay does not qualify.
- **SQLite is canonical durable state, not a fallback cache.** The UI boundary is `Solid/Tauri → typed Bridge/API → Python Core → SQLite`.

The current Model Runtime is provider-neutral at the authority layer. Hosts provide generic model and tool execution; Quillframe validates the novel contract, capability evidence, eligibility, checkpoints, receipts, and exact artifact bindings at its boundary. Model APIs are inference capability—not story or settlement authority.

Read the deeper contracts: [Architecture](docs/architecture.en.md) · [Model Runtime](docs/model-runtime.en.md) · [Agent Runtime](docs/agent-runtime.en.md) · [Context & Memory](docs/context-and-memory.en.md)

## Production is a lifecycle, not a generation call

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/architecture/production-graph.en.dark.svg" />
  <img src="docs/assets/architecture/production-graph.en.svg" alt="Quillframe long-form fiction production lifecycle" width="100%" />
</picture>

DRAFT / REVISE runs through bounded Context, Story/Canon preflight, private character enactment and scene resolution, a Scene Realization Contract with model-composed Writer context, Reader Pressure, one direct Surface Writer, candidate fingerprint freeze, Reader Engagement, Continuity, objective-bound qualification, repair/comparison when needed, independent review, and a user-visible gate.

**The direct candidate remains internal until release. Review is not Accepted. Accepted is not Settled.**

`stored ≠ injected` · `Plan ≠ Canon` · `Review ≠ Accepted` · `Accepted ≠ Settled` · `autosave ≠ Accepted` · `revision ≠ Canon` · `Corpus ≠ Canon` · `persistence ≠ authority`

Settlement is the explicit transaction that turns an authorized accepted change into durable Project state. A before-state mismatch or failed post-condition is `settlement_incomplete`, never a guessed success.

## Writer-first Studio

Quillframe Studio is an authoring environment first—not a framework dashboard first. Writer-facing work stays primary; runtime and control-plane detail are progressively disclosed for inspection when needed.

**Current stack:**

- Frontend / Studio — **SolidJS + TypeScript + Vite**
- Core — **Python**
- Persistence — **SQLite-native** with WAL, foreign keys, native schema fragments, backup/restore, and integrity checks
- Documentation — **Astro + Starlight**
- Desktop — **Tauri 2 thin host** over Host Bridge v11; packaged OS/runtime acceptance remains explicit

Explore the live [Studio](https://studio.quillframe.wei-dev.com/) or read the [Studio architecture](studio/README.en.md).

## Explore

| Goal | Start here |
| --- | --- |
| Understand the product | [Why Quillframe](docs/why-quillframe.en.md) |
| Understand ownership and authority | [Architecture](docs/architecture.en.md) |
| Follow DRAFT / REVISE execution | [Production Pipeline](docs/production-pipeline.en.md) |
| Understand fingerprint-bound review | [Quality Assurance](docs/quality-assurance.en.md) |
| Connect inference endpoints | [Model Runtime](docs/model-runtime.en.md) |
| Build with the agent loop and tools | [Agent Runtime](docs/agent-runtime.en.md) · [Integrations](docs/integrations.en.md) |
| Integrate a fiction Project | [Native Project Contract](docs/project-contract.en.md) |
| Inspect system ownership | [Architecture Atlas](docs/architecture-atlas.en.md) |
| Read machine-oriented product context | [`llms.txt`](site/public/llms.txt) · [`llms-full.txt`](site/public/llms-full.txt) |

## Development

<details>
<summary><strong>Verification commands</strong></summary>

```bash
python scripts/docs_quality.py
python -m unittest discover -s tests -p 'test_quillframe_*.py' -v
corepack pnpm install --frozen-lockfile
corepack pnpm run quality
corepack pnpm run typecheck
corepack pnpm run test
corepack pnpm run build
```

</details>

See [CONTRIBUTING.md](CONTRIBUTING.md), [Roadmap](ROADMAP.md), [Security](SECURITY.md), [Code of Conduct](CODE_OF_CONDUCT.md), and [Changelog](CHANGELOG.en.md).

## Status

Quillframe is on the **1.0 prerelease line and actively developed**. Current `main` includes the embeddable Python façade, Model Runtime, Agent Runtime, fiction Core/authority contracts, SQLite persistence, typed Host Bridge, SolidJS Studio, product site, publication pipeline, and Starlight documentation. Normal CI is deterministic and does not silently call a configured paid/live Model API.

A fiction Project identifies itself only through the native four-key `quillframe.toml`, context with top-level `scope: "novel"`, manifest fingerprint, and `.quillframe/data` boundary. `CH001` is the initial chapter; later chapters use the same contract with real chapter relationships. Framework commit/bundle provenance is recorded independently by the host or release process; it is not Project authority or a consumer lock. This development contract does not certify a full-novel live-model run or cloud release readiness.

## Security & license

Resolved access-token values are transient host secrets. Quillframe never writes them to repository files, SQLite, prompts, Context, AgentJob / AgentResult, checkpoints, receipts, fingerprints, logs, or client bundles. Never paste model access tokens, private manuscript text, or project databases into public issues. See [SECURITY.md](SECURITY.md).

Quillframe is distributed under the **Quillframe Proprietary Source-Available License**. The repository is public and source-available, but the license is **not** an OSI open-source license and restricts redistribution, deployment, and commercial use unless separate written permission is granted. Read the exact terms in [LICENSE](LICENSE).

---

<p align="center"><sub>✦ Creative judgment stays flexible. Execution truth stays explicit. ♡</sub></p>

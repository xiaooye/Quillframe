<p align="center">
  <img src="assets/brand/quillframe-mark.svg" width="104" alt="Quillframe mark" />
</p>

<h1 align="center">Quillframe</h1>

<p align="center"><strong>AI-native long-form fiction framework and authoring environment.</strong></p>

<p align="center">Stories can grow long. Canon, context, character state, and execution truth should still know exactly where they stand.</p>

<p align="center">
  <a href="https://quillframe.wei-dev.com/">Website</a> ·
  <a href="https://studio.quillframe.wei-dev.com/">Studio</a> ·
  <a href="https://quillframe.wei-dev.com/docs/">Documentation</a> ·
  <a href="#quick-start">Quick Start</a>
</p>

<p align="center">
  <a href="https://github.com/xiaooye/cn_webnovel_agent/actions/workflows/quillframe-ci.yml"><img alt="Quillframe 0.9 CI" src="https://github.com/xiaooye/cn_webnovel_agent/actions/workflows/quillframe-ci.yml/badge.svg?branch=main" /></a>
  <img alt="Version 0.9.0" src="https://img.shields.io/badge/version-0.9.0-796BC4" />
  <a href="LICENSE"><img alt="Source-available license" src="https://img.shields.io/badge/license-source--available-C985A4" /></a>
</p>

<p align="center"><sub>0.9.x · pre-1.0 · active development</sub></p>
<p align="center"><a href="README.zh-CN.md">简体中文</a> · <strong>English</strong></p>

---

> **✦ Quillframe is not an LLM chat wrapper.** Models provide semantic judgment and generation. Quillframe owns the system around them: story structure, character and relationship state, Canon, bounded Context, runtime identity, quality gates, learning evidence, persistence, and authorized Settlement.

## Why Quillframe exists

A one-shot writing loop is simple: **prompt → model → text**. A novel that survives hundreds of scenes needs more. It must know which facts are authoritative, which plans are only future intent, which evidence actually entered a model call, whether a review belongs to this exact candidate, and whether an accepted change has been durably applied.

Quillframe turns those questions into explicit system boundaries instead of reconstructing them from chat history.

**Long-form production, conceptually:** bounded Context → Story/Canon preflight → scene and character simulation → generation/revision → independent semantic review when required → reader/continuity validation → user-visible Review candidate → explicit acceptance → Settlement into durable project state.

The framework is deliberately heavier than a one-shot assistant—and useful for exactly the projects where continuity, provenance, recovery, and long-horizon quality matter.

## The principles that matter

| | Principle | What it means in practice |
|---|---|---|
| ✦ | **Canon-aware** | Plan, Draft, Review, Accepted text, Canon, and Settled state are distinct lifecycle/authority states. |
| ✧ | **Context-bounded** | Stored information is larger than any invocation. A sparse Context Manifest selects task-relevant evidence; stored ≠ injected. |
| ♡ | **Character integrity** | Agenda, knowledge boundaries, relationships, location, and emotional consequences are production state—not decorative prompt flavor. |
| ⋆ | **Independent semantic judgment** | Required review is bound to an exact artifact fingerprint and a genuinely separate eligible execution. |
| ✦ | **Writer-first** | Studio is an authoring environment first; runtime inspection is progressively disclosed rather than becoming the default creative IA. |
| ✧ | **SQLite-native** | Durable product state lives in SQLite. Markdown, DOCX, EPUB, and other files are import/export artifacts, not a second live authority. |
| ♡ | **Inference is capability, not authority** | Models interpret and generate; Quillframe owns orchestration, tools, state, permissions, provenance, and project authority boundaries. |
| ⋆ | **Learning without silent promotion** | Feedback can be captured as evidence without silently becoming Canon, Project preference, user taste, or Framework policy. |

## How Quillframe is put together

### Product mental model

```text
Writer
  ↓
Quillframe
  ├─ authoring workflow
  ├─ Story / Character / Relationship / Canon / Context
  ├─ Agent Runtime / Quality / Learning / Settlement
  └─ durable project state
  ↕
Model API
```

The Model API is not above Quillframe in the authority chain. It supplies inference to a Quillframe-owned operation.

### Model connection: two user inputs

The current Model Runtime exposes exactly two ordinary setup inputs:

```text
API Endpoint
Access Token
```

`Access Token` may be empty for an unauthenticated local endpoint. Quillframe owns protocol discovery, model discovery, capability evidence, model selection, tool execution, Session/Run/Checkpoint identity, and the model → tool → model loop. Provider/vendor identity is diagnostic provenance at most, not runtime authority or an onboarding field.

Resolved token values are never persisted into SQLite, prompts, Context, AgentJob/Result, checkpoints, receipts, or fingerprints. Durable Model Service state keeps a credential reference; the host resolves the actual secret just in time.

<details>
<summary><strong>Wire protocol details</strong></summary>

Current codecs cover OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages. These are wire protocol families, not provider identities. Model listing proves discovery only; tools, vision, structured output, context limits, and similar capabilities require separate evidence.

Normal CI never calls a configured live/paid Model API. Live compatibility probing is explicit opt-in and produces timestamped endpoint/model-bound evidence rather than permanent capability truth.

See [Model Runtime](docs/model-runtime.en.md) and [Agent Runtime](docs/agent-runtime.en.md).

</details>

### Framework, Studio, and durable state

```text
SolidJS Studio / host surface
          ↓
   typed Bridge / API
          ↓
   Python Quillframe Core
          ↓
        SQLite
```

A thin Tauri 2 host is the current desktop architecture direction. The checked-in `0.9.0` Studio currently ships its SolidJS Local Web/cloud UI and typed Python Host Bridge rather than a finished Tauri wrapper.

<img src="docs/assets/architecture/framework-mental-model.en.svg" alt="Quillframe orchestration, execution and verification, and Settlement architecture" width="100%" />

The generic Framework owns mechanisms. A consuming Project owns its concrete story facts, characters, relationships, research, plans, manuscripts, Accepted Canon, and current state. Dependency direction is **Project → Quillframe**; private story facts do not become generic Framework truth.

### Production is a lifecycle, not a generation call

<img src="docs/assets/architecture/production-graph.en.svg" alt="Quillframe long-form fiction production graph" width="100%" />

Current DRAFT / REVISE execution includes bounded Context and authority bootstrap, Story/Canon preflight, character/scene simulation, reader pressure, event-first drafting, surface realization, qualification, independent review when required, repair/challenger generation, reader engagement, continuity, and a user-visible gate.

**Raw Draft is internal. Review is not Accepted. Accepted is not Settled.**

## Canon, Context, and Settlement

Quillframe keeps the following distinctions explicit:

```text
stored      ≠ injected
Plan        ≠ Canon
Review      ≠ Accepted
Accepted    ≠ Settled
autosave    ≠ Accepted
revision    ≠ Canon
Research    ≠ Character Knowledge
Corpus      ≠ Canon
session     ≠ Canon
persistence ≠ authority
```

Current Canon precedence is `locked > accepted > active_plan > review > proposal`. This is an authority/lifecycle distinction—not an automatic promotion ladder.

**Settlement** is the authorized transaction that turns explicit acceptance into durable state mutation. It requires exact before → after intent, current before-state validation, write authorization, dependency/projection handling, and post-condition checks. A mismatch yields `settlement_incomplete`; Quillframe does not guess that a partial write probably succeeded.

<details>
<summary><strong>Why sparse Context matters</strong></summary>

A persistent project can contain far more information than a model call should see. Quillframe first decides what evidence is relevant to the current semantic question, then deterministic assembly validates exact references, authority class, visibility/stage constraints, provenance, fingerprints, and hard budget.

This keeps separate what the project stores, what semantic selection considers useful, and what actually entered the model context. See [Context & Memory](docs/context-and-memory.en.md).

</details>

## Learning: automatic intake, governed promotion

Meaningful user feedback can enter learning intake without requiring the user to explicitly trigger a learning task:

`capture → interpret → scope → evidence → candidate → validation`

Automatic capture does **not** imply automatic promotion. `one_off`, `project`, `user_taste`, and `general_craft` remain separate scopes, and none gains durable authority merely because a model inferred a preference.

## Studio · authoring environment first

Quillframe Studio is the product-experience layer around the Core. In `0.9.0` it is a real SolidJS + TypeScript + Vite application shell behind a typed read-only Host Bridge, with local and cloud-hosted web surfaces.

The Writer Mode direction centers Desk, Manuscript, Plan, Story, Review, Research & Corpus, Learning, and Publish, with runtime detail progressively disclosed through an Inspector. A parallel UI/UX branch is actively evolving that authoring surface; **unmerged branch behavior and future screenshots are not released product behavior.**

Current Studio Bridge operations include bridge description, Framework doctor, project inspection, capability inspection, Context inspection, and semantic catalog inspection. The UI does not fabricate mutation, acceptance, Settlement, or direct private SQLite contracts that the Core has not exposed.

## SQLite is the canonical durable state

```text
~/.quillframe/
├─ quillframe.sqlite
├─ projects/
│  └─ <project-id>/
│     ├─ project.sqlite
│     ├─ blobs/
│     └─ exports/
├─ backups/
└─ cache/
```

Connections enable foreign keys, a busy timeout, WAL journal mode, and `synchronous=FULL`. Migrations are ordered and checksum-verified. The persistence CLI exposes `doctor`, backup/verify/restore, project creation, and search.

Persistence never grants Canon, acceptance, Settlement, or Learning-promotion authority by itself.

## Quick Start

### Prerequisites

- **Python >= 3.11**; current CI validates on Python 3.13.
- **Node.js 24** for the product site/docs and Studio builds.
- **pnpm 10.33.0** for `studio/app`.

Quillframe is pre-1.0; consuming Projects should pin the exact Framework revision/bundle required by their project lock rather than assuming latest `main` is compatible.

### Clone, install, and verify the library/Core

```bash
git clone https://github.com/xiaooye/cn_webnovel_agent.git
cd cn_webnovel_agent
python -m pip install -e .
python -c "from quillframe import Quillframe, AgentJob; print(Quillframe.__name__, AgentJob.__name__)"
python project_sdk.py self-test
python studio/host_bridge.py self-test
python persistence/cli.py doctor
```

Successful self-tests print structured output. `doctor` initializes/checks the default data root; persistence never turns manuscript content into Canon by itself.

### Run the current local Studio

```bash
cd studio/app
corepack enable
pnpm install --frozen-lockfile
pnpm build
cd ../..
python studio/local_server.py
```

The local server binds loopback and prints the URL to open. The current Studio consumes the typed read-only Host Bridge. **An AI endpoint is not required for basic inspection/authoring shell startup.**

### Create a fiction Project skeleton

```bash
python project_sdk.py init ./my-novel \
  --id PROJECT-MY-NOVEL \
  --title "My Novel" \
  --language en

python project_sdk.py validate ./my-novel
python project_sdk.py build ./my-novel
```

The Project SDK scaffolds separate plans, state, manuscripts, research, Corpus references, tests, and project locks. It does not automatically promote content into Canon.

<details>
<summary><strong>Run the product site and Starlight docs</strong></summary>

```bash
cd site
npm install --no-audit --no-fund
npm run dev
npm run dev:docs
```

Production verification uses `npm run quality`, `npm run build`, and `npm run docs:build`.

</details>

## Repository map

```text
cn_webnovel_agent/
├─ quillframe/            # embeddable public Python façade
├─ agent_runtime/         # Quillframe-owned AgentJob / Tool / Agent loop
├─ model_runtime/         # endpoint, discovery, capability evidence, inference transport
├─ core/                  # Story / Character / Canon contracts
├─ harness/               # sessions, semantic execution, control plane
├─ quality/               # production readiness and quality evolution
├─ learning/              # evidence intake, hypotheses, governed promotion
├─ corpus/                # governed craft/research evidence
├─ persistence/           # canonical SQLite durable state
├─ publication/           # Accepted-text publication IR/compiler
├─ studio/                # Host Bridge, local server, SolidJS Studio app
├─ site/                  # product site + Astro/Starlight docs build
├─ docs/                  # public concepts, guides, architecture
├─ tests/                 # deterministic contract/regression tests
├─ specs/                 # current and historical engineering specifications
└─ .github/               # CI, deployment, issue/PR contribution surfaces
```

Historical records deliberately preserve their original terminology where provenance matters; current product guidance uses Quillframe / `quillframe`.

## Documentation map

| Start with… | When you need… |
|---|---|
| [Documentation home](docs/README.en.md) | a curated path through the documentation set |
| [Why Quillframe](docs/why-quillframe.en.md) | product fit, tradeoffs, and the system boundary |
| [Architecture](docs/architecture.en.md) | Framework/Project authority, semantic vs deterministic ownership, Settlement |
| [Model Runtime](docs/model-runtime.en.md) | Endpoint + token setup, discovery, capability evidence, secret/network policy |
| [Agent Runtime](docs/agent-runtime.en.md) | AgentJob, tool loop, checkpoints, receipts, embeddable library |
| [Production Pipeline](docs/production-pipeline.en.md) | DRAFT/REVISE lifecycle and user-visible readiness |
| [Context & Memory](docs/context-and-memory.en.md) | sparse Context, visibility, persistence, memory boundaries |
| [Quality Assurance](docs/quality-assurance.en.md) | fingerprint-bound gates, diagnostics, independent review |
| [Adaptive Learning](docs/adaptive-learning.en.md) | feedback intake, evidence, scopes, promotion rules |
| [Project SDK](docs/project-sdk.en.md) | integrating a novel as a reproducible Project |
| [Studio](studio/README.en.md) | current product shell and Host Bridge behavior |
| [Architecture Atlas](docs/architecture-atlas.en.md) | implementation owners and deep contract links |

Public docs are built with **Astro + Starlight** and deployed under the Quillframe product site.

## Current status · 0.9.x

Quillframe is **pre-1.0 and in active development**. Breaking changes may occur before 1.0.

| Area | Current `main` status |
|---|---|
| Embeddable `quillframe` Python library | Implemented; wheel/import validated in CI |
| Quillframe-owned Model Runtime | Implemented; endpoint + token setup, discovery, capability evidence, inference transport |
| Quillframe-owned Agent Runtime | Implemented; typed jobs/results, tool runtime, checkpoint/receipt boundaries |
| Python fiction Core / authority contracts | Implemented and CI-tested |
| SQLite-native persistence | Implemented and CI-tested |
| Typed read-only Host Bridge | Implemented and self-tested |
| SolidJS Studio | Implemented application shell; authoring UX still evolving |
| Product site + Starlight docs | Implemented and deployment-managed |
| Tauri 2 thin desktop host | Architecture direction; finished wrapper is not present in current `main` |
| Writer Mode UX reconstruction | **Active parallel UI/UX work; unmerged work is not released** |

Normal CI deliberately uses deterministic/mock Model Runtime execution; live endpoint compatibility is opt-in evidence rather than a release claim.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Small fixes are welcome, but changes to Canon/Settlement semantics, semantic independence, Learning promotion, persistence authority, Model/Agent Runtime contracts, or other authority surfaces require explicit architecture reasoning and matching tests.

Useful entry points: [Issues](https://github.com/xiaooye/cn_webnovel_agent/issues/new/choose) · [Security](SECURITY.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.en.md)

## Security

Never paste API access tokens, provider credentials, private manuscript text, or sensitive project databases into public issues. Resolved Model API tokens are host secrets and must not enter prompts, receipts, SQLite, or Vite client bundles. Hosted secrets belong server-side. See [SECURITY.md](SECURITY.md).

## License

**This public repository is currently source-available, not OSI open source.** The [LICENSE](LICENSE) permits limited private non-commercial evaluation/research and restricts redistribution, deployment, and commercial use unless separate written permission is granted.

The legal file preserves historical product naming. This repository-presentation work intentionally does not rewrite legal text; any legal identity or relicensing change requires a separate explicit decision.

---

<p align="center"><sub>✦ · Quillframe keeps creative judgment flexible and execution truth explicit. · ♡</sub></p>

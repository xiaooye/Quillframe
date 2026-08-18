# Contributing to Quillframe

Thank you for helping improve Quillframe. This repository is a pre-1.0 fiction framework, agent runtime, and authoring product, so the fastest useful contribution is usually a **small, clearly owned change with evidence that it preserves the surrounding contracts**.

> **License note.** This repository is public and source-available, but its current `LICENSE` is not an OSI open-source license. By intentionally submitting a contribution, you agree to the contribution terms in Section 8 of that license. Please read it before opening a pull request.

## Before you start

Current development prerequisites:

- Python **>= 3.11**; CI currently validates on Python 3.13.
- Node.js **24** for the product site, documentation, and Studio builds.
- `pnpm` **10.33.0** for `studio/app`.

Clone and install the Python package in editable mode:

```bash
git clone https://github.com/xiaooye/cn_webnovel_agent.git
cd cn_webnovel_agent
python -m pip install -e .
```

For a first sanity check:

```bash
python -c "from quillframe import Quillframe, AgentJob; print(Quillframe.__name__, AgentJob.__name__)"
python project_sdk.py self-test
python studio/host_bridge.py self-test
python persistence/cli.py doctor
```

## Repository orientation

| Area | Owns |
|---|---|
| `quillframe/` | public embeddable Python façade |
| `model_runtime/` | Model API endpoint, discovery, capability evidence, inference transport |
| `agent_runtime/` | AgentJob/Result, tools, budgets, Quillframe-owned agent loop |
| `core/` | Story, Character, relationship, and Canon mechanisms/contracts |
| `harness/` | sessions, runs, checkpoints, semantic execution, control plane |
| `quality/` | production readiness and quality evolution |
| `learning/` | feedback evidence, hypotheses, validation, governed promotion |
| `persistence/` | canonical SQLite durable product state |
| `publication/` | Accepted-text publication IR/compiler |
| `studio/` | Host Bridge, local server, SolidJS authoring surface |
| `site/` | product site and Astro/Starlight documentation build |
| `docs/` | public product/architecture documentation |
| `tests/` | deterministic contract and regression tests |
| `specs/` | current and historical engineering decisions |

The generic Framework owns mechanisms; a consuming fiction Project owns its concrete characters, story facts, plans, manuscripts, research, Accepted Canon, and current state. Do not move project-specific story truth into the generic framework.

## Choose the smallest correct change

Small documentation fixes and isolated defects can usually go straight to a focused PR. Structural changes should follow:

```text
spec → plan → tasks → implementation → verification → acceptance
```

A structural change includes anything that materially changes public architecture, runtime contracts, persistence semantics, authority transitions, or the product information architecture.

Keep one primary purpose per PR. Do not combine an unrelated refactor, dependency refresh, UI redesign, and runtime change just because they touch nearby files.

## Authority-sensitive changes

Please call out the impact explicitly when a change touches any of these boundaries:

- Canon or authority precedence;
- acceptance or Settlement;
- independent semantic review/fingerprint binding;
- Context visibility/injection rules;
- Learning scope or promotion;
- Model/Agent Runtime permissions, tools, checkpoints, receipts, or secret handling;
- SQLite durability/migrations or the rule that persistence itself grants no authority.

For these changes, include the owning contract, exact before/after behavior, failure behavior, and matching tests. A UI, adapter, checkpoint, AgentResult, receipt, model response, autosave, or database write must never silently create Canon/Settlement/Framework authority.

## Test the surface you changed

### Python / Core / Runtime

At minimum for Python-facing changes:

```bash
python scripts/version_consistency.py
python scripts/namespace_hygiene.py
python -m unittest discover -s tests -p 'test_quillframe_*.py' -v
python project_sdk.py self-test
python studio/host_bridge.py self-test
```

Run any subsystem-specific self-tests documented by the files you changed. Normal CI intentionally does **not** call a configured live/paid Model API.

### Product site and documentation

```bash
cd site
npm install --no-audit --no-fund
npm run quality
npm run build
npm run docs:build
```

### Studio

```bash
cd studio/app
corepack enable
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
```

If your change is visual, include screenshots for the affected viewport(s) and verify both supported locales where copy/layout is involved. Do not use fixture UI or an unmerged branch screenshot to claim a capability exists on `main`.

## Documentation rules

Current-facing documentation uses **Quillframe**, technical identifiers use the current `quillframe` namespace, and `0.9.x` is pre-1.0. Historical records may retain `NovelForge` where changing the name would damage provenance or historical meaning; do not run a blind global replacement.

Public capability claims must be supported by current `main`. Keep these distinctions explicit:

```text
branch work ≠ merged capability
merged code ≠ deployed surface
Plan ≠ Canon
Review ≠ Accepted
Accepted ≠ Settled
stored ≠ injected
```

## Pull requests

A good PR explains:

- what changed and why;
- the exact scope and intentionally untouched areas;
- tests/builds run;
- screenshots when UI is affected;
- breaking-change status;
- authority/Canon/Settlement/Learning impact;
- related issues/specs.

Prefer bounded commits with descriptive messages. Do not force-push over concurrent work you do not own; fetch and reconcile unfamiliar changes intentionally.

## Security and secrets

Never commit or paste API access tokens, private credentials, private manuscript data, or sensitive SQLite databases into a PR/issue. Resolved Model API tokens are host secrets and must not enter prompts, Context, snapshots, AgentJob/Result, receipts, SQLite, or Vite client bundles.

For vulnerabilities, use [SECURITY.md](SECURITY.md) rather than a public issue.

## Conduct

Participation is governed by the repository [Code of Conduct](CODE_OF_CONDUCT.md). Technical disagreement is welcome; harassment, doxxing, secret disclosure, and personal attacks are not.

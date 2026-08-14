<div align="center">
  <img src="assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="680" />
  <p><strong>Engineer the production system without turning fiction into system logs.</strong></p>
  <p><kbd>CANON</kbd>&nbsp;&nbsp;<kbd>RESUMABLE SESSIONS</kbd>&nbsp;&nbsp;<kbd>READER QA</kbd>&nbsp;&nbsp;<kbd>INDEPENDENT REVIEW</kbd>&nbsp;&nbsp;<kbd>LEARNING</kbd></p>
  <p><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a> · <a href="docs/README.en.md">Documentation</a></p>
</div>

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge · Adaptive Fiction Agent Framework

> 🌸 **NovelForge is a project-agnostic agent framework for long-form and serialized fiction.** It treats story truth, character state, reader quality, runtime recovery, independent review, and preference learning as first-class production concerns—not prompt conventions.

**Project-agnostic · Session-native · Reader-aware · Evidence-driven · Provider-neutral**

> **Boundary ✦** No built-in novel. No hidden Canon promotion. No reviewer shopping. A consuming project owns its story facts; NovelForge owns generic mechanisms.

<p align="center"><a href="docs/why-novelforge.en.md"><strong>Why NovelForge?</strong></a> · <a href="docs/production-pipeline.en.md"><strong>Production Pipeline</strong></a> · <a href="docs/quality-assurance.en.md"><strong>Quality & QA</strong></a> · <a href="docs/architecture-atlas.en.md"><strong>Architecture Atlas</strong></a></p>

---

## 01 · Direct novel-agent comparison ✨

<img src="assets/ui/home-comparison.en.svg" alt="Detailed mechanism comparison between NovelForge, NovelClaw, Novel OS, AuthorAgent, and autonovel" width="100%" />

This is deliberately an apples-to-apples **novel-agent/framework comparison**. Mature author applications such as Sudowrite and NovelCrafter are discussed separately in [Why NovelForge](docs/why-novelforge.en.md); LangGraph, OpenAI Agents SDK, AutoGen, CrewAI, and other general runtimes belong to the [implementation-influence layer](knowledge/AGENT_FRAMEWORK_ADOPTION.en.md).

NovelForge's distinctive bet is that long-form quality depends less on “more agents” than on **authority separation, character ownership, reader-pressure modeling, truthful QA, recoverable execution, and evidence-backed learning**.

---

## 02 · Architecture 🪄

<img src="assets/ui/home-architecture.en.svg" alt="NovelForge five-domain architecture" width="100%" />

Three durable domains are intentionally distinct:

```text
runtime/session state ≠ learning state ≠ project/Canon state
```

That separation prevents a session memory, corpus result, review verdict, or learning hypothesis from silently becoming story truth.

Read [Architecture](docs/architecture.en.md) for the system view and [Architecture Atlas](docs/architecture-atlas.en.md) for subsystem ownership and deep protocol links.

---

## 03 · Production pipeline 📖

```text
Context Freeze
→ Story / Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ post-generation Regression / Independent Review
→ Rewrite or Regenerate
→ Reader Engagement
→ Continuity Audit
→ User-visible Gate
```

**Raw Draft is internal.** The first model completion is never automatically the user-facing chapter. Regression bad examples are loaded only after the Raw Draft is frozen, so known failure samples do not prime first-pass generation.

Failure routing goes back to the owning mechanism: surface cluster → scene regeneration; SAFE-BUT-FLAT → Reader Pressure + Scene Simulation; character failure → Character Simulation; story failure → Story/Plan.

Read [Production Pipeline](docs/production-pipeline.en.md).

---

## 04 · Quality & QA ✅

<img src="assets/ui/home-quality.en.svg" alt="NovelForge quality assurance stack and failure-routing system" width="100%" />

Deterministic code handles schemas, authority boundaries, lifecycle, fingerprints, dependencies, idempotency, blind-queue hygiene, and release invariants. Semantic judgment handles prose quality, reader engagement, nuanced character/scene behavior, and other questions that rules cannot honestly decide.

Mandatory independent review requires a genuinely separate invocation/session and returns a typed result bound to the exact candidate fingerprint. A valid semantic reject must be repaired; it cannot be reviewer-shopped into a PASS.

Read [Quality & QA](docs/quality-assurance.en.md) and [Eval Reference](evals/README.en.md).

---

## 05 · Honest fit ⚖️

<img src="assets/ui/home-fit.en.svg" alt="When NovelForge is a strong fit and when a lighter fiction system is more appropriate" width="100%" />

NovelForge deliberately accepts more ceremony than lightweight writing tools: exact framework locks, explicit authority classes, checkpoints, fingerprints, independent gates, transactional settlement, and reproducible validation.

That cost is justified only when the project is complex enough to need it. If you mainly want fast ideation, prose assistance, or a polished consumer editor, another product may be a better fit.

---

## 06 · Project engineering ⚙️

A consuming novel is a versioned project rather than a loose prompt folder.

```bash
python project_sdk.py init <path> --id PROJECT-X --title "Novel"
python project_sdk.py validate <path>
python project_sdk.py build <path>
python project_sdk.py self-test
```

Projects pin an exact NovelForge revision and own their own profiles, bible, Accepted Canon, current state, plans, manuscripts, research, regressions, tests, and build artifacts.

Read [Project SDK](docs/project-sdk.en.md) and [Project Adapters](docs/project-adapters.en.md).

---

## 07 · Runtime & learning 🔌

The Harness can operate across chat sessions, local Codex/Claude processes, provider APIs, MCP workers, GitHub jobs, local models, and human review—when those paths satisfy the required capabilities and independence constraints.

**Capability ≠ authority.** Technical ability to write does not grant Canon-write permission.

Preference learning is evidence-backed, scoped, contradictable, versioned, and rollbackable. Corpus evidence remains distinct from Canon, character knowledge, and durable user taste.

Read [Runtime & Integrations](docs/integrations.en.md), [Adaptive Learning](docs/adaptive-learning.en.md), and [Corpus Intelligence](corpus/README.en.md).

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

## 08 · Documentation 🌸

<p align="center"><a href="docs/README.en.md"><strong>Docs Home</strong></a> · <a href="docs/why-novelforge.en.md"><strong>Full Comparison</strong></a> · <a href="docs/architecture-atlas.en.md"><strong>Architecture Atlas</strong></a> · <a href="docs/production-pipeline.en.md"><strong>Production Pipeline</strong></a> · <a href="docs/quality-assurance.en.md"><strong>Quality & QA</strong></a> · <a href="assets/DESIGN_SYSTEM.en.md"><strong>Story Loom Design</strong></a></p>

<div align="center">
  <img src="assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="58" />
  <br />
  <sub>strict backstage · vivid fiction · professional engineering with a little sakura warmth 🌸</sub>
</div>

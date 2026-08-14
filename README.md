<div align="center">
  <img src="assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="680" />
  <p><strong>Fiction production, engineered without flattening fiction.</strong></p>
  <p><kbd>CANON</kbd>&nbsp;&nbsp;<kbd>RESUMABLE SESSIONS</kbd>&nbsp;&nbsp;<kbd>READER QA</kbd>&nbsp;&nbsp;<kbd>INDEPENDENT REVIEW</kbd>&nbsp;&nbsp;<kbd>LEARNING</kbd></p>
  <p>
    <a href="README.en.md"><strong>English</strong></a> · <a href="README.zh-CN.md"><strong>简体中文</strong></a> · <a href="docs/README.en.md"><strong>Documentation</strong></a>
  </p>
</div>

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

> 🌸 **NovelForge is a project-agnostic agent framework for long-form and serialized fiction.** It treats story truth, character state, reader quality, runtime recovery, independent review, and preference learning as first-class production concerns—not prompt conventions.

**The hard boundary:** no built-in novel, no silent Canon promotion, no reviewer shopping. A consuming project owns its story facts; NovelForge owns generic mechanisms.

<p align="center">
  <a href="docs/why-novelforge.en.md"><strong>Why NovelForge?</strong></a> ·
  <a href="docs/architecture.en.md"><strong>Architecture</strong></a> ·
  <a href="docs/quality-assurance.en.md"><strong>Quality & QA</strong></a> ·
  <a href="docs/project-sdk.en.md"><strong>Project SDK</strong></a> ·
  <a href="docs/README.en.md"><strong>Docs Home</strong></a>
</p>

---

## 01 · Why NovelForge? ✨

NovelForge is not trying to be a prettier one-shot writing prompt or the most general agent orchestrator. Its strongest fit is **long-running fiction where truth, continuity, character knowledge, quality gates, and execution state must survive many chapters, sessions, models, and revisions**.

<img src="assets/ui/home-comparison.en.svg" alt="Detailed mechanism comparison between NovelForge, NovelClaw, Novel OS, AuthorAgent, and autonovel" width="100%" />

The matrix intentionally compares **direct novel agents/frameworks**. Mature author applications such as Sudowrite and NovelCrafter are covered separately in the [full positioning guide](docs/why-novelforge.en.md); general agent runtimes such as LangGraph and the OpenAI Agents SDK belong to the [implementation-influence layer](knowledge/AGENT_FRAMEWORK_ADOPTION.en.md), not the primary customer comparison.

> **NovelForge's bet ✦** The hard part of serious long-form AI fiction is not generating more text. It is maintaining authority, causality, character independence, reader pressure, truthful QA, and recoverable state while the project evolves.

---

## 02 · Architecture at a glance 🪄

<img src="assets/ui/home-architecture.en.svg" alt="NovelForge five-domain architecture: project context, harness runtime, story core, editorial quality, and evidence learning" width="100%" />

The architecture deliberately separates **project/Canon state**, **runtime/session state**, and **learning state**. They may reference one another through explicit IDs and evidence, but none can silently acquire another domain's authority.

The branded diagram is the presentation layer. The inspectable source diagrams and exact contracts live in [Architecture](docs/architecture.en.md) and the deeper protocol documents.

---

## 03 · A chapter is a production run, not one model call 📖

A chapter moves through four production phases, each with a different responsibility:

**01 · Prepare the run** — Freeze only the necessary context, preflight Story/Canon, simulate scene and character behavior, and establish reader pressure before prose is generated.

**02 · Create an internal candidate** — Produce an event-first Raw Draft, then realize the prose surface. The Raw Draft remains internal; the first completion is never treated as the finished chapter.

**03 · Challenge and repair** — Run post-generation regression evidence and independent semantic review, then repair the layer that actually owns the failure instead of polishing symptoms downstream.

**04 · Release through gates** — Reader Engagement and continuity/state auditing must resolve before the candidate crosses the user-visible gate.

Surface-clean prose is only the floor. Isolated surface defects can be rewritten locally; clustered surface failures regenerate the scene; safe-but-flat prose returns to Reader Pressure and Scene Simulation; character failures return to Character Simulation; story failures return to Story/Plan.

Read the full [Production Pipeline](docs/production-pipeline.en.md).

---

## 04 · Quality & QA ✅

<img src="assets/ui/home-quality.en.svg" alt="NovelForge quality assurance stack and failure-routing system" width="100%" />

NovelForge separates **deterministic correctness** from **semantic literary judgment**.

Deterministic checks cover schemas, authority boundaries, lifecycle, fingerprints, dependencies, idempotency, blind-queue hygiene, project leakage, and release invariants. Semantic gates cover prose realization, reader engagement, character/scene behavior, and other judgments that cannot honestly be reduced to regexes.

Mandatory independent review comes from a genuinely separate invocation/session, receives bounded context, and returns a typed result bound to the artifact fingerprint. A valid semantic rejection routes repair; it does not trigger reviewer shopping.

Read the detailed [Quality & QA guide](docs/quality-assurance.en.md) and [Eval reference](evals/README.en.md).

---

## 05 · Honest fit & tradeoffs ⚖️

<img src="assets/ui/home-fit.en.svg" alt="When NovelForge is a strong fit and when a lighter fiction system is more appropriate" width="100%" />

NovelForge deliberately accepts more ceremony than lightweight writing tools: exact framework locks, explicit authority classes, checkpoints, fingerprints, independent gates, transactional settlement, and reproducible project validation. That cost is justified only when the project is complex enough to need it.

For a short story, casual ideation session, or writer who mainly wants a polished consumer editor, a lighter product may be the better tool.

---

## 06 · Project engineering ⚙️

A consuming novel is a versioned project rather than a loose prompt folder. It owns its manifests, profiles, story bible, Accepted Canon, current state, plans, manuscripts, research, regressions, tests, and build artifacts while pinning an exact NovelForge dependency.

```bash
python project_sdk.py init <path> --id PROJECT-X --title "Novel"
python project_sdk.py validate <path>
python project_sdk.py build <path>
python project_sdk.py self-test
```

The framework can also sit behind legacy project layouts through a mapped Project Adapter. See [Project SDK](docs/project-sdk.en.md) and [Project Adapters](docs/project-adapters.en.md).

---

## 07 · Runtime without provider lock-in 🔌

The same Harness contracts can be carried by a normal chat session, local Codex/Claude process, provider API, MCP worker, GitHub job, local model, or human reviewer—provided the selected runtime actually satisfies the required capability and independence contract.

**Capability is not authority.** A runtime that can technically write a file does not thereby gain Canon-write permission; a session that remembers a fact does not make that fact true in the story.

See [Runtime & Integrations](docs/integrations.en.md), [Session Runtime](harness/session_runtime/SESSION_RUNTIME.en.md), and [Semantic Workers](harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md).

---

## 08 · Evidence-driven learning 🔎

NovelForge can learn from direct edits, accepts/rejects, repeated correction patterns, project conventions, corpus evidence, and evals. Preference hypotheses remain evidence-backed, scoped, contradictable, versioned, and rollbackable.

Corpus is evidence—not Canon, not automatic character knowledge, and not a license to mirror copyrighted works. General-craft promotion requires cross-work evidence, counterexamples or profile boundaries, eval coverage, provenance, versioning, rollback, and green framework validation.

See [Adaptive Learning](docs/adaptive-learning.en.md) and [Corpus Intelligence](corpus/README.en.md).

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

## 09 · Go deeper 🌸

<p align="center">
  <a href="docs/README.en.md"><strong>Documentation Home</strong></a> &nbsp;·&nbsp;
  <a href="docs/why-novelforge.en.md"><strong>Full Comparison</strong></a> &nbsp;·&nbsp;
  <a href="docs/architecture.en.md"><strong>Architecture</strong></a> &nbsp;·&nbsp;
  <a href="docs/quality-assurance.en.md"><strong>Quality & QA</strong></a> &nbsp;·&nbsp;
  <a href="docs/adaptive-learning.en.md"><strong>Learning</strong></a> &nbsp;·&nbsp;
  <a href="corpus/README.en.md"><strong>Corpus</strong></a>
</p>

<div align="center">
  <img src="assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="58" />
  <br />
  <sub><strong>Story Loom</strong> · strict backstage · vivid fiction · professional engineering with a little sakura warmth 🌸</sub>
</div>

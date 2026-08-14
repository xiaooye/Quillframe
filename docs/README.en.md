<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="600" />
  <p><strong>Documentation for builders who want fiction-native state, quality, and agent execution.</strong></p>
  <p><kbd>START</kbd>&nbsp;&nbsp;<kbd>UNDERSTAND</kbd>&nbsp;&nbsp;<kbd>BUILD</kbd>&nbsp;&nbsp;<kbd>VERIFY</kbd>&nbsp;&nbsp;<kbd>OPERATE</kbd></p>
  <p><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge Documentation

> 🌸 **NovelForge is not a general-purpose agent SDK with fiction examples. It is a fiction-production framework whose runtime, state model, quality system, learning loop, and project engineering are all designed around long-form narrative work.**

Use this page as the customer-facing map. Deep protocol documents remain available when you need exact implementation contracts.

---

## 01 · Choose your path ✨

| If you want to… | Start here | Then read |
|---|---|---|
| **Understand the product** | [Why NovelForge](why-novelforge.en.md) | [Architecture](architecture.en.md) |
| **Evaluate technical fit** | [Why NovelForge](why-novelforge.en.md) | [Architecture Atlas](architecture-atlas.en.md) |
| **Understand generation quality** | [Production Pipeline](production-pipeline.en.md) | [Quality & QA](quality-assurance.en.md) |
| **Integrate a project** | [Project SDK](project-sdk.en.md) | [Project Adapters](project-adapters.en.md) |
| **Run across chat / CLI / MCP / API** | [Runtime & Integrations](integrations.en.md) | [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md) |
| **Understand learning and corpus** | [Adaptive Learning](adaptive-learning.en.md) | [Corpus Intelligence](../corpus/README.en.md) |
| **Audit release quality** | [Quality & QA](quality-assurance.en.md) | [Eval Reference](../evals/README.en.md) |

---

## 02 · Product story 🪄

### Why this exists

General agent frameworks are excellent at orchestration, tool use, durable workflows, teams, and automation. NovelForge starts one layer higher: **what does a production system need when the artifact is a long-running fictional world whose truth, characters, continuity, prose quality, and reader experience all evolve over time?**

Read [Why NovelForge](why-novelforge.en.md) for the comparison, including cases where another framework is the better choice.

### What makes the architecture different

NovelForge separates:

1. **Project state** — accepted Canon, current state, plans, research;
2. **Runtime state** — sessions, checkpoints, handoffs, leases, result receipts;
3. **Learning state** — evidence, preference hypotheses, corpus gaps, promotion candidates.

Those domains may reference one another, but authority never flows implicitly between them.

Read [Architecture](architecture.en.md) for the system view and [Architecture Atlas](architecture-atlas.en.md) for subsystem-by-subsystem detail.

---

## 03 · Build and run 📖

### Project engineering

A NovelForge consumer is treated as a reproducible project rather than a loose prompt folder. Projects pin an exact framework revision, keep project-owned story facts outside the generic framework, and validate their manifests, state, plans, manuscripts, research, evals, and migrations.

- [Project SDK](project-sdk.en.md)
- [Project Adapters](project-adapters.en.md)
- [Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md)

### Runtime and orchestration

NovelForge uses one manager by default and adds specialists only for real capability, isolation, independent judgment, or useful parallel work. Chat sessions, local agents, provider APIs, MCP, GitHub jobs, local models, and human reviewers are runtimes—not authorities.

- [Runtime & Integrations](integrations.en.md)
- [Harness Agent](../harness/HARNESS_AGENT.en.md)
- [Orchestration Protocol](../harness/ORCHESTRATION_PROTOCOL.en.md)
- [Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.en.md)

---

## 04 · Fiction systems 🌸

NovelForge has domain mechanisms that general agent frameworks usually leave to the application layer:

| System | Question it answers | Deep reference |
|---|---|---|
| **Story System** | What structural unit exists, what pressure changes, and what must move next? | [Story System](../core/STORY_SYSTEM.en.md) |
| **Character System** | What does each character know, want, risk, remember, and independently pursue? | [Character System](../core/CHARACTER_SYSTEM.en.md) |
| **Canon State** | What is planned, reviewed, accepted, locked, or merely proposed? | [Canon State](../core/CANON_STATE.en.md) |
| **Surface Fundamentals** | Which recurring AI-prose failure mechanisms must be rejected? | [Surface Fundamentals](../surface/FUNDAMENTALS.en.md) |
| **Reader Engagement** | Is the chapter compelling, rewarding, and causally alive—not merely clean? | [Reader Engagement](../surface/READER_ENGAGEMENT.en.md) |

---

## 05 · Quality, QA, and release gates ✅

NovelForge deliberately separates **deterministic correctness** from **semantic literary judgment**.

- deterministic checks cover schemas, lifecycle, permissions, fingerprints, dependency integrity, idempotency, build/release invariants, and project leakage;
- semantic checks cover prose quality, reader engagement, character/scene behavior, and other judgments that cannot honestly collapse into regexes;
- mandatory independent judgments come from a separate invocation/session and are bound to the artifact fingerprint;
- hidden eval labels are removed before semantic reviewers receive blind queues;
- normal CI does not silently spend paid model usage.

Read [Quality & QA](quality-assurance.en.md) for the full gate stack and [Eval Reference](../evals/README.en.md) for runner details.

---

## 06 · Learning and corpus intelligence 🔎

NovelForge can learn from user feedback and external evidence without turning model guesses into permanent rules.

- [Adaptive Learning](adaptive-learning.en.md)
- [Corpus Intelligence](../corpus/README.en.md)
- [Corpus Policy](../corpus/CORPUS_POLICY.en.md)
- [Corpus Ingest Protocol](../corpus/CORPUS_INGEST_PROTOCOL.en.md)
- [Self-improvement Protocol](../harness/SELF_IMPROVEMENT_PROTOCOL.en.md)

---

## 07 · Reference layer ⚙️

These documents are exact contracts rather than onboarding material:

| Area | Reference |
|---|---|
| Harness execution | [Harness Agent](../harness/HARNESS_AGENT.en.md) |
| Session identity / resume | [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md) |
| Runtime capability routing | [Runtime Capabilities](../harness/session_runtime/RUNTIME_CAPABILITIES.en.md) |
| Durable control plane | [Control Plane](../harness/control_plane/CONTROL_PLANE.en.md) |
| Semantic worker contract | [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) |
| Semantic execution | [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md) |
| Framework release bundle | [Framework Bundle](../release/FRAMEWORK_BUNDLE.en.md) |
| Eval implementation | [Eval Reference](../evals/README.en.md) |

---

## 08 · Documentation philosophy ✦

Customer-facing pages explain **why, when, how, and tradeoffs**. Protocol pages define **exact invariants and contracts**. Machine schemas remain single-source JSON/YAML/Python where appropriate.

That separation keeps NovelForge approachable without making the underlying execution model vague.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <br />
  <sub>Start with the product story. Drop into the contracts only when you need precision. 🌸</sub>
</div>

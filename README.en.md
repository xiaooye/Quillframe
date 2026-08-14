<div align="center">
  <img src="assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="640" />
  <p><strong>Engineer the production system without turning fiction into system logs.</strong></p>
  <p><kbd>STORY + CANON</kbd>&nbsp;&nbsp;<kbd>SESSIONS</kbd>&nbsp;&nbsp;<kbd>READER QUALITY</kbd>&nbsp;&nbsp;<kbd>LEARNING</kbd>&nbsp;&nbsp;<kbd>EVALS</kbd></p>
  <p><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>
</div>

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge · Adaptive Fiction Agent Framework

> 🌸 **NovelForge does not reduce fiction production to “outline → prompt → chapter.” It treats story state, Canon, editorial quality, long-term learning, and agent execution as one stateful production system.**

**Project-agnostic · Session-native · Reader-aware · Evidence-driven · Provider-neutral**

> **Boundary ✦** This repository intentionally contains **no built-in novel, character, plot, or Canon**. A consuming project contributes its own profile, state, and plans through a Project Adapter; NovelForge never absorbs those story facts back into the generic framework.

---

## 01 · Why NovelForge ✨

Most AI fiction systems put the model call at the center. NovelForge puts **explicit authority and a recoverable production workflow** at the center instead. Models handle work that genuinely requires semantic judgment; identity, state transitions, permissions, fingerprints, checkpoints, Canon settlement, and idempotency remain deterministic.

| Domain | NovelForge owns | Hard boundary |
|---|---|---|
| **Story / Canon** | story hierarchy, characters, relationships, information boundaries, resources, continuity | Plan / Review / Memory ≠ Canon |
| **Harness / Runtime** | task routing, sparse context, checkpoints, handoffs, workers | Session state ≠ project authority |
| **Editorial Quality** | Surface Fundamentals, Reader Engagement, independent semantic review | “No obvious defect” ≠ “compelling fiction” |
| **Evidence / Learning** | feedback evidence, preference hypotheses, corpus gaps, benchmarks, evals | Model inference ≠ durable preference |
| **Project Engineering** | manifests, exact locks, adapters, validation, builds, release contracts | Framework ≠ consuming project |

---

## 02 · Story Loom System Map 🪄

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "background": "#FFFDFC",
    "primaryTextColor": "#241D2B",
    "lineColor": "#756A7D",
    "fontFamily": "ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif",
    "clusterBkg": "#FFFDFC",
    "clusterBorder": "#E2DAE8"
  },
  "flowchart": {"curve": "basis", "nodeSpacing": 30, "rankSpacing": 38}
}}%%
flowchart TB
    subgraph PROJECT["01  ·  PROJECT / CONTEXT"]
      direction LR
      PA([Project Adapter]) --> CTX([Sparse Context])
    end

    subgraph FORGE["02  ·  HARNESS / RUNTIME"]
      direction LR
      M{{Harness Manager}} --> CP[(Sessions · Checkpoints · Control Plane)]
    end

    subgraph STORY["03  ·  STORY / PRODUCTION"]
      direction LR
      CORE[[Story · Character · Canon]] --> SIM([Scene + Character Simulation]) --> D([Event-first Draft]) --> SURF([Surface Fundamentals]) --> READ([Reader Engagement]) --> SEM{{Independent Semantic Review}} --> CONT([Continuity / State Audit]) --> GATE([User-visible Gate])
    end

    subgraph LEARN["04  ·  EVIDENCE / LEARNING"]
      direction LR
      PREF([Preference Evidence]) --> HYP([Preference Hypotheses]) --> GAP([Corpus Gaps]) --> RIGHTS([Rights / Provenance]) --> BENCH([Benchmarks / Evals])
    end

    PA --> M
    M --> CTX
    CTX --> CORE
    CP -. resume / result binding .-> M
    BENCH -. quality evidence .-> SURF
    BENCH -. reader evidence .-> READ

    classDef project fill:#DDEFF8,stroke:#4F8FBA,color:#241D2B,stroke-width:1.75px;
    classDef runtime fill:#E7E1F8,stroke:#796BC4,color:#241D2B,stroke-width:1.75px;
    classDef editorial fill:#F9DDE9,stroke:#D6679A,color:#241D2B,stroke-width:1.75px;
    classDef evidence fill:#F9EDCF,stroke:#BE892F,color:#241D2B,stroke-width:1.75px;
    classDef validated fill:#DCF1E7,stroke:#4D9B7D,color:#241D2B,stroke-width:2px;
    classDef neutral fill:#FFFDFC,stroke:#62556D,color:#241D2B,stroke-width:1.75px;

    class PA,CTX project;
    class M,CP,SEM runtime;
    class CORE,SIM,D neutral;
    class SURF,READ,CONT editorial;
    class PREF,HYP,GAP,RIGHTS,BENCH evidence;
    class GATE validated;

    style PROJECT fill:#F7FCFF,stroke:#B8D9EC,stroke-width:1px,color:#3C3245
    style FORGE fill:#FAF8FF,stroke:#CFC7EE,stroke-width:1px,color:#3C3245
    style STORY fill:#FFFAFC,stroke:#EDC3D6,stroke-width:1px,color:#3C3245
    style LEARN fill:#FFFCF5,stroke:#E8D2A5,stroke-width:1px,color:#3C3245
```

**Solid edges** show primary execution or dependency. **Dashed edges** show resume, feedback, evidence, or reference paths. Visual tokens come from [`assets/brand/tokens.json`](assets/brand/tokens.json).

---

## 03 · Core Subsystems 📖

### Story / Canon Core

Models `BOOK → VOLUME → ARC → UNIT → CHAPTER → SCENE`, along with character autonomy, relationships, information boundaries, resources, obligations, foreshadowing, evidence, dependencies, Accepted Canon, and settlement. **A plan never becomes Canon merely because the system remembers it.**

### Harness & Sessions

The Harness uses a deterministic outer workflow with one manager by default. Sessions, runs, checkpoints, events, handoffs, worker leases, and result receipts are explicit runtime state. Persistence records **where the work is**, not **what the story has accepted as truth**.

### Surface Fundamentals + Reader Engagement

Surface Fundamentals catch malformed, AI-ish, or mechanically realized prose. Reader Engagement separately evaluates narrative pressure, payoff, tonal contrast, curiosity evolution, scene causality, and forward pull.

> ✨ **Key idea:** clean prose is the floor. A chapter can contain no obvious surface defect and still fail because it is safe, flat, or inert.

### Independent Semantic Review

Mandatory independent review must come from a genuinely separate session or invocation and bind to the candidate artifact fingerprint. Eligible transports include local Codex or Claude processes, provider adapters, MCP workers, GitHub jobs, separate peer chats, local models, and human reviewers.

Same-session “critic role-play” does not count as independence. A valid semantic rejection must be repaired, not reviewer-shopped until something says PASS.

### Adaptive Preference Learning

NovelForge does not compress user taste into a permanent style prompt. It maintains evidence-backed hypotheses that can contradict, narrow, deprecate, and roll back:

```text
feedback
→ evidence
→ preference hypothesis
→ confidence / contradiction
→ style dimensions
→ corpus gap
→ discovery request
→ corpus evidence
→ personalized eval
→ active profile / rollback
```

The framework can discover **new preference dimensions** rather than only tuning predefined sliders. Model inference alone cannot promote durable user taste.

### Corpus Intelligence

Corpus is evidence infrastructure, not Canon. NovelForge can identify evidence gaps, create discovery plans, inspect lawful sources through host-provided Web/GitHub/MCP connectors, classify rights and provenance, derive mechanism-level observations, seek counterexamples, and build cross-work benchmarks.

Modern copyrighted fiction is not mirrored wholesale merely because it is readable online, and NovelForge does not create named-author imitation fingerprints.

### Evals & Self-improvement

Every durable framework behavior promotion requires mechanism evidence, counterexample or profile-boundary analysis, evaluation coverage, versioning and rollback, plus post-change regression checks. User-rejected model output may become negative regression evidence; it cannot become a positive style exemplar.

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

## 04 · Runtime Model ⚙️

```text
project / resource
→ session / thread
→ run / invocation
→ checkpoint
→ event / handoff
→ worker lease / external wait
→ result
→ validation
→ consume-once receipt
→ resume
```

Chat sessions are first-class runtimes. NovelForge does not require an API key when the host can provide another eligible independent worker path.

### Provider-neutral execution

| Runtime | Manager | Specialist | Independent review | Typical transport |
|---|---:|---:|---:|---|
| Current chat session | ✓ | bounded | self-review ✗ | host chat |
| Separate peer chat | — | — | ✓ | user / connector relay |
| Codex CLI | ✓ | ✓ | ✓ separate invocation | local process / MCP |
| Claude Code | ✓ | ✓ | ✓ separate invocation | local process / MCP |
| Provider API | — | ✓ | ✓ | adapter |
| GitHub Actions | — | ✓ | ✓ with worker backend | workflow / event |
| Remote MCP worker | ✓ | ✓ | ✓ isolated session | Streamable HTTP |
| Local model | optional | ✓ | ✓ isolated invocation | adapter |
| Human reviewer | — | — | ✓ | relay |

---

## 05 · Project Adapter Boundary 🧩

A consuming novel supplies only project-owned information:

```text
project/
├── project.yaml            # identity + framework compatibility
├── profile/                # genre / platform / prose / reader targets
├── bible/                  # characters / world / relationships / research
├── state/                  # Accepted Canon + ledgers
├── plans/                  # active plans / scene cards
├── regressions/            # project-only negative cases
└── manuscripts/            # draft / review / accepted artifacts
```

Dependency direction is one-way:

```text
Project → NovelForge
NovelForge -X→ project-specific facts
```

---

## 06 · Repository Map 🗺️

```text
.
├── core/                   # Story / Character / Canon primitives
├── surface/                # prose realization + reader engagement
├── harness/                # orchestration / sessions / control plane / workers
├── learning/               # preference evidence + promotion / rollback
├── corpus/                 # discovery / rights / analysis / benchmarks
├── knowledge/              # generic craft + framework research
├── evals/                  # capability / regression suites
├── docs/                   # architecture / SDK / integration guides
├── assets/                 # Story Loom brand + documentation system
├── project_sdk.py          # project engineering contract
└── project_adapter.py      # standard / mapped project resolution
```

---

## 07 · Visual & Documentation System 🎨

NovelForge's GitHub documentation uses **Story Loom**: an original logo, semantic design tokens, story-thread dividers, numbered section rhythm, and branded Mermaid diagrams. Future AI- or designer-rendered architecture visuals may sit above the source diagrams, while Mermaid remains the inspectable semantic reference.

- [Documentation design system](assets/DESIGN_SYSTEM.en.md)
- [Brand tokens](assets/brand/tokens.json)
- [Architecture](docs/architecture.en.md)
- [Visual provenance](assets/provenance.json)

A tiny `(˶ᵔ ᵕ ᵔ˶)` may appear in non-authoritative README microcopy. It will never appear in a schema, authority contract, or machine state.

---

## 08 · Principles ✦

- Multi-agent is an implementation choice, not a quality feature.
- Persist operational state, not accidental authority.
- Retrieve sparsely: presence in storage does not imply prompt inclusion.
- Keep writer context isolated from regression gold and expected verdicts.
- Learn mechanisms, not author-imitation templates.
- A semantic rejection is a valid judgment, not a reason to shop reviewers.
- Corpus is evidence, not Canon.
- User taste is revisable evidence, not permanent mythology.

<div align="center">
  <img src="assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="58" />
  <br />
  <sub>strict backstage · vivid fiction · professional docs with a few sakura petals 🌸</sub>
</div>

<div align="center">
  <img src="assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="640" />

  <p><strong>Fiction production, engineered without flattening fiction.</strong></p>
  <p>
    <kbd>STORY + CANON</kbd>&nbsp;&nbsp;
    <kbd>SESSIONS</kbd>&nbsp;&nbsp;
    <kbd>READER QUALITY</kbd>&nbsp;&nbsp;
    <kbd>LEARNING</kbd>&nbsp;&nbsp;
    <kbd>EVALS</kbd>
  </p>
  <p>
    <a href="README.en.md"><strong>English</strong></a> · <a href="README.zh-CN.md"><strong>简体中文</strong></a>
  </p>
</div>

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

> 🌸 **NovelForge is a project-agnostic production framework for long-form and serialized fiction.**
>
> It combines explicit story authority, resumable agent execution, sparse context, reader-engagement gates, independent semantic review, lawful corpus intelligence, evidence-driven preference learning, and reproducible project engineering.

### ✦ The hard boundary

**No built-in novel. No hidden Canon promotion. No reviewer shopping.** Consumer projects depend on NovelForge; NovelForge never imports their story facts back into the framework.

---

## 01 · System map ✨

The diagram follows the **Story Loom** brand grammar: blue is project/context, violet is runtime/orchestration, pink is editorial quality, amber is evidence/learning, and mint is validated output. Color is never the only semantic channel.

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
      H{{Harness Manager}} --> S[(Sessions · Checkpoints · Control Plane)]
    end

    subgraph STORY["03  ·  STORY / PRODUCTION"]
      direction LR
      CORE[[Story · Character · Canon]] --> SIM([Scene + Character Simulation]) --> D([Event-first Draft]) --> Q([Surface + Reader Quality]) --> SEM{{Independent Review}} --> G([User-visible Gate])
    end

    subgraph EVIDENCE["04  ·  EVIDENCE / LEARNING"]
      direction LR
      F([User Feedback]) --> L([Preference Learning]) --> C([Corpus · Benchmarks · Evals])
    end

    PA --> H
    H --> CTX
    CTX --> CORE
    S -. resume / bind .-> H
    C -. quality evidence .-> Q
    F -. editor signal .-> Q

    classDef project fill:#DDEFF8,stroke:#4F8FBA,color:#241D2B,stroke-width:1.75px;
    classDef runtime fill:#E7E1F8,stroke:#796BC4,color:#241D2B,stroke-width:1.75px;
    classDef editorial fill:#F9DDE9,stroke:#D6679A,color:#241D2B,stroke-width:1.75px;
    classDef evidence fill:#F9EDCF,stroke:#BE892F,color:#241D2B,stroke-width:1.75px;
    classDef validated fill:#DCF1E7,stroke:#4D9B7D,color:#241D2B,stroke-width:2px;
    classDef neutral fill:#FFFDFC,stroke:#62556D,color:#241D2B,stroke-width:1.75px;

    class PA,CTX project;
    class H,S,SEM runtime;
    class CORE,SIM,D neutral;
    class Q,F editorial;
    class L,C evidence;
    class G validated;

    style PROJECT fill:#F7FCFF,stroke:#B8D9EC,stroke-width:1px,color:#3C3245
    style FORGE fill:#FAF8FF,stroke:#CFC7EE,stroke-width:1px,color:#3C3245
    style STORY fill:#FFFAFC,stroke:#EDC3D6,stroke-width:1px,color:#3C3245
    style EVIDENCE fill:#FFFCF5,stroke:#E8D2A5,stroke-width:1px,color:#3C3245
```

**Solid edges** are execution/dependency. **Dashed edges** are resume, feedback, or evidence. Mermaid is the inspectable source diagram; branded rendered diagrams may later sit above it as a presentation layer.

---

## 02 · What NovelForge owns 📖

| Lane | NovelForge owns | It explicitly does **not** mean |
|---|---|---|
| **Story / Canon** | hierarchy, characters, relationships, state, continuity | plan / memory / review = Canon |
| **Harness / Runtime** | task routing, context, sessions, checkpoints, handoffs | runtime state = project authority |
| **Editorial Quality** | Surface Fundamentals, Reader Engagement, semantic review | grammatically clean = engaging |
| **Evidence / Learning** | feedback evidence, hypotheses, corpus gaps, benchmarks | model inference = durable taste |
| **Project Engineering** | manifests, exact locks, adapters, validation, release contracts | framework = consumer project |

> **Boundary ✦** Canon mutation remains transactional. Corpus, session state, reviewer results, schedules, webhooks, and learning hypotheses do not gain story authority merely because they exist.

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

## 03 · Explore the framework 🪄

| Path | English | 简体中文 |
|---|---|---|
| **Overview** | [README.en.md](README.en.md) | [README.zh-CN.md](README.zh-CN.md) |
| **Architecture** | [docs/architecture.en.md](docs/architecture.en.md) | [docs/architecture.zh-CN.md](docs/architecture.zh-CN.md) |
| **Adaptive learning** | [docs/adaptive-learning.en.md](docs/adaptive-learning.en.md) | [docs/adaptive-learning.zh-CN.md](docs/adaptive-learning.zh-CN.md) |
| **Corpus intelligence** | [corpus/README.en.md](corpus/README.en.md) | [corpus/README.zh-CN.md](corpus/README.zh-CN.md) |
| **Project adapters** | [docs/project-adapters.en.md](docs/project-adapters.en.md) | [docs/project-adapters.zh-CN.md](docs/project-adapters.zh-CN.md) |
| **Runtime & integrations** | [docs/integrations.en.md](docs/integrations.en.md) | [docs/integrations.zh-CN.md](docs/integrations.zh-CN.md) |
| **Brand / design system** | [assets/DESIGN_SYSTEM.en.md](assets/DESIGN_SYSTEM.en.md) | [assets/DESIGN_SYSTEM.zh-CN.md](assets/DESIGN_SYSTEM.zh-CN.md) |

## 04 · Design axioms 🌸

- **One framework, many novels.** Generic mechanisms live here; project facts never do.
- **Deterministic where possible, semantic where useful.** Identity, transitions, permissions, fingerprints, and idempotency stay explicit.
- **Chat is a real runtime.** Local agents, APIs, MCP, GitHub jobs, peer chats, local models, and humans are transports—not authorities.
- **Canon is transactional.** Plans, corpus evidence, model memory, session state, and reviewer output cannot silently become story truth.
- **Quality is more than correctness.** Surface safety is a floor; Reader Engagement and continuity still have to pass.
- **Learning is evidence-driven.** Preference hypotheses can evolve, contradict, narrow, and roll back.
- **No reviewer shopping.** Infrastructure failures may fall back; a valid semantic rejection must be repaired.

<div align="center">
  <img src="assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="56" />
  <br />
  <sub><strong>Story Loom visual system</strong> · professional technical core · anime-editorial warmth ✦</sub>
</div>

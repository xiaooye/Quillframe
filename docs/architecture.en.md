<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Architecture</strong></p>
  <p><kbd>AUTHORITY</kbd>&nbsp;&nbsp;<kbd>RUNTIME</kbd>&nbsp;&nbsp;<kbd>QUALITY</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge Architecture

> ✦ **Core idea: separate fiction production into explicit authority, runtime, quality, and evidence domains, then connect those domains through typed boundaries.**
>
> This page follows the [Story Loom documentation system](../assets/DESIGN_SYSTEM.en.md). Mermaid remains the maintainable source diagram; future branded static visuals are presentation layers only.

---

## 01 · Reading Key 🌸

| Lane | Token | Owns | Never implies |
|---|---|---|---|
| **Project / Context** | `project` · sky | consuming project, adapters, context selection | generic framework truth |
| **Harness Runtime** | `runtime` · lavender | sessions, checkpoints, handoffs, workers, control plane | Canon |
| **Story Core** | `neutral` · ink | story, character, Canon mechanics, simulation, drafting | automatic acceptance into Canon |
| **Editorial Quality** | `editorial` · sakura | Surface Fundamentals, Reader Engagement, semantic review | Canon write authority |
| **Evidence / Learning** | `evidence` · amber | feedback, corpus, hypotheses, benchmarks, evals | automatic promotion into durable behavior |
| **Validated Output** | `validated` · mint | results that satisfied the active gate | implicit Canon settlement |

**Shape grammar:** stadium = boundary or I/O; hexagon = manager, decision, or semantic gate; database = durable state; subroutine = reusable core mechanism.

---

## 02 · System View ✨

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
  "flowchart": {"curve": "basis", "nodeSpacing": 28, "rankSpacing": 36}
}}%%
flowchart TB
    subgraph PROJECT["01  ·  PROJECT BOUNDARY"]
      direction LR
      P([Novel Project]) --> SDK([Project SDK / Adapter]) --> CTX([Context Manifest])
    end

    subgraph FORGE["02  ·  HARNESS RUNTIME"]
      direction LR
      H{{Harness Manager}} --> SES[(Session Runtime)] --> CP[(Control Plane)]
      H --> WORK{{Bounded Workers}}
    end

    subgraph STORY["03  ·  STORY CORE"]
      direction LR
      CORE[[Story · Character · Canon]] --> SIM([Scene + Character Simulation]) --> WR([Event-first Writer])
    end

    subgraph QUALITY["04  ·  EDITORIAL QUALITY"]
      direction LR
      SF([Surface Fundamentals]) --> RG([Reader Engagement]) --> SEM{{Independent Semantic Review}} --> CONT([Continuity / State Audit]) --> G([User-visible Gate])
    end

    subgraph EVIDENCE["05  ·  EVIDENCE LOOP"]
      direction LR
      FB([User Feedback]) --> LS([Learning Store]) --> CG([Corpus Gaps]) --> CR([Rights / Provenance]) --> BENCH([Benchmarks / Evals])
    end

    SDK --> H
    H --> CTX
    CTX --> CORE
    WR --> SF
    CP -. resume / result binding .-> H
    WORK -. typed result .-> H
    BENCH -. quality evidence .-> SF
    BENCH -. reader evidence .-> RG

    classDef project fill:#DDEFF8,stroke:#4F8FBA,color:#241D2B,stroke-width:1.75px;
    classDef runtime fill:#E7E1F8,stroke:#796BC4,color:#241D2B,stroke-width:1.75px;
    classDef editorial fill:#F9DDE9,stroke:#D6679A,color:#241D2B,stroke-width:1.75px;
    classDef evidence fill:#F9EDCF,stroke:#BE892F,color:#241D2B,stroke-width:1.75px;
    classDef validated fill:#DCF1E7,stroke:#4D9B7D,color:#241D2B,stroke-width:2px;
    classDef neutral fill:#FFFDFC,stroke:#62556D,color:#241D2B,stroke-width:1.75px;

    class P,SDK,CTX project;
    class H,SES,CP,WORK,SEM runtime;
    class CORE,SIM,WR neutral;
    class SF,RG,CONT editorial;
    class FB,LS,CG,CR,BENCH evidence;
    class G validated;

    style PROJECT fill:#F7FCFF,stroke:#B8D9EC,stroke-width:1px,color:#3C3245
    style FORGE fill:#FAF8FF,stroke:#CFC7EE,stroke-width:1px,color:#3C3245
    style STORY fill:#FFFEFD,stroke:#D9D1DE,stroke-width:1px,color:#3C3245
    style QUALITY fill:#FFFAFC,stroke:#EDC3D6,stroke-width:1px,color:#3C3245
    style EVIDENCE fill:#FFFCF5,stroke:#E8D2A5,stroke-width:1px,color:#3C3245
```

**Solid edges** carry primary execution or dependency. **Dashed edges** carry feedback, evidence, resume, or typed results. A data path crossing a domain boundary never grants authority by itself.

---

## 03 · Architecture Domains 📚

| Domain | Owns | Boundary |
|---|---|---|
| **Generic Fiction Core** | story hierarchy, character and relationship behavior, information boundaries, Canon lifecycle, dependencies, settlement, continuity | generic mechanisms only; never consuming-project story facts |
| **Quality Runtime** | Surface Fundamentals, Reader Engagement, quality-failure routing | profiles may tune weights and thresholds; they may not silently remove fundamental mechanisms |
| **Harness Runtime** | task modes, sparse context, checkpoints, specialists, semantic routing, user-visible gates | manager coordination ≠ independent judgment |
| **Durable Runtime State** | sessions, events, handoffs, leases, result receipts | persistence never upgrades into Canon |
| **Adaptive Learning** | evidence, preference hypotheses, contradictions, promotion candidates, rollback | model inference alone cannot become durable behavior |
| **Corpus Intelligence** | discovery gaps, rights and provenance, mechanism observations, counterexamples, benchmarks | corpus ≠ Canon; modern copyrighted text is not mirrored by default |
| **Project Engineering** | manifests, lockfiles, adapters, authority/state, plans, tests, migrations, builds | project facts must not leak back into the generic framework |

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

## 04 · Three Persistent State Domains 🧠

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#FFFDFC","primaryTextColor":"#241D2B","lineColor":"#756A7D","fontFamily":"ui-sans-serif, system-ui, sans-serif"},"flowchart":{"curve":"basis"}}}%%
flowchart LR
    R[(Runtime State<br/>sessions · checkpoints · handoffs)]
    L[(Learning State<br/>evidence · hypotheses · corpus gaps)]
    C[(Project State<br/>Canon · current state · plans · research)]

    R -. explicit ID / provenance .-> L
    L -. explicit evidence reference .-> C
    C -. task-scoped context reference .-> R

    classDef runtime fill:#E7E1F8,stroke:#796BC4,color:#241D2B,stroke-width:1.75px;
    classDef evidence fill:#F9EDCF,stroke:#BE892F,color:#241D2B,stroke-width:1.75px;
    classDef project fill:#DDEFF8,stroke:#4F8FBA,color:#241D2B,stroke-width:1.75px;

    class R runtime;
    class L evidence;
    class C project;
```

> **Boundary ✦** These domains may reference one another through explicit IDs, evidence, and provenance, but **authority never flows implicitly**. A session remembering something does not make it accepted story truth; a corpus fact does not automatically become character knowledge.

---

## 05 · Dependency Direction 🔒

```text
Novel Project → NovelForge Framework
NovelForge Framework -X→ project-specific facts
```

The Framework owns **schemas and mechanisms**. The Project owns **instances and facts**. A project may pin an exact NovelForge commit; NovelForge may not import that project's Canon back into generic source.

---

## 06 · Context Philosophy 🧩

**Complete schema, sparse injection. Storage is not the prompt.**

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#FFFDFC","primaryTextColor":"#241D2B","lineColor":"#756A7D","fontFamily":"ui-sans-serif, system-ui, sans-serif"},"flowchart":{"curve":"basis"}}}%%
flowchart LR
    S[(Full Project Storage)] --> M([Task-scoped Context Manifest]) --> I{{Model / Worker Invocation}} --> R([Typed Result])
    R -. validated reference only .-> S

    classDef project fill:#DDEFF8,stroke:#4F8FBA,color:#241D2B,stroke-width:1.75px;
    classDef runtime fill:#E7E1F8,stroke:#796BC4,color:#241D2B,stroke-width:1.75px;
    classDef validated fill:#DCF1E7,stroke:#4D9B7D,color:#241D2B,stroke-width:2px;

    class S,M project;
    class I runtime;
    class R validated;
```

The Context Broker selects only the project-state slice and framework rules relevant to the active task. Presence in storage does not imply prompt inclusion, and specialists do not inherit the manager's entire conversation by default.

---

## 07 · Deterministic vs. Semantic Responsibility ⚙️

| Prefer deterministic code for | Use semantic workers for |
|---|---|
| identity and lifecycle | prose-quality judgment |
| schema validation | reader-engagement judgment |
| fingerprints and result binding | nuanced character and scene evaluation |
| permission and authority preconditions | corpus-mechanism interpretation |
| idempotency, leases, consume-once logic | preference and craft distillation |
| arithmetic and dependency integrity | judgment that should not collapse into brittle rules |
| build and release invariants | independent-review verdicts |

**Rule:** if an invariant can be expressed precisely and deterministically, do not spend model judgment on it. If a literary judgment cannot be reduced to deterministic rules, do not pretend a Python check can validate it.

---

## 08 · Branded Static Diagram Contract 🎨

Future AI- or designer-rendered diagrams follow this relationship:

```text
Mermaid source → semantic reference → branded SVG / WebP → README presentation
```

A rendered diagram may not introduce semantics absent from the source. Architecture changes update Mermaid first, then regenerate the presentation asset. Every static asset requires alt text and provenance.

---

## 09 · Release Philosophy 🚢

A framework release is valid only when all of the following hold:

- machine contracts and schemas are coherent;
- English and Simplified Chinese documentation remain paired;
- the project-agnostic boundary stays clean;
- deterministic self-tests and integration contracts pass;
- semantic baselines remain real typed results rather than CI-faked PASS states;
- visual documentation improves comprehension without becoming a second authority.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <br />
  <sub>keep the complexity in the system, the authority explicit, and the architecture calm ✦</sub>
</div>

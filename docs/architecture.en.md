# NovelForge Architecture

> ✦ **Core idea: split fiction production into explicit authority, runtime, quality, and evidence domains, then connect them through typed boundaries.**
>
> Visual styling follows the [NovelForge Documentation Design System](../assets/DESIGN_SYSTEM.en.md). Color groups information; it never carries semantics by itself.

## 🎨 Reading key

| Lane | Accent | Owns | Never means |
|---|---|---|---|
| **Project / Context** | Sky | consumer project, adapter, context selection | Framework generic truth |
| **Harness Runtime** | Lavender | sessions, checkpoints, handoffs, workers, control plane | Canon |
| **Story / Production** | Neutral ink | Story, Character, Canon mechanisms, simulation, draft | Accepted fact unless the project actually accepts it |
| **Quality** | Sakura | Surface, Reader Engagement, semantic review | Canon authority |
| **Learning / Evidence** | Amber | feedback, corpus, hypotheses, benchmarks, evals | automatic promotion |
| **Validated output** | Mint | result that satisfied the active gate | implicit settlement |

## 🪄 System view

```mermaid
flowchart TB
    subgraph PROJECT[Project Boundary]
        P[Novel Project]
        SDK[Project SDK / Adapter]
        CTX[Context Manifest]
    end

    subgraph RUNTIME[Harness Runtime]
        H[Harness Manager]
        SES[Session Runtime]
        CP[Control Plane]
        WORK[Bounded Workers]
    end

    subgraph CORE[Fiction Core]
        STORY[Story / Character / Canon]
        SIM[Scene + Character Simulation]
        WR[Event-first Writer]
    end

    subgraph QUALITY[Quality Runtime]
        SF[Surface Fundamentals]
        RG[Reader Engagement]
        SEM[Independent Semantic Review]
        CONT[Continuity / State Audit]
        G[User-visible Gate]
    end

    subgraph EVIDENCE[Learning & Evidence]
        FB[User Feedback]
        LS[Learning Store]
        CG[Corpus Gaps]
        CR[Rights / Provenance]
        BENCH[Benchmarks / Evals]
    end

    P --> SDK --> H
    H --> CTX --> STORY
    H --> SES --> CP
    H --> WORK
    STORY --> SIM --> WR --> SF --> RG --> SEM --> CONT --> G

    FB -. evidence .-> LS
    LS --> CG --> CR --> BENCH
    BENCH -. quality evidence .-> SF
    BENCH -. reader evidence .-> RG
    CP -. resume / result bind .-> H
    WORK -. typed result .-> H

    classDef project fill:#DDF2FF,stroke:#5B98C4,color:#2B2433,stroke-width:1.5px;
    classDef runtime fill:#E8DDFB,stroke:#8B7AC6,color:#2B2433,stroke-width:1.5px;
    classDef story fill:#FFFDFB,stroke:#796D84,color:#2B2433,stroke-width:1.5px;
    classDef quality fill:#FAD7E8,stroke:#D982A8,color:#2B2433,stroke-width:1.5px;
    classDef evidence fill:#FFF0C7,stroke:#C9973B,color:#2B2433,stroke-width:1.5px;
    classDef gate fill:#D9F5E5,stroke:#58A98C,color:#2B2433,stroke-width:1.5px;

    class P,SDK,CTX project;
    class H,SES,CP,WORK,SEM runtime;
    class STORY,SIM,WR story;
    class SF,RG,CONT quality;
    class FB,LS,CG,CR,BENCH evidence;
    class G gate;
```

**Solid lines** are primary execution/dependency paths. **Dashed lines** are feedback, evidence, resume, or typed-result flows. A dashed edge is still an explicit data path; it never implies authority silently crossing domains.

## 📚 Architectural domains

| Domain | Owns | Boundary |
|---|---|---|
| **Generic Fiction Core** | story hierarchy, Character/Relationship behavior, information boundaries, Canon lifecycle, dependencies, settlement, continuity | owns generic mechanism only, never consumer story facts |
| **Quality Runtime** | Surface Fundamentals, Reader Engagement, quality failure routing | profiles may tune weights/thresholds but cannot silently delete fundamentals |
| **Harness Runtime** | task modes, sparse context, checkpoints, bounded specialists, semantic routing, user-visible gates | manager coordination ≠ independent judgment |
| **Durable Runtime State** | sessions, events, handoffs, leases, result receipts | persistence never upgrades into Canon |
| **Adaptive Learning** | evidence, preference hypotheses, contradictions, promotion candidates, rollback | model inference alone cannot durably promote behavior |
| **Corpus Intelligence** | discovery gaps, rights/provenance, mechanism observations, counterexamples, benchmarks | corpus ≠ Canon; modern copyrighted text is not mirrored by default |
| **Project Engineering** | manifests, lockfiles, adapters, authority/state, plans, tests, migrations, builds | project facts must not leak back into Generic Framework source |

## 🧠 Three persistent state domains

```mermaid
flowchart LR
    R[Runtime State<br/>sessions · checkpoints · handoffs]
    L[Learning State<br/>evidence · hypotheses · corpus gaps]
    C[Project State<br/>Canon · current state · plans · research]

    R -. explicit ID / provenance .-> L
    L -. explicit evidence ref .-> C
    C -. task-scoped context ref .-> R

    classDef runtime fill:#E8DDFB,stroke:#8B7AC6,color:#2B2433,stroke-width:1.5px;
    classDef evidence fill:#FFF0C7,stroke:#C9973B,color:#2B2433,stroke-width:1.5px;
    classDef project fill:#DDF2FF,stroke:#5B98C4,color:#2B2433,stroke-width:1.5px;

    class R runtime;
    class L evidence;
    class C project;
```

> **Boundary 🌸** The three domains may reference each other through explicit IDs, evidence, and provenance, but **authority never flows implicitly**. A session remembering something does not make it accepted story truth; a corpus fact does not automatically become character knowledge.

## 🔒 Dependency direction

```text
Novel Project → NovelForge Framework
NovelForge Framework -X→ consumer-specific project facts
```

The Framework owns **schema / mechanism**. The Project owns **instance / fact**. A Project may pin an exact Framework commit; the Framework may not import that novel's Canon back into Generic source.

## 🧩 Context philosophy

**Complete schema, sparse injection.** Storage is not the prompt.

```mermaid
flowchart LR
    S[Full Project Storage] --> M[Task-scoped Context Manifest]
    M --> I[Model / Worker Invocation]
    I --> R[Typed Result]
    R -. validated reference only .-> S

    classDef project fill:#DDF2FF,stroke:#5B98C4,color:#2B2433,stroke-width:1.5px;
    classDef runtime fill:#E8DDFB,stroke:#8B7AC6,color:#2B2433,stroke-width:1.5px;
    classDef gate fill:#D9F5E5,stroke:#58A98C,color:#2B2433,stroke-width:1.5px;

    class S,M project;
    class I runtime;
    class R gate;
```

The Context Broker selects only the project-state slice and Framework rules relevant to the active task. Presence in storage does not imply prompt inclusion, and workers do not inherit the manager's whole conversation by default.

## ⚙️ Deterministic vs semantic split

| Prefer deterministic code for | Use semantic workers for |
|---|---|
| identity / lifecycle | prose quality judgment |
| schema validation | reader engagement judgment |
| fingerprint / result binding | nuanced character / scene evaluation |
| permission / authority preconditions | corpus mechanism interpretation |
| idempotency / leases / consume-once | preference / craft distillation |
| arithmetic / dependency integrity | judgment that cannot reasonably collapse into rules |
| build / release invariants | independent-review verdicts |

**Rule:** if an invariant can be expressed precisely and deterministically, do not spend model judgment on it. If a literary judgment cannot be reduced to deterministic rules, do not pretend a Python check can validate it.

## 🚢 Release philosophy

A Framework release is valid only when all of the following hold:

- machine contracts and schemas are coherent;
- bilingual human docs are paired;
- the project-agnostic boundary remains clean;
- deterministic self-tests and integration contracts pass;
- semantic baselines remain real typed results rather than CI-faked PASS states;
- visual documentation improves understanding without becoming a second authority.

<p align="center"><sub>architecture should feel calm even when the system behind it is complicated ✦</sub></p>

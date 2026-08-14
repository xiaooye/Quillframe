<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Architecture · 架构总览</strong></p>
  <p><kbd>AUTHORITY</kbd>&nbsp;&nbsp;<kbd>RUNTIME</kbd>&nbsp;&nbsp;<kbd>QUALITY</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge Architecture · 架构总览

> ✦ **核心思想：把 fiction production 拆成明确的 authority、runtime、quality 与 evidence domain，再通过 typed boundary 协作。**
>
> 视觉遵循 [Story Loom Design System](../assets/DESIGN_SYSTEM.zh-CN.md)。Mermaid 是可维护的 source chart；未来 static rendered chart 只做 presentation layer。

---

## 01 · Reading Key 🌸

| Lane | Token | 负责什么 | 永远不代表什么 |
|---|---|---|---|
| **Project / Context** | `project` · sky | consumer project、adapter、context selection | Framework generic truth |
| **Harness Runtime** | `runtime` · lavender | session、checkpoint、handoff、worker、control plane | Canon |
| **Story Core** | `neutral` · ink | Story、Character、Canon mechanics、simulation、draft | 自动 Accepted |
| **Editorial Quality** | `editorial` · sakura | Surface、Reader Engagement、semantic review | Canon authority |
| **Learning / Evidence** | `evidence` · amber | feedback、corpus、hypothesis、benchmark、eval | 自动 promotion |
| **Validated Output** | `validated` · mint | gate 已满足的可见结果 | 隐式 settlement |

**Shape grammar：** stadium = boundary；hexagon = manager/gate；database = durable store；subroutine = reusable core mechanism。

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

    subgraph FORGE["02  ·  FORGE RUNTIME"]
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
    CP -. resume / result bind .-> H
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

**实线** = execution / dependency；**虚线** = feedback / evidence / resume / typed result。虚线仍是显式数据流，**不代表 authority 自动跨域传播**。

---

## 03 · Architecture Domains 📚

| Domain | Owns | Boundary |
|---|---|---|
| **Generic Fiction Core** | Story hierarchy、Character/Relationship、information boundary、Canon lifecycle、dependency、settlement、continuity | generic mechanism ≠ consumer story fact |
| **Quality Runtime** | Surface Fundamentals、Reader Engagement、failure routing | Profile 可调权重，不能删除 fundamental mechanism |
| **Harness Runtime** | task mode、sparse context、checkpoint、specialist、semantic routing、user-visible gate | manager coordination ≠ independent judgment |
| **Durable Runtime State** | session/event/handoff/lease/result receipt | runtime persistence ≠ Canon |
| **Adaptive Learning** | evidence、hypothesis、contradiction、promotion candidate、rollback | model inference alone ≠ durable promotion |
| **Corpus Intelligence** | discovery、rights/provenance、mechanism observation、counterexample、benchmark | corpus ≠ Canon |
| **Project Engineering** | manifest、lockfile、adapter、state、plans、tests、migration、build | Project fact 不回流 Generic Framework |

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

## 04 · Three Persistent State Domains 🧠

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#FFFDFC","primaryTextColor":"#241D2B","lineColor":"#756A7D","fontFamily":"ui-sans-serif, system-ui, sans-serif"},"flowchart":{"curve":"basis"}}}%%
flowchart LR
    R[(Runtime State<br/>sessions · checkpoints · handoffs)]
    L[(Learning State<br/>evidence · hypotheses · corpus gaps)]
    C[(Project State<br/>Canon · current state · plans · research)]

    R -. explicit ID / provenance .-> L
    L -. explicit evidence ref .-> C
    C -. task-scoped context ref .-> R

    classDef runtime fill:#E7E1F8,stroke:#796BC4,color:#241D2B,stroke-width:1.75px;
    classDef evidence fill:#F9EDCF,stroke:#BE892F,color:#241D2B,stroke-width:1.75px;
    classDef project fill:#DDEFF8,stroke:#4F8FBA,color:#241D2B,stroke-width:1.75px;

    class R runtime;
    class L evidence;
    class C project;
```

> **Boundary ✦** 三个状态域可以通过 explicit ID / evidence / provenance 互相引用，但 **authority 绝不隐式流动**。Session 记住一件事，不等于项目接受它；Corpus 找到一条事实，也不等于角色知道它。

---

## 05 · Dependency Direction 🔒

```text
Novel Project → NovelForge Framework
NovelForge Framework -X→ consumer-specific project facts
```

Framework 拥有 **schema / mechanism**；Project 拥有 **instance / fact**。Project 可以 pin exact Framework commit；Framework 不能反向 import 某本小说的 Canon。

---

## 06 · Context Philosophy 🧩

**完整 Schema，稀疏注入。Storage 不是 prompt。**

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

Context Broker 只选择当前任务真正需要的 project state slice + framework rules。Storage 里“有”不等于自动进入 model context；worker 也不会继承 manager 整段聊天。

---

## 07 · Deterministic vs Semantic Split ⚙️

| Deterministic code 优先负责 | Semantic worker 负责 |
|---|---|
| identity / lifecycle | prose quality judgment |
| schema validation | reader engagement judgment |
| fingerprint / result binding | nuanced character / scene evaluation |
| permission / authority precondition | corpus mechanism interpretation |
| idempotency / lease / consume-once | preference / craft distillation |
| arithmetic / dependency integrity | 不适合压缩成规则的语义判断 |
| build / release invariant | independent review verdict |

**原则：** 能被 deterministic invariant 精确表达的，不浪费 model judgment；无法被规则替代的语义问题，也不假装 Python 能“验证文学质量”。

---

## 08 · Rendered Diagram Contract 🎨

未来 AI / designer-rendered chart 采用：

```text
Mermaid source → semantic reference → branded SVG/WebP → README presentation
```

Rendered chart 不能新增 source 中不存在的语义；architecture 变更先改 Mermaid，再 regenerate static visual；static visual 必须有 alt text + provenance。

---

## 09 · Release Philosophy 🚢

Framework release 只有在以下层面都成立时才有效：

- machine contract / schema 一致；
- 双语 human docs 配对；
- project-agnostic boundary 未泄漏；
- deterministic self-tests / integration contracts 通过；
- semantic baseline 保持真实 typed result，不由 CI 伪造 PASS；
- visual documentation 只改善理解，不变成第二 authority。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <br />
  <sub>calm architecture · explicit authority · one woven story thread ✦</sub>
</div>

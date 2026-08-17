# Quillframe

**一个面向长篇小说的生产框架：让模型判断意义，让显式系统守住故事事实与执行真相。**

<img src="docs/assets/brand/quillframe-mark.svg" alt="Quillframe 标记：一页手稿被一条叙事线穿过" width="92" />

Quillframe 面向的是会持续数十章、跨多个会话、经历多轮修改与审查的小说工程。它把连续性、权威、修订、评审、学习与恢复当成真正的生产问题，同时不让确定性代码伪装成文学判断者。

<img src="docs/assets/architecture/framework-mental-model.zh-CN.svg" alt="Quillframe 心智模型：Project 权威进入 manager，经稀疏执行与验证后，只有获得显式授权才进入 Settlement" width="100%" />

## 为什么需要它

长篇写作会累积不同性质的“真相”。Plan 是未来意图；Review Draft 是候选稿；Accepted 是明确编辑决定；Settled 才是这个决定已经转化成持久状态的结果。Research、Corpus、telemetry、learning hypothesis 与 runtime receipt 都可以是证据，却不会因为系统看见了就自动成为故事事实。

Quillframe 的核心工作，是把这些类别分开，再通过明确契约让它们协作。

## 核心架构

**Project authority 拥有故事事实。** `locked`、`accepted`、`active_plan`、`review`、`proposal` 保持不同层级。Plan != Canon；Review != Accepted；Accepted != Settled。

**模型负责语义判断。** 故事解释、人物可信度、Reader 反应、repair diagnosis、相关性、候选比较与 learning interpretation 都通过受限的 model-readable contract 完成。

**确定性代码负责执行真相。** Identity、permission、fingerprint、provenance、persistence、consume-once、hard budget、routing、transaction 与 fail-closed state transition 可以机械验证。

**Independent review 必须真的独立。** 一旦 gate 要求 independence，reviewer 必须来自真正不同的 invocation/session，并绑定 exact candidate fingerprint。

## 正文是一张生产图

章节不会从 prompt 直接跳到发布。系统先稀疏选择 Context，模拟 Story / Character / Reader Pressure，生成内部候选，再收集质量证据，把缺陷送回真正 owning mechanism；只有完成 pre-independent qualification 的候选才进入独立评审与 user-visible gate。

修复遵守 **FIX + PRESERVE**：修掉目标缺陷，同时保住 objective envelope、reader value 与 character/relationship energy。Fresh regeneration 可以挑战 incumbent，但不得假装继承了被拒绝的 prose。Candidate Lineage 分开记录 comparison ancestry 与 prose derivation，避免两种“父级”语义混在一起。

## 快速开始

```bash
python project_sdk.py init <path> --id PROJECT-X --title "Novel"
python project_sdk.py validate <path>
python project_sdk.py build <path>
```

生产 Project 为了 runtime 可复现性会锁定 exact framework revision；而 Framework 开发文档以当前 `main` 为目标。两者是不同事实，不互相覆盖。

## 关键概念

- [总体架构](docs/architecture.zh-CN.md)：authority、semantic execution、deterministic runtime 与 settlement。
- [生产流水线](docs/production-pipeline.zh-CN.md)：从 sparse context 到 user-visible gate。
- [质量保障](docs/quality-assurance.zh-CN.md)：pre-independent qualification、FIX + PRESERVE、fingerprint binding 与 release truth。
- [Candidate Lineage](docs/CANDIDATE_LINEAGE_V1.zh-CN.md)：comparison parent、prose parent、review receipt 与无权威的 acceptance evidence。
- [上下文与记忆](docs/context-and-memory.zh-CN.md)：让 Context 稀疏可控，而不是让 memory 偷偷变成 Canon。
- [自适应学习](docs/adaptive-learning.zh-CN.md)：自动 capture，受治理 promotion。
- [运行时与集成](docs/integrations.zh-CN.md)：session、run、checkpoint、capability 与 independent execution。
- [Project SDK](docs/project-sdk.zh-CN.md)：Project / Framework 边界。

## 兼容性说明

**Quillframe 是当前 public brand；`NovelForge` 继续作为 legacy technical namespace 保留。** `novelforge.toml`、`novelforge.lock.json`、`novelforge_*` schema、既有 workflow 名、repository path 与 stable contract ID 本次都不改名。

Framework 当前处于 pre-1.0 的 `0.8.0` 开发线。开发期的当前实现真相来自本次冻结的 exact `main` commit，而不是旧文档叙述。

[文档中心](docs/README.zh-CN.md) · [English](README.en.md)

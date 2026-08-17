# 总体架构

理解 Quillframe 最简单的方法，是把它看成三块协作平面：Orchestration 决定当前应执行什么 bounded work；Execution + Verification 产出并判断 exact artifact；Settlement 则是 Accepted evidence 变成 durable story state 的唯一授权通道。

<img src="assets/architecture/framework-mental-model.zh-CN.svg" alt="Quillframe 三平面架构：Orchestration、Execution + Verification、授权 Settlement" width="100%" />

## Project authority 在 Generic Framework 之外

Generic Framework 拥有 Story/Character/Canon mechanics、质量机制、session/runtime contract、semantic execution、learning infrastructure、Corpus governance、eval 与 Project SDK。下游 Project 拥有具体人物、剧情、关系、research、plan、manuscript、Accepted Canon 与 current state。

<img src="assets/architecture/framework-vs-project.zh-CN.svg" alt="Generic Framework 通用机制与 Project 专属故事事实保持分离" width="100%" />

依赖方向只有 Project → Framework。某条 Project 内容即使参加过 run，也不会因此成为 Generic Framework truth。

## Semantic intelligence 与 deterministic execution

Semantic contract 打包 bounded context、rubric、permission、output shape、subject identity 与 semantic fingerprint。模型负责 interpretation；deterministic runtime 负责验证 exact contract identity、provenance、fingerprint binding、permission、typed result 与 consume-once。

Telemetry 可以描述可观察形式，但不能冒充 semantic judgment；manager self-review 可以形成 non-independent evidence，却不能满足 independent gate。

## Authority Ladder

<img src="assets/concepts/authority-ladder.zh-CN.svg" alt="Authority ladder：locked、accepted、active plan、review、proposal；Settlement 与 Acceptance 分离" width="100%" />

`locked > accepted > active_plan > review > proposal` 表达 lifecycle 区分，并不表示 artifact 可以自行向上升级。Plan 是 future intent；Review 是 candidate；Acceptance 是明确 evidence；Settlement 是另一个授权 transaction。

Corpus != Canon；Research != automatic Character Knowledge；Session state != Story state；Learning state != Editorial authority。

## Sparse Context

持久存储永远大于一次 model invocation。Manager 先针对当前 semantic question 选择 sparse Context Manifest；deterministic assembly 再验证 exact refs、authority class、stage isolation、provenance、fingerprint 与 hard budget。

<img src="assets/concepts/sparse-context-manifest.zh-CN.svg" alt="Sparse Context Manifest 只选择当前任务相关的 Project、人物、状态、Research 与 benchmark 引用" width="100%" />

## Session 与 External Work

Quillframe 分开 `project/resource`、`session/thread`、`run/invocation`、`checkpoint`。Checkpoint 只记录 execution position 与 exact artifact，不会把 Plan/Review 提升为 Canon。Resume 必须重核 live authority、artifact fingerprint、pending approval、capability 与 consume-once state。

## Settlement

<img src="assets/concepts/settlement.zh-CN.svg" alt="Settlement transaction：从 explicit acceptance，经 exact state delta 与 before-state validation，到 authorized write、projection、post-condition" width="100%" />

Settlement 要求 explicit acceptance / Canon intent、exact before→after state ops、dependency impact、checkpoint/write intent、live before-state validation、authorized write、required derived projection 与 post-condition。Before-state mismatch 或 required projection failure 必须返回 `settlement_incomplete`，不能猜测式“部分成功”。

Implementation owner 见[架构图谱](architecture-atlas.zh-CN.md)。

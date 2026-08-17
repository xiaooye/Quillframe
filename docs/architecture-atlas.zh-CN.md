# 架构图谱

这份 Quillframe 架构图谱只把概念映射到当前实际实现，不再重复一遍完整生产流水线。

## 故事与事实权威

- `core/STORY_SYSTEM.*`：通用故事机制。
- `core/CHARACTER_SYSTEM.*`：人物与关系机制。
- `core/CANON_STATE.*`：正典权威与状态边界。
- `harness/settlement_runtime.py`：经授权的状态落定事务。

## 上下文与记忆

- `harness/context_inspector.py`：机械可判定的上下文资格与受保护状态检查。
- `harness/context_assembly.py`：语义选择完成后，验证精确选择集合、接收阶段、权威级别、来源链和内容指纹。
- `harness/memory_tiers.py`、`harness/memory_bank.py`：控制派生记忆，但不获得修改正典的权限。

## 语义执行

- `harness/semantic_workers/model_contract_catalog.json`：语义契约索引。
- `harness/semantic_workers/contracts/`：按需展开的契约包。
- `semantic_worker_router.py`：精确任务打包与校验。
- `semantic_worker_runner.py` 与各适配器：选择具备所需能力的执行通道。

## 质量

- `quality/candidate_qualification.py`：独立评审前的候选稿资格检查。
- `quality/objective_envelope.py`：带指纹的“修复且保持”目标约束集。
- `quality/quality_evolution.py`：基准稿与挑战稿的比较账本；语义上的胜者仍由 `quality.compare` 判断。
- `quality/repair_objective_regression.py`：观察修订引发的目标回退。
- `quality/regression_escape.py`：记录已知回退规则漏检的情况。
- `quality/candidate_lineage.py`：比较谱系、文本派生、精确评审回执绑定，以及不具权威性的接受证据。
- `quality/candidate_lineage_runtime.py`：谱系感知且失败即阻断的运行时外观层。
- `quality/production_readiness.py`、`quality/production_release.py`：发布角色与准备状态的不变量。

<img src="assets/concepts/objective-preserving-repair.zh-CN.svg" alt="修复且保持：修复局部缺陷，同时保持目标约束集完整" width="100%" />

## 会话与控制平面

- `harness/session_runtime/`：会话、运行、检查点身份，恢复预检以及经授权的运行时命令。
- `harness/control_plane/`：持久事件、交接、回执和外部工作生命周期。
- `harness/runtime_capabilities.py`：当前宿主环境的能力证据。

## 学习与语料库

- `learning/feedback_intake.py`：自动且受限的用户反馈捕获。
- `learning/author_model.py`、`learning/learning_store.py`：持久保存证据与假设状态。
- `learning/promotion_gate.py`：长期规则提升的确定性前置条件，但不授予写入权限。
- `corpus/`：资料发现、使用权、来源链与写作机制证据。

## 项目工程

- `project_sdk.py`、`project_adapter.py`：独立项目契约与旧目录布局映射。
- `release/build_framework_bundle.py`：可复现的确定性框架构建包。

面向使用者的心智模型见[总体架构](architecture.zh-CN.md)。

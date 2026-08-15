# Resume Preflight · 在开放运行时控制前证明“可恢复”

<p><kbd>RUNTIME SAFETY</kbd>&nbsp;&nbsp;<kbd>READ ONLY</kbd>&nbsp;&nbsp;<kbd>FAIL CLOSED</kbd></p>

Resume 不是一次普通的页面跳转，而是针对持久化状态重新执行的一次验证。

`resume_preflight.py` 只判断一个**既有 Session + 最新 Checkpoint**，在当前环境下是否已经具备足够证据，能够进入未来的 typed resume command。Preflight 本身不会修改 Runtime，不会运行模型，不会写 Canon / Framework，不会执行 Settlement，不会创建新 Run、消费 Result，也不会 Replay 或 Fork。

## Contract

成功的 Preflight 返回：

```text
novelforge_session_resume_preflight_v1
status = READY
ready = true
mutation_performed = false
authority = false
```

任何缺失或过期的绑定都会返回 `BLOCKED`，并提供确定性的 `checks` 与 `blockers`。

`READY` 只表示：**具备进入另一个、仍需单独授权的 Resume Command 的资格**。它不代表 Resume 已获批准，更不代表已经执行。

## 会重新验证什么

第一版只验证它能够确定性证明的证据：

- durable runtime store 与 Session 确实存在；
- 调用方提供的 expected session version 与 Control Plane 中的 durable version 一致（CAS precondition）；
- Session identity 与 lifecycle status 允许恢复；
- `resume_policy` 不是 `forbidden`；
- `same_session` 确实存在 provider / external binding，但不会把私有 identifier 暴露出去；
- Checkpoint 存在，并且普通 Resume 只能使用最新 Checkpoint；
- Checkpoint 与 Session 的 resume policy 一致；
- 不会静默跨过尚未解决的 Gate 或 Handoff；
- 当前 `novelforge.lock.json` 的 Framework version / exact commit / bundle fingerprint 与冻结的 authority evidence 一致；
- `framework.attestation.json` 与当前 lock 一致；
- Project identity 仍与 durable Session 一致；
- Checkpoint 中的 artifact fingerprint 能通过 Project-relative artifact binding 重新计算并验证；
- 声明为 required 的 capability 在传入的 capability evidence 中存在；
- approval reference 的结构有效；
- 整个检查过程没有修改 runtime store。

## 普通 Resume 只允许最新 Checkpoint

从更早的 Checkpoint 开始不是 Resume，而是 **time travel**。它必须使用未来独立的 Replay / Fork Contract。

边界必须保持明确：

```text
resume latest durable cursor
!= replay prior execution
!= fork alternative state
```

## Authority Evidence

Preflight 接收 `novelforge_resume_authority_evidence_v1`，用于保存要与当前状态比较的冻结身份：

- `project_id`；
- Framework `version`、exact `commit`、`bundle_fingerprint`；
- Project-relative artifact binding 与 fingerprint；
- required / available capability identifier；
- 必要时的 approval reference。

这些 evidence **不会授予 authority**，它们只是确定性比较的输入。

Artifact path 禁止使用绝对路径，并且必须保持在 Project root 内。

## Failure Semantics

代表性的 blocker 包括：

- `session_version_mismatch`；
- `session_status_not_resumable`；
- `resume_policy_forbidden`；
- `checkpoint_not_latest_use_replay_contract`；
- `pending_gate_requires_fresh_validation`；
- `pending_handoff_requires_binding`；
- `framework_attestation_mismatch`；
- `framework_identity_changed_or_unproven`；
- `checkpoint_artifact_fingerprint_unverified`；
- `required_capability_unavailable`。

任何 blocker 都必须阻断未来 Resume routing，直到新的证据明确解决它。Runtime 不得从 provider conversation memory 或日志里“猜回”缺失事实。

## 为什么先做 Preflight，再开放 Resume Control

主流 Agent Framework 的 Checkpoint 机制让 interrupt、replay 与 time travel 很实用，但 NovelForge 还存在 Project / Framework authority、exact lock identity、independent gate 与 consequential Settlement 等额外约束。因此，“Checkpoint 已经持久化”本身不足以成为继续执行的 authority。

实现顺序刻意保持为：

```text
observe durable state
→ deterministic resume preflight
→ typed resume command envelope
→ replay/fork contracts later
```

真正的 Resume Command 仍然保持 deferred，直到 command-level idempotency、before-state、capability evidence、approval / authority checks 与 receipt 都有完整契约。

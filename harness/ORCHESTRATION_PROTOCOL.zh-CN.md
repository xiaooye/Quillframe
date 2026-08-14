# NovelForge Orchestration Protocol · v7 中文版

## Common Prefix

```text
读取 framework manifest + skill
→ 验证 consuming project + lockfile
→ 确定 exactly one task_mode
→ 解析/创建 manager session + run
→ 建 sparse Context Manifest
→ 解析 Canon cutoff + permissions
→ 执行 mode graph
```

Resume：

```text
load checkpoint
→ 重核 project/framework compatibility
→ 重核 artifact fingerprints
→ 重核 approvals/write intents
→ pending result bind + consume once
→ 从保存步骤继续
```

## DRAFT / REVISE

```text
Context Freeze
→ Story/Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure Preflight
→ Event-first Raw Draft
→ Surface Realization
→ Surface Lint A
→ freeze candidate
→ post-generation regression / independent semantic review
→ 回 owning layer 修复
→ Surface Lint B
→ Reader Engagement
→ Continuity
→ User-visible Gate
```

Raw Draft freeze 前 Writer 不读取 hidden regression gold。Raw/internal draft 不是可交付 production artifact。

## Semantic Gate Subroutine

```text
freeze semantic payload
→ typed job + fingerprint
→ checkpoint
→ route eligible independent runtime
→ execute | queued handoff | peer relay | await
→ typed result
→ identity/fingerprint/provenance validation
→ named gate consume once
```

Semantic payload 改变 → new fingerprint。Infrastructure retry 可以保持同一 fingerprint。有效 semantic reject 不是 infrastructure failure。

## PLAN / DESIGN

Plan 只生成 `proposal / active_plan`。即使 Harness 把它持久化，也不会修改 current Canon。

采用 rolling elaboration：离生产窗口越近越详细，越远越稀疏。

## RESEARCH

Research 产出 source-bound `REF/CLAIM` 等价 evidence。现实 truth 与 character knowledge 分离。External search capability 不自动授予 project write authority。

## CORPUS-INGEST

```text
learning/craft question
→ discovery request
→ source verification
→ rights gate
→ bounded analysis
→ counterexample search
→ benchmark/eval candidate
```

Corpus output 永远不是 Canon。

## LEARN

```text
feedback/evidence
→ narrowest scope classification
→ preference/craft hypothesis
→ contradiction check
→ corpus/eval gap
→ candidate promotion / rollback
```

重复模型判断不是新证据。

## SETTLE

只有项目明确 acceptance 才允许 Canon settlement。

```text
freeze accepted artifact
→ exact state delta
→ validate before-state
→ dependency impact
→ checkpoint/write intent
→ authorized mutation
→ rebuild derived views
→ post-condition
→ trace/receipt
```

Mismatch → `settlement_incomplete`；不猜、不执行无关部分成功。

## SYSTEM-IMPROVE

Material framework change 必须有 evidence、mechanism、alternatives/conflict review、capability/regression coverage、rollback point、version 与 green deterministic CI。

## Parallelism

可并行 immutable-input research/audit。没有 transaction/version protocol 时，不并发修改同一 shared Canon/state。

## Completion States

`complete | review | awaiting_user | awaiting_external | blocked | failed_gate | semantic_pending | semantic_invalid | settlement_incomplete`

# 上下文与记忆

Persistent storage != model context。Quillframe 先针对当前 semantic question 选择 sparse working set，再验证这组 exact selection 的机械边界。

<img src="assets/concepts/sparse-context-manifest.zh-CN.svg" alt="Sparse Context Manifest 从更大的 Project store 中只选择当前任务真正相关的小集合" width="100%" />

## Sparse Context Manifest

Context Manifest 可以列出当前 book/volume/unit/chapter/scene、实际出场 character/relationship、直接相关 state、claim、dependency、recent Accepted material，以及只与当前 craft problem 相关的 benchmark。它是 selection contract，不是把整个 Novel Bible 或 Corpus 倒进 prompt。

真正需要解释意义时，semantic relevance 由模型判断。Deterministic context code 在 selection 之后验证 exact refs、receiving stage、authority class、provenance、fingerprint、private/hidden restriction、invalidation state 与 hard budget。

## Authority Protection

`locked` / `accepted` reference 继续 protected。编辑 derived memory view 不会覆盖 protected Canon，而是生成 proposal 或其他明确 non-authoritative artifact。Future Plan 结果也不能因为存储位置相邻就泄漏进 current-state field。

## Perspective 与 Knowledge

<img src="assets/concepts/research-corpus-canon.zh-CN.svg" alt="Research、Corpus、Canon 保持不同 evidence 与 authority class" width="100%" />

Research truth != automatic Character Knowledge。Character 只有通过 Project knowledge/state model 与真正发生的 story event，才获得相应知识。Corpus evidence 也不会因为 ingestion 就变成人物记忆。

## Generation Isolation

Regression bad example 与 hidden expected label 不进入 Writer first-pass context。生成后的 Auditor 可以获得额外 authoritative rule / regression material，但不能反向污染已经 freeze 的 candidate。

## Memory Lifecycle

Derived memory 可以在权限范围内 rank、pin、invalidate、rebuild 或 edit；这些操作都不会把 memory promote 成 Canon。Session persistence 也不表示 resume 时应把 provider history 整段重新注入。

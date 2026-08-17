# Candidate Lineage v1

Candidate Lineage 用显式 provenance 解决“一个 parent 字段到底是什么意思”的歧义。它扩展 Quality Evolution，不创建第二套 comparison、acceptance、Canon 或 Settlement authority。

<img src="assets/concepts/candidate-lineage.zh-CN.svg" alt="Candidate Lineage 为 draft、repair、fresh regeneration、user edit 分开 comparison parent 与 prose parent" width="100%" />

## 两种 Parent Relation

**Comparison parent** 回答：这个 challenger 是和哪个 incumbent 比较的？Quality Evolution 现有 parent 继续表示 `quality.compare` 使用的 comparison ancestry。

**Prose parent** 回答：当前 prose 直接由哪份旧 prose 派生？两者必须分开，因为 fresh regeneration 可以和 incumbent 比较，却有意不继承 incumbent prose。

## Origin Rules

`draft` 没有 comparison/prose parent；`repair` 必须有 comparison parent，且 prose parent 必须等于这个 direct parent；`fresh_regeneration` 必须有 comparison parent，但 prose parent 必须为空；`user_edit` 是显式 challenger，derivation 要记录而不是猜。

Runtime facade 在 required lineage 缺失或与 origin 冲突时 fail closed，从不根据 prose similarity 猜 ancestry。

## Exact Review Receipts

Semantic review receipt 把一个 `candidate_id` 与 exact candidate fingerprint 绑定到 contract ID、job fingerprint、result fingerprint、result status。只要 candidate 不同或 fingerprint 已旧，review 就 stale。

## Acceptance Evidence Boundary

Lineage 可以把 opaque external acceptance ref 绑定到 exact candidate fingerprint、authority source ref、authority receipt fingerprint 与 accepted artifact fingerprint，但不会验证 authority source 本身是否真的有权。

所有 view 都保持 `authority=false`；acceptance evidence 明确 `authority_verified=false`、`settlement_authorized=false`。真正的 user/editorial acceptance 必须由 authority/settlement layer 另外验证。

## Compatibility

Schema ID 继续是 `novelforge_candidate_lineage_v1`。这是 legacy technical namespace 下的 stable identifier，不随 Quillframe public brand 改名。

# 规格 · NovelForge 7.1 Adaptive Runtime

## 基线

- 上一版本：NovelForge 7.0.0
- 基线 commit：`de05666cc4eae13f09868d87659e76f2aa524314`
- Rollback：上述基线 commit
- Change class：Framework release / structural feature

## 问题

NovelForge 7.0 已能持久化 preference evidence / hypothesis、生成 Corpus gap、构造 typed discovery request、验证声明的 rights metadata、路由 semantic work、checkpoint 长任务。但这些能力还没有被一个 deterministic、可恢复的 Learning Cycle 串成闭环；Host 的 Web/GitHub/MCP/tool 可用性主要存在于文档与 routing 描述里，而不是 typed capability contract；Project lock 也尚无可独立验证的 immutable bundle fingerprint。

因此仍有三个风险：

1. 模型可能“猜”某个 Web/GitHub/MCP connector 存在，而不是证明 capability；
2. Corpus discovery、source verification、semantic analysis、eval evidence、promotion candidacy 可能退化成松散的临时步骤；
3. Consumer 虽锁 exact commit，却不能独立校验本地 materialized Framework bundle 的内容指纹。

## 目标

### G1 · Typed Host Capability Contract

增加 provider-neutral host capability manifest + deterministic resolver。Capability 只有在显式声明或本地可证明时才能使用。缺失 capability 必须返回真实 pending/blocked route，禁止伪造 tool access。

### G2 · Durable Adaptive Learning Cycle

增加 stdlib-only executable Learning Cycle 状态机，协调：

`evidence/hypothesis → corpus gap → discovery planning → verified discovery results → semantic mechanism analysis → eval evidence → promotion candidate → activation/promotion gate`

Learning Cycle 属于 operational/learning state，永远不是 Canon。

### G3 · Discovery / Provenance Runtime

增加 typed discovery result contract：source locator、retrieval channel、tool/provider provenance、retrieval timestamp、evidence fingerprint、declared rights basis、storage intent、dedupe/diversity accounting。

Discovery 与 Ingestion 严格分离。Deterministic code 不得根据 URL/title 推断版权状态。

### G4 · Analysis + Eval Work Packaging

为 Corpus mechanism analysis 与 learning eval 创建 bounded、fingerprint-bound semantic jobs。默认不携带 hidden gold、writer private reasoning、与研究问题无关的用户私有信息或整部现代版权正文。

### G5 · Promotion Gate

增加 deterministic gate，可输出 `blocked | ready_for_activation | promotable`，但不能自行修改 Framework behavior 或 durable user taste。

General Craft 必须具备 provenance、counterexample/profile boundary、cross-work evidence、capability + regression eval evidence、target version、rollback ref、green deterministic CI。

### G6 · Immutable Framework Bundle

增加 deterministic bundle build + verify。Bundle 内容排序、metadata 归一化；生成的 bundle metadata 不参与自身 fingerprint。输出 content manifest + SHA-256 bundle fingerprint，Consumer 可写入 `novelforge.lock.json`。

### G7 · Release-grade Automation

Normal CI 与 scheduled maintenance 继续禁止模型调用。Weekly maintenance 可以推进 deterministic cycle planning 并生成 typed work queue，但不能声称已经执行不存在的 Web/model tool，也不能 auto-promote Framework behavior。

Live semantic/provider execution 继续保持显式触发、单独计费/usage。

### G8 · Consumer Upgrade Contract

Project SDK/Adapter validation 支持 NovelForge 7.1 lock 与 bundle fingerprint verification。只有最终 7.1 Framework commit CI 绿、deterministic bundle fingerprint 已知后，才升级 Chinatown consumer。

## 非目标

- Generic Framework 不得吸收 consumer novel Canon、人物、剧情、private project state 或 private user taste。
- 不自动 Canon write / SETTLE / 下一章 drafting。
- Candidate 即使 promotable，也不自动修改 General Craft source。
- Normal CI / weekly maintenance 不隐藏消耗 API/Codex/Claude/model usage。
- 不 mass-mirror 现代版权全文。
- 不建立 named-author imitation profile。
- 不要求所有 host 都具备 Web、GitHub、MCP、provider API、Codex 或 Claude。

## Runtime Contract

### Host capability manifest

至少记录：
- schema/version；
- host identity/runtime class；
- capability availability + provenance + permission scope；
- cost/usage class；
- 是否需要 user interaction；
- 是否会执行 model inference；
- credential secret 永远不写入 manifest。

### Learning-cycle identity

`learning_cycle_id != runtime session_id != semantic job_id != project Canon state`。

Cycle 必须记录每个 discovery/analysis/eval result 的 exact ref/fingerprint，并对 logical result consume-once。

### Discovery result

每个 source candidate 必须记录来源 channel 与 tool/provider。Unknown / analysis-only rights 不允许保存 full text。

### Semantic analysis

Corpus analysis job 只携带 research question 与被允许的 bounded evidence。Result 返回 typed mechanism observation、counterexample、applicability boundary、evidence refs、confidence。

### Promotion

Deterministic gate 只检查 evidence completeness；真正的 behavior-source mutation 由 manager/human/authorized Framework workflow 执行。

## Acceptance Criteria

1. `runtime_capabilities.py self-test` 证明 undeclared capability 永不被选中。
2. `learning_cycle.py self-test` 证明合法 transition、resume/idempotency、result consume-once、无 Canon authority。
3. `discovery_runtime.py self-test` 证明 provenance binding、dedupe/diversity、rights-gate enforcement。
4. `learning_eval.py self-test` 证明 blind fingerprinted analysis/eval packaging 且无 answer-key leakage。
5. `promotion_gate.py self-test` 证明 General Craft 缺 counterexample/cross-work/eval/rollback/CI 任一项都不能通过。
6. `build_framework_bundle.py self-test` 证明 deterministic bytes/fingerprint，篡改后 verify 必须失败。
7. 顶层 `novelforge.py self-test` 覆盖全部 7.1 modules。
8. Normal CI 编译/测试 7.1 全模块且 `model_execution=false`。
9. Weekly maintenance 只生成 capability-aware queue，不伪造 Web/model execution。
10. 中英双语 human-facing docs 同步。
11. `HARNESS_MANIFEST.yaml`、`SKILL*`、README/CHANGELOG、Project SDK 全部报告 7.1.0。
12. 最终 NovelForge CI green。
13. Chinatown project lock 升级到 exact green commit + deterministic bundle fingerprint，Project CI green。
14. Chinatown Canon / active story state 在工程迁移中保持不变。

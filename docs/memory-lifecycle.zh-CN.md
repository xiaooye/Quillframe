# Memory Lifecycle · 保留证据，退役派生视图

NovelForge 把 durable memory 视为**source-bound、non-authoritative 的工作层**，而不是 shadow Canon。某条记忆是否过时、矛盾、应该被替代，属于模型 / manager 的语义判断；deterministic runtime 只拥有 lifecycle transition、before-state binding、provenance、persistence 与 idempotency。

## 为什么需要这一层

长时运行 agent 的确能从 consolidation / reflective retrieval 获益，但持续由模型反复重写 consolidated memory 也可能损坏原本有效的信息。因此 NovelForge 采用非破坏性策略：

```text
source evidence
→ derived memory
→ active
→ contested（新 evidence 要求重新判断）
→ superseded（新的 derived memory 取代其 context eligibility）
```

Lifecycle 操作永远不会覆盖或删除原 derived entry。原始 content、source refs、source fingerprints 与 content fingerprint 都继续保留，可供审计和 rebuild。

## Ownership boundary

`harness/memory_lifecycle.py` **不负责**判断：

- 两条 memory 在语义上是否矛盾；
- 新 summary 是否更好；
- 当前写作任务究竟需要哪条 memory；
- 模型生成的 consolidation 是否正确；
- Project Canon 应如何改变。

这些仍属于 semantic judgment 或 Project authority。

Runtime 只接受显式 lifecycle operation，并验证：

- target 必须是 `derived` memory；
- expected content fingerprint 仍匹配；
- expected lifecycle status 仍匹配；
- supersession 必须发生在同一个 memory bank；
- 至少提供一条 evidence ref；
- 通过 content-addressed operation ledger 保证 retry idempotency。

## Contest

当新 evidence 要求重新判断已有 derived memory 时，`contest` 会把它隔离：

```bash
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db contest \
  --entry-id DER-17 \
  --expected-fingerprint sha256:... \
  --evidence-ref accepted:CH-22
```

entry status 变为 `contested`。现有 `memory_bank.export_context()` 只输出 `active` / `proposal`，因此 contested memory 会退出正常 working context，但不会被销毁。

## Supersede

`supersede` 把新的 active derived entry 与旧的 active/contested entry 绑定，并让 predecessor 退出 context eligibility：

```bash
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db supersede \
  --successor-entry-id DER-18 \
  --predecessor-entry-id DER-17 \
  --expected-successor-fingerprint sha256:... \
  --expected-predecessor-fingerprint sha256:... \
  --expected-predecessor-status contested \
  --evidence-ref accepted:CH-22
```

两条 memory 都继续保存在库中。predecessor 变为 `superseded`，successor 保持 `active`；operation ledger 保存双方 fingerprint 与 evidence refs。

若一次 consolidation 来自多条旧 derived memory，先建立一条新的 source-bound derived entry，再逐条显式 supersede predecessor。这里故意不存在“自动重写整个 memory bank”的操作。

## Protected authority

`locked` / `accepted` memory reference 不能通过该 runtime 被 contest 或 supersede。Project truth 仍只能经 Project acceptance / Settlement 改变。Lifecycle operation 始终：

```text
authority = false
canon_write = false
model_execution = false
```

## Retry 与审计

每次操作都根据完整绑定 payload 生成 deterministic `MEMOP-*` identity。完全相同的操作重复执行属于安全的 idempotent retry；evidence、fingerprint 或参与 entry 任一变化都会得到新的 operation identity，并重新经过 before-state 检查。

查看 ledger：

```bash
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db operations
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db operations --entry-id DER-17
```

这个 ledger 是 operational provenance，不是 semantic verdict，也不是 Canon。

## 设计原则

> 保留 raw/source evidence。Consolidation 只是 proposal。Supersession 改变 context eligibility，不改写历史。

# Memory Lifecycle · Preserve Evidence, Retire Derived Views

NovelForge treats durable memory as a **source-bound, non-authoritative working layer**, not as shadow Canon. Semantic judgment about whether a memory is stale or contradicted belongs to the model/manager. Deterministic runtime owns only the lifecycle transition, before-state binding, provenance, persistence, and idempotency.

## Why this exists

Long-running agents benefit from consolidation and reflective retrieval, but repeated model-driven rewriting can also degrade useful memory. NovelForge therefore uses a non-destructive policy:

```text
source evidence
→ derived memory
→ active
→ contested (explicit evidence says re-check it)
→ superseded (a new derived memory replaces its context eligibility)
```

The original derived entry is never overwritten or deleted by these lifecycle operations. Its content, source references, source fingerprints, and content fingerprint remain available for audit or rebuild.

## Ownership boundary

`harness/memory_lifecycle.py` does **not** decide:

- whether two memories semantically contradict;
- whether a new summary is better;
- what is relevant to a current writing task;
- whether a model-generated consolidation is true;
- what Project Canon should become.

Those remain semantic or Project-authority questions.

The runtime only accepts an explicit operation and verifies:

- the target is `derived` memory;
- expected content fingerprints still match;
- expected lifecycle status still matches;
- supersession stays inside one memory bank;
- at least one evidence reference is supplied;
- retries are idempotent through a content-addressed operation ledger.

## Contest

`contest` quarantines active derived memory when new evidence requires re-evaluation.

```bash
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db contest \
  --entry-id DER-17 \
  --expected-fingerprint sha256:... \
  --evidence-ref accepted:CH-22
```

The entry status becomes `contested`. Existing `memory_bank.export_context()` only exports `active`/`proposal` entries, so contested memory stops entering normal working context without being destroyed.

## Supersede

`supersede` binds a new active derived entry to an older active/contested entry and retires the predecessor from context eligibility.

```bash
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db supersede \
  --successor-entry-id DER-18 \
  --predecessor-entry-id DER-17 \
  --expected-successor-fingerprint sha256:... \
  --expected-predecessor-fingerprint sha256:... \
  --expected-predecessor-status contested \
  --evidence-ref accepted:CH-22
```

Both memories remain stored. The predecessor becomes `superseded`; the successor remains `active`. The operation ledger records both fingerprints and evidence references.

For consolidation across several old derived memories, first create a new source-bound derived entry, then explicitly supersede each predecessor. There is intentionally no automatic "rewrite the whole bank" operation.

## Protected authority

`locked` and `accepted` memory references cannot be contested or superseded through this runtime. Project truth changes only through the Project acceptance/Settlement path. Lifecycle operations have:

```text
authority = false
canon_write = false
model_execution = false
```

## Retry and audit

Every operation gets a deterministic `MEMOP-*` identity from its bound payload. Repeating the exact operation is a safe idempotent retry. Changing evidence, fingerprints, or participants produces a different operation identity and must pass fresh before-state checks.

Use:

```bash
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db operations
python harness/memory_lifecycle.py --db .novelforge/memory-bank.db operations --entry-id DER-17
```

The ledger is operational provenance, not a semantic verdict and not Canon.

## Design rule

> Preserve raw/source evidence. Consolidation is a proposal. Supersession changes context eligibility, not history.

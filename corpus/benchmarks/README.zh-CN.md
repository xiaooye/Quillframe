# Generic Mechanism Benchmarks · 通用机制基准

本目录保存 **cross-work、project-agnostic 的 mechanism evidence**，用于校准 Surface/Reader profile、生成 eval，而不是把版权 Corpus 原文塞给 Writer。

Benchmark 不是 style exemplar，也不是 Canon。

```text
source observations
→ per-work analyses
→ counterexample/profile checks
→ mechanism benchmark
→ capability/regression evals
→ profile/guidance candidate
```

## Seed Registry

`mechanisms.json` 保留 NovelForge v7 第一批 generic benchmark family：

- functional micro-action；
- decision-specific interiority；
- pressure-bound exposition；
- 通过 task/object 保持 embodied dialogue；
- 通过实际后果体现 historical/institutional texture；
- task-bound exposition dialogue；
- pressure ladder to action；
- concrete forward-pull ending。

这些只保留 mechanism abstraction，不保存任何 consumer-project facts 或 raw source passage。

## Benchmark Fields

每条记录包括：
- stable benchmark ID；
- mechanism 与它解决的问题；
- positive operational pattern；
- failure boundary；
- applicable profiles；
- linked HF/RG/eval mechanism；
- provenance class/status；
- writer-safe guidance。

## Promotion Boundary

Benchmark 只有在 evidence/counterexample/eval 状态足够时才可以影响 Generic Fundamentals。Migrated seed mechanism 仍然可被后续 Corpus/Learning evidence 拆分、缩窄、降级或 deprecated。

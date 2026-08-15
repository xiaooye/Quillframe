# 008 Tasks · State Integrity P0

## Stage A · #69 property ownership
- [x] 对 state graph、Settlement、Canon/State 与 Project Adapter 完成 evidence/overlap review。
- [x] 定义最小 mutation classes 与 deterministic route vocabulary。
- [x] 实现 resolver/schema + Project-path integration，且不重新解释 legacy Project。
- [x] 从 stale PR #75 salvage 时以 content-addressed blobs 原样保留已验证实现，并重新建立在 current main 上。
- [x] 增加 cross-contract regression：合法 Runtime operational authorization 不能绕过 `settlement_only` Project property。
- [x] Fresh salvage full NovelForge CI `31905483778` 全绿；state-integrity job `95062461054` 实际执行全部 P0 steps。

## Stage B · #63 propagation debt
- [x] 对 state graph、Settlement、memory invalidation、quality evolution 与 resume semantics 完成 overlap review。
- [x] 实现 explicit-dependency、fingerprint-bound debt identity/lifecycle，不做 global invalidation。
- [x] Deterministic regressions 覆盖幂等 replay、conflicting replay rejection、discharge binding、contiguous supersession、evidence-bound waiver 与 restart。
- [x] Debt 始终 non-authoritative / non-executing：不自动 repair、replan、regenerate，不获得 Canon / Framework write。
- [x] 在 #83 修复后的 Runtime Control baseline 上重新验证两套 P0 mechanism。

## Integration / promotion gate
- [x] 把 dedicated State Integrity workflow 接入 current full NovelForge CI。
- [x] 在 `HARNESS_MANIFEST.yaml` 注册 tool/schema/write-boundary semantics，并完整保留 current Runtime Control 条目。
- [x] 在 reusable deterministic contracts 中加入 property policy、propagation debt 与 Runtime/property cross-contract。
- [x] 在 documentation governance 注册成对的 008 spec/plan/tasks。
- [ ] 本次 manifest/docs/contracts integration 后运行 final exact-head full NovelForge CI，并检查 jobs/artifacts。
- [ ] 再核 current main、exact diff 与 rollback boundary；所有 downstream Project lock 保持不变。
- [ ] 只有 fresh salvage candidate 完整替代旧证据后，才 supersede stale PR #75。

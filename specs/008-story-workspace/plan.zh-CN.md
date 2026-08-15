# Plan · Story Workspace & Narrative Runtime

1. **Workspace projection**：新增 Core-owned Story Workspace schema / projector，从 Project SDK / Adapter 已解析对象生成只读、source-bound、authority-preserving projection；不建立第二持久 state store。
2. **Context Trace**：在现有 Context Inspector、`context.select` 与 memory-tier packing 上增加 trace builder / schema，统一记录 eligibility → semantic selection → hard-budget packing → loaded working set，并保留 model/deterministic ownership。
3. **Event IR**：新增 schema + deterministic validator + synthetic fixtures；Event IR 只表达 causal candidate，不拥有 Canon authority，也不要求 prose 机械复述。
4. **Simulation Run**：增加 scene-simulation run envelope，把 base-state fingerprint、`character.action_propose`、`scene.resolve_actions`、Event IR candidates、scenario fork 与 optional `quality.compare` 结果做 fingerprint / provenance binding；不创建 persistent character-agent memory。
5. **Candidate State Delta**：新增 candidate extractor contract / typed schema，把候选正文或 Event realization 的 state / knowledge / relationship / resource / obligation / location changes表达成 source-bound proposal。
6. **Narrative Verification**：扩展现有 state-graph verification；deterministic contradiction 与 semantic narrative verification 分层执行，最终归一到 shared finding contract，并显式保留 repair owner / provenance。
7. **Bridge/query surface**：给 Studio Host Bridge 增加只读 operations，例如 `story.workspace`、`context.trace`、`scene.simulation.get`、`state.candidate`、`continuity.verify`；所有首批操作保持 `canon_write=false` / `settlement=false`。
8. **Studio slice**：先实现只读 Story Workspace / Context Trace / Simulation / Verification 视图；UI 只消费 Core projection，不直接解析 Project 私有数据库。
9. **Evals / CI**：增加 standard + mapped synthetic Project fixtures、fingerprint mismatch、future-knowledge violation、branch authority、Event IR drift、semantic/deterministic ownership tests；保持 normal CI 无 live model usage。
10. **Docs / bundle**：更新 manifest、architecture / context / production docs、documentation manifest 与 bundle coverage；中英双语保持一致。
11. **Release gate**：完成 deterministic CI + required semantic capability/regression evidence 后，形成新的 version / exact commit / bundle fingerprint；此时才允许 consuming Project 做显式 dependency migration。

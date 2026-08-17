# Plan 014 · Pre-Independent Candidate Qualification

## Phase 1 · Authority / drift
- [x] consumer lock 与 attestation exact match。
- [x] Framework main HEAD 与 consumer pin 都是 `f7732856311814d82012159e5856c4aa592007a5`。
- [x] PR #102 保持独立未合并；本任务从 main 单独分支。
- [x] Generic 与 consumer post-generation 顺序 drift 已确认。
- [x] 已检查 Surface、Reader、semantic、readiness/release、repair、session/runtime contracts。
- [x] 已完成 current primary-source research。

## Phase 2 · Contracts
1. 在现有 quality semantic pack 增加 `quality.candidate_self_audit`。
2. 增加 `quality/candidate_qualification.py` 与 schema，生成 fingerprint-bound、`independent=false` qualification receipt。
3. `quality.production_review` job construction 必须验证 qualification proof；proof 不进入 reviewer-visible semantic payload。
4. production readiness/release 增加 qualification defense-in-depth。
5. 保持 regression isolation 与 fresh-realization rejected-prose 隔离。

## Phase 3 · Semantic behavior
Self-audit 覆盖 sentence/block/cluster 三尺度，并检查 Delete Test、micro-action function、explanation-after-evidence、synthetic coolness、AI explanation tone、SAFE-BUT-FLAT interface、semantic ownership，以及 addendum 的 function → ownership → natural realization 三层测试。

同时区分 character-owned humor 与 author-optimized wit，检查 narrator clever reframing 与 punchline stacking。禁止 lexical bans。此次不新增 HF code。

## Phase 4 · Deterministic tests
覆盖 qualification missing/fail/pending、fingerprint mismatch、repair 后 stale、blocking finding、independent PASS 不可覆盖 self-audit fail、self-audit 永远非 independent、qualification metadata 不污染 independent semantic payload、first-pass regression isolation、normal CI 无 live model。

## Phase 5 · Semantic fixtures / ablation
使用 anonymized synthetic fixtures 覆盖原 20 个要求，以及新增：functional-but-overwritten dialogue / natural control；narrator clever reframing / POV-owned metaphor control；punchline stacking / sparse natural humor control。

Paired ablation 比较 BEFORE（functional 即 pass）与 AFTER（function 后继续 ownership + natural realization）。Deterministic CI 只 package/validate；live semantic execution 单独进行，没有 eligible reviewer 时保持 `PENDING_MODEL`。

## Phase 6 · Docs / release
同步 HARNESS_MANIFEST、Skill/Harness、production pipeline、semantic catalog/pack、quality gates、CI 与必要 documentation governance。Framework PR 不修改 consumer Project；consumer `START_HERE` drift 作为独立 migration recommendation。

## Phase 7 · Verification
运行 PR deterministic CI，检查 exact diff、privacy、bundle fingerprint implication、semantic ablation 状态，创建 draft PR，不自动 merge/re-pin。
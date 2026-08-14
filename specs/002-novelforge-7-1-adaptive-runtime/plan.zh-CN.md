# 计划 · NovelForge 7.1 Adaptive Runtime

## 总策略

7.1 继续坚持“deterministic shell + optional host/model capability”。Deterministic 层负责 identity、state transition、fingerprint、provenance、rights/storage policy、idempotency、queue、promotion prerequisite、bundle materialization/verification；Host/Model 只执行它真实拥有 capability 的工作。

## Phase 1 · Capability Contract

新增 `harness/runtime_capabilities.py`：
- `novelforge_host_capabilities_v1` schema；
- 对本地可证明的 executable/runtime fact 做 local probe；
- 对 Chat/MCP/Web/GitHub 等外部 capability declaration 做 normalize；
- requirement resolver 永不选择 undeclared/unavailable capability；
- usage/cost/user-interaction metadata；
- self-test。

新增中英 Runtime Capability 文档并接入 Runtime Routing。

## Phase 2 · Discovery Runtime

新增 `corpus/discovery_runtime.py`：
- 根据 Corpus Scout request + host capability 生成 typed dispatch plan；
- typed discovery result validation；
- source/tool/channel provenance binding；
- evidence fingerprint；
- 使用 `rights_gate.py` 做 deterministic rights/storage validation；
- 按 source locator/content fingerprint 去重；
- 按 work/source/channel 做 diversity summary；
- self-test。

升级 `corpus_scout.py`，每个 search channel 声明 capability requirement，而不是默认 host 有能力。

## Phase 3 · Learning Cycle

新增 `learning/learning_cycle.py`，在同一个 learning DB 内使用独立 cycle tables：
- 从已有 Corpus gap/hypothesis 启动；
- 持久化 cycle identity/state/version；
- register discovery queue/result；
- register analysis/eval queue/result fingerprint；
- enforce legal transition；
- logical consume-once；
- durable resume；
- 永不授予 Canon/Framework-write authority；
- self-test crash/retry/idempotency。

## Phase 4 · Semantic Learning Work

新增 `learning/learning_eval.py`，打包：
- verified discovery evidence → `corpus_analyze` semantic job；
- scope 需要时的 `preference_distill` / `external_review` job；
- capability/regression evidence 的 `eval_judge` job；
- mechanism/counterexample/boundary/evidence refs/confidence typed output contract。

继续复用现有 semantic fingerprint；execution lineage 不进入 semantic fingerprint。

Worker packet 不携带 hidden gold / expected label。

## Phase 5 · Promotion Gate

新增 `learning/promotion_gate.py`。

规则：
- `one_off`：永不 durable promotion；
- `project`：只能成为 project proposal/active preference，Generic Framework code 无权直接激活；
- `user_taste`：要求 explicit/repeated human evidence + contradiction review + eval evidence；gate 只能标 ready，不把 private taste 写入 Generic source；
- `general_craft`：要求 cross-work evidence、counterexample/profile boundary、capability+regression eval、target version、rollback ref、green CI evidence。

Gate 只输出 evidence completeness / blocker，不自行改 Framework behavior。

## Phase 6 · Immutable Bundle

新增 `release/build_framework_bundle.py` 与中英文档。

规则：
- sorted paths；
- deterministic tar metadata（`mtime=0`、固定 uid/gid、mode normalization）；
- `.git`、generated artifacts、runtime DB、specs、bundle metadata 不进入 runtime bundle；
- Core/Surface/Harness/Learning/Corpus/Evals/SDK/docs/bootstrap 进入 bundle；
- per-file SHA-256 content manifest；
- overall bundle SHA-256；
- verify command；
- self-test 必须证明重复 build fingerprint 一致，篡改后 verify 失败。

新增可选 `novelforge-release-bundle.yml` 构建/验证/upload immutable artifact。Normal CI 只验证 builder，不发布 release、不执行模型。

## Phase 7 · CLI / CI / Maintenance

升级 `novelforge.py`：
- Framework version 7.1.0；
- `capabilities` router；
- `learning-cycle` router；
- `learning-gate` router；
- `corpus discovery` router；
- `bundle` router；
- self-test 覆盖全部 7.1 deterministic modules。

升级 reusable CI：
- compile 全部 module；
- 新 self-test；
- assert no model execution；
- bundle build 两次并比较 fingerprint；
- 检查 adaptive queue invariant。

升级 weekly maintenance：
- 只 probe deterministic/local capability；
- 生成 learning/discovery work queue；
- 报告 pending capability requirement；
- 不声称执行未执行的 Web/model work；
- 不 auto-promote。

## Phase 8 · Docs / Manifest / Version

更新：
- `HARNESS_MANIFEST.yaml` → 7.1.0；
- `SKILL.md`、`SKILL.en.md`、`SKILL.zh-CN.md`；
- Harness / Runtime Routing / Self-Improvement；
- Adaptive Learning；
- Corpus docs/policy；
- Integrations；
- Project SDK docs；
- README + CHANGELOG；
- `project_sdk.py` default/minimum version behavior。

记录 OpenAI Agents SDK、LangGraph、MCP、Google ADK 官方机制证据，但不把它们变成 dependency。

## Phase 9 · Framework Release Verification

1. implementation 直接进入 `main`；
2. 等最终 NovelForge CI；
3. CI fail 必须修 owning mechanism，不允许 bless failing commit；
4. green 后构建 deterministic bundle，取得 fingerprint；
5. 如需 commit bundle attestation metadata，metadata 自身必须排除在 fingerprint input 之外，避免 circular hash；
6. 再跑 CI 并确认 final Framework HEAD。

## Phase 10 · Chinatown Consumer Upgrade

最终 7.1 Framework HEAD green 后：
- `novelforge.toml` minimum framework version → 7.1.0；
- `novelforge.lock.json` 写 exact commit + bundle fingerprint；
- 更新 framework attestation；
- 仅在 7.1 capability/bundle semantics 需要时修改 Project bootstrap docs；
- Project validator 对 7.1 lock 强制 bundle fingerprint；
- 跑 Chinatown Project CI；
- 验证 Canon/active story state 未变化。

## Rollback

Framework rollback：`de05666cc4eae13f09868d87659e76f2aa524314`。

Consumer rollback：若 7.1 consumer gate fail，恢复最后 7.0 lock/attestation/bootstrap。此 release 不包含 Canon migration。

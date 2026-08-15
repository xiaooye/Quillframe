# Plan · Production Quality Gate Hardening

1. 建立 `quality/taxonomy.json` + compatibility scanner，并由 deterministic self-test 验证 Framework human docs 与 machine registry 一致。
2. 在 quality semantic pack 注册 `reader.engagement_audit` 与 `quality.production_review`。
3. 强化 `quality/production_readiness.py`：mandatory independent PASS/FAIL 从 validated registered semantic result 派生；拒绝 ad-hoc eval、caller status override、candidate mismatch、伪独立 invocation。
4. 新增 `quality/repair_policy.py`：把上游/cluster ownership 映射到 fresh realization，隔离 rejected prose 与 concrete surface patches。
5. 加 synthetic contract tests / CI，确保 blind eval 仍可使用普通 `eval_judge`。
6. Framework 合并并产生新的 exact commit/bundle 后，再由 consuming Project 做显式 dependency migration；migration 必须先修正所有 stale HF/RG refs，并新增 Project-owned regression 防止 checklist-compliant synthesis。

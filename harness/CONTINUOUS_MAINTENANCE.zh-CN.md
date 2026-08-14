# Continuous Maintenance · v7 中文版

## 目的

Continuous Maintenance 用来保持 Framework 健康，但不能把 schedule/webhook 变成无人授权的编辑权威。

```text
schedule / push / external signal
→ deterministic observation
→ candidate/report
→ tests/evals
→ gated framework change
```

## L0 · Auto-check

允许 unattended：
- compile/static/schema checks；
- bilingual docs / link checks；
- project-leakage scan；
- session/control-plane invariant；
- corpus rights/schema invariant；
- dependency/version drift detection；
- upstream framework freshness metadata；
- non-mutating maintenance report。

## L1 · Auto-candidate

可以生成 bounded candidate：
- 新 regression/capability case；
- stale integration update；
- corpus/research gap；
- external framework mechanism 的 adopt/adapt/reject review；
- docs/schema cleanup。

创建 candidate 不等于 behavior promotion。

## L2 · Gated Promotion

Material generic behavior change 必须服从 Self-Improvement Protocol：evidence、counterexample/profile check、eval/regression、version/rollback 与 green CI。

## L3 · Human / Project Authority

这些始终保留 explicit project/user authority：
- Canon settlement；
- story-direction change；
- 有歧义的 destructive migration；
- 相互冲突的 durable user preference；
- 需要时的 project release acceptance。

## Usage Boundary

Normal scheduled CI/maintenance 不得静默调用付费或 login-bound model inference。Live semantic/research/model check 必须是 separate opt-in workflow，除非 host 明确提供包含的 execution。

## Event Boundary

Webhook/schedule/MCP event 可以唤醒 maintenance workflow，但不会自动授权 drafting、Canon mutation、user-taste promotion 或 framework release。

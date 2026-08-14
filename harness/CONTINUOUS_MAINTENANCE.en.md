# Continuous Maintenance · v7

## Purpose

Continuous maintenance keeps the framework healthy without turning schedules/webhooks into autonomous editorial authority.

```text
schedule / push / external signal
→ deterministic observation
→ candidate/report
→ tests/evals
→ gated framework change
```

## L0 · Auto-check

Allowed unattended:
- compile/static/schema checks;
- bilingual-doc and link checks;
- project-leakage scans;
- session/control-plane invariants;
- corpus rights/schema invariants;
- dependency/version drift detection;
- upstream framework freshness metadata;
- non-mutating maintenance reports.

## L1 · Auto-candidate

May create bounded candidates for:
- new regression/capability cases;
- stale integration updates;
- corpus/research gaps;
- adopt/adapt/reject review of external framework mechanisms;
- docs/schema cleanup.

Candidate creation is not behavior promotion.

## L2 · Gated promotion

Material generic behavior change requires the Self-Improvement Protocol: evidence, counterexample/profile check, eval/regression, version/rollback, and green CI.

## L3 · Human/project authority

Always preserve explicit project/user authority for:
- Canon settlement;
- story-direction changes;
- ambiguous destructive migrations;
- contradictory durable user preferences;
- project release acceptance when required.

## Usage boundary

Normal scheduled CI/maintenance must not silently invoke paid or login-bound model inference. Live semantic/research/model checks are separate opt-in workflows unless the host explicitly supplies included execution.

## Event boundary

Webhook/schedule/MCP events may wake a maintenance workflow. They do not automatically authorize drafting, Canon mutation, user-taste promotion, or framework release.

# Runtime Continuous Maintenance · v6.6

Maintenance observes execution infrastructure without governing story/Canon.

```text
schedule / push / external signal
→ deterministic observation
→ report/candidate
→ eval
→ gated runtime promotion
```

## L0 AUTO-CHECK

Allowed unattended:
- compile/runtime self-tests;
- schema/manifest/authority drift checks;
- session/control-plane invariants;
- event/handoff contract validation;
- provider/framework freshness metadata;
- maintenance reports/issues.

## L1 AUTO-CANDIDATE

May propose:
- runtime regression cases;
- connector/workflow refactors;
- stale integration candidates;
- upstream framework adopt/adapt/reject review.

No behavior promotion.

## L2 GATED-PROMOTION

Requires evidence + regression/capability + conflict check + version/rollback + green CI.

## L3 HUMAN AUTHORITY

Always required for:
- Canon/SETTLE;
- project story direction;
- destructive migrations with ambiguity;
- contradictory durable user preferences;
- authority-domain migration/cutover where source truth could split.

## Event rule

Maintenance can consume `maintenance.requested` through the Control Plane/event router. It may never reinterpret a schedule or webhook as permission to DRAFT, SETTLE, write Canon or promote behavior automatically.

## Secrets/usage

Normal scheduled maintenance is deterministic and does not spend model/API/agentic usage. Live semantic or provider checks must be explicit opt-in workflows.

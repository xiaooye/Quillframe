# Semantic Worker Protocol · v0.3

## Purpose

Semantic work is exchanged as blind, typed, fingerprint-bound evidence across independent sessions/invocations.

```text
frozen artifact
→ bounded job
→ semantic fingerprint
→ handoff/session lineage
→ independent worker
→ typed result
→ deterministic binding validation
→ gate consumer
```

The router never judges prose. The Control Plane never upgrades a judgment into authority.

## Job identity

Canonical required fields:
- `job_id`
- `kind`
- `subject_id`
- `created_at`
- `input_fingerprint`
- `input`
- `rubric`
- `output_contract`
- `permissions`
- `provenance`

Optional v0.3 execution lineage:

```json
{
  "execution": {
    "source_session_id": null,
    "worker_session_id": null,
    "handoff_id": null,
    "attempt_id": null
  }
}
```

Runtime/session lineage is deliberately excluded from the semantic fingerprint. Moving the same frozen question from one eligible transport to another does not change the literary question. Changing subject input/rubric/output contract does.

## Fingerprint

SHA-256 over canonical:

`kind + subject_id + input + rubric + output_contract`

A stale/mismatched result is invalid and must not be consumed.

## Blindness

`eval_judge` input must not contain hidden expected verdict/codes, release status, prior result or equivalent gold fields.

Writer private reasoning, unrelated project data and hidden regression gold stay outside independent review packets.

## Authority

Worker permissions require:
- `canon_write=false`
- `os_behavior_write=false`
- `durable_user_taste_write=false`

A result may be observation/proposal evidence only unless a separate Harness gate authorizes a later action.

Forbidden direct worker actions include Canon settlement, Generic rule promotion, durable-taste overwrite and permission grant.

## Worker kinds

- `eval_judge`
- `artifact_audit`
- `corpus_analyze`
- `benchmark_synthesize`
- `external_review`
- `preference_distill`

Adapters may support a subset. Unsupported kinds return `unsupported`, never fabricated judgment.

## Result

A typed result repeats exact `job_id/subject_id/kind/input_fingerprint`, declares truthful worker provenance and returns:
- status `completed|unsupported|failed`;
- judgment verdict/result/codes/evidence/confidence;
- proposals;
- errors;
- optional execution lineage.

No private chain-of-thought is requested or stored.

## Retry

- infrastructure failure + same fingerprint → safe retry/fallback under policy;
- changed semantic payload → new fingerprint and normally new reviewer session;
- valid reject/fail → `semantic_reject`, repair owning layer; do not reviewer-shop;
- result delivery may duplicate, but Control Plane consumer applies it logically once.

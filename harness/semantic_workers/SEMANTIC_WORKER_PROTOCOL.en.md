# Semantic Worker Protocol · v7

## Purpose

Semantic work crosses a strict boundary:

```text
frozen subject
→ bounded blind job
→ semantic fingerprint
→ independent session/invocation
→ typed result
→ deterministic binding validation
→ named gate consumes once
```

The router and Control Plane never make the literary judgment themselves.

## Job identity

A semantic job contains:
- `job_id`, `kind`, `subject_id`, `created_at`;
- `input_fingerprint`;
- bounded `input`;
- `rubric`;
- `output_contract`;
- least-privilege `permissions`;
- `provenance`;
- optional execution lineage.

## Fingerprint

Semantic fingerprint is computed from the semantic question:

`kind + subject_id + input + rubric + output_contract`

Transport/session/attempt lineage is excluded. The same frozen question may retry through another infrastructure path without pretending the prose changed.

A material change to subject input/rubric/output contract creates a new fingerprint and normally a fresh reviewer session.

## Blindness

Independent reviewer packets exclude:
- expected verdict/gold labels;
- prior reviewer verdicts;
- writer private reasoning;
- irrelevant project context;
- regression answer keys.

The reviewer receives only evidence required to judge the declared rubric.

## Authority

Semantic workers have no implicit authority to:
- write Canon;
- settle project state;
- promote framework behavior;
- overwrite durable user taste;
- grant permissions.

Their result is bounded judgment/evidence.

## Result

Typed result repeats exact job identity/fingerprint and declares truthful worker provenance. It contains status, judgment, evidence/codes/confidence, proposals if allowed, errors, and optional execution lineage.

Private chain-of-thought is neither requested nor persisted.

## Independence

Valid independent review uses a genuinely separate invocation/session. Same-session manager role-play is invalid even if the manager changes system role labels internally.

Eligible transports may include local agent subprocess, provider API, MCP worker, GitHub/service job, separate peer chat, local model, or human.

## Retry semantics

- infrastructure failure + unchanged fingerprint → safe transport retry/fallback;
- invalid/mismatched result → reject result and rerun/repair transport;
- valid semantic reject/fail → route to owning story/character/surface/reader/continuity repair layer;
- never shop reviewers until somebody passes;
- duplicate delivery is handled by consume-once logic.

## Scope

Semantic review complements deterministic checks. Identity, fingerprints, permissions, schemas, lifecycle transitions, arithmetic, and idempotency should remain deterministic where possible.

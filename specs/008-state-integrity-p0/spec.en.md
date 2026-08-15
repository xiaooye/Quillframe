# 008 · State Integrity P0 — Property Ownership and Propagation Debt

## Status
Draft implementation spec for Generic NovelForge. This work is **not** authority for any downstream Project until released and explicitly pinned.

## Evidence
- #69: external Codex systems expose a useful editable/derived field boundary, but also demonstrate dual-writer last-write-wins failures when one property is both human-editable and agent-derived.
- #63: external long-form systems track downstream propagation debt after upstream changes; current NovelForge documents dependency impact but has no durable debt lifecycle.

## Problem
NovelForge already separates Canon, Accepted artifacts, Settlement, derived memory, runtime state, plans, and proposals. Two deterministic gaps remain:

1. A Project cannot machine-declare, at property granularity, which writer class may mutate a value directly versus requiring proposal, Settlement, or reconciliation.
2. After an authoritative upstream change, dependency impact has no generic durable `open → discharged` lifecycle.

## Invariants
- No model inference grants write authority.
- Capability/tool availability is not authority.
- Policy resolution is deterministic. A configured Project policy may authoritatively resolve the **write route**, but the resolver never grants Canon or Framework-write authority and never establishes the truth of a value.
- Existing Projects without a property policy retain current object-level behavior.
- One property must not silently acquire two authoritative writers.
- Settlement remains the authority mechanism for `settlement_only` state.
- Derived state remains `authority=false` and source-bound.
- Propagation debt, when implemented, is a derived work ledger, never Canon.
- No global invalidation or automatic prose regeneration.

## Stage A — #69 Property write-source policy
Projects may opt in by mapping `paths.property_write_policy` to a UTF-8 JSON policy using `novelforge_property_write_policy_v1`.

Resolution precedence:

`global default → object-type default → exact property override`

Mutation classes:
- `user_declared`
- `settlement_only`
- `derived_only`
- `proposal_only`
- `runtime_only`
- `locked`
- `mixed_reconcile`

The deterministic resolver returns only a route:

`allow_direct | proposal_required | settlement_required | reconcile_required | deny | legacy_unmanaged`

It does not decide whether a proposed value is true.

## Stage B — #63 Propagation debt
After Stage A is stable, add a non-authoritative ledger binding an upstream before/after fingerprint to explicit dependent artifacts and a required action (`revalidate|rebuild|replan|resimulate|human_review`). Debt is opened only from explicit dependency evidence and is discharged only by bound result evidence/fingerprint.

## Compatibility
No Project schema-version bump in Stage A. Absence of `paths.property_write_policy` yields `legacy_unmanaged`, preserving current behavior. A configured but missing/invalid policy fails closed for the policy resolver.

## Acceptance
- deterministic self-tests and public CI green;
- schema/tool discoverable in Framework manifest;
- host payload cannot self-escalate write permission;
- broad defaults avoid per-field ACL forests;
- exact policy fingerprint is observable;
- #63 is not implemented until #69 semantics are stable.

# 008 · State Integrity P0 — Property Ownership and Propagation Debt

## Status
Draft Generic NovelForge implementation. Nothing here is downstream Project authority until a release is merged, bundled, attested, and explicitly pinned by that Project.

## Evidence and overlap
- #69: external editable-Codex systems expose useful field ownership but also dual-writer last-write-wins failures.
- #63: external long-form systems track downstream propagation debt after upstream changes.
- Current NovelForge already owns object/fact authority, Settlement, derived memory invalidation, state-graph contradiction detection, quality-evolution ledgers, and resume preflight. P0 must extend those boundaries, not duplicate them.

## Stage A · Property write-source policy (#69)
Projects may opt in through `paths.property_write_policy` using `novelforge_property_write_policy_v1`.

Resolution:
`global default → object-type default → exact property override`

Mutation classes:
`user_declared | settlement_only | derived_only | proposal_only | runtime_only | locked | mixed_reconcile`

Routes:
`allow_direct | proposal_required | settlement_required | reconcile_required | deny | legacy_unmanaged`

The resolver may authoritatively resolve a write route, but it never establishes story truth or grants Canon/Framework-write authority. Projects without the optional policy preserve legacy object-level behavior.

## Stage B · Propagation debt (#63)
`harness/propagation_debt.py` is a deterministic SQLite work ledger with schema `novelforge_propagation_debt_v1`.

A debt may open only when the caller supplies:
- a changed upstream source with exact before/after fingerprints;
- source-change evidence ref + fingerprint;
- source authority (`locked|accepted|settled|active_plan`);
- one explicit dependency edge ref + fingerprint;
- dependent artifact ref + current fingerprint;
- one required action: `revalidate|rebuild|replan|resimulate|human_review`;
- a bounded reason.

No dependency edge means no debt. Unchanged source fingerprint means no debt. The runtime never scans the whole Project to invent dependents and never performs the required action itself.

Debt identity is deterministic from source change + exact dependency/dependent fingerprint + required action. Reopening the same identity is idempotent; replay with conflicting evidence fails closed.

Lifecycle:
`open → discharged | superseded | waived_with_evidence`

Discharge requires the debt's latest source fingerprint, exact required action, result ref/fingerprint, and resulting dependent fingerprint. Supersession is explicit and only allowed when the new debt continues the same source/dependent/dependency lineage from the prior source-after fingerprint. Waiver requires evidence; no silent dismissal.

The ledger is `authority=false`, never Canon, never a second dependency graph, and never a repair executor. Open debt is not a universal resume blocker. A workflow that requires debt-free state must declare that precondition explicitly; ordinary resume remains owned by `resume_preflight.py`.

## Relationship between Stage A and B
After an authorized state/plan mutation, callers may use the Project's explicit dependency evidence to open downstream debt. Property policy answers **who/which route may write**; propagation debt answers **what known dependent work became stale**. Neither grants the other authority and neither bypasses Settlement.

## Compatibility / rollback
- No Project schema-version bump.
- No policy path → `legacy_unmanaged` as before.
- Propagation debt is a new derived runtime DB (`.novelforge/propagation-debt.db` by default); deleting/rebuilding it never rewrites Canon.
- Reverting P0 leaves existing Project files and Settlement data intact.

## Acceptance
- deterministic public CI and full NovelForge CI green;
- exact schemas/tools discoverable in the Framework manifest before promotion;
- no global invalidation, no automatic prose regeneration;
- restart/retry remains idempotent;
- exact diff contains no unrelated Studio/site changes;
- downstream Projects remain on their prior lock until an explicit future migration.

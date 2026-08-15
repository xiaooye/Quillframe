# Resume Preflight · Prove resumability before runtime control

<p><kbd>RUNTIME SAFETY</kbd>&nbsp;&nbsp;<kbd>READ ONLY</kbd>&nbsp;&nbsp;<kbd>FAIL CLOSED</kbd></p>

Resume is not a navigation action. It is a fresh validation act over durable state.

`resume_preflight.py` determines whether one **existing session + latest checkpoint** has enough current evidence to be eligible for a future typed resume command. The preflight itself performs no runtime mutation, model execution, Canon write, Framework write, Settlement, run creation, result consumption, replay, or fork.

## Contract

A successful preflight returns:

```text
novelforge_session_resume_preflight_v1
status = READY
ready = true
mutation_performed = false
authority = false
```

Any missing or stale binding returns `BLOCKED` with deterministic `checks` and `blockers`.

`READY` means **eligible for a separately authorized future resume command**. It does not mean that command was approved or executed.

## What is revalidated

The first contract verifies only evidence it can prove deterministically:

- the durable runtime store and session exist;
- the caller's expected session version matches the durable Control Plane version (CAS precondition);
- session identity and lifecycle status are compatible with resume;
- `resume_policy` is not `forbidden`;
- `same_session` has an existing provider/external binding without exposing the private identifier;
- the checkpoint exists and is the latest checkpoint for ordinary resume;
- checkpoint and session resume policies agree;
- no unresolved gate or handoff is silently crossed;
- current `novelforge.lock.json` Framework version / commit / bundle fingerprint match supplied frozen authority evidence;
- `framework.attestation.json` agrees with the current lock;
- Project identity still matches the durable session;
- checkpoint artifact fingerprints can be re-derived from project-relative artifact bindings;
- declared required capabilities are present in the supplied capability evidence;
- approval references are structurally valid;
- the read-only inspection did not modify the runtime store.

## Latest checkpoint only

Ordinary resume is intentionally restricted to the latest checkpoint. Selecting an older checkpoint is **time travel**, not resume, and must use a future replay/fork contract with its own semantics.

This keeps the boundary explicit:

```text
resume latest durable cursor
!= replay prior execution
!= fork alternative state
```

## Authority evidence

The preflight accepts `novelforge_resume_authority_evidence_v1`. It carries the frozen identity against which current state is compared:

- `project_id`;
- Framework `version`, exact `commit`, and `bundle_fingerprint`;
- project-relative artifact bindings and fingerprints;
- required / available capability identifiers;
- approval references when applicable.

The evidence does not grant authority. It is input to a deterministic comparison.

Absolute artifact paths are forbidden. Artifact paths must remain inside the Project root.

## Failure semantics

Representative blockers include:

- `session_version_mismatch`;
- `session_status_not_resumable`;
- `resume_policy_forbidden`;
- `checkpoint_not_latest_use_replay_contract`;
- `pending_gate_requires_fresh_validation`;
- `pending_handoff_requires_binding`;
- `framework_attestation_mismatch`;
- `framework_identity_changed_or_unproven`;
- `checkpoint_artifact_fingerprint_unverified`;
- `required_capability_unavailable`.

A blocker must stop future resume routing until fresh evidence resolves it. The runtime must not reconstruct missing truth from provider conversation memory or logs.

## Why this precedes resume control

Checkpoint systems in agent frameworks make interruption, replay, and time travel practical, but NovelForge additionally has Project/Framework authority, exact lock identity, independent gates, and consequential settlement semantics. Therefore a persisted checkpoint alone is insufficient authority to continue.

The implementation order is intentionally:

```text
observe durable state
→ deterministic resume preflight
→ typed resume command envelope
→ replay/fork contracts later
```

The actual resume command remains deferred until command-level idempotency, before-state, capability evidence, approval/authority checks, and receipts are contractually complete.

# NovelForge Orchestration Protocol · v7

## Common Prefix

```text
load framework manifest + skill
→ validate consuming project + lockfile
→ choose exactly one task_mode
→ resolve/create manager session + run
→ build sparse Context Manifest
→ resolve Canon cutoff + permissions
→ execute mode graph
```

Resume path:

```text
load checkpoint
→ revalidate project/framework compatibility
→ revalidate artifact fingerprints
→ revalidate approvals/write intents
→ bind and consume pending result once
→ continue saved step
```

## DRAFT / REVISE

```text
Context Freeze
→ Story/Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure Preflight
→ Event-first Raw Draft
→ Surface Realization
→ Surface Lint A
→ freeze candidate
→ post-generation regression / independent semantic review
→ repair at owning layer
→ Surface Lint B
→ Reader Engagement
→ Continuity
→ User-visible Gate
```

Writer does not receive hidden regression gold before the Raw Draft freeze. Raw/internal drafts are not user-visible production artifacts.

## Semantic Gate Subroutine

```text
freeze semantic payload
→ typed job + fingerprint
→ checkpoint
→ route eligible independent runtime
→ execute | queued handoff | peer relay | await
→ typed result
→ validate identity/fingerprint/provenance
→ consume once at named gate
```

Changed semantic payload creates a new fingerprint. Infrastructure retry may preserve the same fingerprint. A valid semantic rejection is not infrastructure failure.

## PLAN / DESIGN

Plans create `proposal` / `active_plan` artifacts only. They never mutate current Canon state merely because the Harness persists them.

Use rolling elaboration: high resolution near the production frontier, lower resolution farther away.

## RESEARCH

Research outputs source-bound `REF/CLAIM`-equivalent evidence. Reality truth remains separate from character knowledge. External search capability does not grant project-write authority.

## CORPUS-INGEST

```text
learning/craft question
→ discovery request
→ source verification
→ rights gate
→ bounded analysis
→ counterexample search
→ benchmark/eval candidate
```

Corpus output never becomes Canon.

## LEARN

```text
feedback/evidence
→ narrowest scope classification
→ preference/craft hypothesis
→ contradiction check
→ corpus/eval gap
→ candidate promotion or rollback
```

Model repetition is not new evidence.

## SETTLE

Only explicit project acceptance permits Canon settlement.

```text
freeze accepted artifact
→ exact state delta
→ validate before-state
→ dependency impact
→ checkpoint/write intent
→ authorized mutation
→ rebuild derived views
→ post-condition
→ trace/receipt
```

Mismatch returns `settlement_incomplete`; do not guess or partially apply unrelated operations.

## SYSTEM-IMPROVE

Material framework changes require evidence, mechanism, alternatives/conflict review, capability/regression coverage, rollback point, versioning, and green deterministic CI.

## Parallelism

Parallelize immutable-input research/audits when useful. Do not concurrently mutate shared Canon/state without an explicit transaction/version protocol.

## Completion states

`complete | review | awaiting_user | awaiting_external | blocked | failed_gate | semantic_pending | semantic_invalid | settlement_incomplete`

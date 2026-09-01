# Confirmed-prefix recovery specification

2026-08-31 · implemented `SYSTEM-IMPROVE` contract · live CH001 recovery remains a separate production gate.

This specification defines one narrow recovery route for a fresh, explicitly authorized `REVISE` run after the preceding run produced an exact candidate, passed its first four prose gates, and then stopped because the self-audit response was syntactically invalid JSON. It does not repair that response, mutate the old run, or grant extra authority.

## 01 · Problem and decision

The source run already paid for and confirmed editor, surface realization, Reader engagement, and continuity against one exact candidate. Its next call returned completed bytes, but those bytes could not form one JSON object. Re-running the whole chapter would spend calls on evidence that has not changed; continuing the old run would exceed its frozen call budget.

The supported decision is a fresh run that references the confirmed predecessor prefix and starts with a new self-audit. Core freezes the reference and the user's recovery authorization in the same transaction that creates the new run.

## 02 · Exact eligible boundary

The source is eligible only when all of these facts revalidate from native storage:

- it is a quiescent `semantic_pending` `REVISE` run in the same Project and target;
- it has no active executor, unresolved call, candidate, qualified checkpoint, independent handoff, narrative proposal, or release;
- its confirmed call order is exactly editor, surface, Reader engagement, continuity, then self-audit;
- the first four results pass and bind the same candidate bytes and fingerprint;
- the fifth result is bound to the self-audit job but is a JSON syntax failure;
- one matching `semantic_output_invalid` event records `automatic_model_retry=false`;
- author request, execution request, repair source, Context, repair plan, local-reuse checkpoint, craft evidence, and stage receipts are canonical and fingerprint-valid.

Any missing, extra, reordered, pending, cancelled, changed, or conflicting evidence rejects recovery before model dispatch.

## 03 · Authority and registration

The caller supplies only four identity fields: source run, terminal call, expected candidate fingerprint, and expected prefix fingerprint. It cannot supply prose, judgments, repair plans, or a list of stages to reuse.

Core requires:

- `task_mode=REVISE`;
- the same Core-frozen repair source;
- a write identity and idempotency key;
- authorization intent exactly `confirmed_prefix_recovery`.

Core derives the private prefix again, freezes a `production_confirmed_prefix_source` checkpoint, and records a separate authorization receipt. Replaying the same registration is idempotent; changing the request under the same key conflicts.

## 04 · Evidence reuse without call copying

The old `AgentJob` and `AgentResult` rows remain owned by the old run. They are never inserted into the new run's stage journal. The new run records three current Context-bound reuse receipts for surface, Reader engagement, and continuity, plus one deterministic reuse checkpoint. Each receipt points to the exact old call/result/receipt fingerprints and states that the current run invoked no model for that stage.

The current run therefore charges zero calls for the reused prefix. Its main-call graph is exactly:

```text
new self-audit
→ new repair comparison
→ new reader-expectations observation
→ new narrative-state proposal
```

The run-level limit for this route is four main calls. Independent review is a fifth, separate invocation after the manager graph reaches `awaiting_external`.

## 05 · Context, craft, and semantic isolation

Run-scoped identities naturally differ, so compatibility is checked through a normalized projection of source universe, target, author preferences, profiles, and stage selections. Exact current Context and freeze fingerprints still bind every new receipt.

The old craft snapshot remains historical generation evidence. The recovery run does not consume the one-off style pack again and does not open a new writer stage. Blind Reader and independent-review inputs remain free of private repair instructions and style-selection data.

No malformed bytes are locally repaired, normalized, or promoted into a judgment. The new self-audit is a fresh call under the current registered contract.

## 06 · Future source verification

A recovered candidate may become a later author-revision source only if its full logical journal can be reconstructed:

- surface, Reader engagement, and continuity resolve through the frozen predecessor reference and current reuse receipts;
- self-audit, comparison, reader expectations, and narrative remain native calls of the recovered run;
- qualification, independent review, release, lineage, candidate bytes, and every fingerprint still match.

The logical journal fingerprint combines the recovered run's native journal, the confirmed-prefix fingerprint, and the three reuse-receipt fingerprints. This preserves provenance without pretending old work happened in the new run.

## 07 · Failure, rollback, and non-goals

Recovery fails closed on evidence drift, changed Context, changed repair source, authorization mismatch, budget exhaustion, malformed new output, independent-review failure, or cancellation. It does not fall back to a full draft and does not dispatch a replacement call automatically.

Rollback disables new confirmed-prefix registrations and preserves every old/new checkpoint, receipt, event, call row, and budget entry. Existing runs remain inspectable.

Non-goals:

- automatic semantic retry or JSON repair;
- increasing an existing run's immutable call limit;
- copying or reassigning historical model calls;
- reusing an old independent review;
- accepting, settling, or promoting Canon;
- treating deterministic tests as literary approval.

## 08 · Forward supersession of specification 032

Specification 032 remains authoritative for durable pending transport and its no-automatic-retry rule. This specification narrowly supersedes its statement that a confirmed old terminal-format failure can only be handled by an entirely fresh graph. The new graph is still a fresh, user-authorized run, but it may reference an exact closed prefix after Core revalidation. It does not convert the old attempt into a live worker, repair its output, or add unapproved calls.

## 09 · Normative requirements

- `CPR-001`: require explicit user authorization and an idempotency key.
- `CPR-002`: accept identity references only; derive all private evidence in Core.
- `CPR-003`: require the exact closed five-call source topology and syntax-failure boundary.
- `CPR-004`: reject any evidence drift before dispatch.
- `CPR-005`: never copy old stage-call rows into the new run.
- `CPR-006`: charge only the four new manager calls and one separate independent review.
- `CPR-007`: do not re-consume the historical one-off craft pack.
- `CPR-008`: preserve future author-revision verification through a logical journal.
- `CPR-009`: retain no automatic retry, no acceptance, no settlement, and no Canon authority.
- `CPR-010`: keep ordinary CI model-free.

## 10 · Completion truth

Engineering completion requires deterministic recovery, tamper, budget, no-copy, future-revision, durable-pending, and regression tests. Live completion additionally requires the exact CH001 run to make only four new main calls, pass one fresh independent review, reconcile the active budget epoch, and expose an unaccepted, unsettled Review Draft through Core.

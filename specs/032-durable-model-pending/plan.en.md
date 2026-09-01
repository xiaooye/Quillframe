# Durable model pending implementation plan

2026-08-31 · `SYSTEM-IMPROVE` followed by an authorized CH001 `REVISE`.

## Phase 1 · Freeze the current state

Record the source snapshot, active run/worker inventory, manager ledger, reset budget epoch, revision request, and candidate fingerprints. Do not mutate historical rows.

Rollback point: no runtime or production mutation.

## Phase 2 · Separate waiter and worker lifetime

Add stable request keys, v3 durable packets, short HTTP pending responses, process heartbeats, and terminal worker state. Keep ordinary unkeyed calls bounded.

Rollback point: disable v3 routing before any v3 packet is launched.

## Phase 3 · Make production resume consume-once

Persist pollability before dispatch, preserve a pending stage row across executor leases and elapsed waiter deadlines, and resume only the exact frozen job. Expose safe text-free pending metadata through the native runner.

Rollback point: drain/reconcile all v3 workers, then restore confirmed-only synchronous resume.

## Phase 4 · Verify deterministic boundaries

Run model, Agent, relay, journal, author-revision, native-runner, and production-runtime tests. Prove no duplicate publication, launch, row, charge, or result consumption.

Rollback point: retain evidence and do not start a live run.

## Phase 5 · Synchronize contracts and operator docs

Publish paired specification, plan, tasks, verification, Model Runtime, and Agent Runtime documentation. Preserve specification 027 as historical evidence and document forward supersession.

Rollback point: revert documentation and code together; never rewrite historical ledgers.

## Phase 6 · Execute the authorized REVISE

Create a REVISE-scoped one-off craft pack, register the exact author-revision source through Core, cap main calls at 12 with one separate independent-review reserve, and execute/poll until the manager graph reaches external review.

Rollback point: stop before registration, or explicitly cancel the new run. Never reuse the consumed DRAFT pack.

## Phase 7 · Fresh independent review and release

Dispatch one fresh packet-only reviewer invocation, preserve exact judgment bytes, complete the Core review gate, and read only the released unaccepted Review Draft. Do not accept or settle it.

Rollback point: leave the run at `awaiting_external`; do not fabricate or reuse old review evidence.

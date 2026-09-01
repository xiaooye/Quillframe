# Confirmed-prefix recovery implementation plan

2026-08-31 · `SYSTEM-IMPROVE`, then the explicitly authorized CH001 evidence-resume `REVISE`.

## Phase 1 · Freeze the recovery boundary

Read the quiescent source run, exact five-call graph, terminal syntax failure, repair source, Context, repair plan, receipts, candidate fingerprint, active budget epoch, and user authorization. Do not mutate the source run.

Rollback point: no new run or model call exists.

## Phase 2 · Register a Core-owned reference

Accept four identity fields only. Re-derive the prefix inside the registration transaction, bind it to the same repair source, and persist a separate recovery-authorization receipt.

Rollback point: reject registration before inserting the new run when any identity or evidence differs.

## Phase 3 · Materialize reuse without copying calls

Revalidate current Context compatibility, persist current-run reuse receipts and a deterministic reuse checkpoint, and seed the exact candidate, Reader binding, and continuity evidence in memory. Do not consume the old style pack or insert historical calls into the new journal.

Rollback point: leave the new run model-free if materialization fails.

## Phase 4 · Preserve future provenance

Teach repair-source and author-revision verification to reconstruct a logical journal from native new calls plus predecessor references. Resolve causal scene and Reader-pressure evidence recursively from verified parent sources.

Rollback point: do not release a candidate that cannot become a valid future revision source.

## Phase 5 · Verify deterministic boundaries

Test the exact four-call remainder, changed-reference rejection before dispatch, old-journal immutability, zero charges for reused stages, future revision, ordinary semantic failure, durable pending, and production regressions. Run documentation QA.

Rollback point: keep live production stopped.

## Phase 6 · Execute CH001

Deploy the verified snapshot to the isolated runtime. Register one fresh run with the user's `confirmed_prefix_recovery` authorization and `max_model_calls=4`. Poll only exact durable pending requests until the manager graph reaches external review.

Rollback point: do not silently create a replacement run or expand the frozen limit.

## Phase 7 · Fresh independent review and delivery

Launch one packet-only independent reviewer, preserve its exact evidence, let Core release only an unaccepted Review Draft, and reconcile the active epoch and historical ledger separately. Do not accept or settle the candidate.

Rollback point: retain `awaiting_external` or failed independent evidence without reviewer shopping.

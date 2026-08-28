# Bounded deadlines for long generation

2026-08-28 · Primary mode: `SYSTEM-IMPROVE` · Implementation checkpoint; production release remains unverified.

## Observed failure

A production run on `e191fd7` completed eighteen model stages, then its prose-generation worker reached the configured 150-second limit without returning a final message. The relay returned HTTP 504 after 170 seconds. Core retained the failed result and released no candidate. This establishes a transport timeout, not a literary rejection or proof that a longer request will succeed.

## Scope

Carry a bounded request deadline from the Agent job through Model Runtime and the local relay to the CLI worker. Permit an explicit longer allowance for the two stages that generate complete prose. Keep ordinary request defaults and all call, token, identity, permission, persistence, and release bounds.

Python owns these timing and identity checks. Narrative choices, applicable writing constraints, quality judgments, and repair decisions remain AI responsibilities. No instruction, required evidence, prose target, or review criterion is removed to make a request finish sooner.

## Contract

1. An optional `AgentBudget.max_model_request_ms` binds an explicit per-request limit into the job fingerprint. When absent, serialization and the existing 180-second default remain unchanged. The actual request is bounded by both this limit and the job's remaining elapsed budget. Invalid types, nonpositive values, and values above 600,000 milliseconds are rejected.
2. Only `event_first_raw_draft` and `surface_realization` explicitly receive a 600,000-millisecond request and elapsed budget in production. Each still permits one model request, with unchanged token and tool bounds. Other stages retain their existing budgets.
3. Model Runtime permits finite positive request timeouts up to 600 seconds; its default remains 180 seconds. The HTTP transport does not retry. A POST to a literal loopback address or `localhost` carries `X-Quillframe-Deadline-Unix-Ms`, derived from the actual request budget. Transport freezes its local deadline at entry; the wire deadline may only narrow before dispatch so a wall-clock rollback cannot grant the relay more time than the caller has left. This HTTP budget has a different time origin from the enclosing journal deadline, which remains an additional acceptance boundary. No deadline metadata is added to model messages, request-body semantics, or remote-provider headers.
4. Relay startup has an explicit finite positive server cap, defaulting to 170 seconds and bounded above by 590 seconds. A caller deadline can only shorten that cap, leaving ten seconds for the caller to receive the response. A request without the header cannot silently acquire a longer allowance than the ordinary 170-second default.
5. The current relay packet freezes its creation and absolute expiry. Before publishing the packet, the relay may only narrow its timeout and expiry to the remaining wall-clock and monotonic allowance. The original creation time, caller deadline, and server cap remain unchanged; the timeout must not exceed the initial cap, and expiry must equal original creation time plus that timeout. A nonpositive export is rejected, never rebased. The CLI driver uses the exported expiry throughout admission, preparation, execution, and publication; queue delay and schema preparation do not restart the clock. Its worker default remains 150 seconds, with an explicit maximum of 570 seconds and a five-second publication reserve. A process-local monotonic deadline also prevents a backward wall-clock adjustment from extending admitted work.
6. Deadline evidence accompanies the original request and attempt records. Expired or malformed requests do not launch a worker. Late or incomplete output is not submitted as success. Every launched or failed attempt remains charged; no automatic retry, old-result replacement, or recovery shortcut is introduced.

## Compatibility and rollback

The local relay and CLI evidence move to version 2. New execution requires the current packet; old packets and receipts remain immutable historical evidence, not inputs for a compatibility adapter. The native project contract remains 1.0, and semantic worker contracts and literary rubrics do not change.

The rollback baseline is `e191fd7`. Source replacement requires an inactive executor and a new run with exact source binding. A rollback does not rewrite old results, timestamps, candidates, or cumulative spending. A larger time allowance is not authorization for additional model calls.

## Acceptance

Tests must cover unchanged ordinary-job fingerprints and defaults, explicit budget fingerprints, invalid values, remaining-time clamping, unchanged model messages, loopback-only header propagation, server/caller/worker deadline ordering, delayed admission and preparation, monotonic expiry, no dispatch after expiry, no late publication, no retry, and preserved failed results. Normal CI performs no model execution. A complete real production run and independent review remain separate requirements before claiming a released manuscript.

## Non-goals

No semantic retry API, asynchronous job architecture, new provider, lower reasoning effort, reduced manuscript requirements, automatic acceptance, settlement, cloud deployment, or remote push.

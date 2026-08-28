# Hosted authoring closure

The product acceptance target is a complete browser journey on a hosted service: sign in, create a project, write with a real model, obtain independent review, explicitly accept, settle, and download a publication. Linux is an implementation requirement of the Core container, not a requirement on the reader's or author's computer. A local WSL installation, static Studio preview, mocked model, or successful container import does not satisfy this target.

## Specification

Keep the existing topology: Studio, a same-origin Cloudflare Worker BFF, WorkOS, WorkspaceCoordinator, SessionVault, encrypted R2 bundles, and the Python Core container. Preserve the Host Bridge v11, canonical SQLite authority, CH001 scope, exact fingerprints, explicit acceptance, independent review, and separate settlement boundaries.

Cloud-native project creation authorizes storing that new project in the user's cloud workspace. It does not authorize uploading unrelated local projects. Restoring a current native snapshot after a container restart is runtime recovery, not a legacy project migration or a local/cloud synchronization feature.

A hosted write may be reported as durable only when its exact native state is recoverable after the container stops. Container `/tmp` is execution storage, not sufficient durability evidence. Model credentials must use the server secret boundary, and hosted endpoint validation must govern the connection actually used by Core. Browser input must not supply trusted workspace identity, Core proof, reviewer identity, or release receipts.

Real GPT subagents may be dispatched by an interactive host during acceptance testing. The deployed service still needs its own authenticated model execution and independent-review dispatcher; it cannot depend on this development conversation remaining active. A generation relay does not provide independent-review evidence.

The current execution order is local production acceptance first, then hosted acceptance. The local run must exercise real Core storage, real GPT generation, a fresh independent reviewer, explicit acceptance, settlement, and the exact publication artifact. A local pass does not close the hosted persistence or deployment gates below.

## Reproduced integration gaps

- C01 repaired the mismatched BFF path, missing CSRF, and non-canonical hosted request bytes.
- C01 also repaired JavaScript integer-key ordering and preservation of special own keys without invoking prototype setters; the cross-language tests use the Python protocol and Cloud parser.
- C02 corrected the Container image from a directory to its Dockerfile and checked it with the pinned CLI.
- C03 adds explicit authenticated Studio bootstrap and a single asset/API routing owner. Session lifecycle and browser delivery still require verification.
- `project.create` is forwarded without establishing a workspace project pointer. The next project-scoped request therefore fails its binding check.
- R2 upload/read verify or return native backups but do not restore a running Core's project state. The current container directory does not establish restart durability.
- Hosted model commands are not connected to SessionVault leases and destination-bound endpoint validation. Independent review needs a deployed dispatcher.
- C06 now restores exact matching acceptance and settlement receipts from Core and resolves the settlement target through the manuscript's stored chapter association. The bounded receipt window cannot prove absence; missing associations block settlement. Publication still needs a verified downloadable artifact, not only an internal path.

## Implementation plan

1. Repair transport and deployment configuration against the existing contracts, with failing regression tests first. Do not auto-bind a static preview or relax authentication to obtain green tests.
2. Add the same-origin authenticated Studio bootstrap and unambiguous asset/API routing. Verify sign-in, expiry, CSRF, logout, and an unbound static build separately.
3. Define and implement atomic workspace/project creation, native snapshot persistence and recovery, and mutation acknowledgement. Exercise concurrent requests, failed uploads, lost acknowledgements, restart, and deletion before using real manuscript data.
4. Bind model credentials and endpoint validation to the actual Core executor. Add a server-owned independent-review dispatch path with frozen packets and actual invocation identities.
5. Restore acceptance/settlement from Core and expose publication download only for the exact verified artifact.
6. Run the complete hosted browser journey with a fresh account session and real generation/review. Restart the container and reopen the project; verify that project state, accepted text, settlement, and downloaded bytes remain bound to their receipts.

## Task ledger

- [x] C01 Repair hosted request path, CSRF, canonical bytes, and cross-language serialization regressions.
- [x] C02 Validate the Container Dockerfile and build context with the pinned deployment CLI.
- [~] C03 Implement authenticated Studio bootstrap and same-origin deployment routing.
- [ ] C04 Implement project pointer creation and durable Core snapshot recovery.
- [ ] C05 Connect hosted secrets, endpoint policy, model execution, and independent review.
- [~] C06 Recover accepted/settled state and deliver verified publication downloads.
- [!] C07 Verify a real Cloudflare/WorkOS deployment and the complete hosted browser journey. Containers entitlement, R2 activation, WorkOS configuration, and the preceding implementation work remain required. Hosted deployment is paused while local production acceptance takes priority.

T409, T606, and T607 remain unresolved. Version identities remain `1.0.0-dev.0`. Deterministic transport tests do not mark C07 or a release gate complete.

## Verification and rollback

Use existing Studio, Cloud, Python Core, persistence, and publication tests. Run Linux storage tests as the container's non-root user on its actual filesystem; do not replace locks, secure file operations, or the user identity to make tests pass. Record real hosted session, restart, model, review, acceptance, settlement, and artifact evidence separately from test fixtures.

Rollback transport/configuration changes together with their consumers. Keep any new durable lifecycle unpublished until failure recovery is verified; preserve existing project snapshots and never substitute ephemeral state for a failed restore.

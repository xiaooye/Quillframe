# Plan
1. Freeze live main and the concurrent-owner map; keep Studio consumer PR #130 isolated from Core implementation.
2. Add production runtime contracts and an immutable Context payload bundle bound to Context Freeze.
3. Add tracked Project Context source loading, semantic profile derivation, Context Decision/Greenlight/Freeze orchestration.
4. Execute every mandatory production mechanism from frozen stage payload only; gate Candidate persistence behind pre-independent qualification, a genuine external `quality.production_review`, and the user-visible gate.
5. Add explicit Context refresh/supersession and stale-conflict handling.
6. Add a Model Service facade over the existing Generic Model Runtime; do not create provider-specific product truth.
7. Advance the typed Core Host Bridge through v8 with production/model/document primitives plus canonical project/document listing, Candidate Review projection, Reject, Request Revision, and read-only Settlement preflight.
8. Keep Request Revision durable but non-automatic: it must not silently start a REVISE run.
9. Harden credential output handling and fix SQLite connection lifetime hygiene in owning persistence layers.
10. Add deterministic/integration/security/backward-compatibility tests and run full Core, Studio and docs/site CI.
11. Verify the exact clean runtime tree with deterministic Framework bundle double-build and exact fingerprint verification.
12. Attempt live semantic acceptance only if the current host has an eligible configured provider; otherwise record `PENDING_MODEL / awaiting_external` without treating fixtures as live evidence.
13. Produce the v8 frontend contract handoff for Studio PR #130, clear review/security gates, merge the Core PR only after explicit authorization, then rebase/integrate the Studio consumer against fresh main.

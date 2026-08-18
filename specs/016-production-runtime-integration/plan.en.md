# Plan
1. Freeze live main and concurrent-owner map; keep UI PR #129 isolated.
2. Add production runtime contracts and immutable Context payload bundle.
3. Add tracked Project Context source loader, profile derivation, Context Decision/Greenlight/Freeze orchestration.
4. Execute each mandatory mechanism from frozen stage payload only; gate Candidate persistence behind independent review and user-visible gate.
5. Add explicit Context refresh and stale-conflict handling.
6. Add Model Service facade over existing Model Runtime; do not create provider-specific product state.
7. Advance Core Host Bridge contract with run/model/document primitives and explicit unsupported capability projection.
8. Fix SQLite connection lifetime hygiene in owning persistence layers.
9. Add deterministic/integration/security/backward-compat tests and run full CI.
10. Attempt live semantic acceptance only if current host has an eligible configured provider; otherwise record PENDING_MODEL.
11. Produce frontend contract handoff for UI PR #129 and open a Draft PR. Do not merge.

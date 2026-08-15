# 008 Plan · State Integrity P0

1. Freeze current Framework `main` exact base; do not change downstream Project locks.
2. Implement #69 as a stdlib-only deterministic resolver plus JSON schema.
3. Discover optional Project policy only through the existing safe `paths` map.
4. Add regression fixtures for writer escalation, Settlement routing, derived authority, mixed reconciliation, UI editability, and legacy compatibility.
5. Advertise the contract in `HARNESS_MANIFEST.yaml` and add public CI.
6. Review exact diff and merge only with green deterministic CI.
7. Only then implement #63 propagation debt against the settled #69 boundary.

Rollback: remove the optional path/tool and revert the Framework commit; Projects without the path are behaviorally unchanged.

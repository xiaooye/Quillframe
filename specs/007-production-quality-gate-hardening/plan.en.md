# Plan · Production Quality Gate Hardening

1. Add `quality/taxonomy.json` plus a compatibility scanner, with deterministic self-tests that keep Framework human documentation aligned with the machine registry.
2. Register `reader.engagement_audit` and `quality.production_review` in the quality semantic pack.
3. Harden `quality/production_readiness.py`: mandatory independent PASS/FAIL is derived from a validated registered semantic result; reject ad-hoc evals, caller status overrides, candidate mismatches, and fake independence.
4. Add `quality/repair_policy.py`: map upstream/cluster ownership to fresh realization and isolate rejected prose plus concrete surface patches.
5. Add synthetic contract tests / CI while preserving ordinary blind `eval_judge` use.
6. After Framework merge and a new exact commit/bundle exist, migrate the consuming Project explicitly; repair stale HF/RG references and add a Project-owned regression against checklist-compliant synthesis before the new gates become production authority.

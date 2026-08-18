# Plan 014 — Semantic Context Runtime

1. Freeze current Quillframe `main` and Shujuku `main`; inventory current Context, Agent Runtime, Model Runtime, Canon/Character/Story, persistence, Control Plane and Host Bridge contracts.
2. Add deterministic `harness/context_runtime.py` for profile binding/staleness, lifecycle eligibility, candidate pools, exact decision validation, stage greenlights, hard-budget packing, freeze/refresh validation, typed query, mandatory graph validation and Inspector projection.
3. Add SQLite migration `002_semantic_context_runtime.sql` plus `ContextRepository` for derived profiles, manual overrides, stage selections and freezes. Preserve existing `context_manifests` as compatibility projection.
4. Extend semantic worker catalog with `context.profile_derive` and `context.stage_select`; keep existing `context.select` intact.
5. Expose the Context runtime through Quillframe CLI/tool inventory and one read-only Studio Host Bridge projection operation. Do not change Studio UI.
6. Update Context docs and Harness manifest with the new authority-first pipeline and Shujuku-vs-Quillframe design record.
7. Add deterministic/integration tests covering all required Context invariants, native SQLite migration/doctor/backup/restore, and host bridge projection.
8. Run Context self-test, full `test_quillframe_*.py`, Agent/Model Runtime tests, Host Bridge self-test, Quillframe aggregate self-test, bundle/release verification and GitHub CI. Treat any failure as incomplete.

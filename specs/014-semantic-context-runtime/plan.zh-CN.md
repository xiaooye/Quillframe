# Plan 014 — 语义上下文运行时

1. 冻结 Quillframe 当前 `main` 与 Shujuku 当前 `main`；盘点 Context、Agent Runtime、Model Runtime、Canon/Character/Story、Persistence、Control Plane、Host Bridge 的真实 contracts。
2. 新增 deterministic `harness/context_runtime.py`：profile fingerprint/stale、lifecycle eligibility、candidate pool、exact model-id validation、stage greenlights、hard budget、freeze/refresh、typed query、mandatory graph validation、Inspector projection。
3. 新增 SQLite migration `002_semantic_context_runtime.sql` 与 `ContextRepository`，持久化 derived profiles、manual overrides、stage selections、freezes；现有 `context_manifests` 继续作为兼容 projection。
4. Semantic worker catalog 新增 `context.profile_derive` 与 `context.stage_select`；保留现有 `context.select` backward compatibility。
5. 把 Context runtime 注册到 Quillframe Core CLI/tool inventory，并给 Studio Host Bridge 增加一个 read-only Context projection；不改 Studio UI。
6. 更新 Context docs 与 Harness manifest，记录 authority-first pipeline 与 Shujuku/Quillframe 差异。
7. 加 deterministic/integration tests，覆盖所有要求的 Context invariant、Native SQLite migration/doctor/backup/restore、Host Bridge projection。
8. 执行 Context self-test、完整 `test_quillframe_*.py`、Agent/Model Runtime、Host Bridge、Quillframe aggregate self-test、bundle/release verification 与 GitHub CI。任何失败都不得称完成。

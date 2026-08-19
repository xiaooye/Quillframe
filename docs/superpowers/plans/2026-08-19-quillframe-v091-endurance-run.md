# Quillframe v0.9.1 Endurance Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Restore the interrupted native-review work, finish Spec 022, narrow Quillframe to a novel-contract kernel with thin native-host adapters, run only CH001 through the real release-bound chain, and publish/verify v0.9.1 when every release and review gate is proven.

**Architecture:** Hosts own generic agent/session/model/tool execution. Quillframe owns novel authority, bounded context, candidate/review/release contracts, and acceptance/settlement boundaries. Project files remain the durable story authority; the local CH001 overlay is never pushed to a consumer remote or promoted to Canon.

**Tech Stack:** Python 3.11+/stdlib, SQLite/WAL migrations, unittest, existing Host Bridge/CLI, SolidJS/Tauri writer surface, deterministic bundle tooling, GitHub Actions and GitHub Release artifacts.

**Spec:** `specs/022-native-independent-review-runtime/spec.en.md`, `specs/022-native-independent-review-runtime/spec.zh-CN.md`, and the focused Phase 2 spec `specs/023-novel-native-host-boundary/` created before boundary implementation.

## Global Constraints

- Framework source remains project-agnostic; no Chinaboy facts enter Framework code, tests, docs, or release artifacts.
- `The host runs the agent. Quillframe governs the novel.` is the product boundary; embedded runtime is optional/reference/local-test infrastructure.
- Only CH001 may enter projection, Context, model invocation, draft, review, or release in this run; CH002/CH003 are excluded everywhere.
- Consumer remotes are read-only and untouched; the local overlay remains outside Framework commits/releases.
- `candidate.accept` and `settlement.apply` are forbidden; final CH001 must retain `accepted=false` and `settled=false`.
- No force push, branch-protection bypass, security/billing/permission changes, deletion of user worktrees/files, or reviewer shopping.
- Every material change uses RED → GREEN tests, an exact checkpoint commit, independent review, and current-head verification.
- Release claims require exact remote-main commit, tag, GitHub Release URL, artifact checksum re-download, install/doctor/self-test, and CI evidence; local artifacts never substitute for a GitHub Release.

### Task 1: Recover and verify the existing Task 1/Task 2 boundary ✅

**Files:** `harness/integrations/host_bootstrap.py`, `harness/semantic_workers/adapters/local_agent_adapter.py`, `harness/semantic_workers/semantic_worker_runner.py`, focused Task 2 tests.

- [x] Reconcile the current dirty diff against `a0f0a1555baf8046773fd3851d370513019668dc`; preserve all Task 1 files and isolate the incomplete Task 2 edits.
- [x] Restore one canonical native lifecycle hook implementation, using trusted host fields, one-time lease claim, fresh reviewer session, frozen packet-only context, JSON-only stop, and reviewer tool denial.
- [x] Bind local packet execution and result metadata to the frozen relay nonce; reject packet/result tampering or malformed output before any semantic result is accepted.
- [x] Run focused host/local/GitHub tests, then the clean Task 1/Task 2 suite. Checkpoint: `2bb6068`.

### Task 2: Complete Spec 022 Task 3 mapped projection ✅

**Files:** `production_runtime/project_projection.py`, `project_adapter.py`, `persistence/migrations/project/004_mapped_project_projection.sql`, `production_runtime/{sources,context,guarded_runtime}.py`, `core_operations.py`, `studio/host_bridge.py`, `studio/host_bridge_contract.json`, mapped projection tests.

- [x] Add explicit manifest validation and deterministic read-only preview.
- [x] Add transactional CAS apply, idempotent replay, source/target drift rejection, authority-escalation rejection, and projection status.
- [x] Materialize only declared bounded objects/sources with stage allowlists; keep Git/Markdown as authority and SQLite rebuildable.
- [x] Make start/execute preflight validate Project/node/document/manifest/source fingerprints before any model call; prove zero calls on all fail-closed paths.
- [x] Route mapped CLI preview/apply/status while preserving standard-layout schemas and behavior.
- [x] Commit after focused and full deterministic verification; checkpoint `ee70d2d` (migration compatibility included).

### Task 3: Complete Spec 022 Task 4 contracts and evidence ✅

**Files:** paired docs, machine manifests/contracts, rollback notes, bundle/reproducibility evidence, task reports.

- [x] Update paired English/Chinese docs and registries to describe native review as host lifecycle attestation, not cryptographic isolation.
- [x] Record exact fingerprints, migrations, compatibility policy, rollback, and Task 1–3 test totals in task reports.
- [x] Run docs QA, JSON/schema/version/namespace checks, py_compile, bundle double-build, and independent diff review. Checkpoint `ccd3cd5` plus reviewed fixes.

### Task 4: Phase 2 Quillframe Novel-Native Host Boundary ✅

**Files:** `specs/023-novel-native-host-boundary/spec.{en,zh-CN}.md`, `plan.{en,zh-CN}.md`, README/architecture/runtime/integration/Studio docs, MCP/Skill capability manifests, version surfaces, `CHANGELOG*`.

- [x] Write and self-review the focused spec/plan before implementation; explicitly classify novelist-facing, internal/ops, and privileged author surfaces.
- [x] Rewrite stale “Quillframe runs the agent” language without claiming embedded runtime deletion; state the host/kernel/project dependency direction.
- [x] Reuse existing operation names and schemas; expose default novelist operations for Project/context/author run/candidate/continuity, internal operations for session/event/handoff/leases/diagnostics, and privileged acceptance/settlement only behind explicit human receipts.
- [x] Freeze all version surfaces to 0.9.1, update changelog and truthful limitations, and record post-0.9.1 backlog without claiming deferred work released.

### Task 5: Minimal CH001 writer-facing review slice ✅

**Files:** existing SolidJS/Tauri/Host Bridge writer surfaces and tests only where needed for CH001.

- [x] Display the Core-backed candidate/review evidence surface and preserve exact framework/projection metadata contracts for the writer slice.
- [x] Keep raw candidate hidden before release; show text only via `candidate.visible.get`; expose reject/revision semantics while leaving accept/settlement privileged and untouched.
- [x] Verify keyboard/accessibility contract, zh-CN/en-US strings, loading/pending/failed/released/stale boundaries, no fake readiness, local web build, and relevant Studio tests. Tauri compile remains awaiting the local Rust toolchain; no site-wide redesign was performed.

### Task 6: Release candidate freeze and exact-head CI

**Files:** release workflows/scripts, bundle metadata, checksum/build reports, feature branch/PR.

- [ ] Run deterministic Python, Studio/site/docs/Tauri and contract suites on a clean feature commit.
- [x] Build the Framework bundle twice and require byte-identical output/fingerprint; verify and run unpacked doctor/self-test. Current checkpoint: `sha256:4a7c0abd7b88d3a522060a529b10b870ddc98682d75f1d51451ee4dbffe021aa`; the unpacked SDK/CLI self-test regression is covered by `BootstrapHostTests.test_unpacked_framework_bundle_runs_project_sdk_self_test`.
- [ ] Create/update the Quillframe PR, push only the non-force feature branch, wait for exact-head CI, repair real failures, and merge only after required checks are green.
- [ ] Re-read remote main exact commit and rebuild/verify the bundle after merge; record lock/attestation update for the local consumer overlay without pushing that overlay.

### Task 7: CH001-only production and human-review handoff

**Files:** a local consumer overlay runtime/evidence directory and a stable local handoff directory.

- [x] Validate exact local Framework commit/tree/bundle/lock/attestation; preview/apply/status the mapped projection and freeze a bounded CH001-only Context. The exact consumer-overlay evidence path is recorded in the local handoff ledger, not in the project-agnostic Framework tree.
- [x] Execute only `DESIGN-BOOK`, `DESIGN-VOLUME`, `PLAN-UNIT`, `PLAN-CHAPTER`, then `DRAFT(CH-001)` and its deterministic/semantic gates. The four planning records are setup-state records; no unproven model output is claimed for them. Raw candidate remained internal.
- [x] Perform exactly one real Codex native independent review. Claude native was integration-tested only and did not review the same candidate.
- [x] On PASS, call only `candidate.visible.get`, save the Review Draft and handoff report, and prove `accepted=false`, `settled=false`. Exact Review Draft/handoff paths remain local consumer artifacts and are emitted in the final evidence report, not copied into Framework sources.
- [x] Prove CH002/CH003, future identities, bad examples, unproven images, and consumer remotes were not accessed or invoked for this chain; Frostloom remote remained untouched.

### Task 8: v0.9.1 tag, GitHub Release, and post-release recovery

**Files:** exact release commit/tag/artifacts and temporary verification directory.

- [ ] Recheck remote main, CI, clean status, version surfaces, bundle fingerprint, and CH001 non-Canon status; ensure `v0.9.1` does not already exist.
- [ ] Create and push `v0.9.1`, create the GitHub Release, and upload deterministic bundle, build report, checksum manifest, and release metadata.
- [ ] Re-download the published artifacts into a new temporary directory; verify checksums, unpack/install, doctor, SDK self-test, MCP/Bridge smoke, and Release→tag→main identity.
- [ ] Produce the final report with release URL, PR/CI URLs, commit/tag/artifact fingerprints, tests, CH001 handoff paths, architecture boundaries, known limitations, rollback, retained worktrees/branches, and one truthful awaiting-user/external blocker if any.

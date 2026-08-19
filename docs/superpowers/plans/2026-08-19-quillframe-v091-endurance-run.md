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

### Task 1: Recover and verify the existing Task 1/Task 2 boundary

**Files:** `harness/integrations/host_bootstrap.py`, `harness/semantic_workers/adapters/local_agent_adapter.py`, `harness/semantic_workers/semantic_worker_runner.py`, focused Task 2 tests.

- [ ] Reconcile the current dirty diff against `a0f0a1555baf8046773fd3851d370513019668dc`; preserve all Task 1 files and isolate the incomplete Task 2 edits.
- [ ] Restore one canonical native lifecycle hook implementation, using trusted host fields, one-time lease claim, fresh reviewer session, frozen packet-only context, JSON-only stop, and reviewer tool denial.
- [ ] Bind local packet execution and result metadata to the frozen relay nonce; reject packet/result tampering or malformed output before any semantic result is accepted.
- [ ] Run focused host/local/GitHub tests, then the 146-test clean Task 1 suite after the Task 2 checkpoint. Commit only the coherent Task 2 surface.

### Task 2: Complete Spec 022 Task 3 mapped projection

**Files:** `production_runtime/project_projection.py`, `project_adapter.py`, `persistence/migrations/project/004_mapped_project_projection.sql`, `production_runtime/{sources,context,guarded_runtime}.py`, `core_operations.py`, `studio/host_bridge.py`, `studio/host_bridge_contract.json`, mapped projection tests.

- [ ] Add explicit manifest validation and deterministic read-only preview.
- [ ] Add transactional CAS apply, idempotent replay, source/target drift rejection, authority-escalation rejection, and projection status.
- [ ] Materialize only declared bounded objects/sources with stage allowlists; keep Git/Markdown as authority and SQLite rebuildable.
- [ ] Make start/execute preflight validate Project/node/document/manifest/source fingerprints before any model call; prove zero calls on all fail-closed paths.
- [ ] Route mapped CLI preview/apply/status while preserving standard-layout schemas and behavior.
- [ ] Commit after focused and full deterministic verification; do not modify Task 1/2 semantics.

### Task 3: Complete Spec 022 Task 4 contracts and evidence

**Files:** paired docs, machine manifests/contracts, rollback notes, bundle/reproducibility evidence, task reports.

- [ ] Update paired English/Chinese docs and registries to describe native review as host lifecycle attestation, not cryptographic isolation.
- [ ] Record exact fingerprints, migrations, compatibility policy, rollback, and Task 1–3 test totals in task reports.
- [ ] Run docs QA, JSON/schema/version/namespace checks, py_compile, bundle double-build, and independent diff review. Commit the Task 4 evidence checkpoint.

### Task 4: Phase 2 Quillframe Novel-Native Host Boundary

**Files:** `specs/023-novel-native-host-boundary/spec.{en,zh-CN}.md`, `plan.{en,zh-CN}.md`, README/architecture/runtime/integration/Studio docs, MCP/Skill capability manifests, version surfaces, `CHANGELOG*`.

- [ ] Write and self-review the focused spec/plan before implementation; explicitly classify novelist-facing, internal/ops, and privileged author surfaces.
- [ ] Rewrite stale “Quillframe runs the agent” language without claiming embedded runtime deletion; state the host/kernel/project dependency direction.
- [ ] Reuse existing operation names and schemas; expose default novelist operations for Project/context/author run/candidate/continuity, internal operations for session/event/handoff/leases/diagnostics, and privileged acceptance/settlement only behind explicit human receipts.
- [ ] Freeze all version surfaces to 0.9.1, update changelog and truthful limitations, and record post-0.9.1 backlog without claiming deferred work released.

### Task 5: Minimal CH001 writer-facing review slice

**Files:** existing SolidJS/Tauri/Host Bridge writer surfaces and tests only where needed for CH001.

- [ ] Display Project/CH001, exact Framework commit/bundle, projection/context readiness, true gate state, reviewer provenance/receipts, candidate fingerprint, and acceptance/settlement booleans.
- [ ] Keep raw candidate hidden before release; show text only via `candidate.visible.get`; expose reject/revision semantics while leaving accept/settlement privileged and untouched.
- [ ] Verify keyboard/accessibility, zh-CN/en-US, loading/pending/failed/released/stale states, no fake readiness, local web build, relevant Studio tests, and Tauri contract smoke. Do not perform a site-wide UI redesign.

### Task 6: Release candidate freeze and exact-head CI

**Files:** release workflows/scripts, bundle metadata, checksum/build reports, feature branch/PR.

- [ ] Run deterministic Python, Studio/site/docs/Tauri and contract suites on a clean feature commit.
- [ ] Build the Framework bundle twice and require byte-identical output/fingerprint; verify and run unpacked doctor/self-test.
- [ ] Create/update the Quillframe PR, push only the non-force feature branch, wait for exact-head CI, repair real failures, and merge only after required checks are green.
- [ ] Re-read remote main exact commit and rebuild/verify the bundle after merge; record lock/attestation update for the local consumer overlay without pushing that overlay.

### Task 7: CH001-only production and human-review handoff

**Files:** a local consumer overlay runtime/evidence directory and a stable local handoff directory.

- [ ] Validate exact release commit/tree/bundle/lock/attestation; preview/apply/status the mapped projection and freeze a bounded CH001-only Context.
- [ ] Execute only `DESIGN-BOOK`, `DESIGN-VOLUME`, `PLAN-UNIT`, `PLAN-CHAPTER`, then `DRAFT(CH-001)` and its deterministic/semantic gates. Keep raw candidate internal.
- [ ] Perform exactly one real Codex native independent review. Claude native is integration-tested only and never reviews the same candidate.
- [ ] On PASS, call only `candidate.visible.get`, save the Review Draft and handoff report, and prove `accepted=false`, `settled=false`. On valid reject, create a fresh candidate (maximum three attempts) without reviewer shopping; on infrastructure failure, retry only under the contract.
- [ ] Prove CH002/CH003, future identities, bad examples, unproven images, and consumer remotes were not accessed or invoked.

### Task 8: v0.9.1 tag, GitHub Release, and post-release recovery

**Files:** exact release commit/tag/artifacts and temporary verification directory.

- [ ] Recheck remote main, CI, clean status, version surfaces, bundle fingerprint, and CH001 non-Canon status; ensure `v0.9.1` does not already exist.
- [ ] Create and push `v0.9.1`, create the GitHub Release, and upload deterministic bundle, build report, checksum manifest, and release metadata.
- [ ] Re-download the published artifacts into a new temporary directory; verify checksums, unpack/install, doctor, SDK self-test, MCP/Bridge smoke, and Release→tag→main identity.
- [ ] Produce the final report with release URL, PR/CI URLs, commit/tag/artifact fingerprints, tests, CH001 handoff paths, architecture boundaries, known limitations, rollback, retained worktrees/branches, and one truthful awaiting-user/external blocker if any.

# Phase 0 Recovery Report · 2026-08-19

## Current checkpoint

- Framework worktree: `/var/home/pc/Documents/Quillframe-native-independent-review-runtime`
- Branch: `codex/native-independent-review-runtime`
- HEAD: `a0f0a1555baf8046773fd3851d370513019668dc`
- Origin feature head: `6bff852` (remote is not treated as the current implementation)
- Framework main worktree: `/var/home/pc/Documents/Quillframe`, HEAD `bc09df8cc08fecd163706ca2c2cffd985e131791`
- Local consumer overlay: `/var/home/pc/Documents/card/new cards/chinaboy_webnovel_quillframe`
- Stale CLI writer: exact `codex resume` PID `6130` held the target thread lock; it was terminated and the lock had no remaining owner.
- Bootstrap: isolated `SYSTEM-IMPROVE` manager session `SES-CODEX-465bae512cd78ebc01b3e44d`, run `RUN-HOST-2dd30b9f1fb04396aec2f437fe6d39ce`, runtime DB `/tmp/quillframe-endurance-recovery-runtime.db`.

## Rules and scope confirmed

The bilingual AGENTS, HARNESS_MANIFEST, SKILL, Harness Agent, Orchestration, Session Runtime, Project SDK, and Spec 022 contracts were read. Framework source remains project-agnostic; the host owns generic agent/model/tool execution; Quillframe owns the novel contract kernel; Project files own concrete story authority. CH002/CH003, Frostloom remote, `candidate.accept`, and `settlement.apply` are excluded.

## Preserved work

Task 1 is complete and independently reviewed at `a0f0a1555baf8046773fd3851d370513019668dc`; its clean-commit evidence is 46 focused tests and 146 full `test_quillframe_*.py` tests. Its migration/provider/recovery compatibility policy is retained. Task 3 and Task 4 are not yet implemented.

## Dirty Task 2 state

The current worktree contains uncommitted Task 2 changes in the host scaffold/SDK, host configuration, local packet adapter/runner, and GitHub transport/tests. The focused diagnostic command was:

```bash
python -m unittest tests.test_quillframe_unified_host_bootstrap tests.test_quillframe_bootstrap_host tests.test_quillframe_ephemeral_chat_host tests.test_quillframe_native_local_packet -v
```

It ran 34 tests with 2 assertion failures and 6 errors. The actionable failures are:

1. `harness/integrations/host_bootstrap.py` dispatches `native_reviewer_hook` but the canonical hook implementation was accidentally removed; trusted SubagentStart/Stop tests fail and real CLI routing raises missing-symbol errors.
2. `semantic_worker_runner.py` has no `invoke_frozen_packet`, and local packet execution returns no `worker` result binding; nonce/result tamper coverage is incomplete.
3. Four exact-pin bootstrap tests fail only because the checkout is intentionally dirty; they must be rerun after a clean checkpoint, not weakened.

The generated SDK/host artifacts and GitHub provider-truth tests currently pass in the focused run. No projection or CH001 files were changed by this recovery step.

## Recovery order

1. Restore one canonical native hook and exact local packet runner with RED→GREEN tests.
2. Review and commit Task 2 only; rerun the clean Task 1/Task 2 matrix.
3. Implement and review Spec 022 Task 3 mapped projection/CAS/preflight.
4. Complete Task 4 paired docs/contracts/evidence.
5. Write/self-review the Phase 2 Novel-Native Host Boundary spec/plan and implement only the minimal v0.9.1 boundary/docs/version surface.
6. Freeze, build, verify, and CI the release candidate before any CH001 model call.
7. Repin the local CH001 overlay to exact v0.9.1, run only CH001, perform exactly one real Codex native review, and save only the released Review Draft through `candidate.visible.get`.
8. Publish and re-download v0.9.1 artifacts; final report must be truthful about any external approval or billing blocker.

This report is a resumable checkpoint; it does not claim Task 2, Task 3, CH001, CI, merge, tag, or release completion.

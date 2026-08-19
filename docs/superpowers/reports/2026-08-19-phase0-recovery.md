# Phase 0 Recovery Report · 2026-08-19

## Current checkpoint

- Framework worktree: `/var/home/pc/Documents/Quillframe-native-independent-review-runtime`
- Branch: `codex/native-independent-review-runtime`
- HEAD: `1866213215f02c9eedca771fc5b1b3ec982ebd25`
- Origin feature head: `1866213` (remote feature branch is synchronized)
- Framework main worktree: `/var/home/pc/Documents/Quillframe`, HEAD `bc09df8cc08fecd163706ca2c2cffd985e131791`
- Local consumer overlay: a separate consumer-owned checkout outside the Framework repository
- Stale CLI writer: exact `codex resume` PID `6130` held the target thread lock; it was terminated and the lock had no remaining owner.
- Bootstrap: isolated `SYSTEM-IMPROVE` manager session `SES-CODEX-465bae512cd78ebc01b3e44d`, run `RUN-HOST-2dd30b9f1fb04396aec2f437fe6d39ce`, runtime DB `/tmp/quillframe-endurance-recovery-runtime.db`.

## Rules and scope confirmed

The bilingual AGENTS, HARNESS_MANIFEST, SKILL, Harness Agent, Orchestration, Session Runtime, Project SDK, and Spec 022 contracts were read. Framework source remains project-agnostic; the host owns generic agent/model/tool execution; Quillframe owns the novel contract kernel; Project files own concrete story authority. CH002/CH003, consumer remotes, `candidate.accept`, and `settlement.apply` are excluded.

## Current recovery checkpoint

The Task 2 native host adapter, Task 3 mapped projection, Task 4 paired
contracts/evidence, and the minimal writer-facing release-boundary slice are
now committed. The latest independent-reviewable checkpoint is `1866213`,
which also fences stale Studio review responses when a writer switches
candidates during concurrent loads.

- Framework deterministic suite: 181/181 clean tests.
- Studio: 14/14 tests, typecheck, quality, and production build pass.
- Site: quality and static/docs build pass.
- Host Bridge v10, MCP, SDK, adapter, version, namespace, peer-bridge, and
  deterministic bundle self-tests pass.
- Framework bundle double-build at the current checkpoint: byte-identical
  fingerprint `sha256:901c3f242d5116b48dcdc3a6851e462b980ced36254bb301d084ab08ebb9770a`;
  403 files and 3,502,080 bytes; bundle verify passes.
- Exact-head PR #144 checks: Quillframe core, site/docs, SolidJS Studio, and
  Tauri 2 thin-host all pass. The separate GitHub Advanced Security agentic
  review is an external service failure (`claude-opus-4.6` unsupported), not a
  source finding; it remains explicitly awaiting external service recovery.

Remaining gates are intentionally not claimed complete: merge after the
external review check is resolved, post-merge main verification, local
CH001-only production and native Codex review, tag/Release publication, and
post-release artifact recovery. The current consumer overlay projection is
CH001-only and ready with `model_invocations=0`, `authority=false`, and
projection fingerprint
`sha256:403b2d2e4d9a51bc9f6cc2bdd7d470ef8a75990b97166c295037e09cc1316883`.

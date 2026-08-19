# Phase 0 Recovery Report · 2026-08-19

## Current checkpoint

- Framework worktree: `/var/home/pc/Documents/Quillframe-native-independent-review-runtime`
- Branch: `codex/native-independent-review-runtime`
- HEAD: `0775147828c8cfee4d0e1bf42fccc541067937fe`
- Origin feature head: `6bff852` (remote is not treated as the current implementation)
- Framework main worktree: `/var/home/pc/Documents/Quillframe`, HEAD `bc09df8cc08fecd163706ca2c2cffd985e131791`
- Local consumer overlay: a separate consumer-owned checkout outside the Framework repository
- Stale CLI writer: exact `codex resume` PID `6130` held the target thread lock; it was terminated and the lock had no remaining owner.
- Bootstrap: isolated `SYSTEM-IMPROVE` manager session `SES-CODEX-465bae512cd78ebc01b3e44d`, run `RUN-HOST-2dd30b9f1fb04396aec2f437fe6d39ce`, runtime DB `/tmp/quillframe-endurance-recovery-runtime.db`.

## Rules and scope confirmed

The bilingual AGENTS, HARNESS_MANIFEST, SKILL, Harness Agent, Orchestration, Session Runtime, Project SDK, and Spec 022 contracts were read. Framework source remains project-agnostic; the host owns generic agent/model/tool execution; Quillframe owns the novel contract kernel; Project files own concrete story authority. CH002/CH003, consumer remotes, `candidate.accept`, and `settlement.apply` are excluded.

## Current recovery checkpoint

The Task 2 native host adapter, Task 3 mapped projection, Task 4 paired
contracts/evidence, and the minimal writer-facing release-boundary slice are
now committed. The latest independent-reviewable checkpoint is `0775147`.

- Framework deterministic suite: 181/181 clean tests.
- Studio: 14/14 tests, typecheck, quality, and production build pass.
- Site: quality and static/docs build pass.
- Host Bridge v10, MCP, SDK, adapter, version, namespace, peer-bridge, and
  deterministic bundle self-tests pass.
- Framework bundle double-build: byte-identical fingerprint
  `sha256:38ee82a18a44cf602d8ccbabb790ab152381fa4604f34a9b34a75cc3d10bf575`.
- Known local tool limitation: `cargo` is not installed, so Tauri compilation
  remains a contract/static check until a Rust toolchain is available.

Remaining gates are intentionally not claimed complete: exact-head PR/CI and
merge, post-merge main verification, local CH001-only projection and native
Codex review, tag/Release publication, and post-release artifact recovery.

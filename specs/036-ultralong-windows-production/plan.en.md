# Windows Ultra-Long Production Implementation Plan

2026-08-31 · `SYSTEM-IMPROVE`

## Phase 1 · Freeze contracts and baselines

Register specification 036, freeze the Shujuku-to-Quillframe `shared/domain → data → service → presentation` mapping, and record the current Windows failure, production gaps, and frozen Corpus v2 boundary while preserving all concurrent worktree changes.

## Phase 2 · Secure Windows storage

Create the Rust workspace and a directly linked Core crate that owns the platform filesystem, SQLite, and Project 1.0. Implement handle-based traversal, no-reparse open, identity checks, exclusive creation, atomic replacement, durable flush, cross-process locking, and recovery for Windows; migrate the existing Linux security primitives into the same Rust contract and fail closed elsewhere.

## Phase 3 · Hierarchy and planning runtime

Expose book/volume/unit/chapter/scene nodes, four typed plan envelopes, and the complete Book Setup in domain. In data, implement setup proposals, exact author approval, book-plan binding, ancestor-dependency CAS, supersession, freeze evidence, and one manuscript document per chapter. Give planning modes real resumable semantic jobs in service.

## Phase 4 · Draft and revision closure

Drive recoverable scene-by-scene production from ordered chapter scenes. Route Reader Pressure, the full ancestor-plan lock, the approved Setup's private character/relationship decision projection, and semantic Context Freeze only to their owning stages. Character simulation and scene resolution remain model-owned; the Surface Writer receives only a fingerprint-bound Director Note without private reasoning. Deterministically enforce per-scene and whole-chapter minimum length, persist checkpoints/logs in data, and orchestrate independent-rejection repair sources, owner-layer invalidation, and Continuity-only summaries in service.

## Phase 5 · Corpus v2 execution and staged loading

Complete the append-resumable research runner, public atlas, publication registry, and production loader. Select zero to four cards per receiving stage with frozen bindings, then rebuild v2 holdout, LOO, leakage, and three-arm evaluations.

## Phase 6 · Long-range learning, lifecycle, and ledger

Bridge reasoned rejection/revision feedback, strengthen independent promotion receipts, settle narrative state through compact typed deltas, retain the latest four fully verified snapshots, and aggregate internal, independent-review, and Corpus research cost states.

## Phase 7 · Direct Studio integration and Python removal

Replace the Python sidecar with a Tauri host that directly links Rust Core. Migrate the CLI, local HTTP/API, and packaging path; remove Python packages, `pyproject.toml`, Python tests/CI, and every Python runtime prerequisite. Keep Node only in the Studio build chain.

## Phase 8 · Scale and release acceptance

Run security and recovery regression on real Windows and Linux, exercise bounded multi-chapter incremental and restart scenarios, and synchronize bilingual documentation. Queue the literary canary separately and report literary conclusions only with author and independent-review evidence.

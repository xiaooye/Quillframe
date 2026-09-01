# Windows Ultra-Long Fiction Production

2026-08-31 · `SYSTEM-IMPROVE` · Successor specification for web serials beyond five million Chinese characters.

This specification makes Windows a supported platform, clean-breaks Quillframe Core to Rust, and sets the long-range objective: reliably plan, draft, revise, review, settle, and maintain an ultra-long web serial exceeding five million Chinese characters. Scale is achieved through sparse, verified, recoverable state—not by placing an entire book in a model context.

## 01 · Definition of success

The system must provide all of the following:

- secure native 1.0 Project creation, open, locking, backup, recovery, and atomic publication by one Rust Core on Windows and Linux;
- addressable book, volume, unit, chapter, and scene nodes, with planning proposals becoming binding only after exact author activation;
- multi-scene chapters and Writer-visible Reader Pressure that remains hidden from Blind Reader and independent review;
- owner-layer revision, including impact analysis against later accepted chapters;
- a recoverable Corpus v2 runner, publication path, frozen production loader, evaluation path, and rollback, with zero to four source-free mechanisms selected per receiving stage.

The final distribution contains no Python and does not require Node at runtime. Deterministic acceptance proves these mechanisms, not the literary quality of a five-million-character novel. Literary evidence still requires a live long-range canary, genuinely independent semantic review, and author judgment.

## 02 · Native Windows security parity

Windows must preserve the security invariants of the POSIX implementation:

- reject symbolic links, junctions, mount points, and other reparse points at every path component;
- verify final object identity, type, link count, and expected parent from handles;
- use exclusive creation, same-volume atomic replacement, and durable flushes;
- prevent deletion or replacement while an object is open, while retaining cross-process locks, CAS, idempotent replay, and crash recovery;
- fail closed for traversal, alternate data streams, reserved device names, hard-link substitution, and races;
- keep unsupported platforms fail closed.

A dedicated Rust native core owns the Windows and Linux implementations. Business code may not scatter Windows branches that skip validation.

## 03 · Shujuku-layered full-Rust clean break

Quillframe adopts Shujuku's one-way layering principle, translated for a native fiction-production system:

```text
presentation · SolidJS Studio / Tauri commands / Rust Host API
      ↓
service      · planning, Context, production, review, revision, Settlement, Corpus, learning
      ↓
data         · SQLite repositories, transactions, checkpoint/log, locks, backup, recovery
      ↓
shared/domain· types, identity, fingerprints, authority, pure validation
```

Dependencies point downward only. `shared/domain` does not depend on storage, models, or UI; `data` does not make literary semantic judgments; `service` does not manipulate DOM or physical SQLite schema directly; `presentation` cannot bypass services to mutate a Project. Rust implements `shared/domain`, `data`, `service`, and the Tauri host. SolidJS implements presentation only. Node builds static Studio assets; it is not a product runtime, server, or durable authority.

This mapping adopts Shujuku's Repository, runtime-state, service orchestration, strict-read, snapshot/checkpoint, and commit-log ideas. It rejects SillyTavern DOM coupling, worldbook takeover, prompt SQL, a TypeScript/sql.js runtime, and chat-persona assumptions. The Tauri host links Rust services directly and no longer spawns a sidecar.

Migration is a clean break: no Python/Rust dual read or write, runtime fallback, adapter, or long-lived compatibility layer. The native `quillframe_project_v1_0` and its SQLite schema may remain stable and be implemented by Rust against the same checksum-known contract. Historical Python runs are frozen evidence only and do not become resumable Rust execution state.

Completion removes Python packages, `pyproject.toml`, the Python CLI/sidecar, Python tests/CI, and Python runtime requirements from product documentation. Python before-state may remain temporarily during migration, but dual-runtime availability is never the target architecture. A giant Rust module that simultaneously owns domain rules, SQL, orchestration, and Bridge routing does not satisfy the layered completion gate.

## 04 · Ultra-long story hierarchy

The sole hierarchy is `book → volume → unit → chapter → scene`. Each node has a stable identifier, parent, sibling order, lifecycle, and current plan version. Every chapter binds a real manuscript document; a scene is a causal and production target rather than an automatic standalone manuscript. `CH001` is only the initial node.

Deleting referenced nodes is outside this specification. Reordering requires explicit CAS and dependency impact evidence and must not rewrite historical runs.

## 05 · Four planning levels and author authority

Each planning mode owns a closed typed envelope:

- `DESIGN-BOOK`: reader promise, protagonist agency, central conflict, progression, endgame reserve, and anti-exhaustion limits;
- `DESIGN-VOLUME`: volume promise, net situation change, opposition, relationship movement, climax, and inherited debt;
- `PLAN-UNIT`: a closable loop, emotional setup–release–aftermath, rewards, delay costs, foreshadowing, and callbacks;
- `PLAN-CHAPTER`: reader question, visible reward, character choice and cost, net change, next pull, and ordered scene objectives.

Model output is first persisted as a fingerprint-bound proposal. Only explicit author activation of the exact proposal/version makes it active. Activation atomically supersedes the prior active plan for the same target. Proposals, drafts, and reviews never grant themselves planning authority.

## 06 · Production and revision closure

A chapter run consumes its active chapter plan, active ancestor plans, and semantically selected sparse long-range state. Targets must match typed forms—`book`, `volume:<id>`, `unit:<id>`, and `chapter:<id>`—without mixing raw IDs and typed references.

Ordered scenes retain character action ownership and causal closure. Writer execution may realize one scene or a coherent scene group, but the chapter candidate has one frozen fingerprint.

Reader Pressure becomes a compact Writer brief and participates in the Writer Pack fingerprint. An empty brief is valid; the system must not force a hook into every chapter. Blind Reader, independent review, and user-visible output never receive the brief or treatment identity.

Independent rejection creates a private repair source for the next REVISE run. A fresh Writer does not receive old reasoning, reviewer chains, or rejected prose. The Editor chooses the owning layer and invalidation boundary. REVISE gives Continuity dependency summaries for later accepted chapters; damage produces downstream impact and propagation debt before settlement, never silent Canon edits.

## 07 · Staged Corpus v2 use

The frozen six-domain Corpus v2 contract in specification 035 is upstream. Production adds source-free projections for book/volume planning, unit/chapter planning, scene resolution, and Writer realization.

Each stage selects zero to four mechanisms. Zero is the baseline when none apply. Every run freezes catalog version, mechanism IDs, selection output, and receiving-stage fingerprint. Corpus identity remains hidden from Readers, reviewers, Canon, and user-taste state.

## 08 · Long-range state and cost

Normal operation may not load an entire manuscript or Corpus. Context follows eligibility, semantic selection, hard-budget packing, and fingerprint-bound freeze, with no untracked reads after freeze.

Chapter dependencies, character/relationship/world state, reader expectations, planning debt, propagation debt, and checkpoints must be incrementally rebuildable. Review draft, accepted, settled, superseded, and published remain distinct lifecycle states.

The full-chain ledger distinguishes provider-confirmed, awaiting-reconciliation, and externally-unreported cost. Unknown cost is never recorded as zero. Authors are not required to set a user-level token or provider-cost cap, while actual usage and provider technical limits remain observable.

## 09 · Acceptance boundary

Acceptance has four layers:

1. platform parity on real Windows and Linux, including attacks, races, locks, atomic publication, and recovery;
2. production closure across planning, multi-scene drafting, Reader Pressure, rejection repair, downstream dependencies, and settlement isolation;
3. bounded multi-chapter fixtures whose open, selection, revision, recovery, and projections remain incremental and exclude unrelated manuscript bodies;
4. a live sequential-chapter literary canary with order exchange, independent review, and author judgment.

The first three belong in deterministic CI. The fourth is explicit and never spends model usage in normal CI.

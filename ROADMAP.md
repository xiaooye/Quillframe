# Quillframe 1.0 Preview Roadmap

Quillframe is on the `1.0.0-dev.x` prerelease line. This roadmap records **development direction, not release promises**: no item below has an implied date, and branch/PR work is not a released capability until it is merged and revalidated on `main`.

## Current 1.0 preview line

The current architecture is converging on:

```text
Writer
  ↓
Quillframe Studio / host surface
  ↓
typed Bridge / API
  ↓
Python Quillframe Core
  ├─ fiction systems + Canon / Context
  ├─ Model Runtime + Agent Runtime
  ├─ Quality + semantic execution
  ├─ Learning + Settlement
  └─ persistence services
  ↓
SQLite

Quillframe ↔ Model API
```

External models provide inference. Quillframe owns the agent/runtime semantics, tools, project authority, durable state, and semantic/settlement contracts around that inference.

## Active areas

### ✦ Writer-first Studio

Continue evolving Studio from a framework-inspection shell into an authoring environment first: manuscript work, planning, story state, review, research/Corpus, learning, and publication at the primary level; Sessions/Runs/Context/Capabilities/Receipts/Diagnostics remain progressively disclosed through advanced inspection surfaces.

The target desktop host is a thin **Tauri 2** layer around the same typed Core boundary rather than a second application architecture.

### ✧ Model and Agent Runtime hardening

The Quillframe-owned Model/Agent Runtime is part of the 1.0 architecture. Ongoing work focuses on model/capability evidence quality, task-profile routing, secure secret/network policy, tool/runtime robustness, embeddable library ergonomics, and preserving the rule that model or tool output never grants Project/Canon/Framework authority by itself.

Normal CI remains deterministic and does not require a paid/live endpoint.

### ♡ Long-form quality and continuity

Keep strengthening production mechanisms that make long-running fiction coherent without reducing creative judgment to deterministic rules: Story/Canon preflight, character simulation, Reader Pressure, independent semantic judgment, objective-preserving repair, reader engagement, continuity, and exact candidate lineage.

### ⋆ Context and state integrity

Improve sparse Context selection, visibility/provenance inspection, planning commitment boundaries, state propagation, and recovery while keeping:

```text
stored ≠ injected
Plan ≠ Canon
Review ≠ Accepted
Accepted ≠ Settled
persistence ≠ authority
```

### ✦ Learning with evidence

Continue the automatic feedback-intake path while keeping promotion governed and scoped. Automatic capture should create evidence/candidates—not silently change Canon, Project Profile, user taste, or the generic Framework.

### ✧ SQLite-native product persistence

Keep SQLite as the canonical durable product database with one native 1.0 schema, backups/restores, integrity checks, and host/API boundaries. Markdown/DOCX/EPUB remain import/export formats rather than a second live authority. Pre-1.0 state is rejected rather than migrated.

### ♡ Documentation and repository experience

Make Quillframe understandable from the repository and product documentation without requiring readers to reverse-engineer internal manifests first. Current-facing public language uses **Quillframe / `quillframe`** while historical records preserve their original terminology when provenance matters.

## Before 1.0 release acceptance

The broad stabilization goal is to reach a point where:

- public APIs and native Project contracts have exact, tested version expectations;
- Studio's writer-facing information architecture and desktop host are stable enough to document as current behavior;
- Model/Agent Runtime route evidence and secret/tool boundaries are repeatable;
- persistence backup/restore behavior is resilient within the native 1.0 schema;
- Canon, Context, semantic independence, Learning promotion, and Settlement boundaries have strong regression coverage;
- documentation, packaging, and installation paths no longer depend on internal development knowledge.

Breaking changes may still occur before that point. Consuming Projects must satisfy the native five-key manifest, CH001 context, manifest fingerprint, and `.quillframe/data` boundary. Host and release automation record Framework commit/bundle provenance separately. There is no consumer-owned Project lock, compatibility layer, or state upgrader for discarded development state.

## What this roadmap does not mean

- It is not a schedule or promise of release dates.
- It does not turn an open branch or Draft PR into a current product capability.
- It does not authorize Framework migrations in ordinary fiction-production tasks.
- It does not change Canon, Settlement, or Project state.
- It does not change the repository's current source-available license.

For exact current capability, use the current `main`, `HARNESS_MANIFEST.yaml`, tests, and the [root README](README.md) rather than this roadmap alone.

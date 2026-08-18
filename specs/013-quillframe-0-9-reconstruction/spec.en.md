# Specification — Quillframe 0.9.0 Reconstruction

Status: active implementation specification
Primary task mode: `SYSTEM-IMPROVE`
Frozen main: `0d583b25616e7e3b009efcf256ee4b21ecb5f8f7`
Target version: `0.9.0`

## Problem

The 0.8 repository has a strong SolidJS product surface and mature Python semantic/runtime mechanisms, but live authority is split across a SolidJS product, a Godot migration/shadow product, transitional parity/baseline paths, and a public Quillframe brand backed by a legacy technical namespace. Persistence is distributed across subsystem-local SQLite/files rather than one explicit product database model, and Studio exposes runtime/diagnostic routes more strongly than author workflows.

0.9 is a breaking pre-1.0 reconstruction, not a compatibility release.

## Required end state

Exactly one live architecture:

- SolidJS + TypeScript + Vite + `@solidjs/router` for all current web product UI.
- Tauri 2 as the only desktop host, thin and semantically non-authoritative.
- Python Quillframe Core for story, character, authority, settlement, learning, context, quality and orchestration semantics.
- SQLite-native global/project persistence, with FTS5 search and fingerprint-addressed blobs.
- One typed Quillframe Host Bridge shared across local HTTP, hosted HTTP and Tauri-local transport.
- Astro + Starlight for current documentation.
- Quillframe / `quillframe` as public, product and active technical identity.
- Borderless Kawaii Editorial as the common product design language.

## Hard removals

The current tree must contain no active Godot implementation, Godot export/config/scripts/assets, Godot CI, shadow product architecture, route/product parity, or `baseline:*` / `shadow:*` product scripts. Migration-only and dead compatibility layers are deleted rather than hidden behind aliases.

Historical specs/changelog may retain historically accurate terminology. Explicit one-shot 0.8 project migration is allowed; runtime fallback is not.

## Project format

Current project identity is `quillframe.toml` + `quillframe.lock.json`, plus Quillframe schema/attestation identities. Normal bootstrap never probes old filenames. `quillframe migrate-project <old-project>` is an explicit migration operation and imports legacy material as non-authoritative proposal state unless existing acceptance evidence is independently proven.

## Persistence

Default root:

```text
~/.quillframe/
  quillframe.sqlite
  projects/<project-id>/
    project.sqlite
    blobs/
    exports/
  backups/
  cache/
```

Global DB owns host/global settings, project registry, provider/model metadata, user-level preference/learning evidence where authorized, diagnostics, local scheduling metadata and backup metadata. Secrets are referenced by secure-host credential handles rather than stored in ordinary semantic tables.

Project DB implements Framework semantics rather than inventing a second model: story hierarchy, documents/revisions, characters, relationships, world, locations, timeline, plans/scene cards, Canon claims/state, character knowledge, research, candidates/lineage/review, acceptance, settlement, context/memory, sessions/runs/checkpoints/events/handoffs/receipts, learning/preferences, corpus/benchmarks and publication builds.

SQLite invariants: WAL, foreign keys, bounded busy timeout, deliberate synchronous durability, ordered checksummed migrations, atomic migration transactions, quick/integrity/foreign-key health checks, WAL checkpoint policy, backup API, corruption detection and blob fingerprint validation.

Autosave creates a revision only. Revision != Accepted. Database persistence != Settlement.

## Product authority

Studio is author-first. Default navigation is Desk, Manuscript, Plan, Story, Review, Research & Corpus, Learning, Publish. Search, command palette, settings and an optional AI Assistant Dock are global utilities. Sessions/Runs/Checkpoints/Context/Agents/Models/Semantic Jobs/Control Plane/Capabilities/Receipts/Diagnostics/Architecture are grouped under Inspector Mode.

Production actions are operation-specific typed Core commands. A browser-local mock must never be represented as DRAFT/REVISE/AUDIT/SETTLE. Exactly one primary `task_mode` is preserved per execution. `AUDIT` cannot rewrite. `DRAFT` cannot settle. Acceptance and settlement are separate. Feedback intake cannot auto-promote. Corpus cannot become Canon. Research cannot silently become character knowledge.

## Deployment/security

Localhost binds loopback by default and establishes an ephemeral local session automatically. Tauri launches/owns the local Core lifecycle without exposing manual endpoint configuration. Hosted public binds fail closed without server-side security bootstrap. `QUILLFRAME_SECRET` must never be emitted through `VITE_*` or the browser bundle; hosted authentication exchanges server-side bootstrap for an authenticated session, preferring secure HttpOnly cookies for same-origin deployments.

Static frontend hosting may live on generic static hosts, Vercel or Cloudflare, but SQLite remains on a durable Quillframe Server. Serverless function filesystems are not canonical persistence.

## Design/UX

The existing SolidJS homepage remains the visual north star. Hierarchy is created by whitespace, typography, composition and tint before borders. Kawaii personality is warm and restrained: ivory canvas, strong editorial type, powder blue/lavender/pink/mint/evidence gold, small sparkles, tape/index motifs and charming microcopy. Avoid card soup, admin-dashboard styling, generic SaaS grids, glassmorphism, cyberpunk and decoration-first anime styling. Touch targets are at least 44px and reduced-motion is honored.

Chinese UI uses natural Chinese; English remains for exact identifiers, commands, code and unavoidable proper nouns.

## Evidence and acceptance

CI must validate version consistency, namespace hygiene, absence of Godot/compatibility, Python contracts/tests, deterministic SQLite migrations, backup/restore/doctor, site/docs build, Studio typecheck/build/route/localization QA, Tauri fmt/check/build-smoke where practical, secret hygiene, visual route matrix and performance budgets.

A failed required gate means the task reports the real failed state rather than claiming production readiness.

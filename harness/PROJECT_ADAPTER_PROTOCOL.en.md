# Project Adapter Protocol

## Purpose

A NovelForge project is a consumer of the generic framework. The adapter tells the Harness how to resolve project-owned identity, profiles, Canon/state, plans, research, manuscripts, tests, and project-only regressions.

The framework never imports project-specific facts into its own source tree.

## Required project identity

Standard projects use:

```text
novelforge.toml
novelforge.lock.json
```

`novelforge.toml` declares project identity, logical authority paths, profiles, and build settings.

`novelforge.lock.json` pins framework compatibility/version/commit/bundle fingerprint.

Alternative adapters may exist, but they must expose the same logical contract.

## Dependency direction

```text
Project → Framework
Framework -X→ Project-specific data
```

The framework may define schemas and validators. It may never contain hard-coded paths, characters, book IDs, plot facts, or repository names belonging to one consumer project.

## Project-owned domains

A project owns:
- project identity and release version;
- genre/platform/project profiles;
- user-approved project overrides within framework-allowed boundaries;
- BOOK/VOL/ARC/UNIT/CH/SCN instances;
- character, relationship, world, organization, research objects;
- current structured state;
- Accepted Canon artifacts;
- active plans;
- project regressions/capability fixtures;
- project corpus refs/benchmarks;
- project assets/manuscripts;
- settlement migrations and derived views.

The framework owns generic mechanisms and quality contracts.

## Adapter output

At bootstrap the adapter resolves at least:

```yaml
project_id:
project_version:
project_root:
framework_lock:
authority_paths:
profile_paths:
canon_cutoff:
active_plan_paths:
research_paths:
eval_paths:
bundle_ref:
```

This is resolution metadata, not model context.

## Sparse Context Manifest

After resolution, Context Curator selects only the project objects needed for the current task.

The adapter must not automatically inject the entire bible/state/manuscript history merely because it can locate them.

## Framework bundle

To avoid repeated cross-repository reads, a project may materialize the pinned framework release into:

```text
.novelforge/framework/
```

The materialized bundle is read-only dependency cache and is normally gitignored.

Rules:
- verify lockfile fingerprint/commit;
- do not edit the cache as project behavior;
- framework upgrade is explicit dependency change;
- failed compatibility tests block upgrade completion.

## Compatibility

A project declares project schema version + minimum/locked framework version.

Non-trivial framework upgrades should use a structural-change spec:

```text
spec → plan → tasks → sync/upgrade → validate → project tests/evals → acceptance
```

Never silently reinterpret old Canon because a framework schema changed.

## Legacy project adapter

Existing projects may keep older physical layouts while implementing the logical contract through an adapter/migration layer.

A migration should gradually map:
- old project entry files → `novelforge.toml`;
- old Canon/state tables → standard authority paths or adapter mapping;
- old prose/project rules → framework fundamentals + true project profile overrides;
- old runtime files → framework lock dependency;
- old generated/derived files → explicit lifecycle classes.

Project migration evidence may inform the Project SDK, but concrete project facts must never be copied into the framework.

## Authority invariant

> The framework supplies the language of production; the project supplies the facts of one story.

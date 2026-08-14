# Project Adapter Protocol · Map storage without importing story truth

A NovelForge Project Adapter maps one consuming project's physical repository into the **logical Project contract** required by the Harness. It resolves identity, safe paths, authority domains and dependency metadata. It does not decide what context is semantically relevant and it never imports project facts into generic Framework source.

> **Core invariant ✦** The Project owns instances and facts. NovelForge owns generic schemas and mechanisms. The Adapter only describes how to reach the Project-owned domains.

---

## 01 · Required project identity

A standard project is rooted by:

```text
novelforge.toml
novelforge.lock.json
```

`novelforge.toml` declares project identity, project schema compatibility, logical authority/path mappings, quality/profile configuration and build settings.

`novelforge.lock.json` records the Framework dependency identity. A production lock may bind version, exact commit and bundle fingerprint. **A lock identifies the dependency; it does not grant the Framework authority over Project facts.**

Alternative/legacy layouts are supported through a mapped adapter, but they must resolve to the same logical boundary.

---

## 02 · Dependency direction

```text
Novel Project → pinned NovelForge Framework
NovelForge Framework -X→ project-specific facts
```

Generic Framework source must not hard-code:

- consumer repository names or paths;
- book/chapter/scene IDs from one project;
- characters, relationships, world facts or plot state;
- project-specific research claims;
- private user preference data;
- project-only profile defaults.

Migration experience may inspire generic mechanisms. Concrete project content may not become the mechanism's embedded fixture or default.

---

## 03 · Standard and mapped layouts

The reference resolver in [`project_adapter.py`](../project_adapter.py) supports:

- `standard` — normal Project SDK directory domains;
- `mapped` — legacy physical paths mapped into the required logical interface.

For every mapped path the resolver:

- requires a non-empty path string;
- resolves it relative to the project root;
- rejects paths that escape the project root;
- verifies required domains exist;
- records whether the resolved target is a file, directory or missing optional path.

The Adapter knows layout. It does **not** gain permission to reinterpret the content it locates.

---

## 04 · Logical domains

A standard Project exposes logical areas such as:

- bible / story definitions;
- structured state;
- future plans;
- manuscripts;
- profiles;
- evals and tests;
- research;
- corpus references;
- specs;
- assets.

A mapped legacy project may instead expose explicit entry files such as project entry, start-here/context protocol, story bible, current state, active plans, manuscripts and profiles.

The exact physical names may differ. Their **authority class** may not be guessed from convenience.

For example:

```text
active plan     ≠ current state
review draft    ≠ accepted manuscript
runtime memory  ≠ Canon
corpus evidence ≠ character knowledge
```

---

## 05 · Adapter resolution output

The deterministic resolver produces metadata similar to:

```yaml
schema: novelforge_project_adapter_resolution_v1
project_id: ...
project_version: ...
project_root: ...
layout: standard | mapped
framework_lock: ...
project_schema_version: ...
authority: ...
paths: ...
quality: ...
build: ...
```

This result answers **where project-owned material lives and how it is classified**.

It is not:

- a Context Manifest;
- a prompt packet;
- a semantic relevance ranking;
- a Canon snapshot by itself;
- proof that an optional file is safe to inject.

---

## 06 · Context comes later

After project resolution, the Harness builds task-scoped context through the Context/Memory system.

The Adapter must never dump every resolved bible/state/manuscript file into the model merely because those files are reachable.

Current context selection separates:

```text
project path + authority resolution  → Adapter / Project SDK
perspective-safe visibility          → deterministic context runtime
semantic relevance to active task    → context.select model contract
hard budget packing                  → deterministic runtime
```

This prevents storage topology from becoming prompt policy.

---

## 07 · Project bundle is a derived view

The Adapter may build a compact mapped project bundle containing:

- project identity;
- Framework lock metadata;
- authority/path map;
- file fingerprints and sizes;
- content-index and bundle fingerprints.

The bundle is useful for bootstrap and reproducibility, but it is a **derived artifact**. It does not become a second authority database.

If source Project state changes, rebuild the bundle rather than editing the bundle as truth.

---

## 08 · Framework materialization

A Project may materialize its pinned Framework dependency under:

```text
.novelforge/framework/
```

Treat this as a read-only dependency cache:

- verify commit/fingerprint evidence required by the lock;
- do not edit cached Framework files as a project override;
- do not infer project facts from Framework session history;
- make Framework upgrades explicit project changes;
- revalidate compatibility before production resumes.

A persistent local copy improves bootstrap performance; it does not weaken dependency direction.

---

## 09 · Framework upgrade

A behavior-changing Framework upgrade is a structural Project change:

```text
resolve current lock
→ inspect migration/compatibility impact
→ spec / plan / tasks when warranted
→ materialize candidate Framework revision
→ validate Project contract
→ run deterministic tests + applicable semantic evals
→ accept dependency change
→ update exact lock / bundle evidence
```

Do not silently reinterpret accepted Canon because a Framework schema or mechanism changed.

If a running session resumes after the lock changed, it must re-bootstrap against the new exact dependency rather than continuing from stale provider memory.

---

## 10 · Legacy migration

A mature legacy novel does not need a destructive directory rewrite before adopting NovelForge.

A safe migration usually moves through:

```text
audit physical layout
→ add manifest + lock
→ map logical authority domains
→ validate path safety and required domains
→ build derived project bundle
→ add deterministic CI
→ separate generic mechanisms from project-only rules
→ remove stale embedded Framework/runtime copies
```

Migration must preserve the meaning of existing authority classes. A convenient old folder name is not sufficient evidence to upgrade a Plan or Review artifact into Accepted Canon.

---

## 11 · Failure semantics

Fail rather than guess when:

- required project identity is missing;
- manifest/lock schema is incompatible;
- a mapped path escapes the project root;
- a required logical domain does not exist;
- a project profile attempts to disable mandatory Framework fundamentals;
- the Framework dependency cannot be verified to the required lock evidence.

An adapter failure is a bootstrap/compatibility problem. It is not permission to invent project state.

---

## 12 · Related contracts

- [Project SDK](../docs/project-sdk.en.md) — standard project structure, validation and build.
- [Project Adapters guide](../docs/project-adapters.en.md) — migration-oriented user guide.
- [Context & Memory](../docs/context-and-memory.en.md) — task-aware sparse context after resolution.
- [Canon State](../core/CANON_STATE.en.md) — authority and settlement.
- [`project_adapter.py`](../project_adapter.py) — deterministic reference resolver.

**The Adapter translates storage shape into a logical interface. It never translates convenience into authority.**

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><strong>Project SDK · treat each novel as an independently governed, reproducible project</strong></p>
  <p><kbd>SCAFFOLD</kbd>&nbsp;&nbsp;<kbd>LOCK</kbd>&nbsp;&nbsp;<kbd>VALIDATE</kbd>&nbsp;&nbsp;<kbd>BUILD</kbd>&nbsp;&nbsp;<kbd>MIGRATE</kbd></p>
  <p><a href="project-sdk.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Project SDK

NovelForge supplies a generic fiction-production framework. A consuming Project supplies **one story's authority, state, plans, manuscripts, research, profiles, regressions, tests, and acceptance history**.

The Project SDK exists to keep that boundary reproducible outside any chat session.

> **Dependency direction: Project → pinned NovelForge.** Framework source must not absorb one Project's Canon, characters, plot, or private taste.

---

## 01 · What a NovelForge Project is

A complete Project is more than a manuscript directory.

It should be independently cloneable, self-describing, structurally validatable, buildable, migration-aware, and resumable without relying on provider conversation history.

The standard layout includes domains such as:

`profiles/` — genre, platform, prose, reader, and project-specific configuration.

`bible/` — Project-owned world / character / story reference material.

`state/` — authoritative Canon, current state, ledgers, and other Project-owned state.

`plans/` — future intent; never automatically current Canon.

`manuscripts/` — draft, review, accepted, and published lifecycle surfaces.

`research/` — evidence and Project fictionalization decisions.

`corpus/` — Project-local corpus references or evidence indexes, not Framework Canon.

`evals/` / `tests/` / `regressions/` — quality and engineering evidence.

`specs/` / `migrations/` — structural-change history.

`dist/` — deterministic derived build artifacts.

Projects with mature legacy layouts may use a mapped Project Adapter instead of physically rearranging files.

---

## 02 · Create a scaffold

```bash
python project_sdk.py init ./my-novel \
  --id PROJECT-X \
  --title "My Novel" \
  --framework-version <compatible-version>
```

The scaffold creates:

- `novelforge.toml`;
- `novelforge.lock.json`;
- standard authority / manuscript / research / quality directories;
- English and Chinese README entrypoints;
- agent-discovery files;
- profile stubs;
- ignore rules for runtime state, local framework materialization, and private learning data.

`init` is a **scaffolding operation**, not proof that the dependency is fully resolved.

The generated lock structure can contain unresolved `commit` or `bundle_fingerprint` fields. A governed production Project should resolve and record the exact Framework revision / bundle evidence required by its bootstrap policy before treating the dependency as pinned.

Do not copy a version number from documentation and assume that alone is an exact lock.

---

## 03 · `novelforge.toml` describes the logical Project contract

The manifest declares the Project rather than one local machine's absolute paths.

Important areas include:

**Project identity** — stable ID, title, language, Project version, lifecycle status.

**Framework contract** — minimum compatible version / lockfile location / project-to-framework dependency direction.

**Authority paths** — Project-owned locations for Canon, current state, ledgers, bible, profiles, plans, manuscripts, research, corpus, evals, tests, migrations, regressions, and generated output.

**Quality contract** — whether generic Framework quality layers remain enabled and which advanced mechanisms the Project supports.

The manifest is configuration and routing evidence. It does not itself make a plan Accepted or a review artifact Canon.

---

## 04 · `novelforge.lock.json` records dependency evidence

The lockfile identifies the Framework dependency separately from Project content.

A resolved Framework lock may record:

- repository;
- version / compatibility metadata;
- exact commit;
- deterministic bundle fingerprint;
- bundle format or materialization metadata.

The exact requirements used at runtime come from the Project's active bootstrap / adapter contract.

Two distinctions matter:

**Compatibility version ≠ exact revision.** A semver-like field can describe compatibility without uniquely identifying Framework bytes.

**Exact commit ≠ exact bundle bytes.** A reproducible bundle may additionally bind the materialized Framework contents through its SHA-256 bundle fingerprint.

Project production should never silently replace its pinned dependency with whichever Framework happens to be newest.

---

## 05 · Validate the Project structure

```bash
python project_sdk.py validate ./my-novel
```

The SDK validator checks deterministic structure such as:

- Project schema and required identity fields;
- lockfile schema and bundle-fingerprint syntax;
- required logical directories / entry files;
- bilingual structural-spec pairing;
- suspicious manuscript-lifecycle duplication;
- Project profiles attempting to disable mandatory Framework Surface Fundamentals.

Validation intentionally does **not** claim that the novel is good, the Canon is semantically correct, or the dependency has passed every production bootstrap gate.

It proves only the deterministic Project contract it owns.

---

## 06 · Build a deterministic Project bundle

```bash
python project_sdk.py build ./my-novel
```

A successful build writes `dist/project.bundle.json` plus class-specific manifests and fingerprints.

The bundle records:

- Project metadata;
- Framework-lock metadata;
- authority / path configuration;
- bootstrap entry files;
- a classified content index;
- per-file SHA-256 fingerprints;
- content-index fingerprint;
- Project bundle fingerprint.

Content classes distinguish authoritative Project material from plans, generated manuscripts, research, evals, corpus references, specs, tests, assets, and metadata.

That classification helps prevent “everything in the repository” from becoming one undifferentiated truth source.

`dist/` is derived output and can be rebuilt.

---

## 07 · Project authority remains explicit

The Project contract must keep lifecycle and authority distinct.

Typical classes include:

`locked` — explicit Project-locked truth.

`accepted` — explicitly accepted and settled truth / artifact.

`active_plan` — current future intent.

`review` — candidate awaiting acceptance.

`proposal` — suggested change with no authority yet.

The precise precedence is Project-owned and should be declared in Project authority documentation.

Important consequences:

- Plan does not become current state because it is stored under `plans/`.
- A review manuscript does not become Canon because QA passed.
- Acceptance and structured settlement are distinct events.
- Memory / semantic results / Corpus evidence do not bypass the Project authority model.

---

## 08 · Standard layout versus mapped Adapter

The standard scaffold is easiest when starting fresh.

Existing fiction repositories often already have good storage conventions. NovelForge does not require a destructive migration just to satisfy folder names.

A mapped Project Adapter can translate logical roles such as Project profile, Accepted Canon, current state, plans, manuscripts, research, or regressions to existing repository paths.

The adapter must preserve **meaning**, not merely file existence.

A wrong mapping that technically resolves to a path is worse than an explicit validation failure.

Continue to [Project Adapters](project-adapters.en.md) and [Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md).

---

## 09 · Structural changes use specs when they actually need them

For consequential structural work, the Project SDK can scaffold a bilingual engineering feature package:

```bash
python project_sdk.py spec-new ./my-novel \
  --title "relationship state migration"
```

The generated package contains paired English / Chinese:

- specification;
- implementation plan;
- task list.

Use this for schema migrations, new subsystems, authority changes, release engineering, or other changes where migration / rollback / verification genuinely matter.

Do **not** manufacture a full engineering ceremony for an ordinary prose micro-edit.

---

## 10 · Project-owned tests and quality evidence

A Project may keep:

- deterministic tests;
- Project-specific eval cases;
- regression evidence from previously rejected failures;
- continuity checks;
- structural migrations;
- artifact fingerprints and acceptance evidence.

Framework quality fundamentals remain generic. Project evidence may tune or extend profile-sensitive behavior, but the Project must not silently disable an explicit Framework failure mechanism merely because a local preference dislikes the gate.

Corpus evidence, regression evidence, and semantic review results remain evidence—not Canon.

---

## 11 · Runtime state is not committed Project truth

Operational stores such as:

- `.novel-os/` or equivalent runtime database;
- `.novelforge/` local framework materialization;
- local learning databases;
- provider sessions;
- temporary semantic packets / receipts;

are runtime or derived state.

They may be essential for execution and recovery, but they are not automatically part of Project authority and should not be committed as story truth by default.

The Project source of truth remains the Project's explicit authority structure plus authorized settlements.

---

## 12 · Recommended bootstrap discipline

A production manager should not treat “the directory validated” as the full bootstrap.

A robust Project start normally does the following:

**Resolve Project.** Load `novelforge.toml` and `novelforge.lock.json`.

**Resolve exact Framework.** Materialize / verify the revision the Project is actually pinned to.

**Read Framework authority.** Load the pinned `HARNESS_MANIFEST.yaml`, Skill contract, and Harness manager protocol from that exact revision.

**Resolve Project adapter.** Validate standard or mapped layout and build sparse logical views.

**Choose one task mode.** Do not turn a DRAFT invocation into an invisible SETTLE or SYSTEM-IMPROVE run.

**Create / restore runtime identity.** Session, run, checkpoints, and capabilities remain distinct from Project truth.

**Build sparse task context.** Load only the Project slices the current work needs.

This is where “software project” discipline becomes operational rather than decorative.

---

## 13 · Common failure cases

**Lock metadata exists but is unresolved** → finish dependency resolution before production bootstrap.

**Project validates structurally but semantic authority is ambiguous** → fix Project authority documentation / adapter mapping; structural validation is not enough.

**Framework source starts containing one novel's facts** → dependency-boundary violation; move Project instances back into the Project.

**Same manuscript appears in multiple lifecycle directories** → resolve lifecycle ambiguity rather than guessing which copy is authoritative.

**Profile tries to disable mandatory Framework Fundamentals** → deterministic validation failure.

**Mapped legacy path changes meaning over time** → adapter drift; revalidate mapping before consequential work.

**Build artifacts are treated as source truth** → rebuild from authoritative Project files instead.

---

## 14 · Exact references

- [`project_sdk.py`](../project_sdk.py) — scaffold, validate, build, and spec tooling.
- [Project Adapters](project-adapters.en.md) — legacy-layout integration.
- [Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md) — logical mapping contract.
- [Architecture](architecture.en.md) — Project / Framework authority boundary.
- [Framework Bundle](../release/FRAMEWORK_BUNDLE.en.md) — deterministic Framework materialization and bundle fingerprints.
- [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md) — operational state outside Project authority.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="48" />
  <br />
  <sub>A novel can stay artistically fluid while its production state stays reproducible. 🌸</sub>
</div>

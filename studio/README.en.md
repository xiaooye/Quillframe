# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio is the product-experience layer around NovelForge Core. **Read-only Phase 1, Phase 2A, and Phase 2B slices now exist on `main`; they are real product-contract and host-boundary implementations, not a released write-capable Studio application.** The future installable shell direction is now selected as **Tauri + React + WeiUI**, while implementation remains pending and Core authority boundaries remain unchanged.

> **Authority boundary ✦** Studio consumes NovelForge Core state. UI state is not Canon, Memory, semantic truth, write authority, or a second workflow engine.

[简体中文](README.zh-CN.md)

## Product architecture

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) — machine-readable portable delivery-surface contract.

The product architecture records both the Core interfaces Studio can consume and the unresolved Core consumer gaps Studio must not patch around locally. It also records the selected Tauri + WeiUI installable-shell direction, token ownership, performance constraints, responsive/i18n requirements, and the acceptance evidence required before that future app can be described as shipped.

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency Run / Context Inspector; loads `novelforge_run_receipt_v1` JSON locally and exposes no write operation.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — clearly synthetic demo receipt for visual and interaction QA.

The first interaction principle is intentionally visible in the prototype:

**support identified by a semantic selection result ≠ evidence that actually entered the model context.**

## Phase 2A · One product, many hosts

Phase 2A treats Studio as a polished SaaS-like experience without making SaaS business infrastructure part of the product model. The same NovelForge semantics should be available through four first-class delivery surfaces:

- **CLI** — scriptable native automation and inspection.
- **Local app / local Web UI** — a creator workstation using local host capabilities through typed adapters.
- **Cloud-hosted UI** — the same product model behind a remote query/command boundary.
- **Agent skill / package** — a thin, versioned adapter for other agent frameworks that does not expose private NovelForge persistence or implementation internals.

Different hosts may have different capabilities and transports. Those differences never change Canon, Settlement, Context, semantic-result, or receipt semantics. **Host capability does not imply NovelForge story authority.**

### Portable Project Hub / Scene vertical slice

- [`project_hub_projection.py`](project_hub_projection.py) — deterministic read-only projection from `novelforge_project_adapter_resolution_v1`; rejects the wrong source schema, strips host absolute paths, and binds exact source/projection fingerprints.
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) — Project Hub + Scene workspace shell with Creator/Inspector progressive disclosure and delivery-surface switching.
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) — synthetic Project Adapter resolution containing deliberately private absolute paths for redaction validation.
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) — synthetic read-only Scene/Reader/Context/Runtime fixture.

The projection explicitly carries `authority=false`, `canon_authority=false`, `framework_write_authority=false`, and `settlement_authority=false`. It never infers current chapter, manuscript lifecycle, publication status, or quality status merely because a logical path exists.

## Phase 2B · Portable read-only host bridge

Phase 2B makes the multi-host boundary executable without turning Studio into another runtime. [`host_bridge.py`](host_bridge.py) accepts a versioned `novelforge_studio_host_bridge_request_v1` envelope and returns a fingerprint-bound `novelforge_studio_host_bridge_result_v1`. [`host_bridge_contract.json`](host_bridge_contract.json) is the machine-readable allowlist shared by CLI, local-app, hosted-UI, and agent-package consumers.

The currently supported read operations are deliberately small: `bridge.describe`, `framework.doctor`, `project.inspect`, `capabilities.inspect`, `context.inspect`, and `semantic.catalog`. Results default-deny host-private paths and carry `authority=false` plus explicit Canon, Framework-write, and Settlement non-authority markers.

Several operations are intentionally **unsupported**, not emulated. Runtime session/event/handoff queries are deferred because the current Control Plane CLI initializes persistence before dispatching even nominal read commands. `run.receipt.get` remains deferred because Core does not yet provide a stable Run Receipt retrieval projection and its event discoverability is still inconsistent. Generic invoke/write and resume commands also remain deferred until Core defines the public command/precondition/CAS/idempotency/receipt contract. These dependencies are tracked in Core issue #23.

### Agent Skill package

[`../agent-skills/novelforge/SKILL.md`](../agent-skills/novelforge/SKILL.md) is the portable Agent Skills package. Its bundled [`novelforge_bridge.py`](../agent-skills/novelforge/scripts/novelforge_bridge.py) client only discovers and calls the shared Studio host bridge; it does not import private Core runtime modules or know the persistence layout.

From the skill directory, discovery starts with:

```bash
python scripts/novelforge_bridge.py describe
```

Then invoke a request envelope with:

```bash
python scripts/novelforge_bridge.py invoke --request /path/to/request.json
```

A host must preserve `unsupported` and `unavailable` states rather than bypassing the bridge through SQLite, private imports, or a mutating Core primitive. Phase 2B remains read-only: **no acceptance, settlement, Canon mutation, generic write API, or hidden authority shortcut is introduced here.**

## Future installable shell · Tauri + WeiUI

The installable Studio direction is selected, but no Tauri application has yet been merged on `main`:

- **Tauri** hosts the desktop application;
- **React 19** provides the application shell expected by `@weiui/react`;
- **WeiUI** supplies reusable components, zero-JavaScript CSS, and W3C-style token infrastructure;
- **NovelForge Story Loom** remains the product visual/semantic authority through a deterministic WeiUI-compatible token adapter;
- Tauri / React / WeiUI stay outside Generic Core runtime correctness, CLI, Framework bundle, and Agent Skill dependencies.

The detailed token-ownership, tree-shaking, runtime-overhead, responsive/i18n, accessibility, reduced-motion, and acceptance-gate rules live in the [Product Architecture](PRODUCT_ARCHITECTURE.en.md). Until those implementation artifacts and measurements land, Tauri + WeiUI is a **selected product direction**, not a shipped Studio capability.

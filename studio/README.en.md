# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio is the product-experience layer around NovelForge Core. **Read-only Phase 1, Phase 2A, and Phase 2B slices exist on `main`; Story Loom v2 plus the exact-pinned zero-JS WeiUI CSS/token foundation is also merged.** The Phase 2C application stack is **SolidJS + TypeScript + Vite + `@solidjs/router`**. Local Web remains first-class; Tauri is an optional/installable host. This is still not a released write-capable Studio application.

> **Authority boundary ✦** Studio consumes NovelForge Core state. UI state is not Canon, Memory, semantic truth, write authority, or a second workflow engine.

[简体中文](README.zh-CN.md)

## Product architecture

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) — machine-readable portable delivery-surface contract.
- [`../assets/brand/weiui.integration.json`](../assets/brand/weiui.integration.json) — exact WeiUI pin and zero-JS consumption contract.
- [`../assets/brand/story-loom.weiui.css`](../assets/brand/story-loom.weiui.css) — live Story Loom `wui-theme` layer.

The product architecture records both the Core interfaces Studio can consume and the unresolved Core consumer gaps Studio must not patch around locally. It also records the low-overhead Phase 2C stack, Local Web / optional Tauri host split, mobile/i18n/accessibility/runtime rules, and Publication/production-readiness surfaces that Core now actually exposes.

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency Run / Context Inspector; loads `novelforge_run_receipt_v1` JSON locally and exposes no write operation.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — clearly synthetic demo receipt for visual and interaction QA.

The first interaction principle is intentionally visible in the prototype:

**support identified by a semantic selection result ≠ evidence that actually entered the model context.**

## Phase 2A · One product, many hosts

The same NovelForge semantics are intended to be available through four first-class delivery surfaces:

- **CLI** — scriptable native automation and inspection.
- **Local Web / local app** — the low-overhead creator workstation, using local host capabilities through typed adapters.
- **Cloud-hosted UI** — the same product model behind a remote query/command boundary.
- **Agent Skill / package** — a thin, versioned adapter for other agent frameworks that does not expose private NovelForge persistence or implementation internals.

Different hosts may have different capabilities and transports. Those differences never change Canon, Settlement, Context, semantic-result, readiness, publication, or receipt semantics. **Host capability does not imply NovelForge story authority.**

### Portable Project Hub / Scene vertical slice

- [`project_hub_projection.py`](project_hub_projection.py) — deterministic read-only projection from `novelforge_project_adapter_resolution_v1`; rejects the wrong source schema, strips host absolute paths, and binds exact source/projection fingerprints.
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) — Project Hub + Scene workspace shell with Creator/Inspector progressive disclosure and delivery-surface switching.
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) — synthetic Project Adapter resolution containing deliberately private absolute paths for redaction validation.
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) — synthetic read-only Scene/Reader/Context/Runtime fixture.

The projection explicitly carries `authority=false`, `canon_authority=false`, `framework_write_authority=false`, and `settlement_authority=false`. It never infers current chapter, manuscript lifecycle, publication status, or quality status merely because a logical path exists.

## Phase 2B · Portable read-only host bridge

[`host_bridge.py`](host_bridge.py) accepts a versioned `novelforge_studio_host_bridge_request_v1` envelope and returns a fingerprint-bound `novelforge_studio_host_bridge_result_v1`. [`host_bridge_contract.json`](host_bridge_contract.json) is the machine-readable allowlist shared by CLI, Local Web/app, hosted UI, and agent-package consumers.

The currently supported read operations are deliberately small: `bridge.describe`, `framework.doctor`, `project.inspect`, `capabilities.inspect`, `context.inspect`, and `semantic.catalog`. Results default-deny host-private paths and carry `authority=false` plus explicit Canon, Framework-write, and Settlement non-authority markers.

Several operations remain intentionally **unsupported**, not emulated. Runtime session/event/handoff queries and Run Receipt retrieval still depend on Core issue #23. Generic invoke/write and resume commands remain deferred until Core exposes the public precondition/CAS/idempotency/receipt contract.

### Agent Skill package

[`../agent-skills/novelforge/SKILL.md`](../agent-skills/novelforge/SKILL.md) is the portable Agent Skills package. Its bundled [`novelforge_bridge.py`](../agent-skills/novelforge/scripts/novelforge_bridge.py) client only discovers and calls the shared Studio host bridge; it does not import private Core runtime modules or know the persistence layout.

## Story Loom v2 · WeiUI zero-JS foundation

The design-system integration is no longer only a future direction:

- Story Loom token schema: `novelforge_brand_tokens_v2`;
- exact WeiUI source pin: `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`;
- allowed WeiUI packages: `@weiui/tokens`, `@weiui/css`;
- forbidden Phase 2C runtime packages: `@weiui/react`, `@weiui/headless`;
- WeiUI runtime JavaScript: **not required**;
- Story Loom theme: `assets/brand/story-loom.weiui.css` in `wui-theme`;
- baseline locales: `en-US`, `zh-CN`;
- mobile-first, 44px minimum touch target, reduced motion, no idle decorative animation, no default polling;
- deterministic design-system CI via `scripts/design_system_quality.py`.

## Phase 2C · SolidJS product shell

The selected application shape is:

```text
Core public boundary
→ Studio view models
→ SolidJS + TypeScript + Vite + @solidjs/router
→ WeiUI tokens/CSS + Story Loom theme
→ Local Web (first-class)
→ optional Tauri package
```

No React runtime is part of the selected Phase 2C plan. Tauri remains useful for an installable desktop build, but the product must stay fully coherent as Local Web without requiring desktop-host overhead.

The app itself still needs implementation and measurement. Before calling Phase 2C production-ready, measure actual idle CPU/RAM, first-interaction latency, route cost and Core-process lifetime; preserve no-default-polling and explicit host lifecycle rules.

## Current Core additions relevant to Studio

`novelforge_production_readiness_v1` now gives Review a real same-fingerprint conjunction gate instead of a made-up quality percentage.

`novelforge_publication_ir_v1` + `publication/compiler.py` now gives Publish a real deterministic minimum Core for Accepted text: clean text, Web HTML, print-oriented HTML/CSS and EPUB 3.3. This does not mean the broader Typesetting Toolkit or Studio Publish UX is complete; richer Issue #16 scope remains open.

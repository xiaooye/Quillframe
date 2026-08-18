# Quillframe Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>LOW-OVERHEAD</kbd></p>

Quillframe Studio is the product-experience layer around Quillframe Core. Phase 1, Phase 2A, and Phase 2B established the product model, safe projections, and portable Host Bridge. **Phase 2C now contains a real read-only SolidJS application shell** built with TypeScript, Vite, `@solidjs/router`, Story Loom v2, and a config-generated zero-runtime-JavaScript WeiUI CSS foundation.

Local Web is first-class and preferred when minimum incremental CPU/RAM matters. Tauri remains an optional future installable host; it is not the semantic center of the product.

> **Authority boundary ✦** Studio consumes Quillframe Core state. UI state is not Canon, Memory, semantic truth, write authority, or a second workflow engine.

[简体中文](README.zh-CN.md)

## Product architecture

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) — one-product/many-hosts delivery contract.
- [`host_bridge_contract.json`](host_bridge_contract.json) — public read-only Host Bridge allowlist.
- [`../assets/brand/weiui.integration.json`](../assets/brand/weiui.integration.json) — exact WeiUI source pin and generated-bundle contract.
- [`../assets/brand/story-loom.weiui.css`](../assets/brand/story-loom.weiui.css) — live Story Loom `wui-theme` layer.

The rule remains simple: **Core owns truth; Studio owns presentation and transport.** Missing public Core primitives stay unavailable rather than being recreated in the UI.

## Phase 1 · Run / Context Inspector prototype

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency read-only Inspector prototype.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — synthetic receipt used only for visual/interaction QA.

The prototype established a central observability distinction: evidence selected as support is not the same as evidence that actually entered a model context.

## Phase 2A · One product, many hosts

Quillframe product semantics are designed for four first-class delivery surfaces:

- **CLI** — scriptable native inspection and automation.
- **Local Web / local app** — low-overhead creator workstation.
- **Cloud-hosted UI** — same product model behind a remote transport.
- **Agent Skill / package** — portable adapter for other agent frameworks.

Different hosts may have different capabilities. Those differences never change Canon, Settlement, Context, semantic-result, readiness, publication, or receipt semantics. **Capability does not imply authority.**

The Phase 2A Project Hub projection remains at [`project_hub_projection.py`](project_hub_projection.py). It strips absolute host paths and carries explicit non-authority markers.

## Phase 2B · Portable read-only Host Bridge

[`host_bridge.py`](host_bridge.py) accepts `quillframe_studio_host_bridge_request_v1` and returns fingerprint-bound `quillframe_studio_host_bridge_result_v1` envelopes.

Current supported operations are deliberately small:

- `bridge.describe`
- `framework.doctor`
- `project.inspect`
- `capabilities.inspect`
- `context.inspect`
- `semantic.catalog`

Runtime session/event/handoff reads, Run Receipt retrieval, resume, generic command invocation, and project mutation remain deferred to Core issue #23. Studio does not read private SQLite state to fake those surfaces.

[`../agent-skills/quillframe/SKILL.md`](../agent-skills/quillframe/SKILL.md) consumes the same operation vocabulary without importing private Core runtime modules.

## Story Loom v2 · WeiUI config-generated foundation

Story Loom remains Quillframe visual/product-semantic authority. WeiUI owns generic CSS/token primitives.

The reviewed upstream is pinned exactly in [`../assets/brand/weiui.integration.json`](../assets/brand/weiui.integration.json). Phase 2C consumes only `@weiui/tokens` and `@weiui/css`; `@weiui/react` and `@weiui/headless` remain forbidden Studio runtime dependencies.

WeiUI now has a first-class **build-time config layer**. Studio declares the required generic UI surface in [`app/weiui.config.json`](app/weiui.config.json):

```text
weiui.config.json
→ exact-pinned @weiui/css config/bundle manifest
→ dependency-closed minimal CSS
→ checked-in vendor CSS + token CSS
→ Story Loom wui-theme
→ SolidJS product surface
```

The generated files are checked in so normal Studio runtime does not need Node, a WeiUI checkout, or a bundler. [`sync_weiui.py`](sync_weiui.py) verifies byte-for-byte regeneration against the exact upstream pin in CI.

Baseline design/runtime constraints remain machine-enforced:

- `en-US` + `zh-CN`;
- mobile-first, phone focus-first composition;
- minimum 44px touch targets;
- logical CSS properties and text-expansion-safe layouts;
- reduced-motion support;
- no idle decorative animation;
- no default polling;
- zero WeiUI browser JavaScript.

## Phase 2C · Real SolidJS product shell

Application source lives in [`app/`](app/).

```text
Core public boundary
→ studio/host_bridge.py
→ studio/local_server.py
→ typed /api/bridge/invoke transport
→ SolidJS + TypeScript + Vite + @solidjs/router
→ config-generated WeiUI CSS + Story Loom theme
```

The current read-only shell includes:

- **Desk** — bridge status, supported/deferred operation counts, current project summary.
- **Project Hub** — real `project.inspect` safe projection.
- **Scene Workspace** — intentionally unavailable until Core exposes a truthful current-scene/content projection; no fixture or filesystem inference is used.
- **Context Inspector** — real `context.inspect` with project-relative manifest/overlay paths.
- **Host Capabilities** — real `capabilities.inspect`, fetched on route entry and only refreshed explicitly.
- **Semantic Catalog** — real `semantic.catalog`, fetched on route entry and only refreshed explicitly.
- **Framework Diagnostics** — explicit `framework.doctor` query.
- **Command palette** — operation vocabulary comes from live `bridge.describe`; deferred Core operations carry their dependency reason instead of appearing enabled.

The app has no default timers, polling loop, WebSocket heartbeat, Redux-like second state store, or browser persistence for project truth. Project root is page-session presentation state only.

### Local server

[`local_server.py`](local_server.py) is a stdlib-only transport. It:

- binds `127.0.0.1` only;
- injects an ephemeral per-process token into the served app;
- enforces Host / Origin / `Sec-Fetch-Site` checks;
- exposes only `POST /api/bridge/invoke` for API traffic;
- rejects CORS preflight;
- caps request bodies at 128 KiB;
- carries no write/Canon/Settlement authority;
- performs no polling or background refresh.

After building the app:

```bash
cd studio/app
pnpm install --frozen-lockfile
pnpm build
cd ../..
python studio/local_server.py
```

The server prints its loopback URL. It does not launch a browser automatically.

## Performance discipline

Phase 2C treats performance as an acceptance condition rather than a later optimization pass. CI enforces raw JS/CSS budgets, route lazy loading is used for the product pages, and heavy editor/runtime libraries are absent from the initial shell.

The first production build is intentionally small: the main Solid/router JS chunk is roughly tens of kilobytes raw, with individual route chunks in the low single-digit-kilobyte range. Runtime memory/idle CPU must still be measured on real target hosts before any desktop wrapper is called production-ready; bundle size is not used as a substitute for runtime measurement.

## Current Core additions relevant to Studio

`quillframe_production_readiness_v1` gives Review a real same-fingerprint conjunction gate instead of a fabricated quality percentage.

`quillframe_publication_ir_v1` + `publication/compiler.py` provide deterministic Accepted-text compilation to clean text, Web HTML, print-oriented HTML/CSS, and EPUB 3.3. Richer Publication Studio work remains bounded by the Core contracts that actually exist.

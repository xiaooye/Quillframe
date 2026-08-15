# NovelForge Studio · Portable Product Contract

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>PHASE 2A</kbd>&nbsp;&nbsp;<kbd>ONE PRODUCT · MANY HOSTS</kbd></p>

NovelForge Studio should feel like a polished SaaS product without requiring SaaS business plumbing. The product contract is shared across CLI, local application, cloud-hosted UI, and agent-skill/package adapters.

> **Invariant ✦ `DELIVERY SURFACE != SOURCE OF TRUTH.`**

## 01 · Four first-class delivery surfaces

### CLI

The CLI is the native automation and scripting surface. It should expose stable, typed query/command contracts and receipts, not force callers to import private Python modules.

### Local app / local Web UI

The local creator workstation can use filesystem-local adapters and local runtime capabilities, but the browser/UI still consumes projections and commands rather than owning Canon or reading persistence internals directly.

### Cloud-hosted UI

The hosted UI uses the same Studio projections and Core command semantics behind a remote API/query boundary. Hosting concerns such as auth, isolation, storage topology, and deployment do not redefine NovelForge story authority.

### Agent skill / package

Other agent frameworks should consume NovelForge through a thin, versioned adapter package. The adapter maps host invocation conventions to NovelForge capability/query/command contracts and returns typed receipts. It must not require the host framework to understand NovelForge's private implementation or database layout.

## 02 · Shared product boundary

```text
NovelForge Core contracts
        ↓
stable query / command / projection boundary
        ↓
┌────────────┬───────────────┬─────────────────┬──────────────────────┐
│ CLI        │ local app     │ cloud-hosted UI │ agent skill/package  │
└────────────┴───────────────┴─────────────────┴──────────────────────┘
```

The surfaces may differ in transport, available host capabilities, latency, and interaction density. They do not differ in Canon semantics, settlement semantics, Context authority, semantic-result meaning, or receipt truth.

## 03 · Capability is host evidence, not story authority

A host may report capabilities such as:

- local filesystem access;
- Git access;
- subprocess / CLI execution;
- Web or search availability;
- external model/provider access;
- MCP or other tool transports;
- publication renderer availability.

Those capabilities describe what the host can technically do. They do not grant Canon-write, Framework-write, settlement, or independent semantic authority.

Studio should therefore render two separate concepts:

1. **Host capability** — what this delivery environment can execute.
2. **NovelForge authority** — what a specific Core command/result is allowed to change or claim.

Never collapse them into one permission badge.

## 04 · Project Hub projection boundary

`novelforge_project_adapter_resolution_v1` contains host-local details that are useful to Core but inappropriate for a browser or remote consumer, especially absolute filesystem paths.

Phase 2A introduces a derived Studio projection with these rules:

- reject unknown source schemas;
- bind the exact source object with a deterministic fingerprint;
- expose project identity, layout, framework lock identity, logical paths, and safe policy metadata;
- omit `project_root` and every `paths.*.absolute` value by default;
- carry `authority=false`, `canon_authority=false`, `framework_write_authority=false`, and `settlement_authority=false`;
- never infer manuscript state, current chapter, publication status, or quality status from path existence alone;
- fingerprint the derived projection separately.

This is a presentation/query projection, not a new Project schema.

## 05 · Scene / Chapter workspace contract

The Scene workspace remains one product across all surfaces. A host may render it richly or expose it textually, but the conceptual modes stay stable:

- **Focus** — manuscript first;
- **Analysis** — manuscript plus Reader / Character / Context evidence;
- **Compare** — incumbent/challenger evidence and regressions;
- **Review** — user-visible gate and unresolved findings.

The workspace must keep these axes separate:

- manuscript lifecycle / authority;
- runtime execution state;
- semantic findings;
- provenance;
- host capability.

A running semantic job does not make a manuscript draft more Canon. An accepted manuscript does not prove that the current host can settle it.

## 06 · Agent-package contract direction

A generic NovelForge agent adapter should be intentionally small. Its stable public surface should be describable in terms of capability discovery, typed queries, typed commands, and receipts.

Recommended conceptual API:

```text
inspect_capabilities()
inspect_project()
inspect_context(...)
inspect_run(...)
invoke(command, input, preconditions)
resume(session_or_run_ref)
```

Phase 2A keeps mutating commands out of the prototype. Later adapters may expose commands only after Core defines the typed command and precondition semantics.

The adapter package should publish:

- adapter/package schema version;
- compatible NovelForge contract versions;
- supported operations;
- required host capabilities;
- permission/authority notes;
- typed result/receipt schemas;
- provider/framework-specific glue kept outside the generic contract.

Possible future host adapters include agent-skill packages, MCP-style hosts, framework plugins, or CLI bridges. These are adapters, not alternative NovelForge runtimes.

## 07 · What remains deliberately undecided

Phase 2A does **not** select:

- React/Vue/Svelte or another frontend framework;
- Electron/Tauri/PWA packaging;
- a cloud provider;
- an auth provider;
- a database topology;
- a specific external agent framework;
- a billing/subscription system.

Those choices should follow measured requirements after the stable boundary exists.

## 08 · Product quality bar

Across every host, NovelForge should preserve:

- Story Loom visual/semantic language where a visual UI exists;
- explicit unavailable/unsupported states rather than invented data;
- progressive disclosure from Creator Mode to Inspector detail;
- exact provenance and fingerprints when available;
- no chain-of-thought exposure;
- no fake engagement/consistency percentages;
- no direct browser mutation of Core persistence;
- no second Canon, Memory, quality, session, or semantic truth store.

## 09 · Phase 2A output

This slice adds:

1. a deterministic Project Hub projection;
2. browser/remote-safe path redaction;
3. exact source + projection fingerprints;
4. one portable product contract for CLI/local/cloud/agent-package delivery;
5. a read-only Project Hub + Scene workspace prototype;
6. synthetic fixtures for interaction QA.

The next architectural gate is not “which SaaS stack?” It is **which stable Core query/command boundary can every host consume without private implementation coupling?**

# Implementation Plan · Quillframe Repository Polish

## Chosen Architecture

Treat repository presentation as a thin public layer over existing authority. The root README orients; Starlight deepens; contributor/security/templates route participation; implementation contracts remain authoritative.

The README narrative will use:

`Hero → product problem → principles → architecture → authoring lifecycle → state boundaries → Studio/persistence → Quick Start → repository/docs map → status/contributing/license`.

Stable SVG brand/architecture assets already in the repository are preferred over a volatile Studio screenshot while the UI/UX branch is active.

## External Benchmark Patterns

Current GitHub presentation patterns were reviewed across LangChain, AutoGen, Pydantic, FastAPI, Vite, Tauri, AppFlowy, and Zed. Reusable patterns:

- one-sentence category clarity in the first screen;
- Quick Start close to the top but after enough product context to know what is being run;
- explicit project/status notices when lifecycle matters;
- layered architecture rather than a giant inventory;
- installation separated from contributor setup;
- docs/contribution/security entry points visible from the root;
- progressive disclosure for advanced internals;
- licensing stated plainly.

No external branding, copy, layout, or assets are copied.

## Affected Objects / Paths

Primary:
- `README.md`, `README.en.md`, `README.zh-CN.md`
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `.github/ISSUE_TEMPLATE/**`, `.github/pull_request_template.md`
- `docs/README.*`, `docs/why-quillframe.*`
- `site/docs-site/src/components/DocsLanding.astro`
- `site/docs-site/src/components/QuillframeActions.astro`

Presentation metadata cannot be changed by the available repository connector; exact recommended Description/Homepage/Topics will be recorded in the PR/report.

## Dependency Graph

1. Freeze live `main` and concurrent branch ownership.
2. Benchmark current public repositories.
3. Reconstruct README from current contracts.
4. Add contributor/security/community entry points.
5. Repair current-facing docs naming/routes.
6. Run/observe repository verification.
7. Re-fetch `main` and concurrent PRs; reconcile only merged truth.
8. Open Draft PR.

## Migration Strategy

Documentation-only additive/replacement changes. No data, runtime, or schema migration.

## Test / Eval Strategy

- current CI on pull request;
- site `quality`, `build`, and `docs:build` through CI;
- relative-path/anchor inventory review;
- YAML/template syntax review;
- external deployment-link verification where tooling permits;
- no Mermaid introduced, so Mermaid renderer validation is not applicable;
- rendered GitHub light/dark QA reported as unverified unless actual rendered evidence becomes available.

## Phases / Checkpoints

1. Specification and ownership freeze.
2. README landing reconstruction.
3. Contributor/security/GitHub templates.
4. Docs entry-point naming/link cleanup.
5. Verification and late truth reconciliation.
6. Draft PR.

## Rollback

Each change is commit-bounded and documentation-only. Revert the relevant commit without touching runtime or persistent project state.

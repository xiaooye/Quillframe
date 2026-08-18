# Tasks · Quillframe Repository Polish

Format: `[ID] exact target + completion criterion`

## Audit / reconciliation

- [x] T001 Freeze starting `main` at `e49304bde7fb0c5ba0822deb3823f960c6425804` and identify concurrent ownership.
- [x] T002 Reconcile merged Agent/Model Runtime PR #108 without importing provider authority.
- [x] T003 Reconcile merged UI/product-language PR #109 and later main layout/consistency fixes.
- [x] T004 Benchmark current high-star README patterns across agent/framework/product repositories.

## Repository landing

- [x] T005 Reconstruct root README as a complete product landing with Quick Start near the top.
- [x] T006 Synchronize native English and Simplified Chinese editions.
- [x] T007 Add stable theme-aware Quillframe mark + architecture/production artwork for GitHub light/dark rendering.
- [x] T008 Keep current status honest: pre-1.0, no shipped Tauri wrapper, no fake provider gateway.

## Contributor / legal surface

- [x] T009 Add `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `ROADMAP.md`, issue forms, and PR template.
- [x] T010 Rename legal product identifiers in `LICENSE` to Quillframe without changing the substantive source-available terms.

## Documentation governance

- [x] T011 Register paired Model Runtime and Agent Runtime docs in `documentation_manifest.json`.
- [x] T012 Surface Model/Agent Runtime in Starlight and repair docs-home links.
- [x] T013 Make standalone `scripts/docs_quality.py` executable against the current public-doc corpus.
- [x] T014 Run `docs_quality.py` in normal CI with no model/API execution.

## AI-readable public surface

- [x] T015 Add `robots.txt`, `sitemap.xml`, `sitemap.md`, `llms.txt`, `llms-full.txt`, `auth.md`, AI catalog, and Agent Skills index.
- [x] T016 Publish explicit `search=yes, ai-input=yes, ai-train=no` content-use signal while keeping the license authoritative.
- [x] T017 Explicitly deny unsupported public Core API / MCP / A2A / OAuth / hosted model-gateway claims.

## Verification / finalization

- [x] T018 Observe green full CI after docs-governance/runtime/Studio/site changes (runs #128 and #130 on earlier exact heads).
- [x] T019 Add an exact-head GitHub README renderer for desktop light/dark and 390px narrow light/dark, with screenshot + JSON evidence artifacts.
- [ ] T020 Obtain actual GitHub-render evidence for the final README head; if GitHub Actions blocks a newly introduced workflow before default-branch availability, record `awaiting_external` rather than a fake PASS.
- [ ] T021 Perform final late reconciliation against current `main` after concurrent sessions stop moving relevant surfaces.
- [ ] T022 Restore/remove any temporary PR-specific CI wiring; keep only reusable QA tooling.
- [ ] T023 Obtain green final-head CI after cleanup/reconciliation.
- [ ] T024 Write Repository Description/Homepage/Topics only if an authorized connected action exists; otherwise report exact settings as external.
- [ ] T025 Refresh Draft PR #110 body with exact final SHA/evidence and keep it Draft/unmerged.

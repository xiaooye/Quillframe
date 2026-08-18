# Implementation Plan · Quillframe Repository Polish

## Chosen Architecture

Treat repository presentation as a thin public layer over live Quillframe authority. README orients and starts; Starlight deepens; AI-discovery files describe; contributor/security/templates route participation; implementation contracts remain authoritative.

README narrative:

`Hero → Quick Start → why → product mental model → Model/Agent Runtime → production lifecycle → Studio/state → Learning → AI discovery → docs/repo map → status/security/license`

This deliberately follows the strongest pattern found in current high-star repositories: explain category and runnable value early, then earn deeper architecture detail.

## Benchmark set

Reviewed current README patterns from OpenClaw, Spec Kit, autoresearch, Pi Agent Harness, World Monitor, Matt Pocock's Skills, DeepSeek Harness, Superpowers, and additional mature framework/product repositories. Reused patterns are information-design patterns only; no external branding, prose, code, or layout is copied.

## Affected surfaces

- root English/Chinese README and theme-aware brand/architecture artwork;
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `ROADMAP.md`;
- GitHub issue/PR templates;
- docs home / Why Quillframe / Starlight navigation;
- `docs/documentation_manifest.json` and deterministic `scripts/docs_quality.py`;
- Model/Agent Runtime documentation discoverability;
- `site/public` AI discovery (`robots.txt`, XML/Markdown sitemaps, llms files, auth note, well-known catalogs, response headers);
- legal product identifier in `LICENSE`;
- README visual-QA automation/evidence tooling.

Repository Description/Homepage/Topics remain an external GitHub settings operation unless the connected GitHub action surface exposes an authorized repository-metadata write.

## Execution order

1. Freeze/re-read live `main` and concurrent ownership.
2. Reconcile merged runtime and UI/product facts.
3. Benchmark current high-signal READMEs and AI-readable web conventions.
4. Polish README and synchronized Chinese/English editions.
5. Register Model/Agent docs; repair Starlight routes and docs-home links.
6. Make `docs_quality.py` executable on the current corpus and add it to normal CI.
7. Add bounded AI discovery/content-use files.
8. Rename the legal product identifier without changing license terms.
9. Add theme-aware README artwork and real GitHub-render QA tooling.
10. Run CI/evidence, repair failures, then late-reconcile `main` again.
11. Refresh Draft PR #110 body; do not merge.

## Verification strategy

- `python scripts/docs_quality.py` in normal CI;
- Quillframe Python/runtime/authority regression suite;
- site `quality`, `build`, `docs:build`;
- Studio frozen install, typecheck, build;
- local-link and manifest inventory checks;
- actual public GitHub README render captured at desktop-light, desktop-dark, narrow-light, narrow-dark when GitHub Actions event semantics permit the new renderer to execute;
- screenshot/report artifacts bound to exact head SHA;
- no claim of visual PASS without actual GitHub-render evidence.

## Rollback

Changes are commit-bounded and avoid persistent project/runtime mutation. Revert repository-presentation/QA commits independently. LICENSE rename can be reverted independently because substantive license clauses were not changed.

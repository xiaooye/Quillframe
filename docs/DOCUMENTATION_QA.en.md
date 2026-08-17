# Documentation QA

Documentation QA verifies that Quillframe's current explanation remains aligned with current implementation without turning prose review into a fake deterministic semantic judge.

## Deterministic checks

The documentation gate should verify manifest registration, paired-language presence, one H1 per registered page, local links and assets, UTF-8, current framework-version identity, stable router paths, and SVG parseability/accessibility metadata.

Current public-brand surfaces must use Quillframe while allowlisted technical identifiers and historical records may retain the legacy namespace. A brand-leak check must be scoped; global string replacement is explicitly forbidden.

## Visual checks

Documentation-owned SVGs are checked for a valid viewBox, non-empty `<title>` and `<desc>`, valid colors, no embedded font files, and readable labels. Human review additionally applies the border budget: remove any border, card background, decoration, or container that does not carry information.

The acceptance question is not “is it pastel?” It is whether the information remains clear with less visual ink and whether the page reads as an editorial canvas rather than a dashboard.

## Semantic review

A human/model documentation review checks whether the mental model matches implementation, whether a diagram encodes the correct authority relationship, whether English/Chinese copies have semantic parity, and whether documentation has accidentally promoted evidence into authority.

Deterministic green checks cannot prove those semantic properties by themselves.

## Historical records

Historical specs preserve the public name and terminology that were true when written. Current docs can annotate or link to them, but documentation reconstruction does not rewrite history.

## Scope guard

Documentation work must not modify Product UI, Godot/Solid/React/Vue implementation, application CSS, runtime semantics, or consumer Project state. Discoveries outside documentation become `UI_REBRAND_FOLLOWUP` or `DOCUMENTATION_DISCOVERED_IMPLEMENTATION_GAP` records.

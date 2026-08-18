# Documentation Standard

Quillframe documentation follows one visual and information principle: **the page is the canvas**. Structure should come from typography, spacing, alignment, and semantic sequence before it comes from containers.

## Information architecture

Major documentation should begin with one paragraph that gives the mental model. Add one canonical diagram only when spatial structure materially improves understanding. Detailed explanation follows. Contracts, schemas, and reference material come last rather than leading the page.

The docs home organizes material as Start Here, Core Concepts, Writing, Quality, Canon & Settlement, Context & Memory, Learning, Semantic Execution, Session & Control Plane, Corpus & Research, Project Integration, Development, and Reference.

## Canvas first, cards second

Default state: no container.

If spacing can create the group, do not draw a border. If a faint semantic wash can create the group, do not draw a border. If typography can create the hierarchy, do not draw a border.

Use a boundary only for a real artifact, state, comparison, or explicit conceptual container. Do not nest framed cards inside framed sections.

## Visual language

The base is warm ivory or soft off-white with graphite ink. Large display type establishes editorial hierarchy. Technical labels stay small, precise, and quiet. Kawaii personality is a restrained accent—roughly five percent of the page, and often less in dense technical diagrams.

Allowed micro-details include a tiny spark, tape fragment, ribbon marker, or soft index tab. A diagram normally needs zero to three such details.

## Semantic color

Project uses soft blue; Runtime violet; Editorial soft pink; Evidence warm cream/gold; Validated mint; Rejected/Stale soft rose; Neutral uses warm paper and graphite. Color is a signal, never the only carrier of meaning.

## Diagram rules

Technical architecture is SVG-first: diffable, inspectable, scalable, accessible. Prefer open groups, text-only nodes, thin connectors, short rules, and small semantic markers over repeated rounded rectangles.

Every documentation SVG needs a meaningful `<title>` and `<desc>`, readable labels, sufficient contrast, and a textual explanation in the document when the structure is complex. Do not use AI-generated raster art as a technical diagram.

## Public brand and technical namespace

Quillframe is the current public brand. The former brand remains only where it names a historical record or compatibility identifier. Repository names, schema IDs, `quillframe.toml`, `quillframe.lock.json`, workflow names, and stable contract IDs are technical namespace and are not globally replaced.

## Bilingual parity

English and Simplified Chinese are native editions with semantic parity, not line-by-line translations. Formal terms such as Canon, SETTLE, Candidate Lineage, and Context Manifest may remain in English when that preserves contract precision.

## Source hierarchy

Current implementation, schema, tests, and current manifest outrank explanatory documentation. Historical specs preserve what was designed under the name used at the time; current docs may link to them without rewriting history.

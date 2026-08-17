# Project SDK

A Quillframe Project is an independently versioned fiction project. The framework supplies generic production mechanisms; the Project supplies concrete story authority.

<img src="assets/architecture/framework-vs-project.en.svg" alt="Project points to a pinned framework while concrete characters, Canon, plans, state, research, and manuscripts remain Project-owned" width="100%" />

## Project identity

A supported Project declares its schema and paths in `novelforge.toml`, pins an exact framework revision in `novelforge.lock.json`, and may attest the materialized framework bundle. These filenames remain compatibility identifiers even though the public framework brand is Quillframe.

## Ownership

Project-owned data includes concrete BOOK/VOL/ARC/UNIT/CH/SCN instances, characters and relationships, current state, claims, dependencies, active plans, profiles, research, regressions, manuscripts, and Accepted Canon.

Generic framework source must never import those private story facts as built-in behavior.

## Standard and mapped layouts

The Project SDK supports a standard layout; Project Adapters can map mature/legacy repositories into the same logical contract. Mapping changes storage paths, not authority semantics.

## Reproducibility

A Project should validate and build without chat memory. The exact framework pin and deterministic bundle fingerprint make runtime bytes inspectable and repeatable. Framework current `main` is development authority for framework maintenance; it is not silently substituted for a consumer's pin during ordinary production.

## Change discipline

Structural changes may use spec → plan → tasks → implementation → verification → acceptance. Ordinary prose micro-edits do not need software-engineering ceremony. Canon mutation still requires explicit acceptance plus settlement regardless of repository layout.

# Native Project Contract

A Quillframe 1.0 Project is the authority boundary for one complete novel. The Framework supplies generic mechanisms; the Project owns concrete story facts and Canon. This is the current development contract, not a declaration that production or cloud release acceptance is complete.

## Create or open

Create and open a local Project through the native launch command:

```bash
quillframe launch ./my-novel --new \
  --id MY-NOVEL \
  --title "My Novel" \
  --language en
```

Opening an existing Project uses `quillframe launch ./my-novel`. With no path, an interactive launch checks the current directory, then the last explicitly opened Project, then offers the new-Project wizard. Non-interactive ambiguity fails with a typed error.

## Exact 1.0 identity

The native four-key `quillframe.toml` contains exactly these root keys:

```toml
schema = "quillframe_project_v1_0"
id = "MY-NOVEL"
title = "My Novel"
language = "en"
```

All values are non-empty strings. The Project identifier is 1–64 ASCII letters, digits, dots, underscores or hyphens and starts with a letter or digit. The resolved context retains `quillframe_project_context_v1_0` and exposes top-level `scope: "novel"`; scope is not a manifest key. An extra `chapter_scope` key, another schema or legacy metadata is rejected before Core state is opened. There is no adapter, state upgrader or dual read path.

Local durable state lives under `.quillframe/data/`. SQLite must match both `project:1.0` and the exact current schema fragments. Incompatible or incomplete development state is left untouched and rejected. Create a separate new Project when the state contract has changed; opening does not migrate, repair or reseed it.

Native creation reserves a new identity and creates the Project row, initial chapter `CH001` and manuscript `DOC-CH001` in one Project-database transaction. It does not upsert an existing Project. Filesystem publication and the global Project registry are separate transaction boundaries.

## Ownership

Project-owned data includes story and character facts, plans, research, manuscript revisions, explicit author decisions, Accepted Canon, settlement receipts, and publication state. Models provide semantic evidence and proposals. Core owns deterministic state, permissions, fingerprints, budgets, transactions, and idempotency.

Neither the browser, a coding-agent host, a model response, SQLite presence, nor a capability declaration grants Canon authority.

## Novel and chapter boundaries

`CH001` is only the initial chapter, not a limit on the novel. Later chapters, including `CH002`, are valid after explicit creation. Each manuscript must refer to a real chapter in the same Project. A syntactically valid chapter identifier alone does not prove that the chapter exists or authorize a workflow.

Review, acceptance and settlement bind an exact chapter candidate and its source fingerprints. Accepting a new revision does not settle it automatically. Changing a settled source can make a dependent chapter stale; a previous settled head must not be presented as the current exportable acceptance while a newer acceptance awaits settlement.

## Reproducibility and export

Core-owned backup and restore use top-level `scope: "novel"`, exact Project/schema fingerprints and actual chapter relationships. They do not synthesize missing chapters. Backup bundles carry the Project database and verified blobs; they do not promise to transport publication files stored outside those members.

Collection publication accepts explicit, unique acceptance IDs in chapter reading order and produces Markdown or text from those exact accepted bytes. Every chosen acceptance must be current, settled and free of stale dependencies for its own run. A historical artifact can still be retrieved by build ID, with its source binding, byte size and SHA-256 fingerprint verified; it is not evidence that the chapter remains current. Publication output has `authority=false`.

Hosted upload must be explicit; local launch never auto-uploads or auto-syncs. Exported bundles must not contain model credentials or private reasoning. Deterministic storage and publication tests do not establish live-model quality, independent-review completion, a full-novel production run or cloud deployment readiness.

## Native contract boundary

The four-key `quillframe.toml`, context with top-level `scope: "novel"`, `manifest_fingerprint` and `.quillframe/data` boundary define native Project identity. A deterministic transport bundle may carry fingerprint evidence, but it is never Project authority. Local launch and Host Bridge v11 use this same Core contract.

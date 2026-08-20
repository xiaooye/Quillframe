# Native Project Contract

A Quillframe 1.0 Project is the single authority boundary for one work of fiction. The Framework supplies generic mechanisms; the Project owns concrete story facts and Canon.

## Create or open

The only author-facing creation and launch surface is:

```bash
quillframe launch ./my-novel --new \
  --id MY-NOVEL \
  --title "My Novel" \
  --language en
```

Opening an existing Project uses `quillframe launch ./my-novel`. With no path, an interactive launch checks the current directory, then the last explicitly opened Project, then offers the new-Project wizard. Non-interactive ambiguity fails with a typed error.

## Exact 1.0 identity

The root `quillframe.toml` declares exactly `quillframe_project_v1_0`, Project identity, language, and `chapter_scope = "CH001"`. Another schema or chapter scope is rejected before Core state is opened. There is no import, mapped layout, state upgrader, or dual read path.

Local durable state lives under `.quillframe/data/` and carries an exact `project:1.0` SQLite schema identity. A database without that identity is left untouched and rejected. Creating a new 1.0 Project is the recovery path for pre-release state.

## Ownership

Project-owned data includes story and character facts, plans, research, manuscript revisions, explicit author decisions, Accepted Canon, settlement receipts, and publication state. Models provide semantic evidence and proposals. Core owns deterministic state, permissions, fingerprints, budgets, transactions, and idempotency.

Neither the browser, a coding-agent host, a model response, SQLite presence, nor a capability declaration grants Canon authority.

## CH001 boundary

1.0 acceptance executes CH001 only. CH002 and later chapters are rejected before projection, context assembly, model routing, drafting, review, acceptance, settlement, or publication.

## Reproducibility and export

Core-owned backup/export actions bind exact Project and artifact fingerprints. Hosted upload is explicit and one-way per action; local launch never auto-uploads or auto-syncs. Exported bundles contain Project material and safe receipts, never model credentials or private reasoning.

## Native contract boundary

The native five-key `quillframe.toml`, CH001 context, `manifest_fingerprint`, and `.quillframe/data` boundary are the only Project identity contract. A deterministic transport bundle may carry fingerprint evidence, but it is never Project authority. Product creation, opening, and normal authoring enter through `quillframe launch` and Host Bridge v11.

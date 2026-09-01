# Windows Ultra-Long Production Verification

2026-09-01 · `SYSTEM-IMPROVE`

## Verified on Windows

- `cargo fmt --all -- --check`, workspace `check`, Clippy with `-D warnings`, and `cargo test --workspace --all-targets --locked` pass. The workspace runs 48 deterministic tests: 39 Core, 1 host, 7 native filesystem/publication, and 1 secrets test.
- The three-chapter Core acceptance runs model-mediated context query/selection, Corpus and preference greenlights, scene-by-scene prose, semantic review/repair, acceptance, settlement, typed-ledger projection, publication, restart continuity, and preference learning.
- The same acceptance corrupts an authoritative character projection, proves strict open rejects it, invokes the explicit local Rust Bridge snapshot restore at expected revision 3, and proves strict reopen succeeds. Restore reports `semantic_inference=false`.
- Tauri manifest formatting, Clippy, and its direct-Core boundary test pass.
- Root `pnpm` quality, typecheck, test, and build pass for the product site, SolidJS Studio, and Cloud contract mirror. Studio tests prove business state goes through the typed Bridge.
- Repository scan finds zero `.py`, `.pyi`, `pyproject.toml`, or `__pycache__` files. CI contains a separate interpreter-residue rejection gate.

## Cross-platform evidence

The main CI and Tauri CI both run Core/Tauri on `windows-latest` and `ubuntu-latest`; Linux desktop dependencies are installed explicitly. This Windows record does not fabricate a local Linux result—the Ubuntu jobs remain the authoritative Linux execution evidence.

## Evidence boundary

No synthetic five-million-character endurance run was performed. These green gates prove deterministic production mechanisms and recovery, not the literary quality of a five-million-character novel. A live sequential literary canary and author judgment remain pending.

# 017 · Tauri 2 Thin Host

## Authority
- Primary task mode: `SYSTEM-IMPROVE`.
- Frozen Framework/Product authority: `main@252fcd6066a73df06953c974f2324e1c264492a6`.
- Branch: `agent/tauri-thin-host-v8`.
- Host Bridge authority: v8.
- No consumer Project repin, novel Canon mutation, prose production, or Studio visual redesign.

## Goal
Complete the missing Desktop host for the already-merged SolidJS Studio consumer without creating a second Core implementation.

Canonical dependency remains:
`SolidJS → Tauri 2 thin host → packaged Python Core sidecar → Host Bridge v8 → Python Core → SQLite`.

## Thin-host ownership
Rust/Tauri may own window/process lifecycle, IPC framing, sidecar launch, OS integration and OS-native secret storage. It must not own Context selection, semantic judgment, Model Service capability inference, Project/Document queries, Candidate lifecycle, Acceptance, Settlement or Canon rules.

The frontend receives exactly the existing Host Bridge result envelope through one command: `bridge_invoke`.

## Sidecar model
Use Tauri external binary packaging for a one-shot Python Core sidecar. Each invocation receives one JSON payload on stdin and returns one sanitized JSON result on stdout. No localhost server, temporary bearer-token file, hidden polling loop or browser database is required.

## Credential durability
Desktop Model Service credentials must survive app restart in the platform-native credential store, never in SQLite or browser state. Durable Core SQLite stores only `credential_ref`.

For credential-producing requests, Tauri must pre-store the secret under a fresh `keyring:qf:<uuid>` reference before Core writes that reference. The injected Python SecretStore must return that exact preallocated reference. If Core fails before committing the reference, Tauri deletes it. If transport acknowledgement is uncertain, Tauri re-reads durable Core credential references before cleanup so it cannot delete a reference already committed by Core.

Existing credential references are enumerated internally by the sidecar from the Model Service repository, resolved by Tauri from the OS credential store, and injected only into that one sidecar process. Secret bytes never enter public bridge results, receipts, Context or logs.

## Acceptance
- Python sidecar source self-test passes against Host Bridge v8.
- PyInstaller one-file target-suffixed sidecar builds and passes the same self-test.
- Rust unit tests and compile pass on current Tauri 2.
- Real Linux Secret Service set/get/delete round-trip passes in CI when the runner provides D-Bus/keyring support.
- `cargo tauri build --debug --no-bundle` succeeds with the packaged sidecar.
- Studio Web consumer regression remains green.
- No plaintext credential appears in public output, SQLite, browser persistence, Vite assets or test logs.
- Core/Studio semantics remain Cloudflare-independent.
- Old PR #129 is closed as superseded only after the new host lands.

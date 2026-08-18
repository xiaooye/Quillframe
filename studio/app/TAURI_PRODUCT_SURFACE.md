# Quillframe Studio · Tauri 2 product surface

Core authority consumed by the current Studio consumer: `main@6ee7299f81b92e11b67da32d16abf73e7ace1ccd`, Host Bridge **v8**.

## Current PR #130 state

The SolidJS consumer side is implemented:

```text
SolidJS Studio
  → BridgeClient
    → TauriTransport
      → invoke("bridge_invoke", { request })
```

`TauriTransport` accepts only the same `quillframe_studio_host_bridge_request_v1` / `quillframe_studio_host_bridge_result_v1` semantics used by other transports. It does not read SQLite, infer Canon, run semantic logic, or persist credentials.

The **actual Tauri 2 host is intentionally not claimed by PR #130**. There is not yet a committed `src-tauri` host in this consumer branch. Desktop therefore remains `awaiting_external` even though the TypeScript transport exists.

## Required thin-host architecture

The follow-on Desktop host must implement:

```text
SolidJS
→ one Tauri command: bridge_invoke
→ thin Rust host
   ├─ packaged Python Core sidecar
   └─ OS-native credential store
→ studio/host_bridge.py v8
→ Python Core
→ SQLite
```

Rust may own process lifecycle, IPC framing, OS integration, window lifecycle and secure secret storage. It must **not** duplicate Python Core operation semantics, Context logic, Candidate lifecycle, Settlement policy, Model Runtime capability judgment, or SQLite domain queries.

## Secret boundary

Desktop Model Service credentials must survive app restart without entering SQLite, browser storage, Vite assets, semantic Context, receipts or logs.

The intended boundary is:

1. Studio sends Endpoint + Access Token only through the Tauri IPC request.
2. Tauri host / OS secure store owns durable secret bytes.
3. Python Core receives a host-injected `SecretStore` view keyed by `credential_ref`.
4. Durable Quillframe SQLite stores only the reference/public presence metadata.
5. Core/bridge public results never echo the credential value.

A process-local `MemorySecretStore` is not sufficient for Desktop production acceptance.

## Desktop acceptance gate

Do not call Desktop production-ready until a separate host implementation proves:

- Tauri 2 app compiles against the current Studio build;
- `bridge_invoke` round-trips a real `bridge.describe` Host Bridge v8 request;
- Python Core is packaged/launched as a sidecar rather than reimplemented in Rust;
- OS-native secret set/get/delete works and survives app restart;
- Model Service reconnect after restart resolves its durable `credential_ref` without storing plaintext in SQLite;
- secret values do not appear in stdout/stderr, window state, browser storage or bridge results;
- Project/manuscript operations round-trip through the same Python Core;
- Desktop remains Cloudflare-independent.

This is a distinct host engineering workstream after the Web/Studio consumer PR #130 is merged; it is not replaced by a browser mock or by declaring the TypeScript transport itself sufficient.

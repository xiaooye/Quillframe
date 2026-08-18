# Quillframe Studio · Tauri 2 consumer surface

Status: **awaiting_external** on frozen main `5fd991a5621f2c68e1030aa6e0b35014ca4011c7`.

This document belongs to the Studio consumer. It does **not** define Python Core behavior, SQLite authority, provider protocols, or secret storage.

## Product topology

```text
SolidJS Studio
  → BridgeClient
    → TauriTransport
      → Tauri 2 command: bridge_invoke
        → local Quillframe Core
          → canonical SQLite
```

The Desktop product must be completely Cloudflare-independent. Cloudflare configuration, bindings, Workers, Pages, or temporary serverless storage are not part of this path.

## Exact host primitive required

Studio detects a real Tauri host only when `window.__TAURI__.core.invoke` exists. It then calls:

- command: `bridge_invoke`
- input: one `quillframe_studio_host_bridge_request_v1` object
- output: one `quillframe_studio_host_bridge_result_v1` object

Until Core/host ownership supplies that command, `TauriTransport.available()` remains false. Studio does not install a JavaScript mock or route requests through Cloudflare.

Current Core contract exposes `local_app` but no distinct `tauri_local` semantic surface. Therefore Tauri forwards the same `local_app` envelope. If Core later introduces a stable Tauri-specific surface, Studio must reconcile after that Core change is reviewed/merged.

## Required host behavior

1. Start/connect to the real local Python Core without copying Core semantics into Rust/TypeScript.
2. Preserve the request/result envelope and operation names exactly.
3. Keep canonical persistence in Core-owned SQLite.
4. Never return secret values to Studio.
5. Return typed `unsupported`/`failed` results rather than fabricating normal-path data.
6. Survive Desktop app restart while relying on Core persistence, not browser persistence.
7. Preserve explicit authorization for authority commands.

## Verification still required

A packaged Tauri build must prove, on an installed application:

- create/open Project;
- manuscript write + autosave + app/Core restart + exact reload;
- Endpoint + Access Token connection through Core-owned secret handling;
- real Agent Run through the production semantic runtime;
- Candidate/Review/Accept/Settlement sequence;
- Context/Run inspection;
- no Cloudflare/network dependency for local-only operation.

Until those checks execute against the real host primitive, Desktop production readiness is not claimed.

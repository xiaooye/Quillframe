# Quillframe Studio · Tauri 2 surface

Status: implemented locally against Host Bridge **v11**; OS/runtime acceptance still required before a desktop release claim.

## Architecture

```text
SolidJS Studio
→ TauriTransport
→ invoke("bridge_invoke", { request })
→ thin Rust host
   ├─ packaged quillframe-core Python sidecar
   └─ OS keyring
→ Host Bridge v11
→ Python Core + project-local SQLite
```

Rust owns process lifecycle, IPC framing, window integration, secret-store calls, and output redaction. It does not duplicate Python workflow, Context, Candidate, Settlement, model-routing, or persistence semantics.

## Secret boundary

The access token enters only the Tauri IPC request. Rust allocates a `keyring:qf:*` reference and writes the secret to the OS keyring before invoking Core. The sidecar receives a request envelope and already committed references, returns only a Bridge result plus secret actions, and never persists plaintext in SQLite. Failed or unconsumed allocations are deleted. stdout, stderr, and returned errors are scrubbed against known secret values.

## Acceptance gate

A desktop artifact remains unreleased until an actual packaged build proves:

- Host Bridge v11 round-trip through the bundled sidecar;
- create/open/write/review/publish operations after restart;
- OS keyring set/get/delete and reference recovery after restart;
- no secret in SQLite, browser storage, process logs, bridge results, or exports;
- offline local operation independent of Cloudflare;
- signed installer and platform-specific permission behavior.

Static TypeScript, Rust unit tests, or a browser mock are necessary evidence but not a substitute for that packaged runtime check.

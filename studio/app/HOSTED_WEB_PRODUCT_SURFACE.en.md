# Quillframe Studio · Hosted Web surface

Status: Cloud Worker implementation and deterministic security tests are local; a real WorkOS/Cloudflare deployment remains `awaiting_external`.

## Topology

```text
Hosted SolidJS Studio
→ Cloudflare Worker BFF
   ├─ WorkOS AuthKit
   ├─ WorkspaceCoordinator Durable Object
   ├─ encrypted SessionVault Durable Object
   ├─ encrypted R2 Project bundles
   └─ Python Core Container
→ Host Bridge v11
```

The browser owns presentation and explicit user actions only. It never receives WorkOS access/refresh tokens, model credentials, R2 encryption keys, or direct Durable Object bindings.

## Authentication and session

Authorization uses state, PKCE, a single-use auth transaction, and an exact callback URI. The BFF issues opaque `__Host-` cookies with `HttpOnly`, `Secure`, and `SameSite=Lax`; state-changing requests also require same-origin and double-submit CSRF evidence. Sessions expire after 30 minutes idle or 8 hours absolute. Logout, explicit session end, and project deletion destroy server-side sessions and leased secrets.

## Project and BYOK boundary

Cloud upload is an explicit request and never begins during local launch or sign-in. R2 stores only encrypted bundles. SessionVault stores AES-GCM ciphertext and bounded leases; model tokens never enter Project bundles, logs, receipts, analytics, or semantic context. Hosted custom endpoints must be public HTTPS and pass DNS, redirect, private-range, rebinding, and destination-bound probe checks.

## Deployment acceptance

Production status requires account-bound evidence for the configured custom auth domain, email/GitHub/Google/passkey flows, callback/logout, durable restart, encrypted upload/restore/delete, Core Container operation, endpoint validation, and log redaction. Until those live checks run, the implementation is not described as deployed or production-ready.

# Quillframe Studio · Hosted Web consumer surface

Core authority consumed by this Studio workstream: `main@6ee7299f81b92e11b67da32d16abf73e7ace1ccd`, Host Bridge **v8**.

The Hosted Web **consumer implementation is complete**. A particular deployment remains `awaiting_external` until its host supplies a real authenticated durable Core endpoint.

## Topology

```text
Hosted SolidJS Studio
  → BridgeClient
    → HostedHttpTransport
      → authenticated Quillframe Core API
        → Python Core
          → durable SQLite host
```

Cloudflare, Vercel, another edge, or a conventional server may host static UI/routing/TLS. None is a Studio/Core semantic model, and ephemeral serverless filesystems must not be treated as canonical SQLite persistence.

## Host configuration

The Studio document may receive a non-secret meta value:

```html
<meta name="quillframe-studio-hosted-endpoint" content="https://core.example.com" />
```

If it is empty, `HostedHttpTransport.available()` is false and Studio remains unbound. Studio does not fall back to browser persistence or fixture authority.

The endpoint itself is not a credential. Authentication/session material remains host-owned and must not be embedded into Vite environment variables or semantic context.

## Required Host Bridge v8 behavior

The hosted Core API must expose the same typed request/result semantics as the other transports. Current Studio authoring paths consume, among others:

- `project.list`, `project.create`, `project.inspect`;
- `document.list`, `document.open`, revision save/list/compare;
- `author.run.start`, `author.run.status`, `author.run.execute`;
- `candidate.review.get`, Accept, Reject, Request Revision;
- `settlement.preflight` then separately authorized `settlement.apply`;
- Model Service Endpoint+Token lifecycle/probes;
- Context/Inspector/publication projections.

Host/CORS/auth failures and Core typed failures must remain failures. The UI never reinterprets them as success.

## Credential boundary

Hosted Web must keep Model Service credentials in a server-side secure secret/session facility and pass them only across the host→Core credential boundary. Browser local/session storage, Vite bundles, Context and Project state are forbidden locations for credential values.

## Deployment acceptance still external

A real hosted deployment is production-ready only after a reachable durable Core instance is tested for:

- create/list/open Project;
- exact Binder/manuscript reload after browser and Core restart;
- Model Service success/failure paths with server-side secret persistence;
- DRAFT/REVISE execution through `awaiting_external` and a genuine independent-review transport;
- exact Candidate Review / Accept / Reject / Request Revision behavior;
- Settlement preflight/apply separation;
- Context/Run inspection;
- durable SQLite state after service restart.

Those are host/deployment acceptance checks, not reasons to fabricate browser authority in the static Studio build.

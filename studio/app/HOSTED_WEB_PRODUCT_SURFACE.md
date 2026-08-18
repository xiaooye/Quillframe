# Quillframe Studio · Hosted Web consumer surface

Status on frozen main `5fd991a5621f2c68e1030aa6e0b35014ca4011c7`: **awaiting_external** unless the host injects a real durable Core endpoint.

## Topology

```text
Hosted SolidJS Studio
  → BridgeClient
    → HostedHttpTransport
      → authenticated Quillframe Core API
        → Python Core
          → durable SQLite host
```

Cloudflare may implement the HTTP hosting layer, routing, TLS, authentication edge, or static asset delivery. It is **not** a Studio/Core semantic model and its ephemeral filesystem must not be treated as canonical SQLite persistence.

## Host configuration

The Studio document may receive a non-secret meta value:

```html
<meta name="quillframe-studio-hosted-endpoint" content="https://core.example.com" />
```

If it is empty, `HostedHttpTransport.available()` is false and the Studio remains unbound. Studio does not fall back to browser persistence or fixture responses.

The endpoint itself is not a credential. Authentication/session material remains host-owned and must not be embedded into Vite environment variables or semantic context.

## Required API behavior

The host must expose the same typed Host Bridge request/result semantics used by other transports. Every normal-path action must return a real Core result. CORS/auth/session policy is a host responsibility; operation semantics remain Core-owned.

Required failure behavior includes explicit HTTP/typed failures for unavailable host, authentication failure, unsupported operation and Core operation failure. The UI must not reinterpret those failures as success.

## Verification still required

Hosted production readiness requires a reachable durable Core deployment and browser verification of:

- create/open Project;
- exact manuscript reload after browser reload/Core restart;
- model connection failure and success paths;
- real semantic Run/Candidate path when Core exposes it;
- Review/Accept/Settlement separation;
- Context/Run inspection;
- persistence after service restart.

Until a real endpoint exists for the PR build, browser E2E remains `awaiting_external` rather than mocked.

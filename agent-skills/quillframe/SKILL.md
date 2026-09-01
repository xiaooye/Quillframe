---
name: quillframe
description: Inspect a Quillframe fiction project through the typed Host Bridge v11 without opening private persistence.
compatibility: Requires Rust 1.88+ and a Quillframe checkout. Set QUILLFRAME_ROOT when installed outside that checkout.
metadata:
  quillframe-host-bridge: "v11"
  authority: "read-only"
---

# Quillframe portable Agent Package

Use the Rust host as a thin adapter over the public Bridge. Core owns Project, Canon, Settlement, model execution, Corpus, and persistence; this package does not become an authority layer.

Build the host:

```text
cargo build -p quillframe-host --locked
```

Send one exact v11 request through `quillframe-host invoke` or a sequence of newline-delimited requests through `quillframe-host stdio`:

```text
quillframe-host invoke --core-root PATH --request JSON
quillframe-host stdio --core-root PATH
```

Begin with `bridge.describe`, whose response schema is `quillframe_host_bridge_description_v11`. Send only exact `quillframe_host_bridge_request_v11` envelopes. This portable skill is query-only and fails closed for command kinds, unknown operations, missing arguments, or operations not allowed on `agent_package`; `database.doctor` is side-effect-free in this surface. Use only operations returned in `operations`; entries in `deferred_operations` are not executable. Preserve the returned request and result fingerprints, keep `authority: false`, and never open a Project database or credential store directly.

Before presenting a result, verify Bridge version `11`, exact request binding, false authority fields, and absence of private paths or credentials.

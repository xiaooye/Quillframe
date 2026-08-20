---
name: quillframe
description: Inspect a Quillframe fiction project through the portable read-only Host Bridge v11. Use it for project orientation, capability discovery, safe projections, publication previews, and typed diagnostics without importing private runtime code.
compatibility: Requires Python 3.11+ and a Quillframe checkout. Set QUILLFRAME_ROOT when installed outside that checkout.
metadata:
  quillframe-host-bridge: "v11"
  authority: "read-only"
---

# Quillframe portable Agent Package

This package is a thin, read-only adapter over the public Quillframe Host Bridge. Core owns Project, Canon, Settlement, model execution, and persistence. The package never becomes an authority layer and never opens a private store.

## Discover the live contract

Run:

```bash
python scripts/quillframe_bridge.py self-test
python scripts/quillframe_bridge.py describe
```

The live description is `quillframe_host_bridge_description_v11`. Use its `operation_contracts` metadata as the only operation vocabulary. Each entry declares `kind`, `required_args`, and, where relevant, `allowed_surfaces`.

## Invoke a query

Create a request with the exact v11 envelope and invoke it through the client:

```json
{
  "schema": "quillframe_host_bridge_request_v11",
  "bridge_version": "11",
  "request_id": "REQ-unique",
  "operation": "project.list",
  "surface": "agent_package",
  "args": {},
  "authority": false
}
```

```bash
python scripts/quillframe_bridge.py invoke --request /path/to/request.json
```

The `agent_package` surface is query-only and fails closed before forwarding if the operation is unknown, is not exactly `kind: query`, lacks required arguments, or is not allowed on `agent_package`. It never carries a command fallback or a second protocol version. Returned envelopes use `quillframe_host_bridge_result_v11`; preserve their request and result fingerprints and `authority: false`.

Typical safe queries include `bridge.describe`, `database.doctor`, `project.list`, `project.inspect`, `project.search`, `document.list`, `document.open`, `document.revisions.list`, `document.revision.compare`, `author.run.status`, `author.run.events`, `model.service.list`, `model.service.get`, `model.capabilities`, `candidate.review.get`, `candidate.visible.get`, `settlement.preflight`, `publication.preview`, and typed inspector projections. Use only entries present in the live description; the list above is illustrative, not an authority source.

`database.doctor` is side-effect-free. Do not send a `fix` argument: repair is not part of the portable query contract.

## Boundary rules

- Keep `surface` exactly `agent_package` and `authority` exactly `false`.
- Never invoke `kind: command`, `semantic_command`, `authority_command`, `secret_command`, `external_query`, or either external-handoff kind from this package.
- Never open `.quillframe/runtime.db`, SQLite, or other private persistence directly.
- Never import private Core, Control Plane, or model-runtime modules as a substitute for the bridge.
- Never forge `local_app`, `hosted_web`, or `cli` as the package surface.
- A successful query, capability, fingerprint, or preflight is not write authority.
- Preserve `unsupported`, `invalid`, `failed`, and other result states exactly; do not reinterpret them as permission to continue.
- This package cannot create or alter Projects, documents, candidates, Canon, Settlement, runtime state, model services, or publication state.

## Final checks

Before presenting a result, confirm the result schema is v11, the bridge version is `11`, `authority` is false, and no private host path, credential, provider session identifier, or direct persistence detail has been exposed.

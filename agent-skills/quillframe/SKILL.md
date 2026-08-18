---
name: quillframe
description: Inspect a Quillframe fiction project through the portable read-only Studio host bridge. Use for Quillframe project orientation, host capability checks, runtime/session observability, deterministic runtime-command preflight checks, Context Manifest inspection, semantic contract discovery, or when another agent framework needs a safe Quillframe integration without importing private runtime internals.
compatibility: Requires Python 3.11+ and a Quillframe checkout. Set QUILLFRAME_ROOT when the skill is installed outside that checkout.
metadata:
  quillframe-host-bridge: "v1"
  authority: "read-only"
---

# Quillframe portable skill

**Language:** English operating instructions. 简体中文用户可以直接提出中文请求；machine contracts and operation identifiers remain unchanged.

Use this skill as a thin **read-only agent-package client** of Quillframe's public product boundary. Do not treat the skill, the current agent, or host tool availability as Canon, Settlement, Framework-write, Project-write, runtime-mutation, or semantic authority.

## Start with discovery

Run:

```bash
python scripts/quillframe_bridge.py describe
```

The shared bridge description is host-wide. Its `supported_operations` may therefore advertise operation-specific commands that are available only to another delivery surface such as `local_app`. For this portable `agent_package` skill, invoke **query operations only**. If an operation contract has `kind: command`, do not invoke it through this skill even when it appears in the shared supported vocabulary.

Never guess operations from private Python modules or persistence tables. Preserve each operation contract's `allowed_surfaces`, mutation scope, authorization requirements, and authority flags exactly.

## Invoke a read operation

Create a JSON request with schema `quillframe_studio_host_bridge_request_v1`, then run:

```bash
python scripts/quillframe_bridge.py invoke --request /path/to/request.json
```

Every request must carry `authority: false`. Treat the returned `request_fingerprint` and `result_fingerprint` as provenance for that invocation.

Typical read-only uses include:

- inspect Framework health;
- inspect a Project through the safe Project Hub projection;
- inspect locally provable host capabilities;
- inspect durable runtime sessions through side-effect-free Core projections;
- inspect one session's safe run/checkpoint state;
- inspect typed runtime event metadata;
- inspect a handoff's safe state/permission projection;
- retrieve metadata-only Run Receipts and runtime-command receipts;
- run `session.resume.preflight` to obtain deterministic resume eligibility;
- run operation-specific termination preflight when the live contract exposes it as a query;
- inspect a project-scoped Context Manifest;
- inspect the semantic contract catalog.

For project-scoped file arguments, pass paths relative to `project_root` where the bridge requires them. Runtime queries require `project_root`, but the bridge and Core query boundary resolve the runtime store internally; consumers must not open the store themselves.

## Runtime observability is not runtime control

Supported runtime reads are deliberately narrower than the underlying durable runtime. Their public projections omit provider session identifiers, absolute host paths, lease owners, private handoff result bodies, and other host-private material.

`session.resume.preflight` is read-only. It revalidates durable session version, latest-checkpoint binding, current Project/Framework identity, frozen artifact fingerprints, unresolved gate/handoff blockers, and other deterministic preconditions. `READY` means only that the session satisfies that preflight contract at that moment. `BLOCKED` is a normal query result and its blockers must be preserved exactly.

The shared bridge now exposes narrowly typed runtime commands such as `session.resume` and `session.terminate` when their live operation contracts permit them. Those commands are **not portable Agent Skills capabilities**: their contracts restrict them to `local_app`, require explicit human authorization plus operation-specific preconditions, use CAS/idempotency, emit durable receipts, and do not grant Canon, Settlement, Project-write, Framework-write, or model-execution authority.

Therefore this skill must never translate a successful query or `READY` preflight into permission to resume, terminate, replay, fork, claim, complete, or otherwise mutate runtime state. Hand the user to the owning `local_app` command surface when an authorized runtime command is required.

## Fail closed on commands and deferred operations

If the bridge returns `status: unsupported`, report that state. If discovery reports an operation with `kind: command`, treat it as unavailable from this `agent_package` client unless a future versioned contract explicitly grants this surface that exact command.

Do not bypass the product boundary by:

- opening `.quillframe/runtime.db` directly;
- importing private Control Plane or persistence modules;
- calling a mutating Core primitive as a substitute;
- forging a `local_app` surface identity through an Agent Skills request;
- reconstructing private runtime state from unrelated files or terminal logs;
- treating host capability, preflight readiness, or a command receipt as write authority.

If a preflight returns `BLOCKED`, do not reinterpret it as permission to continue. Resolve the reported blocker through the owning Quillframe runtime contract.

## Consequential story changes

This skill is read-only. It never accepts or settles manuscript text and never changes Canon. If the user asks for a consequential Quillframe write, use the owning Quillframe Core workflow available in the authorized host rather than manufacturing a write path through this skill.

## Final checks

Before presenting a result:

1. confirm the bridge result schema;
2. confirm `authority` is false;
3. invoke only query operations from the portable skill;
4. preserve unsupported/unavailable/`BLOCKED` states exactly;
5. do not expose host absolute paths or private provider session identifiers;
6. retain result fingerprints when provenance matters;
7. do not reinterpret a local-app-only command as an agent-package capability.

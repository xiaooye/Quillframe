---
name: novelforge
description: Inspect a NovelForge fiction project through the portable read-only Studio host bridge. Use for NovelForge project orientation, host capability checks, runtime/session observability, Context Manifest inspection, semantic contract discovery, or when another agent framework needs a safe NovelForge integration without importing private runtime internals.
compatibility: Requires Python 3.11+ and a NovelForge checkout. Set NOVELFORGE_ROOT when the skill is installed outside that checkout.
metadata:
  novelforge-host-bridge: "v1"
  authority: "read-only"
---

# NovelForge portable skill

**Language:** English operating instructions. 简体中文用户可以直接提出中文请求；machine contracts and operation identifiers remain unchanged.

Use this skill as a thin client of NovelForge's public product boundary. Do not treat the skill, the current agent, or host tool availability as Canon, Settlement, Framework-write, or semantic authority.

## Start with discovery

Run:

```bash
python scripts/novelforge_bridge.py describe
```

Use the returned `supported_operations` as the live operation vocabulary. Do not guess operations from private Python modules or persistence tables.

## Invoke a read operation

Create a JSON request with schema `novelforge_studio_host_bridge_request_v1`, then run:

```bash
python scripts/novelforge_bridge.py invoke --request /path/to/request.json
```

Every request must carry `authority: false`. Treat the returned `request_fingerprint` and `result_fingerprint` as provenance for that invocation.

Typical supported uses include:

- inspect Framework health;
- inspect a Project through the safe Project Hub projection;
- inspect locally provable host capabilities;
- inspect durable runtime sessions through side-effect-free Core projections;
- inspect one session's safe run/checkpoint state;
- inspect typed runtime event metadata;
- inspect a handoff's safe state/permission projection;
- retrieve metadata-only Run Receipts by receipt, run, or session identity;
- inspect a project-scoped Context Manifest;
- inspect the semantic contract catalog.

For project-scoped file arguments, pass paths relative to `project_root` where the bridge requires them. Runtime queries require `project_root` but the bridge and Core query boundary resolve the runtime store internally; consumers must not open the store themselves.

## Runtime observability is not runtime control

Supported runtime reads are deliberately narrower than the underlying durable runtime. Their public projections omit provider session identifiers, absolute host paths, lease owners, private handoff result bodies, and other host-private material.

A successful runtime query does **not** grant permission to resume, replay, fork, claim, complete, or mutate a session/handoff. `session.resume` and generic write commands remain deferred until Core exposes typed command envelopes with checkpoint revalidation, before-state preconditions, capability evidence, CAS/idempotency, authority checks, and receipts.

## Fail closed on deferred operations

If the bridge returns `status: unsupported`, report that state. Do not bypass it by:

- opening `.novelforge/runtime.db` directly;
- importing private Control Plane or persistence modules;
- calling a mutating Core primitive as a substitute;
- reconstructing private runtime state from unrelated files or terminal logs;
- treating host capability as write authority.

## Consequential story changes

This skill is read-only. It never accepts or settles manuscript text and never changes Canon. If the user asks for a consequential NovelForge write, use the owning NovelForge Core workflow available in the host rather than manufacturing a write path through this skill.

## Final checks

Before presenting a result:

1. confirm the bridge result schema;
2. confirm `authority` is false;
3. preserve unsupported/unavailable states exactly;
4. do not expose host absolute paths or private provider session identifiers;
5. cite or retain the result fingerprints when provenance matters.
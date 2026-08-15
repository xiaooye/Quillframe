---
name: novelforge
description: Inspect a NovelForge fiction project through the portable read-only Studio host bridge. Use for NovelForge project orientation, host capability checks, Context Manifest inspection, semantic contract discovery, or when another agent framework needs a safe NovelForge integration without importing private runtime internals.
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
- inspect a project-scoped Context Manifest;
- inspect the semantic contract catalog.

For project-scoped file arguments, pass paths relative to `project_root` where the bridge requires them.

## Fail closed on deferred operations

If the bridge returns `status: unsupported`, report that state. Do not bypass it by:

- opening `.novelforge/runtime.db` directly;
- importing private Control Plane or persistence modules;
- calling a mutating Core primitive as a substitute;
- inferring a Run Receipt from event metadata;
- treating host capability as write authority.

Run Receipt retrieval, runtime-store queries, generic invoke/write commands, and resume remain Core-dependent until the bridge advertises them as supported.

## Consequential story changes

This Phase 2B skill is read-only. It never accepts or settles manuscript text and never changes Canon. If the user asks for a consequential NovelForge write, use the owning NovelForge Core workflow available in the host rather than manufacturing a write path through this skill.

## Final checks

Before presenting a result:

1. confirm the bridge result schema;
2. confirm `authority` is false;
3. preserve unsupported/unavailable states exactly;
4. do not expose host absolute paths;
5. cite or retain the result fingerprints when provenance matters.

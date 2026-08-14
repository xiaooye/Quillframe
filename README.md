# CN Webnovel Agent · Novel Production OS

This repository is the dedicated **Generic Novel Production OS / Harness runtime** for long-form commercial fiction production.

## Authority

- Generic OS authority: `xiaooye/cn_webnovel_agent` · `main`
- Project/Canon authority is **not stored here by default**. A book project supplies its own Project Adapter / Novel Bible.
- The current migration source is `xiaooye/frostloom@89a91267c722c9a71ab3174b984063bc08ccc262`.

During migration, the old source remains authoritative for any Generic OS file not yet migrated. Authority cuts over only after the v6.6 migration/eval gate says `cutover_ready=true`.

## Current target

**Novel Production OS v6.6 · Runtime Control Plane**

The runtime model is:

```text
resource/project
→ session/thread
→ run/invocation
→ checkpoint
→ event / handoff / interrupt
→ claim / execute / result
→ resume
```

v6.6 adds a durable control plane around the existing session-native Harness:

- SQLite Session/Event/Handoff store;
- lease/claim semantics for workers;
- idempotent event ingestion;
- exactly-once logical result consumption;
- stdio MCP adapter for local Codex/Claude/agent runtimes;
- CLI for status/checkpoint/handoff/event operations;
- GitHub event ingress/reusable workflow contracts;
- runtime/session provenance without granting Canon authority.

## Bootstrap

Read in order:

1. `SKILL.md`
2. `harness/HARNESS_AGENT.md`
3. mode/runtime-specific modules selected by the Harness
4. target project's own `PROJECT.md` / `START_HERE.md` / Context protocol

Do not treat this README as the full runtime contract.

## Local smoke tests

```bash
python harness/session_runtime/session_runtime.py self-test
python harness/control_plane/control_plane.py self-test
python harness/control_plane/mcp_stdio.py --self-test
```

Normal deterministic tests must not invoke paid/login-bound models.

## Design boundary

The Generic OS may define schemas, workflows, quality mechanisms and runtime infrastructure. It must not absorb project-specific characters, plot outcomes, Canon facts or user-private story state.

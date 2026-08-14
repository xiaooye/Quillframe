# CN Webnovel Agent · Runtime/Harness Repository

This repository is the dedicated **Novel Production OS Agent Runtime / Harness execution authority** for long-form commercial fiction production.

## Authority split

- **Runtime/Harness execution authority:** `xiaooye/cn_webnovel_agent` · `main`
- **Current Story/Surface policy + 《从唐人街到白宫》 Project Adapter/Canon authority:** `xiaooye/frostloom` · `master`
- Runtime state never overrides project/policy authority.

This split is intentional. The agent repo owns execution identity, sessions, control-plane state, runtime routing, semantic transports, local-agent integration and workflow infrastructure. It does **not** duplicate the book's Canon or silently vendor a second copy of Story/Surface policy.

Current migration baseline: `xiaooye/frostloom@89a91267c722c9a71ab3174b984063bc08ccc262`.

## Current release target

**Agent Runtime v6.6 · Runtime Control Plane**

```text
resource/project
→ session/thread
→ run/invocation
→ checkpoint
→ event / handoff / interrupt
→ claim / execute / result
→ exactly-once logical consumption
→ resume
```

v6.6 adds:
- SQLite Session/Event/Handoff persistence;
- lease/claim semantics for workers;
- idempotent event ingestion;
- exactly-once logical result consumption;
- stdio MCP adapter for local Codex/Claude/agent runtimes;
- local CLI/control-plane operations;
- GitHub event ingress + reusable workflow contracts;
- runtime/session provenance without granting Canon authority.

## Bootstrap

For runtime/Harness work read:
1. `SKILL.md`
2. `harness/HARNESS_AGENT.md`
3. `harness/session_runtime/SESSION_RUNTIME.md` when session/resume/external workers are involved
4. `harness/control_plane/CONTROL_PLANE.md` for event/handoff/persistence work
5. target project's live policy/adapter files selected by the Harness

For 《从唐人街到白宫》, project/policy files currently remain under `xiaooye/frostloom:master/new cards/` until a separately gated content-policy migration is performed.

## Local smoke tests

```bash
python harness/session_runtime/session_runtime.py self-test
python harness/control_plane/control_plane.py self-test
python harness/control_plane/mcp_stdio.py --self-test
```

Normal deterministic CI must not invoke paid/login-bound models.

## Design boundary

Execution infrastructure may record operational state and evidence. It may not create Canon, SETTLE a chapter, promote Generic behavior, or turn a connector/webhook event into write authority.

# Claude Code Bootstrap · Novel Production OS

Read `AGENTS.md` first, then `SKILL.md` and `harness/HARNESS_AGENT.md`.

For session/resume/external-worker work also read:
- `harness/session_runtime/SESSION_RUNTIME.md`
- `harness/session_runtime/RUNTIME_ROUTING.md`
- `harness/control_plane/CONTROL_PLANE.md`

This repository owns Generic Novel Production OS behavior only. The active book project's Canon/Novel Bible must come from an explicit project checkout/source and remains a separate authority.

When Claude Code runs the full Harness locally:
- preserve one explicit manager session;
- attach provider session ID as metadata only;
- checkpoint before external waits/writes;
- use a separate invocation/session for mandatory independent semantic review;
- do not use prompt/agent hooks as a substitute for independent semantic judgment;
- never treat chat/session history as Canon.

Recommended local Control Plane command:

```bash
python harness/control_plane/mcp_stdio.py
```

Runtime databases under `.novel-os/` are local operational state and must not be committed.

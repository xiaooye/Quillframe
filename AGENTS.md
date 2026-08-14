# AGENTS.md · Novel Production OS

This file scopes **Codex / Claude Code / local coding agents** working in this repository.

## Authority

This repository owns Generic Novel Production OS runtime behavior. Project-specific Canon lives in the target project's own repository/adapter and must not be copied into Generic OS.

For any Novel Production OS task:

1. read `SKILL.md`;
2. read `harness/HARNESS_AGENT.md`;
3. determine exactly one task mode;
4. for session/external-worker work read `harness/session_runtime/SESSION_RUNTIME.md` and `harness/session_runtime/RUNTIME_ROUTING.md`;
5. for runtime-control-plane work read `harness/control_plane/CONTROL_PLANE.md`;
6. for semantic work read `harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`;
7. for behavior-changing maintenance read `harness/SELF_IMPROVEMENT_PROTOCOL.md`;
8. load the target project's adapter only when the task actually needs project state.

## Runtime discipline

- `resource/project != session != run != checkpoint`.
- Chat/session history is execution context, never Canon authority.
- Use one manager by default; spawn bounded workers only for isolation, tools or genuine independence.
- Mandatory independent semantic judgment must use a separate invocation/session.
- Infrastructure failure may fall back to another eligible runtime; semantic rejection is a valid judgment and must not trigger reviewer-shopping.
- Checkpoint before external waits and consequential writes.
- Resume must revalidate live authority, relevant fingerprints and write preconditions.

## Control-plane discipline

The v6.6 control plane is operational state only. It may persist sessions, events, handoffs, leases, attempts and consumption receipts. It must not create Canon facts or silently promote OS behavior.

Writes and event consumers must be idempotent. A worker claim uses a bounded lease. A result is logically consumed once; duplicate delivery is recorded but must not repeat downstream side effects.

## Git / maintenance

- Work directly on `main` for user-authorized maintenance unless the user explicitly requests a branch/PR.
- Keep changes minimal and scoped.
- Behavior changes require regression/capability coverage and a rollback point.
- Never commit credentials, provider tokens, chat transcripts, private chain-of-thought, or runtime SQLite databases.
- Normal CI must not silently spend API/Codex/Claude usage.

## Project boundary

When running a full Harness task against a book project, accept an explicit project checkout/path or connected-project source. Do not assume this repo contains that book's Canon.

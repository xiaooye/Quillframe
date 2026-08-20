# Quillframe Agent Runtime

Quillframe is a novel-contract kernel, not a general-purpose agent harness. Codex, Claude Code, Cursor, or another declared host runs the generic session, model/tool loop, sandbox, and subagent lifecycle. Quillframe's embedded Agent Runtime remains an optional/reference implementation for Studio, standalone adapters, and deterministic tests; the novel contract and authority boundaries stay in Quillframe.

## AgentJob

`quillframe_agent_job_v1` freezes session/run/task mode/runtime role, exact Model Service, instruction and bounded context, tool grants, required model capabilities, optional exact-model preference, authority snapshot, hard budgets, idempotency and an exact input fingerprint.

Preference can only reorder already-eligible models. It cannot create capability, independence, or authority.

## Embedded/reference loop

```text
AgentJob
→ resolve verified eligible model
→ model request
→ normalized tool call
→ tool registration/grant/capability/authority/schema checks
→ pre-effect checkpoint when consequential
→ tool execution
→ receipt / post-condition / consume-once
→ tool result
→ model continuation
→ AgentResult
```

Read-only tools need no consequential-write checkpoint. Any side-effect tool without a durable execution hook fails closed as `checkpoint_failed` and its handler is not executed. If the tool did execute but post-receipt persistence cannot be confirmed, the result is `side_effect_unconfirmed`; Quillframe must not report ordinary failure or success.

## Tool Runtime

Reference coding tools are `repo.read`, `repo.search`, `repo.write`, and `process.run`.

`repo.write` requires an exact before fingerprint, atomic replacement, post-condition validation, host capability, job grant, authority and idempotency.

Repository tools deny common secret-bearing paths by default. `process.run` never uses a shell, requires a host executable allowlist, and receives a safe environment allowlist rather than inheriting API keys or tokens.

## Session and Control Plane

Agent Runtime does not create a second session database. Consequential execution hooks reuse `harness/session_runtime/session_runtime.py` and `harness/control_plane/control_plane.py`. Pre-effect state is checkpointed through the existing Session Runtime; completion is bound with Control Plane CAS and consume-once receipts.

AgentResult, ToolReceipt and Checkpoint do not grant Project, Canon or Framework authority.

## Semantic Runtime

General Agent Runtime and Semantic Runtime remain separate. They share Model Runtime, protocol codecs, capability evidence, transport, timeout and provenance. Semantic Runtime exclusively owns semantic fingerprints, rubrics, blind bounded context, typed output contracts, independence and semantic-reject semantics.

Coding plan/implementation work is therefore an AgentJob rather than a fiction semantic-review contract.

## Library

After installing the package:

```python
from quillframe import Quillframe, AgentJob

qf = Quillframe(
    secret_store=host_secret_store,
    data_root="~/.quillframe",
    host_capabilities={"filesystem_read"},
)

service = qf.connect(endpoint, access_token)
result = qf.run(job)
```

`secret_store` is a host dependency, not a third Model API setup field exposed to the author.

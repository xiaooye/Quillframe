# Runtime Capabilities · Prove what this invocation can actually do

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>CAPABILITY EVIDENCE</kbd>&nbsp;&nbsp;<kbd>CAPABILITY ≠ AUTHORITY</kbd></p>

NovelForge never treats a runtime or provider name as proof that a capability exists. “ChatGPT”, “Codex”, “Claude”, “MCP”, “GitHub Actions”, or “local model” describes a runtime family—not whether this invocation can search the Web, write a repository, call a model, access user files, or reach a human reviewer.

> **Core invariant ✦** Route from proven current capabilities. Do not infer them from documentation, memory, branding, or model self-assertion.

## 01 · Why capability evidence exists

A production run may need combinations such as:

- filesystem read/write;
- Git/GitHub repository access;
- Web or business search;
- user-file / file-library access;
- provider model inference;
- local agent invocation;
- MCP client/server transport;
- human/peer relay;
- scheduled/external execution;
- artifact rendering or other host tools.

Availability, permission, cost, and user-interaction requirements can change between sessions even when the code and provider stay the same.

Therefore:

```text
runtime identity
→ typed host capability evidence
→ task/gate requirements
→ deterministic resolution
→ eligible routes
```

## 02 · Host capability manifest

`harness/runtime_capabilities.py` normalizes the typed host-capability contract used by the Harness.

A capability record should carry enough metadata to answer:

```yaml
name:
available:
source_or_provenance:
permission_class:
usage_or_cost_class:
requires_user_interaction:
executes_model:
detail:
```

Do not place credentials or secret tokens in the manifest.

The manifest is operational evidence. It is not an access-control system by itself and never grants Canon/Framework-write authority.

## 03 · Proof classes

### Locally provable

A local runtime may directly prove facts such as:

- a path exists and is readable/writable;
- `git`, `gh`, `codex`, or `claude` exists on PATH;
- a local process can be spawned;
- a configured local endpoint responds.

PATH presence proves executable presence—not login state, account entitlements, model availability, or remote permission.

### Host-declared / connector-backed

The host/integration layer may declare current capabilities such as:

- GitHub connector access;
- Web search;
- user files / file library;
- provider inference;
- MCP connection;
- calendar/mail/drive connectors;
- peer/human relay.

A declaration should have provenance sufficient for the runtime to explain why it considered the capability available.

### Never inferred

Do not infer availability because:

- another conversation had the tool;
- a provider usually supports it;
- documentation says the product can do it;
- a network primitive exists;
- credentials probably exist somewhere;
- a model says “I can access GitHub/Web/files”;
- a prior checkpoint recorded that the capability once existed.

Missing evidence means unavailable for routing until proven again.

## 04 · Capability requirements

A task/gate derives the smallest set of capabilities it truly needs.

Examples:

- repository documentation write → repo read + exact write path/permission;
- independent local semantic review → model execution + isolated invocation + bounded packet transport;
- peer-chat review → relay ability + user interaction + separate conversation identity;
- corpus discovery → specific search/source capability;
- Canon settlement → project write capability **plus separate Canon authority and preconditions**.

Requirements should describe abilities, not hard-code preferred brands.

## 05 · Resolution constraints

After availability, apply constraints such as:

- required permission scope;
- user interaction allowed/disallowed;
- model execution allowed/disallowed;
- usage/cost restrictions;
- independence/isolation requirements;
- current connection/auth state;
- data-locality/security constraints;
- resumability requirements.

A capability may be technically available but ineligible for this particular job.

## 06 · Capability ≠ authority

Capability answers:

> **Can this runtime technically attempt the operation?**

Authority answers:

> **Is this operation allowed to change this durable domain?**

Examples:

- filesystem write capability does not grant Canon write;
- GitHub write does not grant Framework-promotion authority;
- a model can produce a semantic judgment but cannot accept its own draft into Canon;
- Web search can discover a source but cannot decide rights to store full text;
- memory-edit capability cannot mutate protected Accepted/locked Canon.

Both capability and authority must be satisfied where a consequential action requires both.

## 07 · Model-execution transparency

A capability record should distinguish model execution from deterministic infrastructure.

Normal CI should be able to run deterministic contract tests without silently invoking paid/login-bound models.

A workflow that requires semantic judgment should surface the need for an eligible model/human path rather than substituting fake heuristic output.

## 08 · Resume revalidation

Persisting a session does not freeze capability truth.

On resume, re-resolve the capabilities required by **pending external/tool work** because:

- connectors may disconnect;
- tokens/permissions may change;
- local executables may disappear;
- usage/cost policy may change;
- user interaction may no longer be possible;
- a service may be unavailable.

Completed work with valid receipts does not need to be re-executed merely because routing options changed.

## 09 · Failure semantics

If no route satisfies the required capabilities/constraints:

- do not fabricate tool output;
- do not silently weaken independence;
- do not infer credentials;
- do not reinterpret semantic failure as infrastructure failure.

Return the truthful workflow state: e.g. `awaiting_user`, `awaiting_external`, `semantic_pending`, `unsupported`, or another explicit blocked state appropriate to the mode.

## 10 · Invariants

1. Runtime/provider name is not capability proof.
2. Missing capability evidence means unavailable for routing.
3. PATH/network presence is narrower than remote authorization.
4. Capability and authority are independent checks.
5. Resume revalidates pending capabilities.
6. Normal deterministic CI does not silently spend model usage.
7. Capability policy may reorder routes but cannot weaken mandatory semantic/authority gates.

## 11 · Related contracts

- [Runtime Routing](RUNTIME_ROUTING.en.md) — selecting among eligible capabilities.
- [Session Runtime](SESSION_RUNTIME.en.md) — why capability truth is revalidated on resume.
- [Harness Agent](../HARNESS_AGENT.en.md) — capability broker in the manager lifecycle.
- [`runtime_capabilities.py`](../runtime_capabilities.py) — deterministic capability normalization/resolution.

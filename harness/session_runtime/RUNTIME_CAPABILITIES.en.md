# Runtime Capabilities · NovelForge 7.1

## Why this exists

A runtime name is not proof of a capability. “ChatGPT”, “Codex”, “Claude”, “GitHub Actions” or “MCP” does not by itself prove that Web search, filesystem write, a provider model, a connected repository, or a human relay is available in the current invocation.

NovelForge therefore separates **runtime identity** from **capability evidence**.

```text
runtime identity
→ typed capability manifest
→ task requirements
→ deterministic resolution
→ eligible route
```

## Host capability manifest

`harness/runtime_capabilities.py` normalizes a `novelforge_host_capabilities_v1` manifest.

Each capability records:
- `available`;
- provenance/source of that claim;
- permission class;
- usage/cost class;
- whether user interaction is required;
- whether model inference is executed;
- optional non-secret detail.

Credentials are never embedded in the manifest.

## Proof levels

### Locally provable

The reference local probe may prove facts such as a readable filesystem or whether `git`, `gh`, `codex`, or `claude` executables exist on PATH.

A network socket primitive does **not** prove authorization to any remote service.

### Host declared

Chat/Web/GitHub/MCP/file-library/provider capabilities may be declared by the host/integration layer. Missing declarations are treated as unavailable.

### Never inferred

NovelForge must not infer a capability merely because:
- the same provider supported it in another session;
- a tool appears in documentation;
- a credential probably exists;
- an earlier run had the capability;
- a model says it can perform the action.

## Resolution constraints

A task can require one or more capabilities. Resolution additionally applies:
- user-interaction constraints;
- model-execution constraints;
- usage/cost exclusions;
- later Harness permission/independence rules.

A missing or rejected capability produces a truthful unresolved/awaiting state. It must not be replaced with fabricated tool output.

## Capability vs authority

Capability says **what can technically be attempted**. Authority says **what may change durable state**.

A host can have filesystem write capability while lacking Canon-write authority. A provider can return a semantic judgment while lacking permission to promote Framework behavior. A Web search tool can discover a Corpus source while lacking rights to store its full text.

## Resume

A persisted session does not persist capability truth forever. On resume, re-resolve the capabilities required for pending external/tool work because connections, permissions and user usage constraints may have changed.

## CI

Normal CI uses local probe only for locally provable facts and asserts that Web/GitHub search is unavailable unless explicitly declared. This prevents CI from becoming an accidental source of imaginary connector capability.

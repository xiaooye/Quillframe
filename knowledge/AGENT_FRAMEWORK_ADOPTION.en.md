# Agent Framework Adoption · Borrow runtime mechanisms, keep fiction semantics ours

Quillframe is not a thin wrapper around one agent SDK. It studies mature agent/runtime systems for **execution mechanisms**, then adopts, adapts, or rejects them according to long-form fiction requirements.

> **Scope ✦** This is an implementation-influence document, not a product-comparison page. General agent frameworks solve different problems from Quillframe and should not be presented as its primary customer alternatives.

**Research snapshot:** 2026-08-14. Upstream frameworks evolve quickly; verify primary sources before turning an observation here into a dependency or architectural change.

---

## 01 · Adoption rule

A mechanism is worth adopting when it improves one or more of:

- resumability;
- bounded delegation;
- permission / capability clarity;
- state isolation;
- typed handoffs and outputs;
- observability;
- human/external waits;
- reproducible project engineering.

A mechanism is adapted or rejected when it would blur:

- runtime memory vs. story authority;
- worker capability vs. write permission;
- shared conversation state vs. independent judgment;
- long-term memory vs. Canon;
- orchestration convenience vs. sparse context discipline.

Quillframe owns fiction-specific semantics: Story, Character, Relationship, Canon, Reader Engagement, Surface Fundamentals, quality failure routing, settlement, and evidence-backed learning.

---

## 02 · OpenAI Agents SDK

**Current primary-source signals.** The SDK emphasizes a deliberately small primitive set: agents, agents-as-tools / handoffs, guardrails, sessions, tracing, MCP integration, human-in-the-loop support, and isolated sandbox agents. Handoffs can forward prior conversation history but expose input filters; sessions provide persistent working context; the runner can resume interrupted run state.

### Adopt

- small runtime primitive set rather than an explosion of fictional “agent roles”;
- manager-style specialists / agents-as-tools for bounded work;
- typed handoff inputs and structured results;
- input/output guardrails around model/tool boundaries;
- resumable run state and persistent sessions as runtime facilities;
- first-class tracing / observability concepts;
- MCP interoperability;
- isolated workspace/sandbox execution where a specialist needs real files or tools.

### Adapt

- Quillframe passes **task-bounded context**, not the whole prior conversation by default;
- provider/session memory remains execution state, never project Canon;
- observability stores metadata and fingerprints by default rather than copying manuscript text into a second tracing authority;
- mandatory independent semantic gates require separate invocation/session identity and artifact binding, not merely a new agent object inside the same run.

### Reject

- treating provider conversation state as story truth;
- assuming every task needs an agent handoff rather than a direct model contract or deterministic step;
- coupling Quillframe's fiction semantics to one model provider.

Primary sources:
- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/handoffs/
- https://openai.github.io/openai-agents-python/sessions/
- https://openai.github.io/openai-agents-python/running_agents/

---

## 03 · LangGraph

**Current primary-source signals.** LangGraph provides checkpointed graph state organized into threads, durable interrupts, replay/time-travel, fault recovery, short-term thread memory, long-term stores, and stateful or per-invocation subgraphs. Its documentation explicitly recommends per-invocation persistence for many subagent-as-tool patterns where isolation matters.

### Adopt

- durable checkpointing before waits and consequential transitions;
- explicit thread/session identity;
- interrupt/resume as a normal state rather than an exception in product semantics;
- recovery from the last successful durable state;
- separation of thread-scoped execution memory from cross-thread stores;
- per-invocation isolation for specialists that do not need shared long-lived state;
- replay/fork ideas for debugging and scenario exploration.

### Adapt

Quillframe separates more authority domains than a generic agent graph typically needs:

```text
runtime/session state
learning/evidence state
project authority / Canon state
```

Scenario forks, run receipts, checkpoints, memory overlays, and graph state remain non-authoritative unless an explicit project transaction says otherwise.

### Reject

- putting the whole novel's authority inside generic graph state;
- resuming a stale checkpoint without revalidating project authority, artifact fingerprints and required capabilities;
- allowing graph convenience to bypass character/perspective visibility boundaries.

Primary sources:
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/concepts/memory
- https://docs.langchain.com/oss/python/langgraph/use-subgraphs

---

## 04 · Google ADK / agents-cli

**Current primary-source signals.** ADK exposes explicit session/event/state services. Google's agents-cli now treats agent development as a lifecycle: scaffold, build, evaluate, deploy, publish and observe, with coding-agent skills and structured eval datasets.

### Adopt

- standard project scaffolding and lifecycle commands;
- sessions/events as inspectable runtime concepts;
- tests/evals as normal project artifacts rather than optional afterthoughts;
- coding-agent skills / repository guidance as explicit project infrastructure;
- scaffold upgrade workflows and reproducible project metadata;
- trace/eval comparison as part of change validation.

### Adapt

- Quillframe Project SDK scaffolds **fiction projects**, including authority classes, Canon/state, plans, manuscripts, research, corpus and regression evidence;
- Framework upgrades are exact-lock dependency migrations, not implicit toolchain upgrades;
- deployment/observability concepts are useful, but fiction production remains provider- and hosting-neutral.

### Reject

- binding the fiction project model to one cloud deployment target;
- treating generated eval scenarios or LLM grades as authority without Quillframe's blindness/evidence rules.

Primary sources:
- https://google.github.io/adk-docs/
- https://google.github.io/agents-cli/guide/quickstart-tutorial/
- https://google.github.io/agents-cli/guide/evaluation/
- https://google.github.io/agents-cli/reference/skills/

---

## 05 · Microsoft AutoGen

**Current primary-source signals.** AgentChat supports single agents, multiple team patterns, human-in-the-loop interaction, and explicit save/load state for agents and teams. Its current team documentation itself advises starting with a single agent for simpler work and moving to teams only when collaboration or diverse expertise is actually needed.

### Adopt

- explicit save/load state;
- observable agent/team state;
- human feedback as a first-class workflow concern;
- teams only when distinct capabilities or collaboration justify the extra scaffolding;
- termination/resume semantics rather than endless conversation loops.

### Adapt

- Quillframe defaults to **one manager + bounded specialists**;
- independent reviewers receive isolated packets instead of shared group-chat history;
- worker/team state is runtime evidence, not Canon;
- saved state must still be rebound to current project authority on resume.

### Reject

- round-robin discussion as a default quality strategy;
- shared group-chat context for mandatory blind/independent review;
- multiple stateful agents concurrently mutating the same authoritative story state.

Primary sources:
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/index.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html

---

## 06 · Claude Code

**Current primary-source signals.** Claude Code supports repository/project instruction memory, resumable sessions by ID, programmatic print mode, permission modes, MCP configuration, and project-scoped operating guidance.

### Adopt

- repository-scoped agent instructions;
- scoped/nested guidance for subtrees;
- resumable local sessions;
- CLI execution as a real bounded runtime path;
- MCP interoperability;
- deterministic hooks/telemetry for operational lifecycle evidence.

### Adapt

- `CLAUDE.md` is bootstrap/instruction state, not Canon authority;
- resumed sessions must re-check the current project/framework state;
- hooks may record operational facts but cannot silently satisfy literary semantic gates.

### Reject

- persisting accidental chat interpretation as project truth;
- using prompt-only self-review inside the same session to fake mandatory independence.

Primary sources:
- https://docs.anthropic.com/en/docs/claude-code/cli-usage
- https://docs.anthropic.com/en/docs/claude-code/memory
- https://docs.anthropic.com/en/docs/mcp

---

## 07 · Model Context Protocol

**Current primary-source signals.** The 2025-06-18 MCP specification defines JSON-RPC-based stdio and Streamable HTTP transports. The Streamable HTTP specification includes Origin validation and authentication guidance; authorization is a transport concern, not an application-domain authority model.

### Adopt

- standard JSON-RPC lifecycle and capability negotiation;
- stdio for local tool/runtime integration;
- Streamable HTTP for eligible remote services;
- strict stdout discipline for stdio;
- standard tool schemas rather than provider-specific connector protocols;
- Origin/auth protections for remote HTTP transports;
- session/resumption mechanics where the transport supports them.

### Adapt

- Quillframe exposes operational/project-safe capabilities, not raw Canon-write power by default;
- MCP authorization proves transport access, **not story authority**;
- high-authority writes remain explicit Harness / Settlement transactions with project preconditions.

### Reject

- webhook/MCP arrival as implicit permission;
- inventing incompatible provider-specific resume/idempotency models where MCP already fits.

Primary sources:
- https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization

---

## 08 · Software-engineering repository discipline

Quillframe also borrows from ordinary software engineering rather than agent frameworks:

```text
spec → plan → tasks → implementation → verification → acceptance
```

### Adopt

- exact target paths and objects;
- preconditions and before-state;
- phase checkpoints;
- behavior/authority compatibility checks;
- deterministic tests and reproducible builds;
- dependency/migration planning;
- rollback and post-condition verification.

### Adapt

- ordinary prose micro-edits do not need fake feature tickets;
- structural fiction changes, schema migrations, Framework upgrades and Canon migrations receive stronger engineering ceremony;
- chapter production uses plans, Scene Cards, semantic contracts and quality evidence rather than pretending paragraphs are software tasks.

### Reject

- process for process's sake;
- pretending deterministic unit tests can replace artistic/semantic judgment.

---

## 09 · Quillframe synthesis

```text
one manager
→ smallest required semantic / deterministic mechanism
→ bounded specialist only when capability or isolation requires it
→ durable session / checkpoint / control-plane state
→ sparse perspective-safe context
→ typed fingerprint-bound evidence
→ explicit repair owner
→ user-visible gate
→ separate acceptance + settlement authority
```

Governing heuristics:

1. Start with one manager; add workers only for capability, isolation, independence, or real parallelism.
2. Separate runtime memory, learning evidence, derived memory and Canon authority.
3. Pass bounded, perspective-safe context instead of whole histories.
4. Make waits and resume durable, explicit and revalidated.
5. Treat connectors and transports as capabilities, never authorities.
6. Keep semantic intelligence in model-readable contracts and deterministic invariants in code.
7. Preserve run observability through metadata/fingerprints without cloning private reasoning or manuscripts into a second authority store.
8. Treat projects as reproducible software artifacts with manifests, tests, builds, migrations and exact locks.
9. Learn from evidence and counterexamples, not repeated model self-assertion.

---

## 10 · Maintenance rule

Upstream framework research is evidence, not an automatic dependency update.

When an upstream mechanism changes:

```text
verify primary source
→ record adopt / adapt / reject hypothesis
→ identify affected Quillframe contract
→ test capability + regression impact
→ change implementation only when justified
→ update this page with date/source
```

**Quillframe should become better at runtime engineering without becoming a generic agent framework with a fiction prompt attached.**

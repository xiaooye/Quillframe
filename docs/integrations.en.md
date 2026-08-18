# Runtime & Integrations

Quillframe is provider-neutral because runtime identity, capability, and authority are separate concepts. A provider name never proves that a capability exists, and a capability never grants story or write authority by itself.

<img src="assets/concepts/session-run-checkpoint.en.svg" alt="Runtime identity model separating project/resource, session/thread, run/invocation, and checkpoint" width="100%" />

## Identity

`project/resource` identifies the work. `session/thread` is the durable conversational or execution relationship. `run/invocation` is one bounded execution attempt. `checkpoint` is a recoverable snapshot of exact execution state.

Provider session history is not Canon and is not a substitute for Project bootstrap.

## Local coding-agent hosts

Claude Code and Codex can host a local Quillframe session, but neither host owns Quillframe workflow semantics. Both adapters normalize their lifecycle events into the same deterministic bootstrap core.

For a consumer Project, the required path is:

`Project discovery → exact lock/attestation verification → quillframe_agent_session_v1 → exactly one task_mode → one active manager run → sparse Context execution`

The host injects a `QF_SESSION_ID`. Exact authority verification alone is not enough to unlock consequential work: the model/user must semantically select exactly one Quillframe mode and run the exact `quillframe host-run begin ...` command supplied in bootstrap context. Host state remains explicitly `blocked`, `awaiting_task_mode`, or `running`.

Before `running`, edit/write/shell tools fail closed except for the narrowly parsed Quillframe bootstrap command. Codex `apply_patch` is treated as an edit. A changed Project lock/attestation or changed pinned Framework identity invalidates the running authority binding rather than silently refreshing it.

Claude Code loads its generated `CLAUDE.md` and project hooks. Codex reads the generated direct `AGENTS.md`; project-local `.codex/hooks.json` additionally requires the user's project/hook trust. If Codex starts without injected `QF_SESSION_ID`, review/trust the Quillframe hooks with `/hooks` and restart before consequential work. Quillframe does not bypass that host security boundary.

Existing consumer Projects can explicitly repair generated host files with `quillframe host-install .`. Host repair is not a Framework repin and does not mutate Canon or other story state; unknown user-authored host instructions are preserved and reported for manual merge.

## Capabilities

The current host manifest is the evidence for available tools, models, network, filesystem, GitHub, peer chat, local agents, or human review. Undeclared capability is unavailable. Credentials and authority tokens stay outside ordinary semantic context.

## Resume

Resume revalidates the current framework/project compatibility, latest checkpoint, referenced artifact fingerprints, live Project authority, pending approval/write intent, required capabilities, and consume-once state. A different framework revision is a dependency migration question, not ordinary resume.

## Independent semantic execution

<img src="assets/concepts/independent-semantic-review.en.svg" alt="Manager and reviewer use distinct invocation markers with a fingerprint-bound artifact between them" width="100%" />

Eligible independent paths can include a separate local agent invocation, provider call, service/MCP worker, GitHub job, peer chat, local model, or human—when current capability evidence supports it. Transport failure can fall back to another eligible transport for the same fingerprint. A valid semantic rejection cannot.

## Control plane

The Control Plane stores durable event/handoff/result lifecycle and metadata-only receipts. Local host manager sessions use the existing typed session contract rather than a host-specific parallel schema. The Control Plane can prove that execution state or a result was dispatched, returned, validated, and consumed; it cannot turn that state or result into Canon or editorial acceptance.

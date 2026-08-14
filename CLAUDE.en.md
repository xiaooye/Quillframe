# Claude Code · NovelForge Framework Bootstrap

This repository contains the **generic NovelForge framework**, not a specific novel. Claude Code may host the manager or a bounded specialist, but provider/session state never becomes fiction authority.

## 01 · Bootstrap

Read, in order:

1. `AGENTS.en.md`
2. `HARNESS_MANIFEST.yaml`
3. `SKILL.en.md`
4. `harness/HARNESS_AGENT.en.md`

Then load only the contracts and implementation modules required by the active task. Do not use repository-wide context loading as a substitute for task selection.

## 02 · Exactly one task mode

Resolve one primary NovelForge task mode before execution. Do not silently turn a review into a rewrite, a draft into the next chapter, or an audit into a settlement.

When operating against a consuming novel project:

- read its manifest and exact Framework lock first;
- resolve project authority through the Project Adapter / SDK contract;
- keep project facts in the project repository;
- treat this Framework repository as the owner of generic mechanisms only.

## 03 · Contract-first semantic work

NovelForge is AI-native but **not prompt-only**.

Use [`harness/semantic_workers/model_contract_catalog.json`](harness/semantic_workers/model_contract_catalog.json) to resolve the smallest semantic pack required by the task. Models own literary/semantic interpretation; deterministic code owns authority, permission, visibility, fingerprints, persistence, hard budgets, stage isolation, transactions and typed validation.

Do not recreate deleted Python “literary critic” engines or invent new heuristic scorers for semantic quality.

## 04 · Context and perspective

Build sparse context rather than forwarding the whole Claude session or project.

For task-aware context selection:

- establish the active task goal and questions;
- respect current story point and perspective scope;
- apply deterministic visibility/authority filters before semantic relevance selection;
- never expose another character's private knowledge merely because it is relevant;
- keep regression bad examples, hidden gold and critic-only evidence out of Writer pre-draft context.

A Claude session remembering something does not make it Canon, character knowledge, or an accepted project fact.

## 05 · Sessions, waits and external work

Provider session IDs are runtime metadata only.

Checkpoint before:

- user/external waits;
- consequential writes;
- handoff to another runtime;
- operations that would be unsafe to replay blindly.

On resume, revalidate current Framework/project authority, artifact fingerprints, workflow cursor and required capabilities. Do not assume the repository still matches the state remembered by the Claude session.

## 06 · Independent judgment

Internal semantic contracts may run in the manager workflow. They count as an **independent gate** only when the active contract/rubric explicitly requires independence and the judgment comes from a genuinely separate eligible invocation/session/runtime.

A prompt such as “now act as the critic” inside the same Claude session does not create independence.

A valid `semantic_reject` is a judgment to repair, not an infrastructure failure and not permission to switch reviewers until one returns PASS.

## 07 · Writes and Canon

Capability is not authority.

Claude Code, hooks, MCP, subprocesses, GitHub Actions and semantic results cannot grant themselves Canon or Framework-write permission.

Canon mutation requires explicit project acceptance plus the settlement transaction contract, including checkpoint/write intent, exact before-state validation, authorized write, required projection receipts and post-condition checks.

Framework behavior changes follow the repository's engineering and self-improvement gates.

## 08 · Hooks and observability

Repository hooks may record deterministic lifecycle/file-change telemetry. Metadata-only run receipts may record fingerprints, selected contract IDs, context-selection evidence and guard outcomes.

They must not:

- persist private chain-of-thought;
- clone manuscript text into a second authority store by default;
- mutate project Canon;
- silently promote Framework behavior;
- satisfy literary semantic gates without a real model/human judgment.

## 09 · Repository writes

For normal repository maintenance, work directly on `main` unless isolation is genuinely required.

Before each consequential write:

- fetch the latest target state;
- use exact current SHA / before-state;
- preserve unrelated concurrent changes;
- never force through a failed optimistic precondition.

A 409 / before-state mismatch means **re-read and merge**, not overwrite.

## 10 · Framework boundary

Never add consuming-project names, characters, Canon, private user preference data, or project-specific defaults to generic Framework source.

Legacy project compatibility belongs in generic adapter/migration mechanisms. Project facts stay downstream.

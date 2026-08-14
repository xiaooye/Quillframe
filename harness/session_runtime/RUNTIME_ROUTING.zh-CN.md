# Runtime Routing · v7 中文版

## 原则

Runtime 根据 capability、independence、permission、availability、resumability、用户 usage/cost 偏好和 operational friction 选择，而不是 hard-code 某一家 provider。

## Runtime Classes

| Runtime | Manager | Specialist | Independent semantic review |
|---|---:|---:|---:|
| 当前 chat | yes | bounded | 禁止 self-review |
| 独立 peer chat | no | no | yes |
| local Codex CLI | yes | yes | yes，separate invocation |
| local Claude Code | yes | yes | yes，separate invocation |
| provider API | optional | yes | yes |
| GitHub/service job | no | yes | isolated worker 时 yes |
| remote MCP worker | yes | yes | isolated session 时 yes |
| local model | optional | yes | isolated invocation 时 yes |
| human reviewer | no | no | yes |

## Selection

```text
classify task/gate
→ capability filter
→ permission/auth/connection filter
→ independence filter
→ user usage/cost filter
→ 按 explicit preference / automation / isolation / friction / cost 排序
```

Infrastructure failure 可以 checkpoint 后 fallback 到下一个 eligible transport。有效 semantic reject 不是 transport failure。

## Chat Manager Path

当前 chat 即使不能 spawn subprocess，也仍可作为 manager。在宣告 `semantic_pending` 前必须 probe 所有 eligible connected path。若 separate peer chat 可行但需要用户 relay，状态应是 `awaiting_user`。

## Local Agent Path

已认证 Codex/Claude CLI 可以完整运行 Harness，NovelForge 不要求额外 provider API key。Mandatory review 使用 separate invocation/session + blind bounded job。

## Long-running Work

需要 session ID、durable checkpoint、typed pending handoff/event、queued worker lease、resume revalidation 与 consume-once result handling。

## Changed Artifact

Artifact/rubric/output contract material change → new semantic fingerprint，通常 fresh reviewer session。Semantic payload 不变时，infrastructure retry 可以保留同一 fingerprint。

## Cost Preference

Cost preference 可以重新排序 transport，但不能削弱 independence、fingerprint binding、context isolation、authority 或 mandatory quality gate。

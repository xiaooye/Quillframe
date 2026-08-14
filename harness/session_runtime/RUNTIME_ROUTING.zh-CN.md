# Runtime Routing · NovelForge 7.1 中文版

## 原则

Runtime 根据**已经证明/声明的 capability evidence**、independence、permission、availability、resumability、用户 usage/cost 偏好和 operational friction 选择，而不是按 provider 名字或历史经验 hard-code。

涉及 tool/external work 前，必须通过 `../runtime_capabilities.py` + `RUNTIME_CAPABILITIES.zh-CN.md` 建立/读取 typed host capability manifest。

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

上表只描述 runtime class **可能**具备什么角色，不证明当前 invocation 真的可用。当前任务仍必须证明/声明所需 capability。

## Selection

```text
classify task/gate
→ derive required capabilities
→ resolve typed host capability manifest
→ permission/auth/connection filter
→ independence filter
→ user interaction/model execution/usage filter
→ 按 explicit preference / automation / isolation / friction / cost 排序
```

未声明 capability = unavailable。存在 network primitive ≠ 已授权 Web/GitHub/provider access。

Infrastructure failure 可以 checkpoint 后重新 resolve capability，再 fallback 到下一个 eligible transport。有效 semantic reject 不是 transport failure。

## Chat Manager Path

当前 chat 即使不能 spawn subprocess，也仍可作为 manager。在宣告 `semantic_pending` 前，必须针对**当前实际 connected/declared capability**重新 resolve 所有 eligible path。Separate peer chat 可行但需要用户 relay 时，状态是 `awaiting_user`。

Earlier chat/session 曾有 capability，不会自动继承到当前 invocation。

## Local Agent Path

已认证 Codex/Claude CLI 可以完整运行 Harness，NovelForge 不要求额外 provider API key。PATH 上存在 executable 只证明程序存在；实际 auth/model availability 仍由 local runtime 在需要时 resolve。Mandatory review 使用 separate invocation/session + blind bounded job。

## Corpus / Research Discovery

Corpus Scout 会明确发出 `web_search`、`github_search`、`user_files`、`file_library`、`mcp_client` 等 capability requirement。`corpus/discovery_runtime.py` 只 dispatch 当前 host manifest 已满足的 channel。

Discovery result provenance 与 rights/storage validation 仍是独立 gate，不能和 capability 混为一谈。

## Long-running Work

需要 session ID、durable checkpoint、typed pending handoff/event、queued worker lease、resume revalidation 与 consume-once result handling。

Resume 时，pending tool/external work 必须重新 resolve capability，因为 connection、permission、cost constraint 可以独立于 session persistence 发生变化。

## Changed Artifact

Artifact/rubric/output contract material change → new semantic fingerprint，通常 fresh reviewer session。Semantic payload 不变时，infrastructure retry 可以保留同一 fingerprint。

## Cost Preference

Cost preference 可以重新排序 transport，但不能削弱 capability evidence、independence、fingerprint binding、context isolation、authority 或 mandatory quality gate。

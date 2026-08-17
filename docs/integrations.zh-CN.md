# 运行时与集成

Quillframe 能保持 provider-neutral，是因为 runtime identity、capability、authority 是三个不同概念。Provider 名字不证明 capability 存在；capability 本身也不授予 story/write authority。

<img src="assets/concepts/session-run-checkpoint.zh-CN.svg" alt="Runtime identity model 分开 project/resource、session/thread、run/invocation 与 checkpoint" width="100%" />

## Identity

`project/resource` 标识工作对象；`session/thread` 是 durable conversational/execution relationship；`run/invocation` 是一次 bounded execution attempt；`checkpoint` 保存 exact execution state 以便恢复。

Provider session history 不是 Canon，也不能替代 Project bootstrap。

## Capabilities

Current host manifest 才是 tool、model、network、filesystem、GitHub、peer chat、local agent 或 human review 是否可用的 evidence。未声明 capability 视为 unavailable；credential 与 authority token 不进入普通 semantic context。

## Resume

Resume 必须重核 current Framework/Project compatibility、latest checkpoint、artifact fingerprint、live Project authority、pending approval/write intent、required capability 与 consume-once state。Framework revision 变化属于 dependency migration 问题，不是 ordinary resume。

## Independent Semantic Execution

<img src="assets/concepts/independent-semantic-review.zh-CN.svg" alt="Manager 与 reviewer 使用不同 invocation marker，中间只传 fingerprint-bound artifact" width="100%" />

Eligible independent path 可以是 separate local agent invocation、provider call、service/MCP worker、GitHub job、peer chat、local model 或 human，只要 current capability evidence 支持。Transport failure 可以在同 fingerprint 下 fallback；有效 semantic rejection 不可以。

## Control Plane

Control Plane 保存 durable event/handoff/result lifecycle 与 metadata-only receipt，可以证明 result 的 dispatch、return、validate、consume，却不能把这个 result 变成 Canon 或 editorial acceptance。

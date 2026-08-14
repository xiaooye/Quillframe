# Semantic Worker Protocol · v7 中文版

## 目的

Semantic work 通过严格边界执行：

```text
frozen subject
→ bounded blind job
→ semantic fingerprint
→ independent session/invocation
→ typed result
→ deterministic binding validation
→ named gate consume once
```

Router 与 Control Plane 永远不替 worker 做文学判断。

## Job Identity

Semantic job 包含：
- `job_id / kind / subject_id / created_at`；
- `input_fingerprint`；
- bounded `input`；
- `rubric`；
- `output_contract`；
- least-privilege `permissions`；
- `provenance`；
- optional execution lineage。

## Fingerprint

Semantic fingerprint 只代表“语义问题本身”：

`kind + subject_id + input + rubric + output_contract`

Transport/session/attempt lineage 不进入 fingerprint。相同 frozen question 可以换 infrastructure retry，而不假装正文变了。

Subject input/rubric/output contract material change → new fingerprint，并通常使用 fresh reviewer session。

## Blindness

Independent reviewer packet 不得包含：
- expected verdict / gold label；
- prior reviewer verdict；
- writer private reasoning；
- 无关 project context；
- regression answer key。

Reviewer 只拿判断当前 rubric 所必需的 evidence。

## Authority

Semantic worker 没有隐式权限：
- 写 Canon；
- settle project state；
- promote framework behavior；
- 覆盖 durable user taste；
- grant permissions。

它返回的只是 bounded judgment/evidence。

## Result

Typed result 必须重复 exact job identity/fingerprint，并声明 truthful worker provenance。结果包含 status、judgment、evidence/codes/confidence、允许时的 proposals、errors 与 optional execution lineage。

不请求、不持久化 private chain-of-thought。

## Independence

Valid independent review 必须来自真正不同的 invocation/session。同一个 manager 即使内部换 system role label，也不能冒充独立 reviewer。

Eligible transport 可以是 local agent subprocess、provider API、MCP worker、GitHub/service job、独立 peer chat、local model 或 human。

## Retry Semantics

- infrastructure failure + fingerprint 不变 → 可安全 retry/fallback；
- invalid/mismatched result → 丢弃结果，修 transport 或重跑；
- valid semantic reject/fail → 回 owning story/character/surface/reader/continuity repair layer；
- 禁止换 reviewer 一直审到有人 PASS；
- duplicate delivery 由 consume-once 处理。

## Scope

Semantic review 与 deterministic checks 互补。Identity、fingerprint、permission、schema、lifecycle transition、算术、idempotency 等能 deterministic 的部分继续由代码负责。

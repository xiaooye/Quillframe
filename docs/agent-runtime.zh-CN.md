# Quillframe Agent Runtime

Quillframe 是小说契约内核，不是通用 Agent harness。Codex、Claude Code、Cursor 或其他已声明的宿主运行通用 session、model/tool 循环、sandbox 与 subagent 生命周期。Quillframe 内置的 Agent Runtime 仍保留为 Studio、standalone adapter 与确定性测试使用的 optional/reference implementation；小说契约与 authority 边界仍由 Quillframe 负责。

## AgentJob

一个 `quillframe_agent_job_v1` 冻结：

- session / run / task mode / runtime role；
- exact Model Service；
- instruction + bounded context；
- tool grants；
- required model capabilities；
- optional exact-model preference；
- authority snapshot；
- hard budgets；
- idempotency key；
- exact input fingerprint。

Preference 只能重排 eligible model；不能制造 capability、independence 或 authority。

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

Read-only tools 可以不经过 consequential-write checkpoint。任何 side-effect tool 没有 durable execution hook 时 fail closed 为 `checkpoint_failed`，handler 不执行。Tool 已执行但 post-receipt persistence 无法确认时返回 `side_effect_unconfirmed`，不得谎称普通失败或成功。

这个循环只是宿主执行的一种实现。Native host 可以自行运行循环；Quillframe 仍会校验受限小说工作、exact artifact、权限、checkpoint、receipt 以及 release / Settlement 边界。Model API 只是 inference capability，不拥有故事或 Settlement authority。

## Tool Runtime

当前 reference coding tools：

- `repo.read`
- `repo.search`
- `repo.write`
- `process.run`

`repo.write` 需要 exact before fingerprint、atomic replace、post-condition、host capability、job grant、authority 与 idempotency。

Repository tools 默认屏蔽 `.env`、private keys、`.git` 等 secret-bearing path。`process.run` 不经过 shell，只允许 host allowlist executable，并使用安全环境变量 allowlist，不继承 API key/token 环境。

## Session / Control Plane

Agent Runtime 不建立第二套 session database。Consequential tool hook 复用：

- `harness/session_runtime/session_runtime.py`
- `harness/control_plane/control_plane.py`

Pre-effect checkpoint 使用现有 Session Runtime；结果用 Control Plane CAS + consume-once receipt 绑定。

AgentResult、ToolReceipt、Checkpoint 都不授予 Project/Canon/Framework authority。

## Semantic Runtime

General Agent Runtime 与 Semantic Runtime 分开。

共享：Model Runtime、protocol、capability evidence、transport、timeout、provenance。

Semantic Runtime 独占：semantic fingerprint、rubric、blind bounded context、typed output contract、independence 与 semantic reject semantics。

因此 coding plan / coding implementation 是 AgentJob，不会被塞进文学 semantic reviewer contract。

## Library

安装 Quillframe package 后：

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

`secret_store` 是 host dependency，不是作者需要配置的第三个 Model API 字段。

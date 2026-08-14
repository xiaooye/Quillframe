# Runtime Capabilities · NovelForge 7.1 中文版

## 为什么需要这一层

Runtime 名字不是 capability 证明。叫“ChatGPT”“Codex”“Claude”“GitHub Actions”或“MCP”，都不能自动证明当前 invocation 真的拥有 Web search、filesystem write、provider model、connected repository 或 human relay。

NovelForge 因此把 **runtime identity** 与 **capability evidence** 分开：

```text
runtime identity
→ typed capability manifest
→ task requirements
→ deterministic resolution
→ eligible route
```

## Host Capability Manifest

`harness/runtime_capabilities.py` normalize `novelforge_host_capabilities_v1` manifest。

每个 capability 记录：
- `available`；
- 该声明的 provenance/source；
- permission class；
- usage/cost class；
- 是否需要 user interaction；
- 是否执行 model inference；
- optional non-secret detail。

Credential secret 永远不写进 manifest。

## Proof Levels

### Locally provable

Reference local probe 可以证明当前 filesystem 是否可读写，以及 PATH 上是否存在 `git`、`gh`、`codex`、`claude` 等 executable。

存在 network socket primitive **不能**证明某个 remote service 已授权。

### Host declared

Chat/Web/GitHub/MCP/file-library/provider capability 可由 host/integration layer 显式声明。未声明即 unavailable。

### 永不推断

以下情况都不能用来“猜” capability：
- 同一 provider 在另一个 session 曾经有；
- documentation 里出现某工具；
- 估计 credential 应该存在；
- earlier run 曾经有该 capability；
- model 自己声称能执行。

## Resolution Constraints

Task 可以要求一个或多个 capability。Resolver 还应用：
- user-interaction constraint；
- model-execution constraint；
- usage/cost exclusion；
- 后续 Harness permission/independence rule。

缺失/被拒 capability 必须产生真实 unresolved/awaiting state，不能用伪造 tool output 填空。

## Capability ≠ Authority

Capability 表示**技术上能不能尝试**；Authority 表示**允许不允许改变 durable state**。

Host 可以有 filesystem write，却没有 Canon-write authority；provider 可以返回 semantic judgment，却没有 Framework promotion authority；Web search 可以发现 Corpus source，却不因此获得保存其 full text 的 rights。

## Resume

Persistent session 不会永久保存 capability truth。Resume 时，只要 pending work 需要外部/tool capability，就必须重新 resolve，因为 connection、permission、用户 usage constraint 都可能变化。

## CI

Normal CI 只 probe locally provable facts，并明确断言 Web/GitHub search 在没有 host declaration 时 unavailable。这样 CI 不会变成“imaginary connector capability”的来源。

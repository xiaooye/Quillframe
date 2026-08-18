# Runtime Capabilities · 先证明“这次调用现在真的能做什么”

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>能力证据</kbd>&nbsp;&nbsp;<kbd>CAPABILITY ≠ AUTHORITY</kbd></p>

Quillframe 从不把 runtime 或 provider 名字当成 capability 证据。“ChatGPT”“Codex”“Claude”“MCP”“GitHub Actions”“local model”只描述运行时家族，并不能证明这一次 invocation 现在真的能搜索 Web、写 GitHub repo、调用模型、读取用户文件或联系人工 reviewer。

> **核心不变量 ✦** 只根据当前能够证明的 capability 路由。不要根据文档、旧记忆、品牌名称或模型自我声明去猜。

## 01 · 为什么需要 capability evidence

一次生产 run 可能需要：

- filesystem read / write；
- Git / GitHub repository access；
- Web / business search；
- user files / file library；
- provider model inference；
- local agent invocation；
- MCP client / server transport；
- human / peer relay；
- scheduled / external execution；
- artifact rendering 或其他 host tool。

即使代码和 provider 都没变，可用性、permission、cost 与 user-interaction requirement 也可能在不同 session 之间变化。

因此路由链是：

```text
runtime identity
→ typed host capability evidence
→ task / gate requirements
→ deterministic resolution
→ eligible routes
```

## 02 · Host Capability Manifest

`harness/runtime_capabilities.py` 负责归一化 Harness 使用的 typed host-capability contract。

一条 capability record 应足够回答：

```yaml
name:
available:
source_or_provenance:
permission_class:
usage_or_cost_class:
requires_user_interaction:
executes_model:
detail:
```

不要把 credential 或 secret token 写进 manifest。

Manifest 只是 operational evidence，不是完整 access-control system，也不会授予 Canon / Framework write authority。

## 03 · 能力证据分哪几类

### 本地可直接证明

Local runtime 可以直接证明一些事实，例如：

- path 存在，而且可读 / 可写；
- `git`、`gh`、`codex`、`claude` 是否在 PATH；
- 是否能 spawn local process；
- 已配置 local endpoint 是否响应。

PATH 上有 executable，只能证明程序存在，不能证明已经登录、账号有 entitlement、某个 model 可用，或者远端 permission 成立。

### Host / connector 明确声明

Host 或 integration layer 可以声明当前 invocation 真实具备的能力，例如：

- GitHub connector；
- Web search；
- user files / file library；
- provider inference；
- MCP connection；
- calendar / mail / drive connector；
- peer / human relay。

这类声明应带足够 provenance，使 runtime 能说明“为什么我认为它现在可用”。

### 绝不能靠推断得到

不能因为以下原因就认为 capability 存在：

- 另一个聊天曾经有这个 tool；
- 某个 provider 平时支持；
- 产品文档写着支持；
- 网络 socket 可以建立；
- credential 大概存在某处；
- 模型自己说“我能访问 GitHub / Web / files”；
- 旧 checkpoint 记录过它以前可用。

缺证据，就按当前不可用处理，直到重新证明。

## 04 · Task capability requirement

Task / gate 应推导真正需要的最小能力集合。

例如：

- 修改 repo 文档 → repo read + 精确 write path / permission；
- 本地 independent semantic review → model execution + isolated invocation + bounded packet transport；
- peer-chat review → relay capability + user interaction + separate conversation identity；
- corpus discovery → 对应 search / source capability；
- Canon settlement → project write capability **加上独立的 Canon authority 与 precondition**。

Requirement 应描述“需要什么能力”，而不是硬编码某个偏好的品牌。

## 05 · Resolution constraint

确认 available 后，还要继续检查：

- required permission scope；
- 是否允许 user interaction；
- 是否允许 model execution；
- usage / cost constraint；
- independence / isolation requirement；
- 当前 connection / auth state；
- data locality / security constraint；
- 是否需要 resumability。

一个 capability 技术上可能 available，但对当前 job 仍然不 eligible。

## 06 · Capability ≠ Authority

Capability 回答：

> **这个 runtime 技术上能不能尝试这个操作？**

Authority 回答：

> **这个操作是否被允许改变这个 durable domain？**

例如：

- filesystem write 不授予 Canon write；
- GitHub write 不授予 Framework promotion；
- 模型能做 semantic judgment，不代表它可以把自己写的草稿 Accepted 进 Canon；
- Web search 能找到来源，不代表自动获得全文持久存储权；
- memory-edit capability 不能直接修改 protected Accepted / locked Canon。

Consequential action 同时需要 capability 与 authority 时，两者必须分别成立。

## 07 · Model execution 必须透明

Capability record 应明确区分：这个动作会不会执行 model inference，还是只是 deterministic infrastructure。

Normal CI 应当能够运行 deterministic contract test，而不会静默调用需要付费或登录的模型。

真正需要 semantic judgment 的 workflow，应明确暴露“缺少 eligible model / human path”，而不是用 fake heuristic 伪造判断结果。

## 08 · Resume 时重新验证

Persist session 并不会冻结 capability truth。

Resume 时，pending external / tool work 所需 capability 必须重新解析，因为：

- connector 可能断开；
- token / permission 可能变化；
- local executable 可能消失；
- usage / cost policy 可能变化；
- user interaction 可能不再可行；
- service 可能暂时 unavailable。

已经有 valid receipt 的 completed work 不需要因为 route 变化就重新执行。

## 09 · 失败语义

如果没有任何 route 同时满足 capability 与 constraint：

- 不伪造 tool output；
- 不静默降低 independence；
- 不猜 credential；
- 不把 semantic failure 改写成 infrastructure failure。

返回真实 workflow state，例如 `awaiting_user`、`awaiting_external`、`semantic_pending`、`unsupported` 或当前 mode 合适的其他 blocked state。

## 10 · 不变量

1. Runtime / provider 名字不是 capability proof。
2. 没有 capability evidence，就不能拿它参与 routing。
3. PATH / network presence 比 remote authorization 范围窄得多。
4. Capability 与 authority 是两次独立检查。
5. Resume 必须重新验证 pending capability。
6. Normal deterministic CI 不静默消耗模型 usage。
7. Cost / preference 可以重排 eligible route，但不能削弱 mandatory semantic / authority gate。

## 11 · 相关契约

- [Runtime Routing](RUNTIME_ROUTING.zh-CN.md)：如何从 eligible capability 中选择执行路径。
- [Session Runtime](SESSION_RUNTIME.zh-CN.md)：为什么 resume 必须重查 capability truth。
- [Harness Agent](../HARNESS_AGENT.zh-CN.md)：manager lifecycle 中的 capability broker。
- [`runtime_capabilities.py`](../runtime_capabilities.py)：确定性的 capability normalization / resolution。

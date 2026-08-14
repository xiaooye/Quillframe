# 持续维护协议 · 让 NovelForge 保持健康，但不把自动化变成权威

Continuous Maintenance 负责观察 Framework 健康状态、推进安全的确定性维护工作，并为后续审查准备受限 evidence / candidate。它**不会**因为有 schedule、CI、webhook、queue 或 durable state，就自动获得编辑权威或 source-code write authority。

> **核心不变量 ✦** 自动化可以决定“什么时候检查”；它不会因此获得决定故事事实、消耗未授权模型额度、伪造不存在的 capability，或升级 Framework behavior 的权限。

---

## 01 · Continuous Maintenance 与 Self-Improvement 不是一回事

两者职责分开：

```text
Continuous Maintenance
→ observe / validate / queue / report / 推进确定性状态

Self-Improvement
→ 解释 evidence / 评估 mechanism / 满足 promotion prerequisites
→ 证据充分时由有权限的流程真正修改 Framework
```

Maintenance 可以给 Learning 系统提供输入，但不能绕过它。

---

## 02 · L0 · 无人值守的确定性检查

可以安全自动运行的工作包括：

- Python compile / static / schema checks；
- repository hygiene 与 project-leakage scan；
- 中英双语文档 inventory / link check；
- Tier-A SVG 结构 lint；
- Session / Control Plane invariants；
- capability declaration 与 routing invariants；
- Corpus rights / schema / provenance check；
- Project SDK / Adapter self-test；
- deterministic eval release cases；
- dependency / lock / release-metadata drift detection；
- 不修改任何权威状态的 health report。

这些检查可以让 CI 失败，但它们不做文学判断。

---

## 03 · L1 · 自动准备候选工作

Maintenance 也可以创建**受限 candidate**，但不能自动激活：

- regression / capability case proposal；
- stale docs / integration report；
- Corpus / Research gap；
- discovery request / dispatch plan；
- Learning Cycle bookkeeping artifact；
- 上游 framework change 的 adopt / adapt / reject 研究问题；
- schema / docs cleanup candidate；
- missing-capability report。

生成 queue item、issue、candidate、finding 或 report，都不等于 behavior promotion。

---

## 04 · 模型执行必须显式发生

普通 scheduled maintenance 不能静默调用需要付费、登录或其他 usage-bearing 的模型执行。

当前原则：

```text
normal CI model execution       = forbidden
weekly maintenance model use    = forbidden
live semantic execution         = 显式 opt-in workflow / eligible host runtime
```

如果某一步需要真正语义判断，Maintenance 可以准备 typed packet / job，然后诚实停在 `awaiting_semantic` / `semantic_pending`，直到某个合格 runtime 真正执行。

Queue、router、schema 都不等于 model capability。

---

## 05 · 外部检索能力必须真实存在

Maintenance 可以规划 Corpus 或外部 framework discovery，但如果 active host 没有 Web / GitHub / MCP search capability，就不能假装检索已经发生。

正确流程：

```text
出现 research / discovery need
→ resolve host capability
→ 有能力：dispatch bounded request + 保留 provenance
→ 没能力：记录 missing capability / pending work
```

仅仅存在 network primitive，也不能证明系统已经获得访问某个 remote source 的授权。

---

## 06 · Scheduled Learning Cycle 能推进到哪里

只要下一步不需要 semantic judgment，确定性 maintenance 可以继续推进 durable Learning Cycle。

例如：

- 注册已经存在的 evidence / corpus gap；
- 准备 discovery queue；
- attach 已返回、已验证的 artifact；
- 校验 hash / consume-once receipt；
- 判断“下一步需要 semantic analysis / eval”；
- 生成 promotion prerequisite report。

它不能编造缺失的 semantic result，不能在没有 reviewer 的情况下把 blind eval 标成 PASS，也不能自动 promote candidate。

---

## 07 · Promotion 仍然必须过 Gate

任何会改变通用 behavior 的 material change，都要回到 [Self-Improvement Protocol](SELF_IMPROVEMENT_PROTOCOL.zh-CN.md)。

持久升级至少需要 evidence、正确 scope、counterexample / profile boundary、相关 eval、version / rollback evidence、精确 implementation diff 与 green post-change CI。

即使 prerequisite result 是 `promotable`，它仍然没有 authority。真正写入必须由有权限的 manager / human engineering workflow 执行。

---

## 08 · Event 只能唤醒工作，不能授权工作

以下事件都可以触发 maintenance：

- schedule；
- repository push；
- CI completion；
- webhook；
- MCP event；
- Control Plane event；
- external worker result；
- user request。

但它们都不会自动授予：

- drafting authority；
- Canon mutation；
- durable user-taste activation；
- Framework source mutation；
- release authority；
- model / API usage permission。

Event 到达只能证明“事件到了”。

---

## 09 · Human / Project Authority 始终显式存在

这些 consequential decision 始终保留明确 authority：

- Canon settlement；
- story-direction change；
- 有歧义或 destructive migration；
- 解决互相冲突的 durable user preference；
- 批准 generic behavior change；
- 仓库规则要求时的 release / version promotion。

Maintenance 可以准备 decision packet，但不能冒充 decision owner。

---

## 10 · Failure 与 Resume

Maintenance run 应尽量做到 resumable 与 idempotent。

在 consequential external dispatch / write 前：

- checkpoint current state；
- 用 stable ID / fingerprint 绑定工作；
- 保存 provenance；
- 使用 consume-once 或等价 idempotency semantics；
- 明确区分 infrastructure failure 与有效 semantic rejection。

中断以后，从 durable state 恢复，并重新 resolve capability / authority，不能盲目 replay 已经可能完成的 side effect。

---

## 11 · 参考流程

```text
trigger
→ deterministic health observation
→ classify finding / maintenance need
→ resolve required capability
→ 执行安全的 deterministic work
→ 必要时准备 bounded external / semantic work
→ await / consume validated result
→ tests / eval evidence
→ candidate / report
→ 只有 owning protocol 才能执行 authorized change
```

---

## 12 · 相关契约

- [Self-Improvement Protocol](SELF_IMPROVEMENT_PROTOCOL.zh-CN.md)：真正改变持久 behavior 的 authority。
- [自适应学习](../docs/adaptive-learning.zh-CN.md)：evidence / hypothesis lifecycle。
- [Runtime Capabilities](session_runtime/RUNTIME_CAPABILITIES.zh-CN.md)：capability proof 与 constraints。
- [Control Plane](control_plane/CONTROL_PLANE.zh-CN.md)：durable external work coordination。
- [语料智能](../corpus/README.zh-CN.md)：discovery 与 provenance boundary。
- `.github/workflows/novelforge-weekly-maintenance.yml`：scheduled deterministic maintenance 入口。

**持续维护的目标，是让系统更可观察、更少陈旧，而不是让自动化获得超过 authority model 的权力。**

# Semantic Worker Protocol · 让模型做受限判断，但绝不让“会判断”偷偷变成“有权威”

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>MODEL-READABLE CONTRACT</kbd>&nbsp;&nbsp;<kbd>FINGERPRINT-BOUND</kbd>&nbsp;&nbsp;<kbd>禁止 REVIEWER SHOPPING</kbd></p>

Semantic work 是 NovelForge 明确选择让模型或人类处理“确定性规则无法诚实解决的判断”的地方。本协议先冻结语义问题、限制 worker 可以看到的内容、定义允许返回的结果，再用 exact fingerprint 把结果绑定回原问题，之后 owning workflow 才能消费它。

> **核心不变量 ✦** 模型负责 semantic interpretation；确定性 infrastructure 负责 identity、permission、fingerprint、typed validation 与 logical consumption。两边都不能静默获得对方的权威。

## 01 · 通用 semantic boundary

```text
frozen subject
→ model contract / rubric
→ bounded input + permission
→ semantic fingerprint
→ semantic invocation / handoff
→ typed result
→ deterministic binding validation
→ named gate consumes once
```

如果这是 mandatory independent gate，真正执行 judgment 的 invocation / session 还必须额外满足 independence contract。

## 02 · Model Contract Registry

当前 semantic behavior 统一写在 [`model_contracts.json`](model_contracts.json)，而不是分散成一堆专用 Python “critic engine”。

一份 model contract 定义：

- semantic kind / purpose；
- forbidden input key / leakage constraint；
- rubric；
- output JSON schema / contract；
- permission；
- allowed durable result scope；
- 该 contract 是否本身要求 independent invocation。

当前可能包括 Reader reaction / comparison、Character Integrity、Revision diagnosis、Reader Expectations、Narrative State interpretation、Memory Consolidation、Corpus mechanism analysis、Learning eval judgment 等。

新增 semantic capability 时，默认先问“它是不是应该进入这个 registry”，而不是先写新的 specialized runtime code。

## 03 · Semantic job identity

Semantic job 应至少标识：

```yaml
job_id:
contract_or_kind:
subject_id:
created_at:
input_fingerprint:
input:
rubric:
output_contract:
permissions:
provenance:
execution:
```

真正定义“这次到底在问什么”的，是 subject、bounded input、rubric 与 output contract，而不是最后由哪个 provider 执行。

## 04 · Semantic fingerprint

Semantic fingerprint 代表 exact judgment request。

概念上：

```text
contract / kind
+ subject identity
+ bounded semantic input
+ rubric
+ output contract
= semantic fingerprint
```

Transport / session / attempt lineage 属于 execution metadata，不属于 semantic identity。

因此：

- semantic question 完全冻结不变时，infrastructure retry 可以保持同一 fingerprint；
- candidate、相关 context、rubric 或 output contract 一旦实质变化，就产生新 fingerprint；
- 如果 gate 要求 independent review，materially changed artifact 通常需要 fresh reviewer session。

## 05 · Bounded Context

Worker 只收到当前 judgment 真正需要的内容。

常见排除项：

- hidden expected verdict / gold label；
- 会污染当前判断的 prior reviewer verdict；
- writer private reasoning / chain-of-thought；
- manager scratchpad；
- 无关 project state；
- regression answer key；
- 当 contract 只允许 rights-safe bounded evidence 时的 full raw corpus text；
- 会污染 current-state judgment 的 future-plan data。

Context minimization 同时是质量机制和 authority 机制。

## 06 · Independent review 的 blindness

Independent reviewer 不应该被告知 manager 希望得到什么答案。

Blind packet 可以包含：

- frozen candidate / artifact；
- rubric 真正需要的 bounded current-state / context evidence；
- rubric + output contract；
- exact fingerprint / job identity；
- 足以验证 execution 的 provenance。

不应包含 expected verdict、hidden regression gold、prior reviewer outcome，或者任何为了推 reviewer 给 PASS 的提示。

## 07 · Permission

Semantic worker 没有隐含权限去：

- write Canon；
- settle project state；
- 除非当前 mode 另外授权，否则修改 project plan；
- promote Framework behavior；
- overwrite durable user taste；
- 给自己增加 capability；
- 改写 output contract 的意义。

Permission 应明确最大 result scope，例如：

`diagnostic_observation | revision_proposal | derived_memory_proposal | learning_observation | eval_observation`

Model result 可以推荐 change，但 recommendation 不是 mutation。

## 08 · Typed Result

Result 应重复足够 identity，证明“我到底回答的是哪个问题”：

- job / subject identity；
- semantic fingerprint；
- output contract 要求的 status / judgment field；
- 必要的 evidence / code / finding / confidence；
- truthful model / provider / worker provenance；
- contract 要求时的 execution lineage；
- worker 无法完成判断时的 error。

Private chain-of-thought 不属于 contract，不请求、不运输、不持久化。

为了 auditability，可以返回 contract 明确要求的 concise evidence / explanation，但不需要暴露私有 reasoning trace。

## 09 · Deterministic Validation

消费前，确定性 infrastructure 验证它真正能证明的部分：

- job / result schema；
- exact semantic fingerprint match；
- subject / job identity match；
- permission boundary；
- required provenance / lineage；
- output contract field / type / enum；
- 必要的 forbidden-leakage check；
- consume-once identity。

一个结果即使语义上“看起来很合理”，只要 fingerprint 不对，就是 invalid。

## 10 · Independence

Workflow 要求 independent semantic review 时，independence 指真正不同的 eligible invocation / session 或 human identity，不是“manager 切换成 critic persona”。

可以通过：

- separate local-agent invocation；
- isolated provider API call；
- MCP / Control Plane worker；
- GitHub / service worker；
- separate peer chat；
- isolated local-model invocation；
- human reviewer。

即使使用同一个 provider / CLI family，只要 execution identity 与 context 真正独立，仍然可以满足 requirement。

## 11 · Internal semantics 与 Independent Gate 是两回事

不是每个 semantic contract 都是 independent gate。

Manager workflow 内部可以调用 semantic job 来做：

- scene / character reasoning；
- reader diagnostic；
- revision diagnosis；
- context / memory consolidation；
- research / corpus interpretation。

它们都可以非常“模型智能”，却仍然只是 manager workflow 的内部步骤。

Mandatory independent gate 是额外的 execution requirement。不能把“换了一个 prompt / persona”当 independence。

## 12 · Retry semantics

严格区分三种情况。

### Infrastructure failure

Transport crash、adapter unavailable、timeout、lease expiry 或 malformed delivery，而且 semantic question 未变。

→ checkpoint / retry 或 fallback 到另一个 eligible transport。

### Invalid result

Fingerprint 不对、schema 不对、缺 provenance、发生 forbidden leakage，或者 output 不兼容。

→ reject result / 修 transport 或 worker invocation。

### Valid semantic reject / fail

Reviewer 确实完成了正确 judgment，并明确拒绝 artifact。

→ 消费该 judgment，然后把 repair 送回 Story / Character / Reader / Surface / Continuity 等 owning mechanism。

不能因为想要 PASS，就把第三种情况谎称成第一种。

## 13 · 禁止 Reviewer Shopping

有效 semantic rejection 就是证据。

禁止：

- 同一 frozen candidate 不断换 reviewer 直到有人 PASS；
- 为了引导 fresh blind reviewer，把旧 rejection 一起塞给它；
- 看到不喜欢的结果以后偷偷改 rubric，却不承认已经产生新 semantic question / fingerprint；
- 把 same-session self-review 叫 independent。

修过的 artifact 内容改变，可以合法获得新 fingerprint 并接受 fresh review。

## 14 · Canon / Learning / Framework Boundary

Semantic result 可以影响 plan、repair、learning evidence 或 user decision，但本身不会成为 durable authority。

```text
semantic judgment
→ validated observation / proposal
→ owning workflow gate
→ explicit authority / acceptance / promotion mechanism
→ durable change（如果真正被授权）
```

这样可以防止“模型说得很有道理”直接绕过 Project / Framework governance。

## 15 · 不变量

1. Semantic intelligence 属于 model / human judgment layer。
2. Job identity、fingerprint、permission、schema、consumption 保持确定性。
3. Model contract 必须 bounded，并明确 permission。
4. Independent gate 要求真正 separate execution identity。
5. Semantic question 实质变化就产生新 fingerprint。
6. Valid semantic reject 不是 infrastructure failure。
7. 禁止 reviewer shopping。
8. Semantic result 单独存在时永远不授予 Canon / Framework / taste-write authority。

## 16 · 相关契约

- [Semantic Execution Runtime](SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)：semantic job 怎样到达 eligible runtime。
- [Runtime Routing](../session_runtime/RUNTIME_ROUTING.zh-CN.md)：通用 route eligibility。
- [Control Plane](../control_plane/CONTROL_PLANE.zh-CN.md)：queued handoff / lease / result consumption。
- [质量演进](../../docs/quality-evolution.zh-CN.md)：模型负责质量语义、确定性 ledger 负责持久状态。
- [`model_contracts.json`](model_contracts.json)：live semantic behavior registry。

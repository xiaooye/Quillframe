<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="540" />
  <p><strong>自适应学习 · 模型解释反馈，确定性状态控制持久权威</strong></p>
  <p><kbd>OBSERVE</kbd>&nbsp;&nbsp;<kbd>INTERPRET</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd>&nbsp;&nbsp;<kbd>HYPOTHESIS</kbd>&nbsp;&nbsp;<kbd>EVAL</kbd>&nbsp;&nbsp;<kbd>AUTHORIZE</kbd>&nbsp;&nbsp;<kbd>ROLLBACK</kbd></p>
  <p><a href="adaptive-learning.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 自适应学习

NovelForge 可以从明确的用户 / Project 证据学习，但模型不能把自己的解释直接变成 durable authority。

```text
runtime/session state != learning evidence != Project Canon
semantic interpretation != promotion judgment != write authorization
```

`learning/author_model.py` 继续只是建立在既有 Learning Store 上的 projection/capture 层，不是第二套偏好数据库。

## 1. Feedback intake 默认自动发生，但只自动到 evidence/candidate

在任何 primary task mode 中，只要 user / authorized human 对既有模型产物、创作结果或工作方式给出有评价含义的 semantic feedback，manager 都应把它作为 `feedback.observed` candidate 处理；**basic Learning intake 不需要切换到 LEARN mode。**

同一个 durable feedback event 可以有多个互不吞噬的 logical consumer：

```text
feedback.observed
├─ author_steering:<session>        → 当前 run 的即时 steering
├─ learning_feedback:<project/user> → 自动 Learning intake
└─ observability                    → 只读状态
```

Control Plane 的 consume-once 按 consumer 区分。Steering 已消费，不代表 Learning 已消费；Learning retry 也不能重复写 evidence。

Automatic Learning 的边界是：

```text
observe
→ semantic capture | skip
→ narrowest scope + mechanism
→ source-bound evidence
→ candidate / hypothesis reconciliation
→ optional corpus/eval queue
```

它**不自动**：

- 修改 Project Profile；
- 激活 durable user taste；
- promote General Craft；
- 修改 Framework behavior；
- 写 Canon / SETTLE。

## 2. “每条用户消息”不等于“每条偏好”

`learning.preference_interpret` 首先判断 `capture_decision`：

`capture | skip`

这是 semantic judgment，不是 regex/keyword classifier。

例如：

- “这个对白太书面了”可能是 learnable feedback；
- “上一版人物更活，这版更专业但不好看”可以形成 comparison evidence；
- “继续下一段”“ok”通常应 `skip`；
- 普通事实问题或操作命令不能因为包含“应该”等词就被强行变成 preference。

`skip` 可以留下 processed/skipped receipt，但不能制造 scope、mechanism 或 hypothesis。

## 3. Semantic interpretation 由模型负责

对 `capture`，`learning.preference_interpret` 提出最窄的 plausible scope：

`one_off | project | user_taste | general_craft`

它还可以说明：

- feedback type / polarity；
- mechanism、desired/avoid behavior；
- applicability / exceptions / uncertainty；
- 与 compact hypothesis index 的关系；
- `create | strengthen | contest | supersede | split`。

模型只可针对 supplied bounded evidence 与 exact hypothesis IDs 判断，不得凭措辞相似度制造 merge。

用户说“所有网文都……”本身不等于 General Craft 成立；最多成为 candidate evidence。General Craft promotion 仍需要独立 research/corpus/counterexample/eval/version/rollback/CI 与授权。

## 4. Learning Store 拥有 durability，不拥有 meaning

Deterministic store 负责：

- feedback event/hash、evidence/hypothesis ID 与 provenance；
- stable event-derived evidence identity；
- versioned state、contradiction / supersession record；
- exact source refs / target fingerprint；
- persistence / rollback history；
- consumer-specific consume-once；
- Project / user scope isolation。

同一 event retry 不能成为第二条 evidence。真正独立的新 user turn 可以作为第二条 evidence，模型再决定是否 strengthen 同一个 hypothesis。

一个 record 即使已经持久化，也仍然可以是 tentative / contested。Persistence 不会把模型推断变成真理。

## 5. Pending / resume 是正常状态

如果当前 host 没有 eligible semantic capability：

```text
feedback.observed
→ feedback intake = awaiting_semantic
→ durable queue / fingerprint retained
→ later resume revalidates event + authority + semantic job
→ consume exactly once
```

系统不能丢掉反馈，也不能用关键词 heuristic 猜 scope/mechanism。

`learning.preference_interpret` 本身不是 independent gate；当前 manager model 已经在执行 request 时，可以在同一 invocation 中按正式 contract 做 bounded interpretation。只有真正要求 independence 的 eval/review 才使用另一 invocation/session。

## 6. Current explicit instruction 与 durable learning 分离

同一句用户反馈可以同时产生两个效果：

1. **当前显式指令立即生效**；
2. **作为 Learning evidence candidate 被自动摄取**。

它们不互相等待。

```text
current explicit instruction > old active preference
current explicit instruction != automatically active durable preference
```

因此“这一章不要专业感，主要要幽默、魅力和剧情张力”当前就应被执行，但是否成为未来 Project/user-taste durable behavior 仍服从 Learning authority。

## 7. Promotion Gate 只把 semantic review 绑定到 authority

`learning/promotion_gate.py` 不用 arbitrary evidence-count threshold 假装证明 semantic sufficiency。

Semantic promotion review 判断 supplied evidence 是否真的支持 proposed scope/mechanism，以及重要 contradiction/counterexample 是否仍 unresolved。

Deterministic gate 只验证围绕这份 review 的客观 prerequisite，例如：

- exact contract/result/evidence binding；
- candidate scope / identity；
- policy 要求时的 eval / counterexample artifact；
- General Craft 所需 version/rollback/CI refs；
- surrounding authority mechanism 提供的 explicit write authorization。

Promotion review PASS 只是 prerequisite，**不是写权限**。

## 8. Active != relevant

Author Model hypothesis 的 `active` 只表示它具备 durable eligibility，不表示每一次 future production 都应该把它塞进 context。

Author Model 暴露 compact active index；manager/model 显式选择当前任务 relevant 的 active hypothesis IDs。Deterministic code 只验证这些 ID 确实 active 且 scope-compatible，然后返回 detail。

这样可以防止自动 Learning 更强以后反而造成 context pollution。

## 9. 不同 scope 的 authority

### One-off

只用于当前 task/repair，自动 intake 可以保留 evidence/candidate 以供审计，但不会自动变 future active behavior。

### Project preference

自动 intake 默认只形成 Project candidate。只有 Project 明确授予 preference activation/write authority 的后续路径才能激活；不会直接改 Project Profile。

### Durable user taste

必须同时满足：

1. 同 mechanism/scope 的当前 bound promotion prerequisite result；
2. explicit durable-user-taste write authorization。

Personal learning data 默认留在 user/runtime storage，不提交 Generic Framework repo。

### General Craft

General Craft 仍属于 Framework `SYSTEM-IMPROVE`。它要求更强的 current research、cross-work evidence、counterexample/profile boundary、eval/regression、compatibility、version/rollback、green CI 和 explicit Framework promotion authority。Production feedback 不能自动晋升它。

## 10. Rejection / acceptance / Canon authority 分离

明确拒绝的 AI artifact 可以成为 negative evidence：

- artifact ref / fingerprint；
- feedback event/ref；
- rejection mechanism；
- `rejected_negative_only` disposition。

不要把失败正文复制进 Learning Store，也不要因为捕获 rejection 就把 rejected prose 变成正向 benchmark 或 Writer pre-draft context。

Reasoned acceptance 可以成为学习信号，但 plain “accepted” 不能自动推断“用户永久喜欢该 artifact 内所有机制”。

Canon acceptance 与 learning evidence 是两个 authority domain：Canon acceptance 可能满足 Project Settlement 的前置条件；Learning acceptance 只描述用户对 artifact 的反应。一个不能替另一个授权。

## 11. Contradiction / rollback 是一等机制

新 feedback 可以：

- strengthen 旧 hypothesis；
- `contest`；
- `supersede`；
- `split` applicability；
- 缩窄到某种 scene/profile/时期；
- evidence 改变时 deprecate 某行为。

例如“专业细节多一点”与“开篇不要专业感”未必是两个互斥 universal rules。模型可以把后者限定到 opening applicability；runtime 只保存 exact target/version/provenance，不自己判断文学语义。

“Strengthening”意味着出现新的独立 evidence，而不是同一个 event retry、同一个模型重复解释自己，或时间变久。

## 12. Corpus / Research 只是取证，不是“抓到就变真理”

Semantic learning agent 可以识别 evidence gap，并在 allowed capabilities 内搜索合法 contrast/counterexample material；search/retrieval strategy 仍由模型决定。

Corpus discovery ≠ ingestion；ingestion ≠ Canon；corpus analysis ≠ promotion。

Rights、provenance、source identity、Project/user isolation 继续由 deterministic boundary 保证。

## 13. Observability 与 privacy

`learning/feedback_query.py` 只读打开既有 Learning DB；query 不创建表、不 consume receipt、不更新时间戳、不执行模型。

可查询：

- observed / awaiting_semantic / skipped / persisted / blocked / failed；
- event/hash、target/artifact fingerprint；
- semantic job/result fingerprint；
- evidence/hypothesis/action/contradiction refs；
- version/timestamps。

Query 不返回 whole conversation、bounded feedback text、private reasoning、hidden eval gold 或 secrets。

## 14. Production use

```text
user feedback in any primary mode
→ current instruction/steering acts now
→ feedback.observed durable
→ automatic Learning intake
→ semantic capture | skip
→ source-bound evidence
→ create / strengthen / contest / supersede / split candidate
→ optional corpus/eval cycle
→ later authorized activation/promotion only if prerequisites pass
→ active eligibility
→ model selects relevant active hypothesis IDs for future task
```

仅仅因为 `learning.db` 中存在记录，Writer/Editor 不会收到一份隐藏的全局 style profile。

## 精确实现边界

- `learning/learning_store.py` —— durable evidence/hypothesis/candidate/promotion history。
- `learning/feedback_intake.py` —— feedback event → semantic job → pending/result validation → Author Model capture → learning consumer receipt。
- `learning/feedback_query.py` —— side-effect-free feedback intake projection。
- `learning/promotion_gate.py` —— 围绕 model-owned promotion review 执行 deterministic binding/authority check。
- `learning/author_model.py` —— bounded feedback capture、exact hypothesis reconciliation、scope-aware activation binding、active index、explicit selected projection。
- `harness/semantic_workers/contracts/production-loop.json` —— `learning.preference_interpret` capture/skip contract。
- `evals/feedback_learning_ablation_manifest.json` / `feedback_learning_ablation.py` —— 独立 semantic BEFORE/AFTER 与控制组 packet；没有独立 reviewer 时保持 `PENDING_MODEL`。
- Framework Self-Improvement Protocol —— General Craft promotion authority。

<div align="center"><sub>反馈默认被听见；记忆默认受限；永久行为永远需要额外证据与 authority。🌸</sub></div>

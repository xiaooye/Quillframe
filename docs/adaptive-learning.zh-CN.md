<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="540" />
  <p><strong>自适应学习 · 模型解释反馈，确定性状态控制持久权威</strong></p>
  <p><kbd>INTERPRET</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd>&nbsp;&nbsp;<kbd>HYPOTHESIS</kbd>&nbsp;&nbsp;<kbd>EVAL</kbd>&nbsp;&nbsp;<kbd>AUTHORIZE</kbd>&nbsp;&nbsp;<kbd>ROLLBACK</kbd></p>
  <p><a href="adaptive-learning.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 自适应学习

NovelForge 可以从明确的用户 / Project 证据学习，但模型不能把自己的解释直接变成 durable authority。

```text
runtime/session state != learning evidence != Project Canon
semantic interpretation != promotion judgment != write authorization
```

`learning/author_model.py` 继续只是建立在既有 Learning Store 上的 projection/capture 层，不是第二套偏好数据库。

## 1. Semantic interpretation 由模型负责

`learning.preference_interpret` 解释 supplied feedback，并提出最窄的 plausible scope：

`one_off | project | user_taste | general_craft`

它可以说明底层 mechanism、desired/avoid behavior、exceptions、uncertainty，以及与旧 hypothesis 的冲突，但不能授予 durability / activation。

“这些 evidence 在语义上是否足以支持稳定 scope/mechanism”由模型判断，而不是 Python evidence-count threshold。

## 2. Learning Store 拥有 durability，不拥有 meaning

Deterministic store 负责：

- evidence/hypothesis ID 与 provenance；
- versioned state、contradiction / supersession record；
- exact source refs；
- persistence / rollback history；
- consume-once result handling；
- Project / user scope isolation。

一个 record 即使已经持久化，也仍然可以是 tentative / contested。Persistence 不会把模型推断变成真理。

## 3. Promotion Gate 只把 semantic review 绑定到 authority

`learning/promotion_gate.py` 不再用 arbitrary evidence-count threshold 假装证明 semantic sufficiency。

Semantic promotion review 判断 supplied evidence 是否真的支持 proposed scope/mechanism，以及重要 contradiction/counterexample 是否仍 unresolved。

Deterministic gate 只验证围绕这份 review 的客观 prerequisite，例如：

- exact contract/result/evidence binding；
- candidate scope / identity；
- policy 要求时的 eval / counterexample artifact；
- General Craft 所需 version/rollback/CI refs；
- surrounding authority mechanism 提供的 explicit write authorization。

Promotion review PASS 只是 prerequisite，**不是写权限**。

## 4. Active != relevant

Author Model hypothesis 的 `active` 只表示它具备 durable eligibility，不表示每一次 future production 都应该把它塞进 context。

Author Model 暴露 compact active index；manager/model 显式选择当前任务 relevant 的 active hypothesis IDs。Deterministic code 只验证这些 ID 确实 active 且 scope-compatible，然后返回 detail。

这样可以防止把所有 learned preference 自动注入造成 context pollution。

当当前用户显式指令与旧偏好冲突时，当前显式指令优先。

## 5. 不同 scope 的 authority

### One-off

只用于当前 task/repair，除非之后另行捕获新的 evidence。

### Project preference

只有在 Project 明确授予 preference-write authority 时才能激活；不会改变 Framework behavior。

### Durable user taste

必须同时满足：

1. 同 mechanism/scope 的当前 bound promotion prerequisite result；
2. explicit durable-user-taste write authorization。

模型与 Promotion Gate 都不能给自己授予这项权限。

### General Craft

General Craft 仍属于 Framework `SYSTEM-IMPROVE`。它要求更强的 counterexample/eval/compatibility/version/rollback evidence 与 explicit Framework promotion authority。Production feedback 不能自动晋升它。

## 6. Corpus / Research 只是取证，不是“抓到就变真理”

Semantic learning agent 可以识别 evidence gap，并在 allowed capabilities 内搜索合法 contrast/counterexample material；search/retrieval strategy 仍由模型决定。

Corpus discovery ≠ ingestion；ingestion ≠ Canon；corpus analysis ≠ promotion。

Rights、provenance、source identity、Project/user isolation 继续由 deterministic boundary 保证。

## 7. Contradiction / rollback 是一等机制

新 feedback 可以：

- strengthen hypothesis；
- 缩窄 applicability；
- 标成 `contested`；
- 拆分 over-broad mechanism；
- supersede 旧 hypothesis；
- evidence 改变时 deprecate 某行为。

“Strengthening”意味着出现了新的独立 evidence，而不是同一个模型重复同意自己，也不是时间变久。

## 8. Production use

```text
explicit feedback
→ semantic preference interpretation
→ source-bound evidence
→ revisable hypothesis
→ durable activation 被提议时运行 semantic promotion review
→ deterministic authority/prerequisite validation
→ active eligibility
→ model 为未来任务选择 relevant active hypothesis IDs
→ production observe outcome
→ 新 evidence 可继续 revise/supersede hypothesis
```

仅仅因为 `learning.db` 中存在记录，Writer/Editor 不会收到一份隐藏的全局 style profile。

## 9. Privacy

Personal preference evidence 属于 user scope，默认不提交到通用 Framework repo。不得从 fiction preference 推断无关的人口属性或个人画像。

## 精确实现边界

- `learning/learning_store.py` —— durable evidence/hypothesis/candidate/promotion history。
- `learning/promotion_gate.py` —— 围绕 model-owned promotion review 执行 deterministic binding/authority check。
- `learning/author_model.py` —— bounded feedback capture、contradiction/supersession、scope-aware activation binding、active index、explicit selected projection。
- `harness/semantic_workers/contracts/production-loop.json` —— `learning.preference_interpret`。
- Framework self-improvement protocol —— General Craft promotion authority。

<div align="center"><sub>语义上解释，谨慎地持久化，只在证据与 authority 都成立时激活。🌸</sub></div>

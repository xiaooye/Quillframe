# 自适应学习

Quillframe 的 Learning 会在 meaningful feedback 到来时自动开始 intake，但 automatic intake 从来不等于 automatic promotion。

<img src="assets/concepts/automatic-learning-intake.zh-CN.svg" alt="Learning intake：从 automatic feedback capture，经 interpretation、scope、hypothesis，到 governed validation 与 promotion" width="100%" />

## Automatic Capture

Durable `feedback.observed` event 可以被 Learning Intake 独立于 current-run Author Steering 消费。`learning/feedback_intake.py` 把 feedback 封装给 `learning.preference_interpret`；由模型判断 `capture | skip`、证据真正支持的最窄 scope、mechanism、contradiction 与 hypothesis relation。

系统不会用 keyword/regex 冒充“这是不是有意义反馈”的语义判断。

同一个 durable event retry 不算新 evidence；真正不同的新 user turn 才可能成为 independent evidence，用来 strengthen、contest、supersede 或 split 既有 hypothesis。

## 四种 Scope

`one_off` 只服务当前 request/run；`project` 只属于一本 Project；`user_taste` 是跨项目的 durable preference hypothesis；`general_craft` 才是 Generic Framework behavior 的候选。

Evidence 永远使用它真正支持的最窄 scope。

## Governed Promotion

Automatic intake 默认所有 protected write permission 都是 false。它不会自动改 Project Profile、激活 durable user taste、promote General Craft、修改 Framework source 或写 Canon。

Durable activation 需要 evidence、contradiction review、相关 eval evidence、provenance，以及目标 scope 要求的 authority。General Craft 门槛最高：cross-work evidence、counterexample/profile boundary、capability/regression eval、version/rollback、green deterministic CI 与 explicit engineering authority。

## Rejected Output

被拒 artifact 可以按 ref/fingerprint + negative meaning 成为 regression evidence，但不是 positive prose exemplar，也不能泄漏回 pre-draft writer context。

## Research 与 Corpus

Learning 可以创建 Corpus gap，并寻找 rights-safe contrast evidence。Discovery != ingestion；ingestion != preference；analysis != promotion；Corpus != Canon。

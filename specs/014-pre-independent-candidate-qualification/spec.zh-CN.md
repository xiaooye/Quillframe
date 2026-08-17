# Spec 014 · Pre-Independent Candidate Qualification

## 1. 问题

当前 `0.8.0` production graph 已经有 Blind Reader、Semantic Rule Auditor、Editor repair、continuity 和 independent `quality.production_review`，但缺少一个**不可绕过、fingerprint-bound 的 manager qualification receipt**。因此一个只做过局部/macro cleanup、仍残留已知 Surface / regression / semantic-ownership / Reader-Grip 缺陷的 candidate，可以在 manager 自己完成充分 post-generation quality loop 之前进入昂贵的 independent reviewer。

Consumer Project 还存在 execution-order drift：pinned Generic Harness/production docs 是 `freeze → Reader → Rule Auditor → Editor repair → continuity → independent`；consumer `START_HERE` 却写成 `Surface/Regression → freeze → independent → Rewrite/Regenerate → Reader Engagement → Continuity`。Generic execution authority 属于 pinned Framework；consumer adapter 文档不得覆盖它。

## 2. 目标

生产图变为：

```text
Raw Draft
→ Surface Realization
→ freeze diagnostic candidate fingerprint
→ manager/internal semantic quality loop
   → Surface + Project regression + semantic ownership/natural-realization audit
   → Blind Reader / Reader Engagement
   → Editor repair diagnosis
   → continuity/state check
→ repair owning mechanism when blocked
→ new candidate fingerprint after material repair
→ repeat bounded loop
→ pre-independent qualification receipt
→ independent production review dispatch
→ independent PASS → user-visible Review Draft
→ independent FAIL → owning repair layer → new fingerprint → qualify again → fresh independent review
```

`manager/internal semantic quality loop` 可以由当前 manager invocation 执行；其结果必须 `independent=false`，永远不能满足 mandatory independent gate。

## 3. Diagnostic candidate 与 qualified release candidate

不新增 Canon lifecycle authority class，只增加 execution-state distinction：

- **diagnostic candidate**：Surface realization 后已经冻结 exact fingerprint，可安全加载 post-generation regression/rule evidence；
- **qualified release candidate**：同一 exact fingerprint 已通过 required manager self-audit、Reader Engagement 和 continuity，并且没有 unresolved blocking finding，才允许 dispatch independent review。

Material prose change 必须产生新 candidate fingerprint；旧 qualification 与旧 reviewer result 均 stale。

## 4. Semantic vs deterministic responsibility

### Model owns

- 句/段/block/scene 是否具有叙事功能；
- Delete Test 的语义判断；
- micro-action 是否真正改变 action/information/relationship/pressure/timing/ownership；
- show 后是否又 explain；
- random embodiment、staged routine reveal、synthetic coolness、AI explanation tone；
- Surface/Project regression 的 applicability；
- semantic ownership；
- Reader Grip / SAFE-BUT-FLAT；
- repair owner 与 repair depth；
- “functional but over-authored” 的自然实现判断。

### Deterministic runtime owns

- candidate/subject identity；
- exact fingerprint；
- typed semantic contract/result validation；
- qualification receipt existence/status；
- no unresolved blocking finding；
- receipt fingerprint/provenance；
- dispatch refusal；
- stale qualification invalidation；
- independence role separation；
- retry/replay safety；
- normal CI no live model usage。

禁止用 `看/笑/不是/低声`、句长或 punchline 词汇做 deterministic literary verdict。Optional lexical highlighting 只能产生 candidate spans，不能产生 PASS/FAIL。

## 5. Candidate self-audit semantic contract

新增 non-independent semantic contract `quality.candidate_self_audit`。

输入至少绑定：

- `candidate_fingerprint`
- `candidate_text`
- bounded authoritative Surface/regression rule material
- bounded project/profile/voice constraints when applicable

它应检查三个尺度：

1. sentence / utterance；
2. local block；
3. scene/cluster。

核心 diagnostics：

- Delete Test；
- action-tag / micro-action function；
- explanation-after-evidence；
- artificial punch / synthetic coolness；
- AI explanation tone；
- procedural chronology / SAFE-BUT-FLAT interface；
- semantic ownership；
- cluster failure；
- Project regression applicability。

输出为 typed findings，带 `scope`、`severity`、`repair_owner`、`evidence_refs`、`blocking`；允许 `pass | fail | insufficient_evidence`。Contract 明确 `independent_gate=false`。

## 6. Functional-but-over-authored addendum

`FUNCTIONAL != NATURAL != CHARACTER-OWNED != PRODUCTION-READY`。

Delete Test 只能回答“无功能是否应删”，不能证明有功能表达自然。对 salient narrator sentence / dialogue turn，自审必须继续三层判断：

1. **FUNCTION**：删除后是否损失 action / information / relationship / pressure / humor / timing / voice？
2. **OWNERSHIP**：措辞与理解是否真实属于当前 POV / narrator profile / speaker？
3. **NATURAL REALIZATION**：即使有功能且归属正确，此刻的人是否真的会用这种完整度、对称度、cleverness、quote-readiness 来表达？

高风险但非 lexical ban 的机制：

- ordinary fact 被 narrator clever reframing；
- punchline-first 而非 purpose-first speech；
- unusually complete / polished character lines；
- 多人连续 witty comeback；
- `setup → clever answer → clever comeback → witty gloss → punchline` 的 punchline stacking；
- humor/charisma secondary objective 压过当前 social purpose。

优先用现有 `HF-27 SEMANTIC ROLE MISATTRIBUTION`、`HF-29 AI POLISH WITHOUT STORY FUNCTION`、`HF-25`、`HF-30`、Character Integrity 与 `RG-08 CHARACTER-OWNED HUMOR/HUMANITY` 组合表达。**本 spec 不新增 HF code**；只有后续 cross-case evidence 证明 taxonomy 无法稳定描述该机制时，才另开 General Craft promotion。

### Character-owned humor vs author-optimized wit

Good humor 来源于 relationship + agenda + status + misunderstanding + pressure + history + self-interest；即使拿掉“好笑”这一评价，该 utterance 仍是人物为了当下目的会做的 social move。

Synthetic humor 是先有“这里需要魅力/人味/笑点”的作者目标，再倒推出 quote-ready line。Self-audit 必须检查这一差别，但不能因此把 witty/charismatic character 压平成平庸口语。

Cluster failure 路由到 `Character Simulation + Dialogue/Scene Realization + Surface Realization`，而不是逐句换同义词。

## 7. Qualification receipt

新增 `novelforge_candidate_qualification_v1`，至少表达：

- candidate fingerprint / subject id；
- repair cycle；
- self-audit status + exact semantic binding refs；
- Reader Engagement status + exact semantic binding refs；
- continuity status / receipt；
- blocking findings；
- qualification status；
- provenance；
- `independent=false`；
- no Canon/Framework/taste write authority。

状态：

- `awaiting_semantic`
- `repair_required`
- `qualified_for_independent`

Qualification 不重新判断文学质量，只组合已经完成的 exact bound evidence。

## 8. Independent dispatch guard

任何 `quality.production_review` job construction/dispatch 必须要求：

1. current candidate fingerprint；
2. valid `novelforge_candidate_qualification_v1`；
3. receipt fingerprint/subject/candidate exact match；
4. status = `qualified_for_independent`；
5. unresolved blocking findings = empty；
6. qualification `independent=false`；
7. qualification 本身不携带 review verdict/gold/private reasoning 给 reviewer。

缺失/stale/fail/pending → hard refusal，不是 warning。

Qualification metadata 属于 runtime dispatch proof，不进入 independent reviewer semantic payload，避免 verifier contamination。

## 9. Final release defense-in-depth

`production_readiness` / `production_release` 在 independent review 已返回后仍验证：

- independent result exact candidate-bound；
- required qualification receipt exact candidate-bound；
- independent PASS 不能覆盖 unresolved qualification FAIL；
- candidate material change 让旧 qualification/review stale。

## 10. Regression isolation

保持现有 hard invariant：

- Raw Writer / first-pass generation 看不到 rejected bad-example text / hidden expected labels；
- freeze diagnostic candidate 后 Auditor/Editor 可以读取直接 relevant regression evidence；
- fresh realization Writer 默认只拿 owning mechanism + scene/character/reader constraints + writer-safe repair projection，不拿 rejected exact prose；
- rejected artifact 不成为 positive exemplar。

## 11. Cost / complexity

默认：`single manager + bounded semantic quality loop + mandatory independent reviewer`。

不要求 self-audit 独立 invocation；当前 manager 可按正式 contract 完成。只有 mandatory independent `quality.production_review` 要真正 separate invocation/session。避免为了 qualification 新增多-agent bureaucracy。

## 12. Observability

高层 production state 至少可表达：

`raw_generated | surface_realized | self_audit_failed | repairing | qualified_for_independent | awaiting_independent | independent_failed | review_ready`

用户可被告知 blocking family（如 Surface cluster / Reader Grip / continuity），但不暴露 chain-of-thought、hidden regression gold 或 private worker chatter。

## 13. Compatibility

- 不改变 Canon/Settlement authority；
- 不修改 consumer Project 或 repin；
- Generic Framework 不保存具体 Project 角色、章节原句或 private user text；
- `quality.production_review` 的 semantic reviewer input shape保持 reader-visible bounded packet；qualification 是 runtime-only dispatch proof；
- 旧 runtime 若没有 qualification component，升级后 production independent dispatch 会 fail closed，需迁移调用链；
- 旧 consumer 继续按旧 pin 运行，不受本 PR 影响。

## 14. Research synthesis

### Adopt

- **OpenAI Agents SDK guardrail/tripwire**：采用“在昂贵/后续执行前存在 blocking precondition”的 execution principle；不采用其 safety-specific语义作为文学判断。
- **Anthropic evaluator-optimizer**：采用生成→语义评估→反馈→再生成的 bounded loop，适用于写作这种反馈可明显改进的任务。
- **Anthropic 2026 eval guidance**：采用 deterministic graders where possible + model graders where nuance is required、positive/negative balanced controls、isolated trials、明确 Unknown/insufficient-evidence path、capability/regression 分离。
- **Google Agents CLI / ADK eval**：采用 generate→grade→compare 的 staged eval-fix loop 与 baseline/candidate comparison。

### Adapt

- evaluator 不必是独立 agent：manager self-audit 明确 `independent=false`；只有 release independent gate 分离 invocation。
- guardrail不做词法规则；它只验证 semantic result receipt 是否存在且 PASS。
- grader isolation分两层：self-audit 可见 post-generation regression/rules；independent reviewer保持 blind，不看 manager audit checklist/findings。

### Reject

- 每个 sentence 触发独立 paid critic；
- regex/lexical hard bans；
- 多个 reviewer 投票直到 PASS；
- 把 manager self-audit 当 independent evidence；
- 把一次 Project failure 直接升级成 universal HF mechanism。

## 15. Acceptance criteria

完成标准：一个带明显已知 Surface / Project regression / AI-explanation / Reader-Grip / functional-but-over-authored cluster 的 candidate，在 manager 修复并取得 exact qualification receipt 之前，runtime 无法构造/dispatch mandatory `quality.production_review` job；clean/legitimately witty prose 不因关键词或“有幽默”被 deterministic false-positive。
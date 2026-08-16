# Spec 012 · 自适应生产学习与 Realization 边界

状态：implementation candidate
范围：仅 Generic NovelForge
Primary mode：SYSTEM-IMPROVE

## 问题

真实 production evidence 暴露出一个 intent–execution gap：NovelForge 即使已经有正确的 Framework rules 与 Project profile，某次 run 仍可能组装出“形式合法、质量贫血”的 Context；把人物私有状态过于直接地暴露给 prose generation；把某个 semantic review PASS 当成完整 release permission；最后又在 revision 之后丢掉用户真正有价值的反馈。

这不能靠再加几条 prose instruction 解决。Production runtime 需要显式状态与接口，把作者意图、Context Assembly、simulation、realization、Reader/Editor feedback 与 future runs 真正连起来。

## 设计来源

本 candidate 借鉴成熟写作工具与 agent system 中反复出现的 mechanism，而不是复制其产品表面：

- 持久、可编辑的 creative intent / story-bible state，而不是依赖聊天记忆；
- task-aware sparse context assembly，而不是把所有持久资料灌进 prompt；
- 分层/受限规划，同时保留 emergence；
- 先 character/world simulation，再 prose realization；
- evaluator/editor revision loop，而不是 one-shot generation；
- subjective revision 使用 incumbent/challenger pairwise comparison；
- feedback 可以进入 future work，但不会因此静默获得 durable authority。

NovelForge 继续保留更严格的 authority、fingerprint、session、settlement、rights 与 independent-review 边界。

## 不变量

### I1 · Author intent 是一等状态

Production 只能消费经过授权、适用于当前任务的 Author Model projection。优先级为：

`当前明确要求 > Project 明确 intent/profile > active scoped preference > candidate/inferred hypothesis`。

Hypothesis 是 evidence，不是 behavior。仅靠模型推断不能激活 durable user taste，也不能成为 General Craft。

### I2 · Review feedback 产生 evidence，不自动变成规则

实质性用户 Review feedback 必须可以分类为 `one_off | project | user_taste | general_craft`，并可以生成 typed observation 与 proposed preference delta。真正 activation 继续服从对应 scope 的 authority。

Project-authorized preference 可以影响未来 Project run；user-taste hypothesis 继续服从已有 learning/activation prerequisites；General Craft observation 只进入 SYSTEM-IMPROVE evidence。

### I3 · Context Assembly 必须证明 required context obligation 已满足

Semantic selector 决定“什么最相关”。确定性 runtime 只证明：声明为 required 的 obligation，确实由 eligible、stage-safe、未 invalidated 且 authority/provenance 合法的 context item 满足。

Required obligation 没有合格 selected item → assembly BLOCK。Optional context 可以为空。

### I4 · 人物私有状态不是 prose payload

人物 agenda、fear、goal、risk、private knowledge 与 simulation reasoning 是 causal control state，不是 Writer 的 exposition obligation。

Pre-draft character/scene simulation 可以消费 private character state；Prose generation 默认应消费 writer-safe realization projection，其中只包含：observable action/event、POV 合法 inner state、interaction tactic、shared context、withheld/compressed information、social cost、task/object carrier、turn pressure，以及确有必要时的 formal-completeness reason。

### I5 · Agenda 驱动对白，但 Agenda 不是对白

`AGENDA-TO-DIALOGUE LEAKAGE / CHARACTER-SHEET-TO-DIALOGUE SERIALIZATION` 是 Framework quality failure：当人物私有状态以近同构、过度完整的方式被直接翻译成对白，而没有充分经过 immediate tactic、listener model、shared knowledge、关系/社会成本、省略、扭曲、打断、task action 或其他 interaction pressure 的变换。

如果 speech act 本身要求完整，则完整表达合法，例如 testimony、briefing、instruction、formal risk explanation、record-making，或对方明确要求完整交代。

### I6 · Reader → Editor 是 creative repair loop

Reader 先整体判断真实阅读体验，输出 multidimensional semantic evidence；Editor 再把这些 finding 转成 bounded repair specification：preserve/change priorities、owning mechanism、local/global depth、invalidation need，以及是否需要 incumbent/challenger comparison。

当一个结构化 Reader + 一个 Editor 已经足够时，不建立重复文学 reviewer 委员会。

### I7 · Revision 不默认等于 improvement

对 scene realization、reader grip、voice、paragraph rhythm、dialogue embodiment、platform fit 等 material repair，如果 policy 标记 comparison required，就必须证明 challenger 不比 incumbent 更差。Pairwise 结果允许 A、B、tie。

### I8 · 确定性代码不判断文学真理

one-sentence-paragraph ratio、sentence-length distribution、fragment density、consecutive short-paragraph runs 等只是 telemetry。除非 Project profile 显式声明 hard threshold，否则数字本身不能成为通用 pass/fail。

`pseudo-speed fragmentation`、`paragraph-function failure`、commercial/platform fit、agenda-dialogue leakage 等 profile-sensitive 判断属于 semantic evaluation。

### I9 · Structural release evidence 继续采用 conjunctive gate

Semantic reviewer PASS 不能补齐缺失的 required structural receipt。如果 run policy 要求当前 context-assembly receipt，那么它必须绑定当前 run/candidate，并且真实存在，user-visible readiness 才能为 true。

### I10 · Consequential write 必须匹配 typed intent

Write intent 必须绑定 resource class、operation class、exact target、authority/precondition 与 idempotency。实际 connector action 若属于不同 resource/operation/target，必须 fail closed：`BLOCK_RESOURCE_ACTION_MISMATCH`。

## Compatibility

- 本 Framework candidate 不改变 Canon，也不改变 downstream Project state。
- 已有 Author Steering、Learning Store、Context Inspector、Character Action Proposal、Scene Action Resolution、Production Readiness、Reader Engagement、Quality Evolution 继续作为 owner；本工作负责连接并收窄接口，不重新发明它们。
- 未声明新 obligation 时，已有 DRAFT/REVISE 可以保持兼容；只有 policy 明确要求的新 obligation 才 fail closed。
- Generic Framework 不硬编码任何具体项目的 genre/platform。

## Non-goals

- 不自动 promote General Craft；
- 不自动迁移 consumer lock；
- 不创建 named-author imitation profile；
- 不制造 deterministic literary scoring engine；
- 不要求每次 DRAFT 都检索 Corpus；
- 不规定对白必须短、碎、口语化或不完整；
- 本 candidate 不替换 planning-commitment-horizon 的既有语义。

## Acceptance

只有在 deterministic self-tests、catalog/schema/reference checks、generic eval queue、exact-head CI evidence，以及 candidate fingerprint 对应的 independent semantic capability/counterexample evidence 都可检查后，才足以进入人工审核。Promotion / activation 仍是之后单独授权的决定。

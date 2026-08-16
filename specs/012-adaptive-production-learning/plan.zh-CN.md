# Plan 012 · AI-Native 自适应生产架构重构

## 目标

把 PR #90 现有 review unit 收口成 coherent 的 **thin-kernel / model-owned semantic-runtime** candidate。不创建平行 owner，不 merge/release，也不修改下游 Project。

## Live reconciliation

本 refoundation 的 live bootstrap 永远从当前 PR/HEAD 重新解析，旧聊天或历史 Plan 里的 SHA 只算记录。此次 authority synchronization 前的 rollback checkpoint 是 `b6f13ac97a105221f8ee78d862c4e6f02e4cf9ab`；之后每一次 consequential write 都必须重新读取 PR #90 before-state。

Current owner decision：

- KEEP Session Runtime、Control Plane、exact identity/fingerprint、CAS、receipt、stage isolation、hard budget。
- THIN Context Assembly、Writer realization、repair routing，只保留 machine-required field。
- MIGRATE semantic relevance/search、Reader experience、rule applicability、repair depth、planning quality、character reasoning、feedback interpretation 到 model contract。
- prose telemetry 降为 OPTIONAL_TOOL。
- 优先 MERGE_WITH_EXISTING_OWNER，不发明第二套 store/Reader/simulator/release。
- 新 language/runtime/dependency 在没有真实 owner + measurable need 前统一 DEFER。

## Phase A · Authority / stale-state cleanup

1. 重新 bootstrap PR #90、main base、changed files、workflow、exact Framework authority。
2. PR body / 旧 Plan SHA 只当 historical note。
3. `HARNESS_MANIFEST.yaml` schema ID / contract name 与 live code 同步。
4. 删除“Python 决定 literary repair depth / semantic context obligation”的 stale 声明。
5. Framework version 保持 `0.8.0`；不 release/promote。

## Phase B · Semantic role separation

1. `reader.engagement_audit` 保持 production Blind Reader。
2. `quality.semantic_rule_audit` 独立承担 semantic hard-rule audit。
3. `quality.production_review` 在启用时承担 genuinely independent holistic gate。
4. `editor.repair_spec` 是 semantic repair owner。
5. `quality/repair_policy.py` 只消费 Editor 已选好的 generation mode，并执行对应 writer-information boundary。

## Phase C · Agent-owned search/context

1. `context.select` 决定缺失信息、query、relevance、reformulation、continuation、stopping。
2. `context_inspector.py` 只负责 eligibility/stage/protected-edit mechanics，永不判断 relevance。
3. `context_assembly.py` v2 只验证 exact selected refs、exact higher-authority required refs、source fingerprints、stage safety、private-state boundary。
4. `memory_tiers.py` 可以在硬预算下装载 whole selected blocks，但 priority/top-k 不能变成 literary truth。
5. 删除 deterministic class/purpose obligation = semantic sufficiency 的文档表述。

## Phase D · Planning / simulation / realization

1. `planning_horizon.py` 保留 commitment strength/depth/CAS/fingerprint mechanics。
2. 明确 useful depth / uncertainty 由 Planner 决定，不由 runtime 决定。
3. private character state → action → scene collision 继续由 semantic model 完成。
4. Runtime 只检查 evidence identity、story-time eligibility、permission、visibility。
5. Writer projection 保持 compact，禁止重新膨胀成 Realization Sheet。

## Phase E · Learning

1. Semantic `learning.preference_interpret` 解释 feedback。
2. LearningStore/Author Model 在 CAS + authority 下持久化 evidence/hypothesis。
3. `active` 只表示 eligibility；manager/model 显式选择当前 relevant hypothesis IDs。
4. Promotion Gate 验证 bound semantic review + durable-write prerequisites，不再使用 numeric evidence-count literary threshold。

## Phase F · Ablation / regression coverage

增加/保留以下 blind semantic family：

- recent horizon 之外的 remote context；
- irrelevant similarity match；
- search continuation；
- search stopping；
- agenda-to-dialogue artificiality，Blind Reader 不看 expected HF code；
- legitimate formal completeness；
- inaccessible knowledge + plausible inference；
- dynamic planning profile；
- character embodiment；
- Reader contamination（unprimed vs taxonomy-primed）；
- rule audit（holistic vs decomposed mandatory rules）；
- telemetry anchoring（not preloaded vs preloaded）；
- deterministic unauthorized-state rejection；
- deterministic stale-candidate rejection；
- long-horizon resume / stale checkpoint authority revalidation。

Semantic ablation pair 记录在 `evals/ai_native_ablation_manifest.json`。Pair 必须绑定 same candidate text / same authority；deterministic CI 只验证 packet 构造，semantic outcome 必须由真实 model worker 给出。缺模型能力时保持 `PENDING_MODEL`。

## Phase G · Evaluator freshness

Independent semantic workflow 不能永久 hard-pin 已过时模型。Current primary-source research 已把 OpenAI `gpt-5.6` alias 识别为当前 complex-production baseline，因此 workflow 应从旧 `gpt-5.1` 更新到该 alias。这只是 evaluator infrastructure freshness change，本身不构成 semantic evidence。

未来 model migration 仍执行同样原则：先研究 current official guidance，再在 representative eval 上比较；不能因为某模型流行就自动切换。

## Phase H · Deterministic verification

跑完 candidate-owned focused checks：

- Python compile；
- context inspector / Context Assembly；
- semantic router/catalog/reference integrity；
- repair policy、production readiness/release、telemetry；
- promotion gate / Author Model；
- planning horizon；
- workflow 已拥有的 bundle/version identity 与 deterministic double-build；
- blind queue / hidden-gold guard；
- exact-candidate receipt/fingerprint/independence validation。

不得增加“证明 prose quality”的 Python test。

## Phase I · CI anti-stall / stale optimization

采用 UI completion contract 中对 SYSTEM-IMPROVE 同样有价值的执行纪律，但不引入 UI scope：

- 每次 poll/build/workflow observation 都必须 bounded；
- `WAITING` 不能在没有新 evidence 的情况下持续；
- 同一 workflow 连续两个 observation cycle 仍 pending，就检查 jobs/logs，而不是继续 sleep；
- 每次 consequential write 前重新验证 PR branch、HEAD、base、exact before-state；
- failure 分为 candidate-owned、pre-existing/base、external-capability、transport/configuration；
- 只有 cause 改变后才 retry，禁止无限重复相同失败。

## Phase J · Security / compatibility

确认：

- model 只能在 allowed capability scope 内自己选择 search；
- source text 不能授予 permission 或重定义 authority；
- credential 不进入 semantic context；
- Reader/private-character/manager information boundary 不被破坏；
- semantic result 不能自授 Project/Canon/Framework/user-taste authority；
- stale candidate/receipt/session state fail closed；
- 不修改 downstream lock/manuscript/Canon/Settlement。

## Exact CI classification policy

Pre-existing Product/Godot/Studio failure 仍需报告，但不等于本 candidate 失败；除非它直接阻断 architecture work，否则 SYSTEM-IMPROVE 不顺手修 UI debt。Final HEAD 上 candidate-owned deterministic workflow 必须 green。

Workflow 只是成功记录 `PENDING_MODEL`，说明缺失能力被诚实处理；它不提供 semantic PASS。

## Rollback

- 本 synchronization slice 的 rollback base：`b6f13ac97a105221f8ee78d862c4e6f02e4cf9ab`；
- docs/authority/eval slice 各自形成 reviewable commit；
- 不 force-push / 不 rewrite history；
- downstream consumer 继续 pinned，因此 revert PR #90 不会改变其 live Framework authority。

## Stop condition

正常完成要求所有当前可执行 deterministic/docs/ablation-packet/CI/security/compatibility work 都完成，且 required independent semantic evidence 已绑定 exact final candidate。若 independent model capability 不可用，就完成其他全部工作，最终只以明确 external blocker `PENDING_MODEL` 停止。

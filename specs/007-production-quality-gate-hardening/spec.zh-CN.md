# NovelForge · Production Quality Gate Hardening

## 问题

真实 Project production run 暴露出四个可重复的系统漏洞：

1. Framework migration 后 Project 仍可保留语义已漂移的 HF/RG 编号；编号存在，但代表的机制已经改变。
2. mandatory production semantic gate 可以由 manager 自定义 `eval_judge` rubric 满足，而不是注册的 model contract。
3. 独立 reviewer 容易退化成 checklist verification：局部满足 humor / competence / reversal / hook 等要求，却没有先判断整章因果拓扑和真实阅读体验。
4. scene / character / reader-pressure 等上游失败会被消费成 rejected prose 上的局部 patch，形成 checklist-compliant synthesis。

## 目标

- Framework-owned HF/RG identifiers 成为机器可验证接口。
- production release 的 independent semantic evidence 必须来自注册 contract + exact candidate fingerprint + validated result；ad-hoc eval 不能冒充 release gate。
- 提供 cold Reader Engagement audit 与 fresh independent production review 两个不同语义职责。
- 上游或 cluster failure 能被确定性路由成 fresh realization，并默认隔离 rejected prose / concrete critic patches。
- 兼容普通 blind eval：`eval_judge` 仍然合法，只是不拥有 production release role。

## 非目标

- 不让 deterministic runtime 判断文学质量。
- 不引入 numeric literary score aggregation。
- 不让 semantic result 获得 Canon / Settlement / Framework-write authority。
- 不把某一本小说的正文、角色、Canon 或用户私有 regression 内容复制进 Generic Framework。
- 本 slice 不修改 NovelForge Studio。

## Acceptance

1. `RG-10 SAFE-BUT-FLAT`、`HF-23 SIGNIFICANCE-INFLATION`、stale `RG-01..RG-10` 能被 machine compatibility scanner 拒绝。
2. `production_readiness` 在 independent semantic required 时拒绝没有 registered release contract binding 的 `pass`。
3. caller 不能把 semantic judgment `fail` 改写成 gate `pass`。
4. production contract 必须绑定同一 candidate fingerprint。
5. independent review contract 不能使用 writer reasoning / Scene Card / prior verdict 等 creator-only input。
6. Reader Engagement contract 明确先进行 holistic causal reading，再检查维度，并把 SAFE-BUT-FLAT 作为 blocking mechanism。
7. repair policy 对 story / plan / scene / character / reader ownership 和 Surface cluster 返回 `fresh_realization_required=true`。
8. Generic tests 使用 synthetic fixtures，不导入 consuming Project prose。

# 为什么是 Quillframe？

本页文件名来自旧 public brand，为稳定兼容路径而保留；当前产品名称是 **Quillframe**。

Quillframe 要解决的是长篇创作里一个常被混在一起的矛盾：创意解释必须保持弹性，而 authority 与 execution state 必须保持精确。

## 系统边界本身就是产品能力

确定性脚本不应该判断一段关系是否“有生命”；模型也不应该自行决定 Plan 已经成为 Canon、stale review 仍然有效，或者一次失败写入“大概成功了”。

因此 Quillframe 分开 semantic ownership 与 deterministic ownership。需要理解意义的判断交给模型或人；identity、permission、fingerprint、lifecycle、provenance、transaction 与 reproducibility 交给代码证明。

## 长篇需要 authority，不只是更大的 memory

更大的 context window 并不能回答“哪条信息算权威”。Quillframe 分开 Project truth、current state、plan、review candidate、derived memory、research、Corpus evidence 与 runtime state，再通过 Sparse Context Manifest 只选择当前任务真正需要的内容。

<img src="assets/concepts/authority-ladder.zh-CN.svg" alt="从 locked 到 proposal 的 authority ladder，并明确 Plan 不等于 Canon、Accepted 不等于 Settled" width="100%" />

## Revision 需要 lineage，而不是无限改写

修复可能把局部问题改好，却把章节真正的目标改坏。Quillframe 冻结 objective envelope，用 semantic comparison 比较 incumbent/challenger，记录 repair-induced regression，并分开 comparison ancestry 与 prose ancestry。Fresh regeneration 可以竞争，但不会继承被拒 prose。

## Independence 是 runtime property

Manager 在同一次 invocation 里换一个“reviewer”角色名，不构成 independent review。Gate 要求 independence 时，artifact 必须 freeze + fingerprint，交给真正独立且 eligible 的 invocation/session，再对 exact fingerprint 验证并 consume-once。

## Learning 的 intake 自动，promotion 受治理

用户对既有产物或工作方式给出的 meaningful feedback，可以在任何 primary mode 中进入 bounded learning intake。Automatic 的是 capture，不是 promotion。`one_off`、`project`、`user_taste`、`general_craft` 四个 scope 仍然分开，模型推断不会自动获得 durable write authority。

## 代价与适用边界

Quillframe 有意比一次性 writing assistant 更重。只有当项目足够长，continuity、state、revision provenance、recovery、independent review 与 learning discipline 真正重要时，这些机制才值得。轻量 ideation 或单次改写，简单工具反而可能更合适。

## 兼容性

旧 public name 仍存在于 `novelforge.toml`、`novelforge.lock.json`、schema、workflow 与 repository path 等 technical identifier 中。它们属于 compatibility surface，不是当前 public branding；本次 documentation migration 有意保留这些 ID。

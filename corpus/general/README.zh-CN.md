# 匿名公开通用语料库

这里是 Quillframe 在仓库中发布匿名、无原文写作证据的固定目录。它不是本地小说的镜像，不是作者文风合集，也不承诺“只要做过抽象就一定不存在版权问题”。

## 当前发布状态

[`registry.json`](registry.json) 目前有意保持为空，状态为 `awaiting_first_validated_release`。模式定义和发布能力已经存在，不代表任何作品已经完成研究或公开发布。只有精确 120 部作品的研究完成，并由调用方再次确认预览令牌与清单指纹以后，才会加入随机命名的 `PS-*` 发布目录；该目录及对应登记记录经过审查并提交到 Git 后，才正式成为公开语料库的一部分。

公开登记表由 [`registry.schema.json`](registry.schema.json) 约束；单作品记录与发布清单分别由 [`public_work.schema.json`](public_work.schema.json) 和 [`public_manifest.schema.json`](public_manifest.schema.json) 约束。

行文文风图谱属于另一套更严格的发布家族。[`style_registry.json`](style_registry.json) 同样有意保持为空；对应契约为 [`style_atlas.schema.json`](style_atlas.schema.json)、[`style_atlas_preview.schema.json`](style_atlas_preview.schema.json) 和 [`style_atlas_registry.schema.json`](style_atlas_registry.schema.json)。无来源技法制品只能从精确的 StyleStudyRunner 完成回执构建；预览不授予发布权。真实发布还要求彼此独立、与同一精确制品绑定的来源／权利、语义泄漏、盲测、提升和人工批准可信回执，以及可安全回滚的登记迁移。调用方自报的布尔值和自行计算的哈希不是证据。目前没有任何文风图谱通过这些门槛。

固定的 [`style_publication_trust_policy.json`](style_publication_trust_policy.json) 只记录各签名角色的密钥标识和经过域分离的密钥指纹，不保存密钥。五个角色必须使用不同密钥，发布器也必须与这份相邻策略精确匹配。仓库中的策略目前明确为 `unconfigured`，因此默认公开目录无法执行真实发布。成功发布以后，完整声明、签名和人工确认挑战进入受 [`style_atlas_release_receipt.schema.json`](style_atlas_release_receipt.schema.json) 约束的内容寻址收据；回滚等登记迁移则写入受 [`style_registry_transition_receipt.schema.json`](style_registry_transition_receipt.schema.json) 约束的独立收据。登记表按修订顺序只引用这些事件收据的指纹；每次可信读取都从空登记表重放完整事件链，并重新验证全部签名、基础修订和目标路径。

## 发布包可以包含什么

第一版发布包必须恰好包含 120 条随机 `public_work_id` 记录。允许的内容包括数值派生结果，句子、场景、章节、节奏、对话、视角、张力和感官八个维度的受控特征，跨作品机制、适用边界、反例状态、失败模式，以及完整性指纹。

发布包不得包含来源路径、文件名、书名、创作者、原文、引文、近似复述、可以还原来源的摘要、人物或设定身份，也不得增加任意模式字段。`unresolved` 是合法的证据边界。这里的结果描述的是匿名三窗口样本，不是写作配额，更不能支持模仿特定作者。

如果以后发布文风图谱，它会更小，而且不含逐作品记录。技法卡只允许公开受控行文轴、操作、效果、适用／避免条件、失败边界、`general` 内容区、有界置信表示和完整性指纹。评测与批准回执作为独立治理制品保存，不能塞进 Writer 安全图谱。

## 原文与内容分区

完整小说始终留在用户控制的本地存储中。私有账本可以保留标识、文件位置、指纹和证据链，但不保存小说正文。每部入选作品只绑定一个经确认的版本，并临时读取开篇、中段、收束三个窗口；每个窗口最多 4,000 个 Unicode 字符。

用户确认清单时必须明确选择 `general` 或 `adult_explicit`，Quillframe 不会根据原文自动猜测。一次研究、全部 120 条作品记录及其聚合结果始终属于同一个配置；`adult_explicit` 证据不能混入通用发布，也不能默认进入普通写作任务。

身材、解剖、服饰和外貌描写——包括单独出现的“巨乳”——继续属于普通 `general` 文风证据，本身不能建立露骨内容分类。真实露骨性语境仍然独立治理。

## 许可证与法律边界

本目录中由仓库权利人拥有的派生制品，继承仓库的 [Quillframe 专有源码可见许可证](../../LICENSE)。“公开”只表示它会随公开仓库可见，并不表示采用开放数据许可或允许自由再分发。本目录不会为任何第三方原文重新授权。

是否拥有分析权、派生结果是否适合发布，仍需按具体来源审查。非商业目的和内容抽象都不能替代这项责任；Quillframe 的确定性门只验证声明是否符合仓库政策、输出是否符合封闭模式，不作法律结论。

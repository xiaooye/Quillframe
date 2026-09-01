# AI-native 长篇规划 v2

Quillframe 需要一套能支撑数百万字小说、但不要求作者或模型预先写完全部章节剧本的规划契约。因此，远期计划保持粗粒度，当前剧情单元逐步具体化，只有当前章的可执行场景剧本被冻结。

## 契约

规划顺序为：

1. 故事基础与初版人物弧、关系弧；
2. 全书方向；
3. 分卷承诺与局面净变化；
4. 剧情单元循环；
5. 章节合同；
6. 有序场景剧本；
7. 逐场景正文生产与结算。

故事设计和文学判断仍由模型负责。Rust 只验证类型完整性、身份、顺序、引用、指纹、CAS 与权威边界。

`BookPlan` 拥有类型化 `StoryFoundation`、`CharacterArcPlan` 和 `RelationshipArcPlan`。它们属于生效中的计划资产，不是已结算的人物或关系状态，不得复制进权威 `characters` 或 `relationships` 投影。

`ChapterPlan` 拆分为 `ChapterContract` 与 `SceneScript`。每个场景记录目标、阻力、转折、选择、后果、价值变化、信息变化、进入/退出状态，以及预期情绪和读者效果。它是可执行语义合同，不是预写对白或正文。

## 继承与冻结

沿用现有 Book → Volume → Unit → Chapter 指纹链作为唯一分层计划真相。WriterPack 继续绑定四个精确的生效计划，并从冻结的 `SceneScript` 确定性派生场景 brief；调用方不能在相同场景 ID 和序号下替换不同内容。

生效祖先改变后，后代必须显式重规划并重新激活，才能冻结新的 WriterPack。不增加兼容适配器、双读或状态升级器。

## 状态切换

类型化计划提案升级为 `quillframe_typed_plan_proposal_v2`，分层计划锁升级为 `quillframe_hierarchical_plan_lock_v2`，WriterPack 升级为 `quillframe_writer_pack_v4`。

Project schema fragment 024 记录 `ai-native-longform-v2`。缺少该精确分片的项目数据库在打开时 fail closed，不静默迁移已有项目数据。

## 验收

- Book 计划拒绝缺失的故事基础、重复人物 ID，以及参与者不是两个不同已知人物的关系弧。
- Chapter 计划拒绝不完整章节合同、乱序场景剧本和缺少因果状态变化字段的场景。
- Plan 与 WriterPack 指纹覆盖全部新增字段。
- WriterPack 场景 brief 只能由冻结章节剧本派生，并拒绝替换内容。
- Rust 生产测试在不调用真实模型 Provider 的前提下跑通分层计划激活、逐场景生成、审查、接受与结算。


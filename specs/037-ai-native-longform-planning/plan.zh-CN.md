# 实施计划

1. 在类型化 Book 规划中加入故事基础、人物弧和关系弧，同时确保这些计划资产不进入已结算故事状态表。
2. 把章节 payload 拆成章节合同与场景剧本，并为每个场景加入因果状态变化字段。
3. 硬切换 Plan 与 WriterPack 精确 schema，并登记 Project schema fragment 024 作为 fail-closed 状态标记。
4. 从冻结场景剧本确定性派生 WriterPack 场景 brief，继续以现有四层指纹继承为唯一来源。
5. 更新 Bridge fixture 与 Studio 计划序列化器，使其只发送新的精确 payload。
6. 增加确定性结构、指纹、重启和端到端生产测试；在不调用真实模型的前提下运行 Rust workspace 质量门禁。


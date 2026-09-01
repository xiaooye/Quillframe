# 网文 Corpus 分析架构实施计划

2026-08-31 · `SYSTEM-IMPROVE`

## 阶段 1 · 冻结后继契约

建立六域层级、v2 观察/候选/编译/Writer 投影 schema 和协议指纹。让旧 v1 输入在新入口明确失败，并保留 V5 历史证据不变。

## 阶段 2 · 改造研究运行

把逐轴批处理改为按需维度激活。采样器只返回有界候选窗口；模型负责章节功能、叙事跨度、情绪阶段和证据缺口判断。新运行使用独立的维度状态与回执，不迁移旧表。

## 阶段 3 · 改造语义契约

用 `corpus.webnovel_observe`、单作品综合、维度综合、维度协调和留出验证替换五个旧 style contract。同步本地模型适配器和契约目录。

## 阶段 4 · 收紧生产投影

公共 atlas 与生产加载器使用 `domain + dimension` 卡片。语义选择器每次选择一到四张中文、场景相关的机制卡；Reader 与 reviewer 保持盲态。

## 阶段 5 · 重建评测与证据

重新生成合成 fixture 和 v2 候选。执行跨作品/反例、holdout、leave-one-work-out、泄漏、三臂盲测和顺序交换。旧 V5 评测不得复用。

## 阶段 6 · 同步文档与发布边界

更新 Manifest、Corpus policy、ingest protocol、README、自适应学习文档、发布 schema 和 changelog。运行文档 QA、定向测试和相关确定性 CI，并把真实文学验证的未完成项明确留在 verification。

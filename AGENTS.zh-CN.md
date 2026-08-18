# AGENTS · Quillframe 仓库 Agent 指南

## 适用范围

本文件约束 **Generic Quillframe Framework Repo** 内的 coding / agent 工作。

任何下游小说项目的人物、剧情、正典、仓库路径或用户私有偏好数据都不能进入这里。

## 启动流程

1. 读取 `HARNESS_MANIFEST.yaml`；
2. 读取 `SKILL.zh-CN.md`；
3. 读取 `harness/HARNESS_AGENT.zh-CN.md`；
4. 确定且只确定一个 primary `task_mode`；
5. 结构级 Framework 变更读取 `harness/SELF_IMPROVEMENT_PROTOCOL.zh-CN.md`；
6. 项目工程化工作读取 `docs/project-sdk.zh-CN.md`；
7. 学习 / 语料工作读取 `docs/adaptive-learning.zh-CN.md` 与 Corpus policy；
8. **只要任务涉及 README、人类可读文档、图表、竞品比较、文档信息架构或视觉体系，编辑前必须读取并遵守 `docs/DOCUMENTATION_STANDARD.zh-CN.md`、`docs/DOCUMENTATION_QA.zh-CN.md` 与 `assets/DESIGN_SYSTEM.zh-CN.md`。**

## 工程规则

- **用户已授权的日常维护默认直接修改 `main`。不要因为任务较大就习惯性新建 branch。** 只有用户明确要求、仓库保护规则强制、改动确实需要隔离审查 / 迁移、多贡献者需要协调边界，或外部流程必须依赖 PR 时，才使用 branch / PR。
- **Branch budget：** 除 `main` 外，正常 active working set 尽量保持为 **最多 1 条 general / agent branch + 最多 1 条 UI / product / visual branch**。适合直接修改 `main` 时，0 条 working branch 更优。这个约束是 repo hygiene 目标，不得用来绕过确实需要的隔离或审查。
- 新建任何 branch 前，先检查当前 branches 与 open PRs。若同类别已有 scope 兼容的 working branch，应继续复用；不要按 task、coding agent、chat / session 一项一条 branch。
- 新 coding-agent / session 默认应继续使用 `main` 或当前同类别 working branch。如果确有不兼容工作需要新 branch，而该类别已有 working branch，先 merge / close / delete 或明确 supersede 旧 branch。只有用户明确批准例外，或外部 workflow 确实要求并行 branch 时，才允许同类别临时并行。
- Branch 是工作状态，不是档案库。历史上下文应保存在 commits、merged / closed PR、issues、release artifacts 或 tags 中；有效工作已保留后，应删除 stale / superseded branch ref。
- 如果可能存在其他 session / contributor 并行工作，重要写入前先读取最新 `main`，确认目标路径没有发生冲突，并保留所有无关并行修改。
- 特殊情况下创建的临时 branch，完成后应及时 merge / close 并删除，不长期堆积。
- Generic Framework 与下游项目永远单向依赖：Project → Framework；
- Framework 的 code / test / doc 不得引入 project-specific import 或默认值；
- Normal CI 不得静默消耗 API / Codex / Claude / model usage；
- 实质行为变更必须有 mechanism evidence、tests / evals、version / rollback 与 green CI；
- Identity、state、schema、fingerprint、permission、idempotency、算术和 release invariant 优先由确定性代码负责；
- 只有真正需要语义判断时才使用 independent semantic worker；
- Runtime state、learning state、project Canon 必须分域持久化；
- 不得提交 credential、本地 runtime / learning DB、private chat 或 chain-of-thought。

## 文档规则

仓库级人类可读文档标准是 `docs/DOCUMENTATION_STANDARD.zh-CN.md`；视觉唯一规范是 `assets/DESIGN_SYSTEM.zh-CN.md` 与 `assets/brand/tokens.json`；强制作者自检门槛是 `docs/DOCUMENTATION_QA.zh-CN.md`。

必须遵守以下摘要：

- 文档是产品表面，不是源码目录的装饰。
- 根 Landing 页必须快速回答：Quillframe 是什么、为什么不同、如何工作、为什么 QA 可信、有哪些真实取舍、如何开始。
- A 级 Landing 页的核心产品概念必须使用统一的 Story Loom 展示模块。**不能**用原始 `A → B → C` 箭头串、默认占位 Mermaid、低信息密度卡片堆，或本应高密度比较却直接放巨型原生 Markdown 表，来承担系统架构、章节生产流水线、QA 栈或主要竞品比较。
- **SVG 生成成功不等于资产通过。** 新建或实质修改的 A 级视觉必须先通过确定性文档检查，再实际渲染并在真实 GitHub 阅读宽度下检查；文案必须脱离视觉单独审一遍；双语资产还要做语义对齐。如果当前环境无法看到真实 render，就保持 WIP，不能接入 A 级页面。
- 不得用“继续缩小字体直到塞进去”的方式解决 overflow；应删减 / 重构文案或修复布局。
- 面向用户的文档工作完成前运行 `python scripts/docs_quality.py`。普通 CI 运行同一套确定性 checker，但不得调用模型 API。
- 首页主要竞品类别是**直接小说智能体 / 小说框架**。通用 Agent runtime 放到实现思想 / 技术采用文档；作者 SaaS / 编辑器类产品在产品类别确实不同的情况下单独讨论。
- 竞品比较描述可验证机制，不使用星级或营销分数。会随时间变化的竞品能力，在做实质性修改前必须重新核实当前资料。
- 英文与简体中文是两套**原生专业表达、语义等价的权威版本**，不是逐句翻译。中文正文与中文图表优先使用自然中文术语，只保留真正需要精确匹配的 identifier / 产品名；英文必须读起来像专业技术英语原文。
- 面向用户的文档必须诚实说明局限和成本，不能把 Quillframe 写成在所有场景都更优。
- A 级页面优先使用品牌化 SVG / UI 模块作为展示层；Mermaid 继续作为可检查、可差异比较的技术源图 / 参考层。
- 静态视觉资产必须原创或有明确授权 / 来源记录，必须有可访问性处理，并由附近文字或参考文档提供语义支撑。
- Story Loom 的目标约为 `70% 专业技术感 / 30% 二次元编辑感`；emoji 可以增加温度，但不能替代结构、状态或导航语义。
- “看起来干净”不等于完成。信息密度、层级、双语原生质量、准确性、权威边界、链接、可访问性、诚实定位和 render QA 都必须通过。

Human-facing authoritative docs 必须成对发布 `.en.md / .zh-CN.md`。只有外部工具要求固定路径时，才允许保留精简的双语 router。

Machine schema 保持单份 JSON / YAML / TOML-compatible contract，其人类说明必须双语。

## Project SDK 原则

每一本小说 project 都是完整 engineering artifact：manifest、lockfile、authority / state、plans、manuscripts、research、tests / evals、build bundle、migration、rollback history 都应存在。

Generic Framework 不得 hard-code 某个 legacy project 的目录；旧结构通过 adapter / migration 兼容。

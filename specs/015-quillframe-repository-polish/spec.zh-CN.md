# 规格说明 · Quillframe Repository Polish

状态：实施候选
Primary mode：`SYSTEM-IMPROVE`
冻结起点 `main`：`e49304bde7fb0c5ba0822deb3823f960c6425804`

## 问题 / 背景

仓库已经有较完整的 Quillframe 0.9 Framework 与产品表面，但 GitHub 第一入口仍像内部工程目录：根 README 只是语言跳转；缺少贡献、安全与社区入口；GitHub Description / Homepage / Topics 为空；Starlight 首页仍暴露当前语境下的 NovelForge 文案和已退役 Studio 域名。

## 当前状态审计

- 当前产品名：Quillframe；技术命名空间：`quillframe`；版本：`0.9.0`。
- 当前运行事实以 `HARNESS_MANIFEST.yaml`、`SKILL*`、`harness/HARNESS_AGENT*`、实现、测试与冻结 `main` 为准。
- Canon、Context、Learning、独立语义评审、Settlement 均有明确权威边界。
- `persistence/quillframe_sqlite.py` 中 SQLite 是 canonical durable state。
- 冻结基线中的 Studio 是 SolidJS + TypeScript + Vite，通过 Python Host Bridge / local server 消费 Core；Tauri 2 是桌面宿主方向，不应被写成已经发布的 wrapper。
- Model Runtime 工作仍在 Draft PR #108，不能冒充已合并能力。
- UI/UX 工作位于 `ui/homepage-product-language-unification`，不得覆盖其实现 ownership。
- 当前 `LICENSE` 是 proprietary source-available，并明确声明不是 OSI open source；除非单独作出 relicensing 决策，公共文案必须如实说明。

## 用户 / 编辑价值

第一次访问者应在 30 秒知道 Quillframe 是什么，5 分钟理解它的 authority/runtime 模型，10 分钟找到真实 setup 路径，并且无需先读内部契约就知道如何参与贡献。

## Requirements

1. 把 `README.md` 重构为完整 GitHub 产品 landing，并同步英文与自然中文版本。
2. 用 GitHub-native 方法表达 Borderless Kawaii Editorial：留白、克制符号、真实品牌资产、小型状态标签、图解和渐进披露。
3. 解释长篇小说为何需要显式 Canon、Context、持久状态、独立语义判断、受治理 Learning 与 Settlement，而不是单一 prompt → model → text。
4. 解释产品 architecture，不把 Model API 放在 authority chain 顶端。
5. 明确区分已实现、开发中、规划中。
6. Quick Start 只写冻结基线真实存在的命令。
7. 增加简洁 CONTRIBUTING / SECURITY / Conduct / Issue / PR 入口，并与当前 license 和 authority model 一致。
8. 修复当前公开文档入口的 NovelForge 残留与死亡域名，不改写历史记录或法律文本。
9. 不修改 Core、Agent Runtime、Model Runtime、SQLite schema、Studio behavior 或 CSS。
10. 只创建 Draft PR，不 merge。

## Non-goals

- Runtime/schema migration。
- Agent / Model Service 实现。
- Studio component/CSS redesign。
- 仓库 relicensing。
- 对历史 `NovelForge` 做全局替换。
- 把 Draft PR 或规划中的 Tauri 包装写成 released。

## Authority / Canon 影响

无。文档与 GitHub 展示不会产生 Canon、Accepted、Settlement、Learning promotion 或 Framework write authority。

## 兼容性约束

- `Quillframe` 是当前产品身份；`quillframe` 是当前技术命名空间。
- `0.9.x` 仍为 pre-1.0，1.0 前可能发生 breaking change。
- 历史 specs 与当前法律 license 在改动会破坏 provenance/legal meaning 时保留原始命名。
- Public URLs 必须与当前部署 workflow 一致，并在工具允许时重新验证。

## 验收场景

- 陌生访问者能回答：Quillframe 是什么、Framework/Model/Project 各自拥有什么、状态如何持久化、如何运行当前表面、如何贡献。
- README 不把 PR #108 的 Model Runtime 写成已合并。
- README 不宣称冻结基线已经发布 Tauri wrapper。
- README 不把当前 license 称为 open source。
- 当前 Starlight 导航不再出现 active NovelForge branding 或退役 Studio URL。
- CI/docs build/link 检查通过；无法直接证明的视觉 QA 必须明确报告限制。

## 风险

- 并行 UI/UX / Agent branch 可能在本任务完成前 merge，因此 review 前必须 late truth reconciliation。
- Studio 正在快速变化，README 固定截图容易过期；优先使用稳定品牌/架构资产。
- 没有真实 GitHub rendered evidence 时，不得宣布 light/dark visual PASS。

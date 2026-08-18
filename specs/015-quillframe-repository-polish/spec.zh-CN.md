# 规格说明 · Quillframe Repository Polish

状态：实施与验证候选
Primary mode：`SYSTEM-IMPROVE`
冻结起点 `main`：`e49304bde7fb0c5ba0822deb3823f960c6425804`

## 问题 / 背景

Quillframe 0.9 已经具备较完整的框架、产品网站、Studio 与文档体系，但 GitHub 仓库本身仍需要从“内部源码目录”升级成一致的产品入口。同时，公开页面也应让当前 AI discovery 系统容易理解，但不能因此发明 Quillframe 实际并未提供的协议、服务或 authority。

## 已对齐的实现事实

- 当前产品身份：**Quillframe**；技术命名空间：`quillframe`；版本线：`0.9.x`。
- PR #108 的 Agent/Model Runtime 已合并：普通模型设置只有 `API Endpoint + Access Token`；模型发现、能力证据、模型选择、工具、session/checkpoint、authority 与 agent loop 都由 Quillframe 自己负责。
- PR #109 的产品语言/UI 工作以及后续一致性与布局修复已经合并；本任务只做 reconciliation，不重复实现或覆盖。
- SQLite 仍是 canonical durable product state。
- 当前 Web/Studio 技术栈是 SolidJS + TypeScript + Vite；Tauri 2 仍是 thin desktop host 方向，不应写成已发布 wrapper。
- 仓库仍是 proprietary source-available，不是 OSI open source。法律文件中的产品名现在统一为 Quillframe；许可范围和限制没有改变。

## 用户 / 编辑价值

第一次访问者应该在几秒内知道 Quillframe 属于什么产品类别、核心差异是什么，快速找到真实可执行的 setup 路径，并理解长篇创作为什么需要显式状态和权威边界，而不必先通读整套 Framework。

## Requirements

1. 将 `README.md` 做成完整产品 landing，并保持英文与自然中文版本同步。
2. 参考当前高 star GitHub 项目的有效模式：第一屏讲清类别、记得住的产品陈述、靠前的 Quick Start、单一清晰心智模型、渐进展开、明确 status/security/license，避免 inventory-first 信息墙。
3. 用 GitHub-native 方式表达 Borderless Kawaii Editorial：留白、克制符号、真实 badges、稳定品牌资产、light/dark 自适应图解，不做 dashboard/card soup。
4. 清楚解释 Canon、受限 Context、人物/关系状态、独立语义评审、Learning 治理、SQLite persistence 与 Settlement，同时不把 Model API/provider identity 放到 authority chain 顶端。
5. 如实说明已合并的 Model Runtime 与 Agent Runtime，并把双语 runtime docs 注册进 documentation governance/Starlight。
6. 让 `python scripts/docs_quality.py` 成为可独立执行的确定性 gate，并在 normal CI 中执行，且不消耗模型/API。
7. 完整维护 CONTRIBUTING / SECURITY / Conduct / Issue / PR 入口，并与当前 authority model 和 source-available license 一致。
8. 增加受边界约束的 AI-readable discovery surface：`robots.txt`、XML + Markdown sitemap、`llms.txt`、完整 machine guide、discovery catalog、Agent Skills index 与 content-use signal；不得虚构 MCP/A2A/OAuth/API 服务。
9. 将 `LICENSE` 的法律产品标识从 NovelForge 改为 Quillframe，但不修改实质性许可范围和限制。
10. 在工具允许时产出真实 GitHub-rendered README 的 light/dark/narrow QA 证据；不得拿本地 Markdown mock 冒充 GitHub render。
11. 每次 consequential write 前重新确认并行 `main` 变化，只 reconcile 已 merge 的事实。
12. 全部工作保留在 Draft PR #110，本 session 不 merge。

## Non-goals

- Runtime、Canon、Settlement、Learning 或 SQLite 行为修改。
- Provider gateway 或把第三方 agent product 变成 Quillframe authority。
- 改成 OSI license。
- 为了统一名称而破坏历史 provenance。
- 伪造 repository metadata 写入、公开 API、agent protocol 或 visual QA 证据。

## Authority / Canon 影响

无。Repository presentation、AI discovery metadata、文档注册与 QA tooling 都不会产生 Canon、Accepted、Settlement、Project-write、Learning promotion 或 Framework-write authority。

## 兼容性约束

- 历史记录保留历史语义；current-facing guidance 使用 Quillframe。
- Pre-1.0 下游项目按 project lock 固定 exact Framework revision/bundle。
- Model token 是 host secret，不进入 prompt、Context、SQLite、receipt、fingerprint 或 client bundle。
- Public AI discovery 只是 metadata；允许抓取不等于扩大 license 权利。

## 验收场景

- README 能回答 Quillframe 是什么、各层 ownership、模型负责什么、truth/state 在哪里、如何开始、哪些仍属于 pre-1.0。
- 英文/中文 README 图解在 GitHub light/dark 下可读，narrow width 不出现横向溢出。
- Model/Agent Runtime docs 已注册，并能通过 Starlight 导航访问。
- `python scripts/docs_quality.py` 在 normal CI 中真正执行，并能阻断确定性文档缺陷。
- AI discovery 文件内部一致，并明确否认不支持的 authority/service。
- LICENSE 使用 Quillframe 名称，同时保留既有法律条款。
- Repository Description/Homepage/Topics 只有在 connected action 真正支持时才写；否则把精确目标值报告为外部设置步骤。
- 最终 PR 保持 Draft，并与当前 `main` 对齐。

## 风险

- 并行 session 仍可能推动 `main`，final review 前必须 late reconciliation。
- 新增 GitHub Actions visual-QA workflow 在进入 default branch 前可能受 GitHub event/security 语义限制；这只能报告成 tooling boundary，不能伪造 PASS。
- AI crawler/content-signal 规范仍在演进；discovery 文件应保持窄职责，并服从 license/security contract。

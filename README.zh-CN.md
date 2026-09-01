<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/quillframe-mark-dark.svg" />
    <img src="assets/brand/quillframe-mark.svg" width="104" alt="Quillframe 标志" />
  </picture>
</p>

<h1 align="center">Quillframe</h1>

<p align="center"><strong>面向长篇小说的 AI-native 创作框架与写作环境。</strong></p>
<p align="center">让故事持续生长，同时始终分清什么是真的、模型看到了什么、什么发生了变化，以及谁有权让变化真正写入状态。</p>

<p align="center">
  <a href="https://quillframe.wei-dev.com/">产品网站</a> ·
  <a href="https://studio.quillframe.wei-dev.com/">Studio</a> ·
  <a href="https://quillframe.wei-dev.com/docs/">文档</a> ·
  <a href="docs/why-quillframe.zh-CN.md">为什么是 Quillframe</a> ·
  <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/xiaooye/Quillframe/actions/workflows/quillframe-ci.yml"><img alt="Quillframe CI" src="https://github.com/xiaooye/Quillframe/actions/workflows/quillframe-ci.yml/badge.svg?branch=main" /></a>
  <img alt="Version 1.0.0-dev.0" src="https://img.shields.io/badge/version-1.0.0--dev.0-796BC4" />
  <a href="SECURITY.md"><img alt="Token 仅驻留于 Host" src="https://img.shields.io/badge/security-tokens%20stay%20host--local-4D9B7D" /></a>
  <a href="LICENSE"><img alt="Quillframe source-available license" src="https://img.shields.io/badge/license-source--available-C985A4" /></a>
</p>

<p align="center"><sub>1.0.0-dev.0 · 验收进行中 · 持续开发</sub></p>

<img src="assets/brand/story-thread.svg" width="100%" alt="Quillframe story thread divider" />

> [!IMPORTANT]
> **宿主运行 Agent，Quillframe 管理小说。** Codex、Claude Code、Cursor 或其他已声明的宿主负责通用 session、model → tool → model 循环、sandbox 与 subagent 生命周期。Quillframe 负责小说契约：Project 解析、Story / Character / Relationship / Canon 边界、受限 Context、candidate 生命周期、质量门槛、独立评审、可见性，以及 Acceptance / Settlement。内置 runtime 仍保留为 Studio、本地 adapter 与确定性测试使用的 optional/reference implementation。
>
> **Token 只在 Host 侧短暂存在。** 解析后的 Access Token 是瞬态 Host Secret。Quillframe 不会把它写入仓库文件、SQLite、prompt、Context、AgentJob / AgentResult、checkpoint、receipt、fingerprint、日志或客户端 bundle；Host 只会在向你配置的模型 endpoint 发起认证时临时使用该凭据。

## 快速开始

**环境要求：** Python 3.11+。只有 Web / Studio surface 需要 Node.js 24 与 pnpm 10.33.0。

从干净的 Quillframe 源码工作区安装框架，并检查本地运行环境：

```bash
git clone https://github.com/xiaooye/Quillframe.git
cd Quillframe
python -m pip install -e .
quillframe doctor
```

在通用 Framework 仓库**之外**创建小说 Project，并用唯一的 native 命令打开 local-first Studio：

```bash
quillframe launch ../my-novel \
  --new \
  --id MY-NOVEL \
  --title "My Novel" \
  --language zh-CN
```

该命令为整部小说创建精确的原生四键 manifest（`schema`、`id`、`title`、`language`），在项目上下文顶层输出 `scope: "novel"`，并创建初始章节 `CH001` 和正文文档 `DOC-CH001`。运行状态保存在 `.quillframe/data`，Studio 仅绑定本机回环地址。已有项目可用 `quillframe launch ../my-novel` 重新打开；打开时不会自动迁移、修复或补建旧开发状态。如果同时使用 Claude Code 或其他编程代理，请从项目目录启动该宿主；Quillframe 的正确性不依赖仓库 hook 或宿主专用配置。宿主运行 Agent，小说与正典权威仍归 Quillframe。

基础写作与检查 shell 不需要先连接模型。真正需要 inference 时，普通设置刻意只保留两个输入：

```text
API Endpoint
Access Token
```

无认证的本地模型服务可以留空 Token。Provider / vendor identity 只用于诊断 provenance，不会成为 runtime authority。

<details>
<summary><strong>在本地运行 Studio</strong></summary>

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @quillframe/studio-app build
quillframe launch ../my-novel
```

</details>

## 为什么是 Quillframe

一次性的 AI 写作助手可以近似成 **提示 → 模型 → 文本**。一部长篇小说不能。写到几十、几百个场景以后，真正困难的是持续维护故事事实、人物连续性、受限上下文、评审 provenance、持久状态与明确写入权。

| 长篇写作常见失效 | Quillframe 的机制 |
| --- | --- |
| 事实、计划和草稿混在一起 | **Canon + Settlement** 把故事事实与经过授权的状态变更分开 |
| Prompt 逐渐变成巨大记忆倾倒 | **Context** 稀疏且按任务注入：stored ≠ injected |
| 人物逐渐扁平，忘记自己的目标与后果 | **Story + Character + Relationship** 保留因果状态和知识边界 |
| Manager 自己换个身份评自己，却叫“独立评审” | **Quality** 要求真正独立的语义判断绑定 exact candidate fingerprint |
| Agent 状态只活在聊天记录里 | **Runtime + SQLite** 显式保存 Session、Run、Checkpoint、receipt 与 durable state |
| 一条反馈悄悄永久改变系统 | **Learning** 自动接收证据，但不会自动晋升为永久规则 |

Quillframe 的通用系统覆盖 **Story · Character · Relationship · Canon · Context · Runtime · Quality · Learning · Settlement**。具体小说 Project 拥有自己的人物、剧情、正文、研究、计划、Accepted Canon 与当前故事状态；依赖方向始终是 **Project → Quillframe**。

## 系统怎样拼在一起

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/architecture/framework-mental-model.zh-CN.dark.svg" />
  <img src="docs/assets/architecture/framework-mental-model.zh-CN.svg" alt="Quillframe 框架心智模型" width="100%" />
</picture>

边界是刻意设计的：

- **模型负责小说语义判断。** 故事、人物、读者体验、相关性与修复方式由模型判断。
- **Quillframe 负责执行事实。** 确定性代码负责身份、权限、fingerprint、routing、hard budget、transaction、persistence 与 reproducibility。
- **独立就必须真的独立。** 需要独立语义判断时，结果必须来自真正不同的 invocation / session / worker，并绑定 exact artifact fingerprint；Manager 自己角色扮演不算。
- **SQLite 是 canonical durable state，不是 fallback cache。** UI 边界是 `Solid/Tauri → typed Bridge/API → Python Core → SQLite`。

当前 Model Runtime 在 authority 层保持 provider-neutral。宿主负责通用模型与工具执行；Quillframe 在自己的边界内校验小说契约、能力证据、eligibility、checkpoint、receipt 与 exact artifact binding。Model API 只是 inference capability，不拥有故事或 Settlement authority。

继续阅读：[架构](docs/architecture.zh-CN.md) · [Model Runtime](docs/model-runtime.zh-CN.md) · [Agent Runtime](docs/agent-runtime.zh-CN.md) · [Context 与 Memory](docs/context-and-memory.zh-CN.md)

## 正文生产是一条生命周期，不是一次生成调用

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/architecture/production-graph.zh-CN.dark.svg" />
  <img src="docs/assets/architecture/production-graph.zh-CN.svg" alt="Quillframe 长篇小说生产生命周期" width="100%" />
</picture>

DRAFT / REVISE 会经过受限 Context、Story / Canon 预检、人物私有行动推演与场景解析、Scene Realization Contract 和模型组合的 Writer 上下文、Reader Pressure、单次 direct Surface Writer、候选指纹冻结、Reader Engagement、连续性、逐项目标资格门、必要时的修订比较、独立评审与用户可见门槛。

**直接生成的候选在发布前仍是内部产物。Review 不等于 Accepted；Accepted 不等于 Settled。**

`stored ≠ injected` · `Plan ≠ Canon` · `Review ≠ Accepted` · `Accepted ≠ Settled` · `autosave ≠ Accepted` · `revision ≠ Canon` · `Corpus ≠ Canon` · `persistence ≠ authority`

Settlement 是把经过明确授权和接受的变更真正写入 durable Project state 的事务。Before-state 不匹配或 post-condition 失败时，结果是 `settlement_incomplete`，而不是猜测成功。

## Studio · 作者优先

Quillframe Studio 首先是创作环境，而不是 Framework dashboard。日常写作 surface 保持优先；Runtime 与 control-plane 细节按需渐进展开。

**当前技术栈：**

- Frontend / Studio — **SolidJS + TypeScript + Vite**
- Core — **Python**
- Persistence — **SQLite-native**，包含 WAL、foreign keys、native schema fragment、backup / restore 与 integrity checks
- Documentation — **Astro + Starlight**
- Desktop —— 基于 Host Bridge v11 的 **Tauri 2 thin host**；packaged OS/runtime 验收保持显式

可以直接进入在线 [Studio](https://studio.quillframe.wei-dev.com/)，或阅读 [Studio 架构](studio/README.zh-CN.md)。

## 从哪里继续

| 目标 | 入口 |
| --- | --- |
| 了解产品适合什么场景 | [为什么是 Quillframe](docs/why-quillframe.zh-CN.md) |
| 理解 ownership 与 authority | [架构](docs/architecture.zh-CN.md) |
| 跟踪 DRAFT / REVISE 执行 | [正文生产流程](docs/production-pipeline.zh-CN.md) |
| 理解 fingerprint-bound review | [质量保障](docs/quality-assurance.zh-CN.md) |
| 连接 inference endpoint | [Model Runtime](docs/model-runtime.zh-CN.md) |
| 使用 agent loop 与 tools | [Agent Runtime](docs/agent-runtime.zh-CN.md) · [运行时与集成](docs/integrations.zh-CN.md) |
| 接入小说 Project | [Native Project Contract](docs/project-contract.zh-CN.md) |
| 查看系统 ownership | [架构图谱](docs/architecture-atlas.zh-CN.md) |
| 读取面向机器的产品 Context | [`llms.txt`](site/public/llms.txt) · [`llms-full.txt`](site/public/llms-full.txt) |

## 开发

<details>
<summary><strong>验证命令</strong></summary>

```bash
python scripts/docs_quality.py
python -m unittest discover -s tests -p 'test_quillframe_*.py' -v
corepack pnpm install --frozen-lockfile
corepack pnpm run quality
corepack pnpm run typecheck
corepack pnpm run test
corepack pnpm run build
```

</details>

参见 [贡献指南](CONTRIBUTING.md)、[路线图](ROADMAP.md)、[安全策略](SECURITY.md)、[行为准则](CODE_OF_CONDUCT.md) 与 [变更记录](CHANGELOG.zh-CN.md)。

## 当前状态

Quillframe 正处于 **1.0 预发布持续开发阶段**。当前 `main` 已包含 embeddable Python façade、Model Runtime、Agent Runtime、小说 Core / authority contract、SQLite persistence、typed Host Bridge、SolidJS Studio、产品网站、publication pipeline 与 Starlight 文档。Normal CI 使用确定性执行，不会悄悄调用配置好的付费 / 在线 Model API。

小说项目通过原生四键 `quillframe.toml`、顶层含 `scope: "novel"` 的上下文、manifest fingerprint 与 `.quillframe/data` 边界标识自身。`CH001` 是初始章节，后续章节沿用同一契约，并验证真实章节关系。Framework commit / bundle provenance 由宿主或发布流程独立记录，不是项目权威或项目锁定契约。这份开发契约不代表整本小说的真实模型运行或云端发布已经验收通过。

## Security 与 License

解析后的 Access Token 是瞬态 Host Secret。Quillframe 不会把它写入仓库文件、SQLite、prompt、Context、AgentJob / AgentResult、checkpoint、receipt、fingerprint、日志或客户端 bundle。也不要把 Token、私有正文或 Project database 粘贴到公开 issue。参见 [SECURITY.md](SECURITY.md)。

Quillframe 使用 **Quillframe Proprietary Source-Available License**。仓库公开且 source-available，但该许可证**不是** OSI open-source license，并限制未经单独书面许可的再分发、部署与商业使用。准确条款以 [LICENSE](LICENSE) 为准。

---

<p align="center"><sub>✦ 创作判断保持灵活，执行事实保持明确。♡</sub></p>

<p align="center">
  <img src="assets/brand/quillframe-mark.svg" width="96" alt="Quillframe 标志" />
</p>

<h1 align="center">Quillframe</h1>

<p align="center"><strong>让故事越写越长，让系统始终知道自己在做什么。</strong></p>
<p align="center">面向长篇小说的 AI-native 创作框架与写作环境：显式 Canon、受限 Context、Quillframe 自己的 Agent Runtime，以及 SQLite-native 持久状态。</p>

<p align="center">
  <a href="https://quillframe.wei-dev.com/">产品网站</a> ·
  <a href="https://studio.quillframe.wei-dev.com/">Studio</a> ·
  <a href="https://quillframe.wei-dev.com/docs/">文档</a> ·
  <a href="#快速开始">快速开始</a>
</p>

<p align="center">
  <a href="https://github.com/xiaooye/cn_webnovel_agent/actions/workflows/quillframe-ci.yml"><img alt="Quillframe 0.9 CI" src="https://github.com/xiaooye/cn_webnovel_agent/actions/workflows/quillframe-ci.yml/badge.svg?branch=main" /></a>
  <img alt="Version 0.9.0" src="https://img.shields.io/badge/version-0.9.0-796BC4" />
  <a href="LICENSE"><img alt="Quillframe source-available license" src="https://img.shields.io/badge/license-source--available-C985A4" /></a>
</p>

<p align="center"><sub>0.9.x · pre-1.0 · 持续开发中</sub></p>
<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

---

> **Agent 由 Quillframe 自己运行，模型 endpoint 只提供 inference。** 用户只需要给出 API endpoint 和 access token；Context、tools、sessions、checkpoints、质量门槛、authority 与持久状态仍由 Quillframe 掌握。

## 快速开始

**环境要求：** Python 3.11+；Web surface 使用 Node.js 24；`studio/app` 使用 pnpm 10.33.0。

```bash
git clone https://github.com/xiaooye/cn_webnovel_agent.git
cd cn_webnovel_agent
python -m pip install -e .

python project_sdk.py self-test
python persistence/cli.py doctor
python studio/host_bridge.py self-test
```

运行本地 Studio：

```bash
cd studio/app
corepack enable
pnpm install --frozen-lockfile
pnpm build
cd ../..
python studio/local_server.py
```

基本写作/检查 shell 不需要先配置模型。真正需要 inference 时，普通模型设置刻意只保留两个输入：

```text
API Endpoint
Access Token
```

无认证的本地模型服务可以留空 token。模型/协议发现、能力证据、合格模型选择，以及 model → tool → model loop 都由 Quillframe 自己执行；provider 名称只是 provenance，不是 runtime authority。

> Quillframe 仍处于 pre-1.0。下游小说项目应按自己的 project lock 固定 exact Framework revision / bundle，不要默认最新 `main` 一定兼容。

## 为什么需要 Quillframe

一次性的 AI 写作助手可以简化成 **提示 → 模型 → 文本**。长篇小说不行。写过几十、几百个场景之后，真正难的是状态与权威：

- 哪些事实已经是 Canon，哪些还只是计划、proposal、research 或 review note？
- 这一次模型调用到底真正看到了什么？
- 每个角色现在知道什么、想要什么、记得什么，又还背着哪些前文后果？
- 当前 review 评的是这一版候选稿，还是上一版？
- 作者接受修改后，项目状态是否真的完整写到了正确位置？

Quillframe 不靠聊天历史去反推这些答案，而是把它们做成显式系统契约。

**实际效果是：** 需要判断力的地方交给模型；身份、权限、fingerprint、持久化与写入边界交给确定性代码。

## 产品心智模型

<img src="docs/assets/architecture/framework-mental-model.zh-CN.svg" alt="Quillframe 框架心智模型：项目权威、语义执行与验证、经过授权的 Settlement" width="100%" />

Quillframe 把普通 AI 写作流程经常混在一起的四类“事实”拆开：

- **故事事实** —— Story、Character、Relationship、Canon、时间线、计划、研究与当前叙事状态。
- **上下文事实** —— 项目保存的内容大于单次调用真正注入的内容；稀疏 Context Manifest 为每次操作划清边界。
- **执行事实** —— Session、Run、Checkpoint、tool receipt、candidate fingerprint 与 semantic result provenance 都有明确身份。
- **权威事实** —— 生成、review、persistence、acceptance 与 Settlement 是不同操作，也拥有不同权限。

具体 Project 拥有自己的人物、剧情、正文、研究、计划、Accepted Canon 与当前状态；Quillframe 只拥有通用机制。依赖方向始终是 **Project → Quillframe**。

## Model Runtime + Agent Runtime

Quillframe 不会把 Codex、Claude Code、OpenCode 或其他 provider-specific coding agent 当成自己的 agent runtime authority。

Model Runtime 把一个 endpoint 转成受边界约束的 inference capability：endpoint/network policy → transient credential resolution → model/protocol discovery → capability evidence → eligibility → inference。当前 wire codec 支持 OpenAI Chat Completions、OpenAI Responses 与 Anthropic Messages；这些是 protocol family，不是 provider identity。

Agent Runtime 负责 `AgentJob`、model selection、hard budget、标准化 tool call、capability/authority check、重要写入前 checkpoint、receipt、post-condition 与 `AgentResult`。无法建立要求的 durable execution boundary 时，side effect 会 fail closed。

解析后的 access token 是 host secret，不会进入 SQLite、prompt、Context、AgentJob/Result、checkpoint、receipt 或 fingerprint。

继续阅读：[Model Runtime](docs/model-runtime.zh-CN.md) · [Agent Runtime](docs/agent-runtime.zh-CN.md) · [运行时与集成](docs/integrations.zh-CN.md)

## 正文生产是一条生命周期，不是一次生成调用

<img src="docs/assets/architecture/production-graph.zh-CN.svg" alt="Quillframe 长篇小说生产生命周期" width="100%" />

当前 DRAFT / REVISE 会围绕受限 Context、Story/Canon 预检、场景与人物模拟、Reader Pressure、事件优先起草、表层实现、candidate qualification、需要时的独立语义评审、repair/challenger generation、读者投入度、连续性与用户可见门槛执行。

**Raw Draft 是内部产物。Review 不等于 Accepted；Accepted 不等于 Settled。**

系统刻意保持这些区别：

`stored ≠ injected` · `Plan ≠ Canon` · `Review ≠ Accepted` · `Accepted ≠ Settled` · `autosave ≠ Accepted` · `revision ≠ Canon` · `Corpus ≠ Canon` · `persistence ≠ authority`

只有作者明确接受重要变更后，**Settlement** 才负责校验精确 before-state、应用预期 after-state、更新必要 projection 并验证 post-condition。出现 mismatch 时结果是 `settlement_incomplete`，而不是“应该写成功了”。

## Studio · 作者优先

Quillframe Studio 是基于 **SolidJS + TypeScript + Vite** 的创作界面，并由 typed Core / Host Bridge contract 提供边界。产品语言与视觉统一工作已经合并到 `main`；产品网站、文档和 Studio 现在共享同一套 Borderless Kawaii Editorial 设计语言。

面向作者的工作始终优先。运行时细节通过渐进展开的 inspection surface 提供，而不是把日常创作界面变成 Framework dashboard。Core 没有授予的 Canon、acceptance、Settlement 或 SQLite authority，UI 不能自行制造。

**Tauri 2 thin desktop host** 仍然是桌面架构方向；当前 `0.9.0` checkout 还没有完成并交付 Tauri wrapper。

## SQLite-native 持久状态

Canonical product state 使用 SQLite：

```text
~/.quillframe/
├─ quillframe.sqlite
├─ projects/<project-id>/project.sqlite
├─ projects/<project-id>/blobs/
└─ backups/
```

Core 开启 foreign keys、WAL、busy timeout 与明确 durability policy，并使用顺序/校验和 migration、backup/restore、integrity check 与 `quillframe doctor` 类诊断。Markdown、DOCX、EPUB 等只是 import/export artifact，不是第二套 live authority。

UI 边界保持单向：**Solid/Tauri → typed Bridge/API → Python Core → SQLite**。

## Learning：自动接收，但不偷偷晋升

有意义的用户反馈可以自动进入 learning intake：

`capture → interpret → scope → evidence → candidate → validation`

自动 capture 不等于自动 promotion。`one_off`、`project`、`user_taste` 与 `general_craft` 仍然是不同 scope；模型推断出的偏好不会悄悄变成 Canon、永久 user taste、Project policy 或 Framework behavior。

## 对 AI 也友好的公开入口

产品网站现在提供一组小而明确的 AI discovery surface，但不会假装网站本身就是带 authority 的 agent server：

- [`llms.txt`](site/public/llms.txt) —— 精简的产品与 Context 指南。
- [`llms-full.txt`](site/public/llms-full.txt) —— 更完整的 machine-oriented 架构与 authority 说明。
- [`ai-catalog.json`](site/public/.well-known/ai-catalog.json) —— 面向机器的 public-surface catalog。
- [`agent-skills/index.json`](site/public/.well-known/agent-skills/index.json) —— 暴露真实 Quillframe portable Agent Skill 的发现入口。
- [`agent-skills/quillframe/SKILL.md`](agent-skills/quillframe/SKILL.md) —— 给外部 agent package 使用的 read-only Host Bridge skill。

这些文件**不会**授予 Canon、Project-write、Framework-write、Settlement、MCP、A2A、OAuth 或 hosted-model-gateway authority。Public discovery 只是 metadata；capability 与 authority 仍然必须由明确契约证明。

## 文档

按你现在要完成的任务进入：

- [为什么是 Quillframe](docs/why-quillframe.zh-CN.md) —— 产品定位、取舍与替代方案。
- [架构](docs/architecture.zh-CN.md) —— 系统 ownership 与 authority boundary。
- [正文生产流程](docs/production-pipeline.zh-CN.md) —— DRAFT / REVISE 生命周期。
- [质量保障](docs/quality-assurance.zh-CN.md) —— exact-fingerprint gate 与独立评审。
- [上下文与记忆](docs/context-and-memory.zh-CN.md) —— sparse Context、visibility、persistence 与 memory boundary。
- [Model Runtime](docs/model-runtime.zh-CN.md) / [Agent Runtime](docs/agent-runtime.zh-CN.md) —— provider-neutral inference 与 Quillframe 自有 agent execution。
- [Project SDK](docs/project-sdk.zh-CN.md) —— 可复现的小说 Project 接入。
- [Studio](studio/README.zh-CN.md) —— 创作界面与 Host Bridge 行为。
- [架构图谱](docs/architecture-atlas.zh-CN.md) —— 子系统 ownership 与深层契约入口。

发布后的文档使用 **Astro + Starlight** 构建；文档治理由 `docs/documentation_manifest.json` 与 `python scripts/docs_quality.py` 直接执行。

## 仓库地图

```text
quillframe/       对外 Python façade
model_runtime/    endpoint、discovery、capability evidence、inference transport
agent_runtime/    AgentJob、tools、budget、checkpoint、receipt、agent loop
core/             Story / Character / Canon contract
harness/          session、semantic execution、control plane、Settlement
quality/          readiness、finding、repair、candidate evolution
learning/         feedback evidence 与受治理的 promotion
corpus/           受治理的 craft/research evidence
persistence/      canonical SQLite durable state
publication/      Accepted-text publication IR/compiler
studio/           Host Bridge、local server、SolidJS Studio
site/             产品网站 + Astro/Starlight 文档
```

## 当前状态 · 0.9.x

Quillframe 仍处于 **pre-1.0 持续开发阶段**。当前 `main` 已包含 embeddable Python façade、Model Runtime、Agent Runtime、小说 Core/authority contract、SQLite persistence、typed Host Bridge、SolidJS Studio、产品网站与 Starlight docs。Normal CI 使用确定性/mock execution，不会在没有明确 opt-in 的情况下偷偷调用配置好的付费/在线 Model API。

仍然有意保持为未完成状态的部分包括：pre-1.0 compatibility 尚未冻结，authoring UX 还会继续演进，Tauri 2 desktop wrapper 尚未交付。

## 开发与贡献

```bash
python scripts/docs_quality.py
python -m unittest discover -s tests -p 'test_quillframe_*.py' -v

cd site && npm install --no-audit --no-fund && npm run quality && npm run build && npm run docs:build
cd ../studio/app && corepack enable && pnpm install --frozen-lockfile && pnpm typecheck && pnpm build
```

参见 [贡献指南](CONTRIBUTING.md)、[路线图](ROADMAP.md)、[安全政策](SECURITY.md)、[行为准则](CODE_OF_CONDUCT.md) 与 [变更记录](CHANGELOG.zh-CN.md)。

## 安全

不要把模型 access token、私有正文或项目数据库贴到公开 Issue。Hosted secret 必须留在 server/host side；解析后的 token 不应进入 browser bundle、prompt、Context、SQLite、receipt 或 fingerprint。详见 [SECURITY.md](SECURITY.md)。

## 许可证

Quillframe 使用 **Quillframe Proprietary Source-Available License**。仓库公开、源码可查看，但该许可证**不是** OSI open-source license，并对重新分发、部署与商业使用设有限制；除非另行获得书面许可。

精确法律条款以 [LICENSE](LICENSE) 为准。

---

<p align="center"><sub>✦ 让创作判断保持自由，让执行事实保持明确。 ♡</sub></p>

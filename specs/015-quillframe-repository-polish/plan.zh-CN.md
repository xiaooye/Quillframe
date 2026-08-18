# 实施计划 · Quillframe Repository Polish

## 选定架构

把 repository presentation 当成现有 authority 之上的薄公共层：根 README 负责 orientation；Starlight 负责深入文档；CONTRIBUTING / SECURITY / GitHub templates 负责参与入口；真正执行权威仍在 manifest、contracts、implementation 与 tests。

README narrative：

`Hero → 为什么存在 → 核心原则 → architecture → authoring lifecycle → state boundaries → Studio / persistence → Quick Start → repository/docs map → status / contributing / license`

UI/UX branch 正在进行，因此优先使用仓库已有且稳定的 SVG 品牌与架构资产，不把短期易过期的 Studio 截图固定为 README hero。

## 外部 Benchmark Patterns

已研究当前 LangChain、AutoGen、Pydantic、FastAPI、Vite、Tauri、AppFlowy、Zed 的 GitHub presentation。可复用的是信息设计模式：

- 第一屏一句话讲清 category；
- Quick Start 靠前，但先给足最小产品上下文；
- 生命周期重要时把 status notice 明确放出来；
- 用分层 architecture 代替 giant inventory；
- 用户运行路径与 contributor setup 分离；
- docs / contributing / security 从根入口可见；
- 高级内部细节用 progressive disclosure；
- license 如实直说。

不复制任何外部品牌、文案、精确布局、代码或资产。

## 影响对象 / 路径

主要：
- `README.md`, `README.en.md`, `README.zh-CN.md`
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `.github/ISSUE_TEMPLATE/**`, `.github/pull_request_template.md`
- `docs/README.*`, `docs/why-quillframe.*`
- `site/docs-site/src/components/DocsLanding.astro`
- `site/docs-site/src/components/QuillframeActions.astro`

当前可用 GitHub connector 不提供 repository Description/Homepage/Topics 写接口，因此在 PR/final report 提供 exact recommended values。

## Dependency Graph

1. 冻结 live `main` 与并行 branch ownership。
2. 研究 current public repositories。
3. 根据 current contracts 重构 README。
4. 增加 contributor/security/community 入口。
5. 修复 current-facing docs naming/routes。
6. 运行/观察 repository verification。
7. 重新 fetch `main` 与并行 PR，只吸收已经 merged 的事实。
8. 创建 Draft PR。

## Migration Strategy

纯文档 / presentation 的 additive 或 replacement changes，不进行 data/runtime/schema migration。

## Test / Eval Strategy

- Pull Request 上的 current CI；
- CI 中 site `quality`、`build`、`docs:build`；
- relative path / anchor inventory review；
- YAML / GitHub template syntax review；
- 工具允许时验证 public deployment links；
- README 不引入 Mermaid，因此 Mermaid renderer validation 为 N/A；
- 若无法拿到真实 rendered GitHub evidence，light/dark QA 明确写 unverified。

## Phases / Checkpoints

1. Spec 与 ownership freeze。
2. README landing reconstruction。
3. Contributor / Security / GitHub templates。
4. Docs entry point naming/link cleanup。
5. Verification + late truth reconciliation。
6. Draft PR。

## Rollback

所有改动按 commit bounded，且不触碰 runtime/persistent project state；需要回退时直接 revert 对应 commit。

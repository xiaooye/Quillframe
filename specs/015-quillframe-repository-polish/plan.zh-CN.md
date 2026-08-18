# 实施计划 · Quillframe Repository Polish

## 选定架构

把 repository presentation 视为 live Quillframe authority 之上的薄公共层：README 负责 orientation 与开始使用；Starlight 负责深入；AI discovery 文件负责描述；contributor/security/templates 负责参与入口；真正权威仍在 implementation/contracts/tests。

README narrative：

`Hero → Quick Start → 为什么存在 → 产品心智模型 → Model/Agent Runtime → 正文生产生命周期 → Studio/state → Learning → AI discovery → docs/repo map → status/security/license`

这与当前高 star repository 的高质量模式一致：先讲清类别和可运行价值，再逐层展开 architecture，而不是第一屏就展示内部 inventory。

## Benchmark 集合

研究了当前 OpenClaw、Spec Kit、autoresearch、Pi Agent Harness、World Monitor、Matt Pocock Skills、DeepSeek Harness、Superpowers，以及其他成熟 framework/product repository 的 README。只吸收信息设计模式，不复制外部品牌、文案、代码或精确布局。

## 影响表面

- root 英文/中文 README 与 light/dark 自适应品牌/架构图；
- `CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`ROADMAP.md`；
- GitHub Issue / PR templates；
- docs home / Why Quillframe / Starlight navigation；
- `docs/documentation_manifest.json` 与 deterministic `scripts/docs_quality.py`；
- Model/Agent Runtime 文档发现入口；
- `site/public` AI discovery：robots、XML/Markdown sitemap、llms、auth note、well-known catalog、response headers；
- `LICENSE` 中的法律产品标识；
- README visual-QA automation/evidence tooling。

Repository Description/Homepage/Topics 只有在 connected GitHub surface 暴露经过授权的 metadata write action 时才直接修改；否则保留为外部 GitHub settings 步骤。

## 执行顺序

1. 冻结/重读 live `main` 与并行 ownership。
2. Reconcile 已 merge 的 runtime 与 UI/product facts。
3. Benchmark current high-signal README 与 AI-readable web conventions。
4. Polish README 并同步中文/英文版本。
5. 注册 Model/Agent docs，修复 Starlight route 与 docs-home link。
6. 让 `docs_quality.py` 可在 current corpus 上真正运行，并接入 normal CI。
7. 增加受边界约束的 AI discovery/content-use 文件。
8. 修改 license 产品标识，但不改许可条款。
9. 增加 theme-aware README artwork 与真实 GitHub render QA tooling。
10. 收集 CI/evidence、修失败项，再次 late-reconcile `main`。
11. 刷新 Draft PR #110 body，不 merge。

## 验证策略

- normal CI 中运行 `python scripts/docs_quality.py`；
- Quillframe Python/runtime/authority regression suite；
- site `quality`、`build`、`docs:build`；
- Studio frozen install、typecheck、build；
- local link 与 manifest inventory check；
- GitHub Actions event 语义允许时，对 public GitHub README 做 desktop-light、desktop-dark、narrow-light、narrow-dark 的真实 render capture；
- screenshot/report artifact 绑定 exact head SHA；
- 没有 actual GitHub-render evidence 就不宣布 visual PASS。

## Rollback

所有变更按 commit 划分，不触碰 persistent project/runtime state。Repository-presentation/QA commit 可独立 revert；LICENSE rename 也可独立回退，因为实质性 license clauses 没有改变。

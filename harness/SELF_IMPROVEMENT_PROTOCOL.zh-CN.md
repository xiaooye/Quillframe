# Framework Self-Improvement Protocol · v7 中文版

## 目标

NovelForge 可以自主学习和改进，但 durable behavior change 必须始终有 evidence、可测试、scope 清晰、可 rollback。

```text
Capture → Classify → Distill → Counterexample → Test → Promote → Observe → Roll back
```

## Learning Scopes

- `one_off`：仅当前 response/run；
- `project`：单一 consuming novel/project；
- `user_taste`：某个用户跨项目偏好，默认存于 generic source control 之外；
- `general_craft`：NovelForge 自身的 generic mechanism candidate。

永远选择 evidence 能支持的最窄 scope。

## Evidence Hierarchy

强 evidence 包括：用户明确规则、直接编辑、带理由的接受/拒绝、多次一致修正、project convention、cross-work corpus mechanism、外部 primary/framework evidence。

Model inference 本身只是弱 evidence，不能 promote durable user taste 或 General Craft。

## User Preference Learning

用户 feedback 先变成 traceable evidence，再变成可推翻 hypothesis。系统可以自主检测 contradiction、生成 Corpus gap、通过已授权工具找 contrast/counterexample、生成 personalized eval，并 strengthen/narrow/deprecate hypothesis。

被用户拒绝的模型输出不能成为 positive exemplar。

## General Craft Promotion

Framework behavior promotion 必须满足：
1. mechanism 不依赖单一 project/user；
2. provenance/evidence；
3. counterexample 或 profile-boundary analysis；
4. capability + regression eval；
5. 与已有 fundamentals/profiles 的 conflict check；
6. smallest sufficient change；
7. version/rollback reference；
8. green post-change deterministic CI；
9. promotion 后继续 observe。

模型重复同意自己多少次，都不能替代新 evidence。

## Corpus-derived Learning

Corpus observation 只有经过 cross-work synthesis 与 rights/provenance governance 才可能成为 general guidance。禁止建立现代 named-author imitation profile。

## External Framework Learning

OpenAI Agents SDK、LangGraph、ADK、AutoGen、Claude Code、MCP 等上游变化只产生 `adopt | adapt | reject` candidate。上游更新不自动等于更适合小说生产。

## Rollback

后来发现有害或 provenance 无效时：
- hypothesis/promotion 标记 contested/deprecated；
- invalidate dependent benchmark/eval；
- 恢复之前 behavior/profile；
- 记录 rollback evidence；
- 重跑相关 regression。

## Boundary

Framework self-improvement 可以修改 generic mechanism；绝不能把 consumer novel 的人物、Canon、剧情结果或 private project state 吸收到 generic source。

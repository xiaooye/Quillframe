# Product Godot 迁移 · Visual Parity Contract

## 状态

这是 NovelForge Product Site 从 Solid/Vite shell 迁移到 Godot Web 的迁移契约。它不改变 Story Loom Kawaii Atelier 的产品视觉规范，只改变实现技术栈。

## Source of truth

迁移期间有且只有一个视觉/行为基线：当前 `main` 上已经通过 Browser QA 的 Solid/Vite Product Site。Godot 不拥有重新设计权。

基线证据：

- desktop：1440×900 首页 Browser Proof；
- mobile：390×844 首页 Browser Proof；
- Product Site source/quality contracts；
- Story Loom Kawaii Atelier v5 spec；
- 当前双语 copy、路由、Docs hard-navigation、Studio external handoff 与 accessibility 行为。

## 硬规则

1. **Implementation migration, not redesign.** 同一信息架构、同一 section 顺序、同一 copy、同一主次层级、同一密度与近似像素几何。
2. **Production stays Solid until parity passes.** Godot 先以 shadow runtime 构建和截图；不得因为“Godot 已能跑”就替换线上 shell。
3. **Typography is deterministic.** Web export 不依赖 Godot 默认字体或宿主 system font。迁移使用内容固定的开源 CJK 字体，并用 `FontVariation` 显式控制字重。
4. **No 3D.** 允许的 2.5D 只来自 2D layer、shadow、轻微 rotation、parallax / depth cue；禁止 `Node3D` / `Camera3D` / mesh scene。
5. **No ambient perpetual motion.** 沿用 Product Experience v5 的 reduced-motion 与 idle-motion 约束。
6. **Mobile is a first-class composition.** 390×844 必须单独验收，不能缩放 desktop canvas。
7. **Browser semantics remain explicit.** Product internal routes使用 browser history；`/docs/**` hard-navigation；Hosted Studio external handoff。
8. **No authority expansion.** Product Site、shadow runtime、generated visual evidence 均为 `authority=false`。

## Cutover gate

Godot 只有同时满足以下条件才可以成为 production root：

- Godot source/smoke/Web export 全绿；
- desktop + mobile 首页截图人工视觉确认；
- 无 CJK missing-glyph / tofu；
- typography hierarchy、headline wrap、header、CTA、workspace card 与首屏纵向节奏与 baseline 一致；
- 主要 Product routes 的 route-specific Browser QA 通过；
- keyboard focus、locale、reduced motion 与 Docs boundary 通过；
- hosting asset policy 已解决，且不能靠降低视觉质量绕过；
- 最后一次 cutover 前重新生成 Solid baseline 与 Godot candidate 的同尺寸证据。

在 gate 通过前，Godot workflow 只能产出 shadow artifact，不部署到 `novelforge.wei-dev.com`。

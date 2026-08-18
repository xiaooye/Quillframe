# 实施计划

## Phase 1 · Authority 与 shared shell

1. 以 `e49304bde7fb0c5ba0822deb3823f960c6425804` 为唯一 base authority。
2. 保持 `ui/homepage-product-language-unification` 为唯一实现分支，不 merge main。
3. 修复 ProductShell navigation ownership：top / mobile / footer / command palette 从共享导航模型派生。
4. 恢复真实 GitHub repository entry；补齐 Changelog 与 Studio landing 可达性；Hosted Studio 保持独立 external action。
5. 把 shell 可见版本从 stale 0.8.x 同步到 0.9.x。

## Phase 2 · Shared visual primitives

1. 重构 `ProductSurfaceHero` style owner：hero root 回归 canvas composition，移除 frame / radius / shadow / large tone gradients / dashed inset。
2. 保留 optional visual slot；route-specific artifact 只在其信息对象需要边界时使用 contained surface。
3. 复核 ProductSectionHeading、shared shell、small object surfaces，避免建立新 override layer。

## Phase 3 · Public routes

1. Product / Studio landing：从 card-grid 说明切换到 editorial sequence / rail / asymmetric composition。
2. Architecture：清理大面积 radial rainbow、减弱 node/card chrome，突出 execution path 与 inspector information hierarchy。
3. Publication：改成 proofing/typesetting desk；profile switcher 与 preview 保留真实交互，色彩转为小面积语义 accent。
4. Inspect / Playground / Agents：保留真实工具对象，去除 enclosing hero-card / nested surface syndrome。
5. Changelog：改成 release notebook / timeline。

## Phase 4 · Docs

审计 Starlight chrome、landing、article、sidebar、TOC、code、table、callout、pagination、mobile sidebar 与 404。共享 Quillframe language，但 reading-first；不建立第二套 token authority。

## Phase 5 · Studio

审计所有 Writer / Inspector route。先修 `.nf-page-intro` 与 shell composition，再处理 route-specific density。保留真实 Core Bridge、settings、model/runtime/session/semantic surfaces。

## Phase 6 · Quality / verification

1. 更新 `site/scripts/*` stale visual invariants，新增 GitHub entry 与 navigation synchronization contract。
2. 更新 Studio / Docs quality checks，使 gate 保护新设计，而非旧 CSS property。
3. 运行 deterministic site/docs/studio build 与 quality tests。
4. 检查 no `!important` introduced、no late override CSS、no polling/infinite animation regression。
5. 验证 1440 / 1024 / 768 / 430 / 375，以及 keyboard/focus/touch target/accessibility。
6. 实际 render Product routes、Docs representative pages、Studio Writer/Inspector routes，执行 desktop + phone visual-family audit。

## Acceptance

代码与 deterministic gates 通过但尚未由用户 visually accept 时，状态为 `review / awaiting_user`。任何 mandatory visual/render gate 未执行时不得称 complete。
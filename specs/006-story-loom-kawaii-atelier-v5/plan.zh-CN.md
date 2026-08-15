# Product Experience v5 · 实施计划

## 目标

在保留 Product Entry 已交付能力与 authority 边界的前提下，把 v4 dark-glass presentation 替换为 Story Loom Kawaii Atelier。

## Phase 1 · 冻结当前能力面

- 保留现有 routes 与 runtime behavior；
- 保留 WeiUI generated foundation 与 exact pin；
- Story Loom semantic lane variables 继续作为唯一品牌色权威；
- 保留 build-time documentation ingestion 与结构化 AST renderer；
- 保留 Command Palette、context/readiness labs、Hosted Studio 入口、Architecture explorer 与 Publication switcher；
- implementation 开始时的 current main 作为 write before-state。

## Phase 2 · 重做 Product shell

- 压缩 sticky app bar，让它像 atelier tool strip，而不是 dashboard chrome；
- 建立 warm/paper-like 页面底材；
- 升级 appearance migration 版本，让首次进入 v5 时只把遗留的 v4 dark preference 迁回 light 一次；
- 迁移完成后继续尊重用户主动选择的 dark mode。

## Phase 3 · 重组首页

- Hero 改成紧凑 atelier desk：叠放产品物件 + 真实 launch actions；
- Capability ribbon 改成 tactile lane tabs / stickers；
- 两个 Labs 组合成一个 notebook/workbench spread；
- Product doors 改为非对称 shelf/bento，并让 Studio 成为主要入口；
- 真实文档 preview 继续存在，但表现成 knowledge shelf/library object，而不是“文档章节”；
- 明显减少垂直死留白，避免重复“section heading + card grid”公式。

## Phase 4 · 统一 routes

- InteractiveRouteFrame 改成紧凑 application toolbar，不再是 brochure hero；
- Product / Studio / Architecture / Publication 统一成高密度工作 surface；
- Knowledge Explorer 与 document reader 保持完整功能，并接入同一套 atelier material language；
- 保留 keyboard navigation 与 mobile bottom-nav。

## Phase 5 · Progressive CSS showcase

- 独立建立 v5 enhancement layer，只把现代 CSS 当 progressive enhancement；
- 使用 interaction-driven material response、view/scroll timelines、View Transitions、container queries、`:has()`、`@scope`、`@property`、`@starting-style`、discrete transition、mask/blend，以及 guard 后的 anchor/corner-shape；
- 禁止 infinite idle animation 与 decorative `requestAnimationFrame` loop；
- reduced-motion 直接落在漂亮的静态终态。

## Phase 6 · Quality contract

更新 Product Site QA，验证：

- v5 appearance migration；
- warm atelier identity marker；
- Story Loom lane token 的实际消费；
- WeiUI primitives 继续存在；
- Knowledge build/runtime 继续存在；
- v5 CSS 仅渐进增强并满足 reduced-motion；
- 不退化回 dark-dashboard-only；
- 无 fake marketing/social proof；
- 无 authority bleed。

## Verification

完整运行当前 Product Site workflow：

`foundation sync → documentation build → Product Site contract → tsc → Vite build → Cloudflare Pages deploy → custom-domain post-condition`

之后继续做真实 desktop/mobile visual review。CI 通过是必要条件，不等于视觉验收完成。

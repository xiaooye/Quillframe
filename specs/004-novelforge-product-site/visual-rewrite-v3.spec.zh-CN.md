# Specification · Product Site Visual Rewrite v3

## Baseline

- Parent Product Site contract：`specs/004-novelforge-product-site/spec.zh-CN.md`。
- Tracking issue：#34。
- Framework baseline：implementation start 时 latest `main`。
- Primary mode：`SYSTEM-IMPROVE`。
- Change class：presentation architecture rewrite；不改变 Core/runtime authority。

## 问题

当前 Product Site 的信息结构与产品事实已经正确，但视觉层级仍然更像“做得不错的文档站 / SaaS landing page”。大面积浅色背景、重复卡片网格和常规左右双栏 Hero，无法形成 NovelForge 应有的 premium、cinematic、editorial 产品身份。

这次不能继续给旧版加装饰，而要直接替换首页 composition 与 visual grammar，同时保留 product truth、routes、accessibility、i18n、Story Loom authority、低运行时开销和 deterministic build/deploy contracts。

## UI/UX Pro Max evidence

UI/UX Pro Max 继续作为 design evidence，本轮采用高 variance / 高 motion / 低 density 的 marketing 组合：

- Gradient Mesh / Aurora Evolved：负责 hero / background atmosphere；
- Editorial Grid / Magazine：负责不对称产品叙事；
- Motion-Driven：负责 scroll-linked choreography 与 state transition；
- Tactile Digital：只用于克制的 press/hover material response；
- Liquid Glass：仅用于 navigation/control chrome，禁止演化成 content-card soup；
- Hero-Centric + Scroll Storytelling + Product Demo：作为 landing structure。

凡与 NovelForge contract 冲突的 generic 建议一律拒绝：不做 idle infinite Aurora loop、不要求 custom cursor、不允许动画承载唯一内容、不默认引入重型 WebGL/Three.js、不建立平行 product palette。

## Visual thesis

**Cinematic editorial instrument，而不是 SaaS card catalogue。**

页面应像一件精密创作工具，以 premium publication/editorial 语言呈现：

- 深色 cinematic opening stage；
- 发光的 Story Loom thread / evidence lane；
- 不对称 typography 与 negative space；
- 深浅章节交替，而不是一整张连续白色文档页；
- proof object 融入构图，而不是每项都装进同尺寸 feature card；
- chrome、manuscript、runtime、evidence、publication surface 有不同 material identity；
- 纵深来自 layering、mask、gradient、border、optical highlight 与 scroll choreography，而不是无意义的重型 3D scene。

## Homepage architecture

### H1 · Cinematic hero

移除常规 left-copy/right-card Hero，改成 full-width stage：

- 简洁产品 thesis；
- atmospheric mesh / loom field；
- 与舞台融合的 floating provenance instrument，而不是悬空 dashboard card；
- 一条紧凑 contract rail，展示真实 machine-backed proof noun；
- pointer-responsive lighting 作为 progressive enhancement，且没有 frame loop；
- 通过 scroll-linked transition 进入下一章节。

### H2 · Editorial problem chapter

移除三张等尺寸卡片。使用一个 dominant statement + 三个编号 failure mode 的 asymmetric editorial rail/column 结构。Desktop 可 sticky / asymmetric；mobile 必须保持线性阅读顺序。

### H3 · Forge scroll story

Forge 成为首页核心 scroll-story。一个 visual stage 保持 sticky，Project → Context → Simulation → Draft → Gates → Review 通过显式步骤推进。滚动效果必须原生/progressive，不得 scroll-jacking。

### H4 · Proof field

Proof module 使用不同 span、typography scale、inline machine identifier 与轻量 diagram，禁止回到 uniform card wall。

### H5 · Studio / Publication feature chapters

Studio 与 Publication 变成大型 immersive chapter，使用不同 material identity，而不是普通 two-column marketing band。视觉仍必须明确是 illustrative，不伪装成真实 runtime screenshot。

### H6 · Architecture constellation

Architecture 使用 connected system / constellation 方式呈现，不再使用普通 bento grid。每个 node 都必须有可读文本 fallback 与明确 ownership label。

### H7 · Release / CTA close

结尾使用克制的 release-truth surface 与强 next-step navigation，不模仿 pricing/conversion template。

## Motion contract

- 优先 native CSS `animation-timeline: view()` / `scroll()` progressive enhancement；
- locale/theme/navigation state change 可用 same-document View Transitions；
- pointer response 可在 pointer event 中直接写 CSS custom properties；禁止 `requestAnimationFrame` / default polling loop；
- motion 只用于解释 depth、focus、continuity 或 state transition；
- Product Site showcase CSS 禁止 `animation: ... infinite`；
- `prefers-reduced-motion: reduce` 必须直接呈现完整可读 final state。

## Material contract

- Story Loom v2 token 继续是 color/semantic authority；
- Dark hero 可以通过 `color-mix()` 从现有 semantic role 派生深色，但不得新增第二套 brand palette；
- Glass 仅限 header/control/instrument overlay，且背景关系必须保持可读；
- 主要阅读 surface 必须足够 opaque，确保稳定 contrast；
- texture/noise 可用 gradient/mask 生成，不要求大型 decorative image dependency。

## Performance contract

- v3 不要求新增 framework/runtime dependency；
- default path 不引入 WebGL/Three.js；
- 无 idle JS loop；
- 不支持高级 CSS 时降级为完整 static composition；
- mobile 优先移除非必要 blur/depth layer，而不是牺牲 readability / interaction latency。

## Acceptance

1. Homepage DOM composition 与 Visual v2 有实质差异，不是 CSS reskin。
2. Desktop 第一印象是 cinematic / premium / editorial，而不是 documentation / SaaS-card-first。
3. Mobile 保留相同内容层级，无横向滚动、无 hover dependency。
4. 中英文继续拥有独立自然 typography geometry。
5. 不引入 fabricated social proof 或新的 product authority。
6. 不引入 idle animation / default polling。
7. reduced-motion 立即显示完整内容。
8. Product Site deterministic quality + Vite production build 通过。
9. Cloudflare deployment 继续只是 host-neutral static output。
10. Rewrite 可独立 revert，不改变 Core/Studio runtime semantics。

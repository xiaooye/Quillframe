# Specification · NovelForge Product Site

## Baseline

- Framework 开发基线：latest `main`。
- Tracking issue：#34。
- Change class：Product Web surface / structural feature。
- Primary mode：`SYSTEM-IMPROVE`。
- Rollback：Product Site implementation 的 parent commit。

## 问题

NovelForge 现在已经拥有足够多真实的 Product、Runtime、Publication、Design System 与 Documentation surface，仅靠 GitHub README 已经无法形成清晰的公开产品入口。

新用户目前必须先从架构文档里反推产品价值，导致：

1. 价值主张晚于实现细节出现；
2. 产品 proof 分散在 Core、Studio、Publication、Quality 与 Release 文档中；
3. Story Loom 只能作为静态文档装饰，而没有一等交互产品展示面。

Product Site 的目标是一套独立、SaaS-like 的 SPA，第一职责是**让人理解产品并进入正确下一步**，而不是把 Markdown 换一个壳。

## 产品角色

网站按下面顺序沟通：

`value → problem → mechanism → proof → product surfaces → deep documentation`。

它永远只是 presentation/navigation layer，不成为 Canon、Memory、semantic truth、production-readiness truth、Publication truth、Settlement authority、Framework-write authority 或第二套 runtime。

## Design evidence

UI/UX Pro Max 作为 external design evidence 使用，不获得 repository authority。适用模式是有边界的组合：

- Hero-Centric Design；
- Scroll-Triggered Storytelling；
- Product Demo + Features；
- Bento Grid Showcase；
- Trust & Authority。

Generic skill 的 palette/style 建议不能覆盖 Story Loom v2 token 与 Product contracts。

## Goals

### G1 · SaaS-like Product Home

首页首先是产品叙事，不是 docs index。

必须包含：

1. Hero：一句清楚的 NovelForge thesis + primary CTA + secondary proof/navigation CTA。
2. Problem：为什么 prompt-only / one-shot fiction generation 会丢失 authority、continuity、context discipline、evidence 与 repeatability。
3. The Forge：可视化 Project → Context → Simulation → Draft → Reader/Continuity/Semantic gates → User-visible candidate。
4. Proof, not promises：展示 `main` 上真实 machine-backed distinctions。
5. Studio：Creator/Inspector 与 portable delivery story。
6. Publication：Accepted-text deterministic publication core 及其当前边界。
7. Architecture：subsystem bento + deep links。
8. Delivery：CLI / Local Web / hosted / Agent Skill；host capability != story authority。
9. Release truth：当前 pre-1.0 identity 与开发状态。
10. CTA：Docs / Architecture / Studio / GitHub。

禁止 fake testimonial、customer logo、usage metric、pricing、uptime、rating、scarcity。

### G2 · 长期 Route Model

初始 routes：

- `/`
- `/product`
- `/studio`
- `/architecture`
- `/publication`
- `/docs`
- `/changelog`

SPA 必须支持 deep link；hosting 是可替换的 static infrastructure。

### G3 · One Content Truth

Product Site 不建立第二套 CMS 或 Framework contract 副本。

- Marketing copy 可以总结 maintained contracts；
- technical claim 必须链接或来源于 repository maintained source；
- Docs route 第一阶段可以是 curated navigation；未来 Markdown renderer/search 必须 build-time 消费 repository source；
- static site 不能伪造 dynamic runtime truth。

### G4 · Story Loom / WeiUI Foundation

- `assets/brand/tokens.json` 继续是 NovelForge product-token authority；
- `assets/brand/weiui.integration.json` 继续是 exact WeiUI consumption contract；
- `assets/brand/story-loom.weiui.css` 继续是 live mapping/theme surface；
- 不维护第二套手写 palette；
- 不引入 `@weiui/react` / `@weiui/headless` runtime；
- WeiUI 跨 repo distribution 尚未稳定前，Site 可以直接消费已合并的 Story Loom application theme，但不能虚构不存在的 npm import。

### G5 · Low-overhead SolidJS Surface

Application stack：SolidJS、TypeScript、Vite、`@solidjs/router`。

Local Web 是主要公开形态，本 Product Site 不需要 Tauri dependency。

Site 不得给 Generic Core、CLI、Framework bundle、Agent Skill 或 Studio host bridge 增加 runtime dependency。

### G6 · 双语架构

Baseline locales：`en-US`、`zh-CN`。

- Locale 显式可切换；
- layout 不依赖固定英文宽度；
- 中文使用自然产品文案，不逐句硬翻；
- exact machine identifiers 不翻译。

### G7 · Accessibility / Responsive / Motion

硬要求：

- mobile-first；
- interactive target ≥44×44px；
- visible focus；
- keyboard-operable navigation/controls；
- 不依赖横向滚动；
- semantic headings/landmarks；
- contrast 遵守 Story Loom QA；
- reduced-motion 保留完整内容与最终状态；
- no idle animation loop；
- no default polling；
- 没有 JS animation 时仍可完整理解页面。

### G8 · Product Proof Modules

Proof 必须来自真实 current contracts，例如：

- semantic support vs actually loaded Context；
- story-order / perspective-safe evidence；
- same-candidate-fingerprint production-readiness conjunction；
- character-visible evidence discipline；
- exact Accepted-text Publication fingerprint preservation；
- portable Host Bridge `authority=false`；
- deterministic Story Loom/WeiUI design-system checks。

允许简化展示，不允许发明 metric、score、customer outcome 或 authority claim。

### G9 · Static Hosting

Build 输出 host-neutral `dist/`。

Cloudflare Pages 是优先 deployment target，但不属于产品 authority；站点必须仍可部署到其他 static CDN/host。

第一阶段不需要 database、Pages Function、analytics SDK、auth 或 server runtime。

### G10 · Deterministic Quality Gate

Normal CI 至少验证：

- dependency/version contract；
- TypeScript/Vite production build；
- required routes/source；
- forbidden WeiUI runtime package absence；
- 无明显 fake social-proof placeholder；
- locale structure；
- Story Loom theme/source references；
- reduced-motion/focus/mobile contracts；
- Site 不 import Core runtime。

CI 不执行模型。

## Information Architecture

Primary nav：Product、Studio、Architecture、Publication、Docs。
Secondary：Changelog、GitHub、locale、appearance。

首页采用 editorial pacing，不做等尺寸 feature-card 墙。Narrative、proof、diagram/product preview 与 bento 交替出现。

Docs 是重要目的地，但不是首页身份。第一阶段可直接 curated deep-link 到 canonical source。

## UX / visual constraints

- Story Loom：precise、editorial、warm、engineered；
- 避免 generic purple-gradient SaaS；
- 避免 glass-card soup 与 giant everything-dashboard；
- 避免纯装饰 fake terminal；
- provenance/fingerprint 只在真正解释产品时出现；
- motion 用于说明 continuity/state transition，否则保持克制；
- no scroll-jacking；
- 不允许只有 hover/drag 才能完成的交互。

## Non-goals · first slice

user accounts/auth、billing/pricing、analytics/tracking、collaboration、server DB、write-capable Studio、Tauri packaging、完整 Markdown 全文搜索，以及没有真实证据的 customer case study。

## Acceptance criteria

1. `site/` 可独立 build 成 static `dist/`。
2. 首页是完成度足够的产品叙事，没有 lorem ipsum/placeholder。
3. 初始 routes 全部存在并适合 SPA deep link。
4. `en-US` / `zh-CN` 有显式 locale architecture。
5. 视觉语义复用 Story Loom v2，不创建平行 token palette。
6. 不引入 forbidden WeiUI runtime package。
7. mobile/narrow reading order 连贯，交互 target 符合 44px contract。
8. keyboard focus 与 reduced-motion 已实现。
9. Product proof 来自当前 repository contracts，无 fabricated social proof。
10. Site build/quality CI deterministic、model-free。
11. Generic Core 与 site stack 保持独立。
12. 无需 hosting account 就能 review 第一阶段成品。
# Tasks · NovelForge Product Site

## T0 · Structural contract

- [x] 创建 tracking issue #34。
- [x] 定义双语 Product Site specification。
- [x] 定义双语 implementation plan。
- [ ] 以单一 structural-intent checkpoint 提交 spec / plan / tasks。

## T1 · Application scaffold

- [ ] 创建 `site/package.json`，固定 SolidJS/Vite/router/TypeScript exact versions。
- [ ] 创建 TypeScript / Vite config。
- [ ] 创建语义完整的 `index.html` metadata shell。
- [ ] 增加 `src/main.tsx` 与 router/AppShell。
- [ ] 输出 host-neutral static `site/dist/`。

## T2 · Story Loom application foundation

- [ ] 直接消费 repository Story Loom application theme，不复制 product palette。
- [ ] `assets/brand/tokens.json` 继续作为 source authority。
- [ ] `assets/brand/weiui.integration.json` 继续作为 exact WeiUI upstream contract。
- [ ] 不引入 `@weiui/react` / `@weiui/headless`。
- [ ] Site-only layout/marketing CSS 只引用 semantic variables，不重新定义产品颜色。

## T3 · Global UX shell

- [ ] Responsive top nav：Product / Studio / Architecture / Publication / Docs。
- [ ] Secondary：Changelog / GitHub / locale / appearance。
- [ ] Mobile nav control >=44px 且 keyboard-operable。
- [ ] visible focus。
- [ ] Footer 提供 product/status/deep-doc links。
- [ ] `en-US` / `zh-CN` locale architecture。

## T4 · Product Home

- [ ] Hero-Centric：一个 primary thesis + 两个诚实 next-step CTA。
- [ ] Problem：说明 prompt-only failure modes，不做 competitor FUD。
- [ ] “The Forge”：Project → Context → Simulation → Draft → quality/semantic gates → candidate。
- [ ] “Proof, not promises”：所有 module 来自 current machine contracts。
- [ ] Studio section。
- [ ] Publication section，准确标出 current scope。
- [ ] Architecture bento，每卡一个 message。
- [ ] one-product-many-hosts delivery section。
- [ ] 0.8.x release-truth section。
- [ ] Final CTA：Docs / Architecture / GitHub。

## T5 · Destination routes

- [ ] `/product` —— product model / why NovelForge。
- [ ] `/studio` —— Creator/Inspector/portable-host product story。
- [ ] `/architecture` —— subsystem map + deep links。
- [ ] `/publication` —— current deterministic compiler + #16 remaining scope。
- [ ] `/docs` —— curated canonical documentation portal。
- [ ] `/changelog` —— release truth + canonical changelog links。

Route 不能是空白 placeholder，也不能原样复制 Home。

## T6 · Accessibility / responsive / motion

- [ ] Mobile-first，无 required horizontal scroll。
- [ ] Interactive target >=44×44px。
- [ ] Semantic landmarks/headings。
- [ ] 所有 interactive control 有 focus-visible。
- [ ] `prefers-reduced-motion` 保留完整内容与最终状态。
- [ ] No idle animation loop。
- [ ] No default polling。
- [ ] No hover-only / drag-only interaction。
- [ ] English / Chinese layout 独立 review。

## T7 · Deterministic site quality

- [ ] 增加 `site/scripts/quality.mjs`。
- [ ] Reject forbidden WeiUI runtime dependencies。
- [ ] 检查 required routes/locales/source refs。
- [ ] 检查 fake marketing placeholders（`10K+`、fake SLA、fake logo/testimonial/trial/pricing copy）。
- [ ] 检查 reduced-motion/focus/touch source contract。
- [ ] 检查 `site/` 不 import Core private runtime。
- [ ] 新增 dedicated model-free GitHub Actions install/build/quality workflow。

## T8 · Product review

- [ ] Desktop render inspection。
- [ ] Narrow/phone render inspection。
- [ ] English copy/product-flow review。
- [ ] 简中 native-copy/product-flow review。
- [ ] Keyboard/focus review。
- [ ] Reduced-motion review。
- [ ] 所有 machine/product claim 对齐 latest `main`。

## T9 · Deployment

- [ ] Vite output 保持 host-neutral。
- [ ] 文档记录 Cloudflare Pages root/build/output config。
- [ ] 只有获得 authorized hosting account/tool 后才真正 connect/deploy。
- [ ] SPA 不加入 Cloudflare-specific product logic。

## T10 · Later extensions

- [ ] build-time Markdown renderer。
- [ ] documentation-manifest-driven nav/freshness metadata。
- [ ] build-time full-text search。
- [ ] interactive architecture explorer。
- [ ] publication sample previews。
- [ ] Social/OpenGraph assets。
- [ ] analytics 仅在单独 privacy/product decision 后加入。
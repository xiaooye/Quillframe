# Product Experience v5 · 任务清单

## Contract

- [ ] T01 冻结 current `main` before-state，并确认 Product Entry v4 的真实功能继续作为能力基线。
- [ ] T02 保持 WeiUI generated foundation exact pin 与 Story Loom import 顺序。
- [ ] T03 Public Product Site 始终 authority-free，不 import Core 私有实现。

## Shell

- [ ] T10 增加 v5 一次性 appearance migration，默认回到 warm light。
- [ ] T11 把 sticky app bar 重组为紧凑 atelier tool strip。
- [ ] T12 保留语言/主题切换、Command Palette、mobile menu 与 mobile bottom navigation。

## Home

- [ ] T20 Hero 重建为 Story Loom Atelier desk：紧凑文案 + Studio/Knowledge/Architecture 真实入口。
- [ ] T21 Capability ribbon 改成 lane-colored tactile tabs/stickers。
- [ ] T22 Context/readiness labs 组合成一个 notebook/workbench spread。
- [ ] T23 Studio/Knowledge/Architecture/Publication 入口重组为非对称 product shelf。
- [ ] T24 Knowledge preview 重组为真实数据驱动的 library/shelf surface。
- [ ] T25 删除重复的“巨大标题 + 两张卡”节奏，明显减少垂直死留白。

## Routes

- [ ] T30 压缩 `InteractiveRouteFrame`；任何 route 都不再以巨大 brochure hero 开场。
- [ ] T31 Product browser 改成高密度 interactive work surface。
- [ ] T32 Studio route 围绕真实 Hosted Studio 入口与能力状态组织。
- [ ] T33 保持 Architecture explorer 行为并接入 atelier composition。
- [ ] T34 保持 Publication profile switcher 并接入 atelier composition。
- [ ] T35 保持完整 Knowledge search/filter 与 document reader routes。

## Visual system

- [ ] T40 Story Loom lane colors 必须真正驱动 surface identity。
- [ ] T41 使用 premium-kawaii shape language：paper/tape/sticker/scallop/squircle/tactile motifs。
- [ ] T42 Kawaii 永远是产品清晰度之后的次级人格；mascot/emoji 不得遮挡 primary action/state。
- [ ] T43 Modern CSS enhancement 包含 `:has()`、container queries、scroll/view timelines、View Transitions、`@property`、`@scope`、`@starting-style`、discrete transitions、mask/blend，以及 guard 后的 anchor/corner-shape。
- [ ] T44 禁止 infinite idle animation、decorative frame loop 与 default polling。
- [ ] T45 保持 reduced-motion、keyboard focus、44px semantic touch target 与 mobile no-overflow。

## Quality 与部署

- [ ] T50 Product Site quality contract 更新到 v5 identity 与硬边界。
- [ ] T51 `npm run quality` 通过，包括 WeiUI sync 与 documentation ingestion。
- [ ] T52 `tsc --noEmit` + Vite production build 通过。
- [ ] T53 Cloudflare Pages production deploy 与 custom-domain post-condition 通过。
- [ ] T54 v5 presentation 必须继续经过 desktop/mobile 真实视觉 review，不能只凭 CI 宣布验收。

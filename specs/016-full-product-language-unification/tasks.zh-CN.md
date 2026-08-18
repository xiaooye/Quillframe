# Tasks

## Shared shell

- [ ] ProductShell 使用共享 `primaryNav` / `utilityNav` source，而不是 header/footer/mobile 各自硬编码。
- [ ] Primary nav 加入真实 GitHub repository entry。
- [ ] Mobile nav 与 footer primary section 与 top nav 同步。
- [ ] Command palette 加入 Studio landing、Changelog、GitHub，并区分 Hosted Studio。
- [ ] Shell 可见版本同步到 0.9.x。
- [ ] `product-shell-quality` 增加 GitHub 与 navigation-sync gate。

## Shared primitives

- [ ] `ProductSurfaceHero` root 变成 borderless canvas composition。
- [ ] 移除 hero root 28px radius、shadow、大面积 tone gradient、dashed inset frame。
- [ ] Route visual artifact 保持可独立 contained，但不得重新把整个 hero 包成 card。
- [ ] `surface-audit-quality` 替换 stale framed-hero invariant。

## Public Product Site

- [ ] `/product` editorial sequence，去机械 card grid。
- [ ] `/studio` landing editorial sequence，保留真实 Hosted Studio action。
- [ ] `/architecture` white execution-paper canvas，减弱 rainbow/card chrome。
- [ ] `/publication` proofing/typesetting desk，减弱 format wallpaper。
- [ ] `/inspect` 去 hero-card + tool-card syndrome。
- [ ] `/playground` 保留 scratch/tool surfaces，页面保持 canvas-first。
- [ ] `/agents` 保留 Host Bridge truth，减少 host card soup。
- [ ] `/changelog` release notebook/timeline。

## Docs

- [ ] Global header / search / locale / theme 与 Quillframe product language 对齐。
- [ ] Landing / article / sidebar / TOC / code / table / callout / pagination / mobile / 404 audit。
- [ ] 保持 reading-first 与 CJK readability。
- [ ] 更新 docs-specific quality contract。

## Studio

- [ ] `.nf-page-intro` 去 generic rounded admin card。
- [ ] Writer routes：Desk / Manuscript / Plan / Story / Review / Research & Corpus / Learning / Publish。
- [ ] Settings 与 Global surfaces：AI Dock / Search / Command Palette。
- [ ] Inspector routes：Sessions / Runs / Checkpoints / Context / Agents & Models / Semantic Jobs / Control Plane / Capabilities / Receipts / Diagnostics / Architecture。
- [ ] 保留真实 Core Bridge 与 state truth。
- [ ] 更新 Studio product-language quality gate。

## Verification

- [ ] Product / Docs / Studio deterministic build + quality tests。
- [ ] 1440 / 1024 / 768 / 430 / 375 responsive verification。
- [ ] Keyboard / visible focus / dialog / aria-expanded / reduced motion / 44px touch targets。
- [ ] No new `!important` / late override / infinite idle animation / polling。
- [ ] Product all routes desktop + phone screenshots。
- [ ] Docs representative pages desktop + phone screenshots。
- [ ] Studio Writer / Inspector representative routes desktop + phone screenshots。
- [ ] Visual-family audit：隐藏 logo 后仍能识别为同一个 Quillframe 产品。
- [ ] 停在 branch，等待用户 visual acceptance，不 merge main。
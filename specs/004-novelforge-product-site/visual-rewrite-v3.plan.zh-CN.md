# Plan · Product Site Visual Rewrite v3

## Phase V0 · 冻结重写契约

- 保留现有 Product Site routes、authority boundaries、i18n model、Story Loom/WeiUI source authority 与 deployment pipeline。
- 当前 Visual v2 首页只是可替换 presentation，不是 implementation authority。
- 在重写 application structure 之前，先提交本 spec / plan / tasks checkpoint。

## Phase V1 · Clean-slate homepage composition

从零重写 `site/src/App.tsx` 的首页 composition，同时保留 shared route shell 与 truthful content source。

目标 chapters：

1. cinematic full-width hero；
2. editorial problem chapter；
3. sticky Forge scroll story；
4. asymmetric proof field；
5. immersive Studio chapter；
6. publication material chapter；
7. architecture constellation；
8. host/release close；
9. final navigation CTA。

不得继续把旧版三卡 problem wall、generic proof grid、普通 architecture bento 或 detached dashboard-card hero 作为主 composition。

## Phase V2 · 重建 CSS architecture

重写 `site/src/styles/site.css`：只承担 base/reset/layout/accessibility；重写 `site/src/styles/showcase.css`：承担 premium material/motion。

使用：

- CSS Grid named/asymmetric layout；
- `color-mix()` 派生 Story Loom colors；
- radial/conic gradient + mask；
- SVG/CSS loom/thread visuals；
- chrome/instrument surface 上克制的 backdrop blur；
- 有意义的 perspective / layered transform；
- `animation-timeline: view()` / `scroll()` progressive enhancement；
- View Transition styling；
- pointer event 直接更新 CSS variables；
- mobile/reduced-motion fallback。

本 slice 不新增 animation framework。

## Phase V3 · Native bilingual geometry

- 中文 Hero 与 chapter heading 独立于英文调节；
- 不把英文 display line length 硬套给中文；
- machine ID / contract name 只在 proof/provenance 真正需要时显示；
- 保留现有 native-copy quality gate。

## Phase V4 · Destination route coherence

Destination routes 可以比 Home 克制，但必须继承新 material system、typography、header、transition 与 dark/light chapter identity，不能让用户一跳转就像进入另一个产品。

## Phase V5 · Deterministic verification

运行现有 Product Site quality + production build。只有必要时才扩展检查，确保：

- premium rewrite 仍包含 required progressive-enhancement primitives；
- 无 idle infinite animation；
- 无 `requestAnimationFrame` / polling decorative loop；
- locale-specific typography 仍显式存在；
- Story Loom theme 继续是 source authority；
- routes 与 host-neutral build 不变。

## Phase V6 · Visual acceptance

必须 review：

- large desktop；
- 普通 laptop/desktop；
- phone/narrow width；
- `zh-CN` / `en-US`；
- normal / reduced motion。

重点检查：第一印象 premium 程度、章节节奏、是否再次出现过度 card repetition、gradient 上的文本可读性、motion coherence，以及 mobile 是否正确简化。

## Phase V7 · Deploy

继续使用现有 Product Site workflow。只有 quality/build pass 后才接受 deployment。Cloudflare 继续只是可替换 static infrastructure，不进入 Product Site semantics。

## Rollback

Rewrite implementation 尽量保持为一个可独立 revert 的 presentation commit（如验证需要，可跟少量 narrow fix）。Revert 后只能恢复旧视觉，不改变 Core、Studio Host Bridge、Publication 或 production-readiness contracts。

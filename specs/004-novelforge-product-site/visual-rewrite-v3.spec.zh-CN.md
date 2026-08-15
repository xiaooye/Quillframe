# Product Site Visual Rewrite v3 — 已被 Godot Web 契约取代

**状态：** 已由 `spec.zh-CN.md` 中的 Godot Web Product contract 取代。  
**历史角色：** 本文件最初描述迁移前的 DOM/CSS/Vite visual rewrite。下面只保留仍然有效的设计意图；旧实现机制不再具备规范效力。

## 保留的视觉命题

NovelForge 应该像一个**电影感的 editorial instrument / production control room**，而不是 SaaS 卡片目录或文档首页。

当前 Godot implementation 通过以下方式延续这一意图：

- dark Story Loom stage；
- 非对称 control-room composition 与 negative space；
- connected topology，而不是 equal-card grid；
- project/runtime/editorial/evidence/validated 等 semantic surfaces；
- 2D layering、elevation、glow、parallax、animated route packets 与 optical depth；
- 在同一个 live Product runtime 内按 route 改变视觉重心；
- 独立 phone topology，而不是缩放 desktop。

## 当前实现规则

1. Product visual 由 Godot Canvas / `Control` nodes 实现，不使用 DOM/CSS layout 作为 Product runtime。
2. `assets/brand/tokens.json` 继续是 visual authority，并确定性投影到 Godot。
3. 景深限制为 controlled 2.5D；禁止 3D scene stack。
4. 禁止 perpetual idle animation loop。Motion 只围绕 route transition / 用户交互短时运行；pointer parallax 由输入事件驱动。
5. Reduced-motion 必须落到完整、静态、可读的最终状态。
6. Product 保留 `en-US`/`zh-CN`、44px minimum target、keyboard focus 与 visible focus ring。
7. `/docs/**` 继续是独立 Starlight semantic HTML application。
8. Browser acceptance 针对 exported Godot runtime，而不是 Vite Product build。

## Authority

当前要求以以下文件为准：

- `spec.en.md` / `spec.zh-CN.md` — Product contract；
- `plan.en.md` / `plan.zh-CN.md` — Godot replacement plan；
- `tasks.en.md` / `tasks.zh-CN.md` — implementation / release acceptance。

旧版本里的 DOM、CSS animation、scroll-story 或 Vite requirement，除非已经明确重述进上述 current contract，否则全部视为非权威历史设计资料。

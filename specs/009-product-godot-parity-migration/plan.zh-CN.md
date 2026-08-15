# Godot Parity Migration Plan

1. **Shadow bootstrap**：恢复 Godot Web 工程、确定性字体、Compatibility renderer 和独立 CI artifact；production 不切换。
2. **Home parity**：先锁 1440×900 与 390×844 的 header / hero / CTA / launcher / trust pill，解决字体和换行。
3. **Interaction parity**：locale、theme state、browser history、Docs hard navigation、Studio handoff、keyboard/focus。
4. **Route parity**：Product → Architecture → Publication → Inspect → Playground → Agents，逐页以现有 Browser QA 截图为基线迁移。
5. **Visual gate**：同尺寸 baseline/candidate screenshot + diff metric + 人工审图；所有 gate 通过前不 cutover。
6. **Production cutover**：只替换 Product root；`/docs/**` 继续由 Astro/Starlight 拥有。
7. **Post-cutover regression**：保留 Solid baseline 一段时间作为视觉回归证据，确认稳定后再删除旧实现。

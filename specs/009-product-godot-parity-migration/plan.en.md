# Godot Parity Migration Plan

1. **Shadow bootstrap:** restore the Godot Web project, deterministic fonts, Compatibility renderer, and an independent CI artifact; do not switch production.
2. **Home parity:** first lock the 1440×900 and 390×844 header, hero, CTAs, launcher, and trust pill, including font and line-wrap corrections.
3. **Interaction parity:** locale, theme state, browser history, Docs hard navigation, Studio handoff, keyboard, and focus.
4. **Route parity:** migrate Product → Architecture → Publication → Inspect → Playground → Agents, using the existing Browser QA screenshots as the per-route baseline.
5. **Visual gate:** same-size baseline/candidate screenshots, diff metric, and human visual review; do not cut over until every gate passes.
6. **Production cutover:** replace only the Product root; `/docs/**` remains owned by Astro/Starlight.
7. **Post-cutover regression:** retain the Solid baseline for a period as visual-regression evidence, then remove the old implementation after stability is confirmed.

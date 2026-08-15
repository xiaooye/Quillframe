# Product Site CSS architecture

The Product Site has one stylesheet entrypoint: `index.css`. `main.tsx` must not import route CSS directly.

The cascade is intentionally split into four responsibilities:

1. **Foundation** — `site.css`, generated WeiUI, Story Loom, and the shared repo-level `novelforge-product-language.css` tokens.
2. **Stable product primitives** — shared surface/layout contracts such as `product-surface.css` and `unified-product-app.css`.
3. **Route-owned feature styles** — Architecture, Publication, Inspector, Playground, Agents, and other specialized surfaces. A route owns only its feature body; it must not recreate app chrome or global state.
4. **Product-language composition** — kawaii/product-specific composition loaded after feature defaults. Cross-cutting resilience/accessibility rules belong in the final hardening layer, not in ad-hoc `*-fixes.css` or `*-audit.css` files.

Do not restore a final "audit override" stylesheet. If a visual rule is authoritative, put it in the component or route layer that owns it. New global tokens shared with Studio belong in `assets/brand/novelforge-product-language.css`.

# NovelForge Studio Cloud Host

The hosted Studio surface is a delivery host, not a NovelForge Core runtime.

- Production target: `https://studio.novelforge.wei-dev.com`
- Cloudflare Pages project: `novelforge-studio`
- Product surface: `cloud_ui`
- Core host: unbound by default
- Authority: `false`

The same SolidJS application is used by Local Web and the hosted surface. Local Web receives an ephemeral token injected by `studio/local_server.py`; the static Cloudflare build retains the `__NOVELFORGE_STUDIO_TOKEN__` placeholder. Studio treats the unresolved placeholder as an explicit unbound-host state and does not issue `/api/bridge/invoke` requests.

Project-backed queries remain available only when a real Host Bridge transport is bound. Cloudflare Pages, Pages Functions, Workers, KV, D1, Durable Objects, and other Cloudflare persistence are not NovelForge Core authority and are not used to synthesize project/runtime state in this slice.

Cloudflare Pages serves the SPA directly. `public/_headers` supplies static security headers and `public/robots.txt` keeps the product shell out of search indexing. The hosted build deliberately has no top-level `404.html`, so Pages' native SPA fallback can route deep links back to the application shell.

Future remote Core connectivity must reuse the public typed Host Bridge/query-command contracts rather than adding a Cloudflare-specific semantic backend.
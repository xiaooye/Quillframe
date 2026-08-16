#!/usr/bin/env bash
set -euo pipefail

if ! command -v godot >/dev/null 2>&1; then
  echo "godot executable is required for the production Web export" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT_DIR="${ROOT_DIR}/dist"
DOCS_DIR="${OUT_DIR}/docs"
STAGE_DIR="${ROOT_DIR}/dist-godot-shadow"
MAX_PAGE_ASSET_BYTES="${MAX_PAGE_ASSET_BYTES:-26214400}"

node "${ROOT_DIR}/scripts/godot-production-quality.mjs"

# Docs are a permanent Astro/Starlight ownership boundary and must already have
# been built before the Godot Product root is assembled.
test -s "${DOCS_DIR}/index.html" || {
  echo "Expected Starlight output at ${DOCS_DIR}/index.html before Godot cutover build" >&2
  exit 1
}

# There is exactly one Godot Web exporter in the Product build graph.
# build-godot-shadow.sh is the path already proven by route parity and by the
# slim-template asset ceiling gate. Production consumes that exact artifact
# instead of maintaining a second export path with subtly different behavior.
bash "${ROOT_DIR}/scripts/build-godot-shadow.sh"

test -s "${STAGE_DIR}/index.html"
compgen -G "${STAGE_DIR}/index*.wasm" >/dev/null
compgen -G "${STAGE_DIR}/index*.pck" >/dev/null
grep -q 'data-novelforge-runtime="loading"' "${STAGE_DIR}/index.html"
grep -q '<base href="/"' "${STAGE_DIR}/index.html"

# Replace only the Product root. /docs/** remains the independently built
# Astro/Starlight application.
find "${OUT_DIR}" -mindepth 1 -maxdepth 1 ! -name docs -exec rm -rf {} +
cp -a "${STAGE_DIR}/." "${OUT_DIR}/"
cp "${ROOT_DIR}/public/_redirects" "${OUT_DIR}/_redirects"

test -s "${OUT_DIR}/index.html"
test -s "${DOCS_DIR}/index.html"
test -s "${OUT_DIR}/_redirects"
compgen -G "${OUT_DIR}/index*.wasm" >/dev/null
compgen -G "${OUT_DIR}/index*.pck" >/dev/null
grep -q 'data-novelforge-runtime="loading"' "${OUT_DIR}/index.html"
grep -q '<base href="/"' "${OUT_DIR}/index.html"
for route in product studio architecture publication inspect playground agents changelog; do
  grep -q "^/${route} /index.html 200$" "${OUT_DIR}/_redirects"
done

grep -q '^/docs /docs/ 301$' "${OUT_DIR}/_redirects"
grep -q '^/docs/en /docs/en/ 301$' "${OUT_DIR}/_redirects"

python3 - "${OUT_DIR}" "${MAX_PAGE_ASSET_BYTES}" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
limit = int(sys.argv[2])
offenders = []
for path in root.rglob('*'):
    if not path.is_file():
        continue
    size = path.stat().st_size
    if size >= limit:
        offenders.append((str(path.relative_to(root)), size))
if offenders:
    for name, size in offenders:
        print(f"Cloudflare Pages asset ceiling exceeded: {name} = {size} bytes", file=sys.stderr)
    raise SystemExit(2)
print(f"Cloudflare Pages asset ceiling: PASS (< {limit} bytes per file)")
PY

rm -rf "${STAGE_DIR}"
echo "NovelForge Godot Product root assembled at ${OUT_DIR}; Starlight docs preserved at ${DOCS_DIR}"

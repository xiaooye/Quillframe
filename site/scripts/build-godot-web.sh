#!/usr/bin/env bash
set -euo pipefail

if ! command -v godot >/dev/null 2>&1; then
  echo "godot executable is required for the production Web export" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GODOT_DIR="${ROOT_DIR}/godot"
OUT_DIR="${ROOT_DIR}/dist"
DOCS_DIR="${OUT_DIR}/docs"
SMOKE_LOG="${TMPDIR:-/tmp}/novelforge-godot-production-smoke.log"
MAX_PAGE_ASSET_BYTES="${MAX_PAGE_ASSET_BYTES:-26214400}"

node "${ROOT_DIR}/scripts/godot-production-quality.mjs"
bash "${ROOT_DIR}/scripts/fetch-godot-fonts.sh"

# Docs are a permanent Astro/Starlight ownership boundary and must already have
# been built before the Godot root export starts.
test -s "${DOCS_DIR}/index.html" || {
  echo "Expected Starlight output at ${DOCS_DIR}/index.html before Godot cutover build" >&2
  exit 1
}

# Replace the Product SPA root while preserving the independently built docs app.
find "${OUT_DIR}" -mindepth 1 -maxdepth 1 ! -name docs -exec rm -rf {} +

godot --headless --path "${GODOT_DIR}" --import

set +e
godot --headless --path "${GODOT_DIR}" --quit-after 2 >"${SMOKE_LOG}" 2>&1
status=$?
set -e
cat "${SMOKE_LOG}"
if [ "${status}" -ne 0 ] || grep -Eq 'SCRIPT ERROR|Parse Error|Invalid call|Invalid access|Cannot open file|No loader found|requires the pinned' "${SMOKE_LOG}"; then
  echo "Godot production smoke test failed" >&2
  exit 1
fi

godot --headless --path "${GODOT_DIR}" --export-release Web "${OUT_DIR}/index.html"
cp "${ROOT_DIR}/public/_redirects" "${OUT_DIR}/_redirects"

test -s "${OUT_DIR}/index.html"
test -s "${DOCS_DIR}/index.html"
test -s "${OUT_DIR}/_redirects"
compgen -G "${OUT_DIR}/index*.wasm" >/dev/null
compgen -G "${OUT_DIR}/index*.pck" >/dev/null
grep -q 'data-novelforge-runtime="loading"' "${OUT_DIR}/index.html"
grep -q '<base href="/">' "${OUT_DIR}/index.html"
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

echo "NovelForge Godot production root exported to ${OUT_DIR}; Starlight docs preserved at ${DOCS_DIR}"

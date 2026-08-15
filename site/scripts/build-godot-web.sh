#!/usr/bin/env bash
set -euo pipefail

if ! command -v godot >/dev/null 2>&1; then
  echo "godot executable is required for the product runtime export" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GODOT_DIR="${ROOT_DIR}/godot"
DIST_DIR="${ROOT_DIR}/dist"
SMOKE_LOG="${TMPDIR:-/tmp}/novelforge-godot-smoke.log"

mkdir -p "${DIST_DIR}"

# Import once so CI catches resource/script errors before the runtime smoke test.
godot --headless --path "${GODOT_DIR}" --editor --quit-after 1

# Instantiate the real main scene outside the browser. Browser-only bridge code
# is feature-gated, so this catches scene/runtime regressions without WebGL.
set +e
godot --headless --path "${GODOT_DIR}" --quit-after 2 >"${SMOKE_LOG}" 2>&1
smoke_status=$?
set -e
cat "${SMOKE_LOG}"
if [ "${smoke_status}" -ne 0 ] || grep -Eq 'SCRIPT ERROR|Parse Error|Invalid call|Invalid access' "${SMOKE_LOG}"; then
  echo "Godot runtime smoke test failed" >&2
  exit 1
fi

godot --headless --path "${GODOT_DIR}" --export-release Web "${DIST_DIR}/index.html"

test -s "${DIST_DIR}/index.html"
compgen -G "${DIST_DIR}/index*.wasm" >/dev/null
compgen -G "${DIST_DIR}/index*.pck" >/dev/null

grep -q 'data-novelforge-runtime="loading"' "${DIST_DIR}/index.html"
grep -q 'NovelForge' "${DIST_DIR}/index.html"

# The Docs application is built first and must survive the product-root export.
test -d "${DIST_DIR}/docs"

echo "Godot product runtime exported to ${DIST_DIR}"

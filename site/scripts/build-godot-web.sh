#!/usr/bin/env bash
set -euo pipefail

if ! command -v godot >/dev/null 2>&1; then
  echo "godot executable is required for the product runtime export" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GODOT_DIR="${ROOT_DIR}/godot"
DIST_DIR="${ROOT_DIR}/dist"

mkdir -p "${DIST_DIR}"

# Import once so CI catches resource/script errors before the release export.
godot --headless --path "${GODOT_DIR}" --editor --quit-after 1

godot --headless --path "${GODOT_DIR}" --export-release Web "${DIST_DIR}/index.html"

test -s "${DIST_DIR}/index.html"
compgen -G "${DIST_DIR}/index*.wasm" >/dev/null
compgen -G "${DIST_DIR}/index*.pck" >/dev/null

# The Docs application is built first and must survive the product-root export.
test -d "${DIST_DIR}/docs"

echo "Godot product runtime exported to ${DIST_DIR}"

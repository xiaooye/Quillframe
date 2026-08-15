#!/usr/bin/env bash
set -euo pipefail

if ! command -v godot >/dev/null 2>&1; then
  echo "godot executable is required for the parity shadow export" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GODOT_DIR="${ROOT_DIR}/godot"
OUT_DIR="${ROOT_DIR}/dist-godot-shadow"
SMOKE_LOG="${TMPDIR:-/tmp}/novelforge-godot-shadow-smoke.log"

bash "${ROOT_DIR}/scripts/fetch-godot-fonts.sh"
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

godot --headless --path "${GODOT_DIR}" --editor --quit-after 2
set +e
godot --headless --path "${GODOT_DIR}" --quit-after 2 >"${SMOKE_LOG}" 2>&1
status=$?
set -e
cat "${SMOKE_LOG}"
if [ "${status}" -ne 0 ] || grep -Eq 'SCRIPT ERROR|Parse Error|Invalid call|Invalid access|Cannot open file' "${SMOKE_LOG}"; then
  echo "Godot parity shadow smoke test failed" >&2
  exit 1
fi

godot --headless --path "${GODOT_DIR}" --export-release Web "${OUT_DIR}/index.html"

test -s "${OUT_DIR}/index.html"
compgen -G "${OUT_DIR}/index*.wasm" >/dev/null
compgen -G "${OUT_DIR}/index*.pck" >/dev/null
grep -q 'data-novelforge-godot-shadow="loading"' "${OUT_DIR}/index.html"
grep -q 'Godot parity shadow' "${OUT_DIR}/index.html"

echo "Godot parity shadow exported to ${OUT_DIR}"

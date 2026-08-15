#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FONT_DIR="${ROOT_DIR}/godot/generated"
mkdir -p "${FONT_DIR}"

fetch_and_verify() {
  local url="$1"
  local output="$2"
  local expected="$3"
  if [ ! -s "${output}" ]; then
    curl --fail --location --silent --show-error "${url}" --output "${output}.tmp"
    mv "${output}.tmp" "${output}"
  fi
  local actual
  actual=$(git hash-object "${output}")
  if [ "${actual}" != "${expected}" ]; then
    echo "Pinned font asset mismatch: ${output}" >&2
    echo "expected git blob ${expected}" >&2
    echo "actual   git blob ${actual}" >&2
    rm -f "${output}"
    exit 1
  fi
}

# Primary bilingual UI font.
fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf" \
  "${FONT_DIR}/NotoSansSC-wght.ttf" \
  "fb0637bafbcd804fe32152370a1225990745b4bc"
fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt" \
  "${FONT_DIR}/NotoSansSC-OFL.txt" \
  "1c9f43281b8f216c5461fe9ac729afbade7724e4"

# Deterministic Unicode fallbacks for the existing Kawaii Atelier symbols and kaomoji.
fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf" \
  "${FONT_DIR}/NotoSansSymbols2-Regular.ttf" \
  "caf89dd0e60e23ac39ce18da823095959d409437"
fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols2/OFL.txt" \
  "${FONT_DIR}/NotoSansSymbols2-OFL.txt" \
  "7c95767f5c669c448148e7e6c8fc4ee2c85128b1"

fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansthai/NotoSansThai%5Bwdth%2Cwght%5D.ttf" \
  "${FONT_DIR}/NotoSansThai-wdth-wght.ttf" \
  "34b48ab6f74867dbfce19410a2f452abef34e3ff"
fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansthai/OFL.txt" \
  "${FONT_DIR}/NotoSansThai-OFL.txt" \
  "7fa8dcb08ce4d2667b683ac4a8e79166e44e5277"

fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf" \
  "${FONT_DIR}/NotoSansArabic-wdth-wght.ttf" \
  "f1d01edce4ebaedcbe9a06fc75fec07b304ec3df"
fetch_and_verify \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/OFL.txt" \
  "${FONT_DIR}/NotoSansArabic-OFL.txt" \
  "14c589f6384505ede3f8e52627d397513af3662d"

printf 'Pinned Godot font set ready:'
for asset in \
  NotoSansSC-wght.ttf \
  NotoSansSymbols2-Regular.ttf \
  NotoSansThai-wdth-wght.ttf \
  NotoSansArabic-wdth-wght.ttf; do
  printf ' %s=%s' "${asset}" "$(du -h "${FONT_DIR}/${asset}" | cut -f1)"
done
printf '\n'

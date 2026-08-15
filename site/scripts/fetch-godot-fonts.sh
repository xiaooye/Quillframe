#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FONT_DIR="${ROOT_DIR}/godot/generated"
FONT_FILE="${FONT_DIR}/NotoSansSC-wght.ttf"
LICENSE_FILE="${FONT_DIR}/NotoSansSC-OFL.txt"
FONT_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf"
LICENSE_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt"
EXPECTED_GIT_BLOB="fb0637bafbcd804fe32152370a1225990745b4bc"
EXPECTED_LICENSE_BLOB="1c9f43281b8f216c5461fe9ac729afbade7724e4"

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

fetch_and_verify "${FONT_URL}" "${FONT_FILE}" "${EXPECTED_GIT_BLOB}"
fetch_and_verify "${LICENSE_URL}" "${LICENSE_FILE}" "${EXPECTED_LICENSE_BLOB}"

echo "Pinned Noto Sans SC font ready: $(du -h "${FONT_FILE}" | cut -f1)"

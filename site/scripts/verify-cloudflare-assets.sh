#!/usr/bin/env bash
set -euo pipefail

root="${1:-dist}"
limit="${2:-$((25 * 1024 * 1024))}"

if [ ! -d "${root}" ]; then
  echo "Asset root does not exist: ${root}" >&2
  exit 2
fi

largest_bytes=0
largest_path=""
file_count=0

while IFS= read -r -d '' file; do
  bytes=$(stat -c '%s' "${file}")
  file_count=$((file_count + 1))
  if [ "${bytes}" -gt "${largest_bytes}" ]; then
    largest_bytes="${bytes}"
    largest_path="${file}"
  fi
done < <(find "${root}" -type f -print0)

if [ "${file_count}" -eq 0 ]; then
  echo "No production assets found under ${root}" >&2
  exit 2
fi

printf 'Production assets: %s files\n' "${file_count}"
printf 'Largest production asset: %s bytes %s\n' "${largest_bytes}" "${largest_path}"
printf 'Cloudflare Pages individual-file ceiling: %s bytes\n' "${limit}"

if [ "${largest_bytes}" -ge "${limit}" ]; then
  echo "Production asset exceeds Cloudflare Pages 25 MiB individual-file limit." >&2
  exit 1
fi

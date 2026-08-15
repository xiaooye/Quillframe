#!/usr/bin/env bash
set -euo pipefail

# Build the intentionally small NovelForge Web export template. The product UI
# uses Control/CanvasItem only, so shipping the general-purpose 3D, physics,
# media, networking, import, XR, and advanced-editor GUI stacks is unnecessary.
# JavaScriptBridge remains enabled because product routing/readiness uses it.

GODOT_RELEASE="${GODOT_RELEASE:-4.7.1-stable}"
GODOT_SOURCE_SHA256="${GODOT_SOURCE_SHA256:-0230d490846467c4fd772cc70b08dc56cb3adfedd55d039de0af74ddfdba00eb}"
OUTPUT_DIR="${1:-${HOME}/.cache/novelforge-godot-template}"
WORK_ROOT="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/novelforge-godot-template"
SOURCE_ARCHIVE="${WORK_ROOT}/godot-${GODOT_RELEASE}.tar.xz"
SOURCE_DIR="${WORK_ROOT}/godot-${GODOT_RELEASE}"
OUTPUT_TEMPLATE="${OUTPUT_DIR}/web_nothreads_release.zip"

if ! command -v emcc >/dev/null 2>&1; then
  echo "emcc is required to compile the NovelForge Godot Web template" >&2
  exit 1
fi
if ! command -v scons >/dev/null 2>&1; then
  echo "scons is required to compile the NovelForge Godot Web template" >&2
  exit 1
fi

mkdir -p "${WORK_ROOT}" "${OUTPUT_DIR}"
rm -rf "${SOURCE_DIR}"

curl -fsSL \
  "https://github.com/godotengine/godot/releases/download/${GODOT_RELEASE}/godot-${GODOT_RELEASE}.tar.xz" \
  -o "${SOURCE_ARCHIVE}"
echo "${GODOT_SOURCE_SHA256}  ${SOURCE_ARCHIVE}" | sha256sum --check --status

tar -xJf "${SOURCE_ARCHIVE}" -C "${WORK_ROOT}"
cd "${SOURCE_DIR}"

JOBS="${NOVELFORGE_GODOT_BUILD_JOBS:-$(nproc)}"

scons \
  platform=web \
  target=template_release \
  threads=no \
  optimize=size_extra \
  debug_symbols=no \
  disable_3d=yes \
  disable_advanced_gui=yes \
  disable_physics_2d=yes \
  disable_physics_3d=yes \
  module_astcenc_enabled=no \
  module_basis_universal_enabled=no \
  module_bcdec_enabled=no \
  module_bmp_enabled=no \
  module_camera_enabled=no \
  module_csg_enabled=no \
  module_dds_enabled=no \
  module_enet_enabled=no \
  module_etcpak_enabled=no \
  module_fbx_enabled=no \
  module_gltf_enabled=no \
  module_gridmap_enabled=no \
  module_hdr_enabled=no \
  module_interactive_music_enabled=no \
  module_jsonrpc_enabled=no \
  module_ktx_enabled=no \
  module_mbedtls_enabled=no \
  module_meshoptimizer_enabled=no \
  module_mp3_enabled=no \
  module_mobile_vr_enabled=no \
  module_multiplayer_enabled=no \
  module_navigation_2d_enabled=no \
  module_navigation_3d_enabled=no \
  module_noise_enabled=no \
  module_ogg_enabled=no \
  module_openxr_enabled=no \
  module_raycast_enabled=no \
  module_regex_enabled=no \
  module_svg_enabled=no \
  module_tga_enabled=no \
  module_theora_enabled=no \
  module_tinyexr_enabled=no \
  module_upnp_enabled=no \
  module_vhacd_enabled=no \
  module_vorbis_enabled=no \
  module_webrtc_enabled=no \
  module_websocket_enabled=no \
  module_webxr_enabled=no \
  module_zip_enabled=no \
  "-j${JOBS}"

BUILT_TEMPLATE="${SOURCE_DIR}/bin/godot.web.template_release.wasm32.zip"
test -s "${BUILT_TEMPLATE}"
cp "${BUILT_TEMPLATE}" "${OUTPUT_TEMPLATE}"

# Inspect the actual engine payload inside the template. The final exported
# index.wasm has the same engine payload plus negligible export glue, and must
# remain below Cloudflare Pages' 25 MiB individual-asset ceiling.
TMP_UNPACK="${WORK_ROOT}/template-unpack"
rm -rf "${TMP_UNPACK}"
mkdir -p "${TMP_UNPACK}"
unzip -q "${OUTPUT_TEMPLATE}" -d "${TMP_UNPACK}"
WASM_PATH=$(find "${TMP_UNPACK}" -maxdepth 2 -type f -name '*.wasm' -print -quit)
test -n "${WASM_PATH}"
WASM_BYTES=$(stat -c '%s' "${WASM_PATH}")
PAGES_LIMIT=$((25 * 1024 * 1024))
TARGET_LIMIT=$((24 * 1024 * 1024))

printf 'NovelForge custom Godot template: %s bytes (%s)\n' "${WASM_BYTES}" "${WASM_PATH##*/}"
if [ "${WASM_BYTES}" -ge "${TARGET_LIMIT}" ]; then
  echo "Custom Godot Web engine is ${WASM_BYTES} bytes; target is <24 MiB to leave deployment headroom (Cloudflare hard limit: ${PAGES_LIMIT})." >&2
  exit 1
fi

cat > "${OUTPUT_DIR}/build-meta.txt" <<EOF
schema=novelforge_godot_web_template_v1
godot_release=${GODOT_RELEASE}
threads=false
optimize=size_extra
disable_3d=true
disable_advanced_gui=true
disable_physics_2d=true
disable_physics_3d=true
wasm_bytes=${WASM_BYTES}
cloudflare_asset_limit_bytes=${PAGES_LIMIT}
authority=false
EOF

printf 'Custom Web template ready: %s\n' "${OUTPUT_TEMPLATE}"

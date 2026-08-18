import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const dist = new URL("../dist/", import.meta.url);
const assetsDir = new URL("assets/", dist);
const entries = await readdir(assetsDir, { withFileTypes: true });
const files = entries.filter((entry) => entry.isFile()).map((entry) => entry.name).sort();

async function measure(extension) {
  const selected = files.filter((name) => name.endsWith(extension));
  let bytes = 0;
  let gzipBytes = 0;
  let largestBytes = 0;
  for (const name of selected) {
    const path = join(assetsDir.pathname, name);
    const data = await readFile(path);
    const size = (await stat(path)).size;
    bytes += size;
    gzipBytes += gzipSync(data).byteLength;
    largestBytes = Math.max(largestBytes, size);
  }
  return { files: selected.length, bytes, gzip_bytes: gzipBytes, largest_bytes: largestBytes };
}

const js = await measure(".js");
const css = await measure(".css");
const integration = JSON.parse(await readFile(new URL("../../../assets/brand/weiui.integration.json", import.meta.url), "utf8"));

const payload = {
  schema: "quillframe_studio_footprint_v1",
  generated_at: new Date().toISOString(),
  measurement: "production_build_artifacts",
  assets: { javascript: js, css },
  runtime_contract: {
    weiui_runtime_javascript_required: integration.consumption.runtime_javascript_from_weiui,
    persistent_database_required_by_hosted_ui: false,
    core_required_for_browser_preflight: false,
    core_required_for_local_playground_preview: false,
  },
  not_measured: ["idle_memory_bytes", "startup_duration_ms", "interactive_latency_ms"],
};

const targetDir = new URL(".well-known/", dist);
await mkdir(targetDir, { recursive: true });
await writeFile(new URL("quillframe-studio-footprint.json", targetDir), `${JSON.stringify(payload, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ schema: payload.schema, js_bytes: js.bytes, css_bytes: css.bytes, js_gzip_bytes: js.gzip_bytes, css_gzip_bytes: css.gzip_bytes }));

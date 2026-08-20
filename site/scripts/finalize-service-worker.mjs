import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

export const PLACEHOLDER = "__QF_SITE_CACHE_VERSION__";
export const METADATA_PATH = "generated/quillframe-site-service-worker.json";

export async function listBuildFiles(distDir) {
  const output = [];
  async function walk(current) {
    for (const entry of await fs.readdir(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      const relative = path.relative(distDir, absolute).split(path.sep).join("/");
      if (entry.isDirectory()) {
        await walk(absolute);
      } else if (entry.isFile() && relative !== "sw.js" && relative !== METADATA_PATH && !entry.name.startsWith(".") && !entry.name.includes(".tmp-") && !entry.name.endsWith(".tmp")) {
        output.push(relative);
      }
    }
  }
  await walk(distDir);
  return output.sort();
}

export async function hashBuildFingerprint(files, distDir = process.cwd()) {
  const hash = crypto.createHash("sha256");
  for (const relative of [...files].sort()) {
    const bytes = await fs.readFile(path.join(distDir, relative));
    const header = Buffer.from(JSON.stringify({ path: relative, byteLength: bytes.byteLength }, null, 0), "utf8");
    hash.update(header);
    hash.update(Buffer.from([0]));
    hash.update(bytes);
  }
  return `sha256:${hash.digest("hex")}`;
}

export async function atomicWrite(file, contents) {
  const temporary = `${file}.tmp-${process.pid}-${Date.now()}`;
  let owned = false;
  try {
    await fs.writeFile(temporary, contents, { flag: "wx" });
    owned = true;
    await fs.rename(temporary, file);
    owned = false;
  } finally {
    if (owned) await fs.rm(temporary, { force: true });
  }
}

export async function finalizeServiceWorker({ distDir, atomicWriter = atomicWrite, rollbackWriter = atomicWrite }) {
  const swPath = path.join(distDir, "sw.js");
  const source = await fs.readFile(swPath, "utf8");
  const metadataPath = path.join(distDir, METADATA_PATH);
  let originalMetadata;
  try { originalMetadata = await fs.readFile(metadataPath); } catch (error) { if (error.code !== "ENOENT") throw error; }
  const placeholders = source.match(new RegExp(PLACEHOLDER, "g")) ?? [];
  const finalizedMatches = source.match(/quillframe-site-[0-9a-f]{16}/g) ?? [];
  if (placeholders.length !== 1 && !(placeholders.length === 0 && finalizedMatches.length === 1)) throw new Error("service worker placeholder must occur exactly once or already be finalized");
  for (const required of ["docs/index.html", "docs/en/index.html"]) {
    try { if (!(await fs.lstat(path.join(distDir, required))).isFile()) throw new Error("not regular"); } catch { throw new Error(`required shell missing: ${required}`); }
  }
  const files = await listBuildFiles(distDir);
  const fingerprint = await hashBuildFingerprint(files, distDir);
  const cacheName = `quillframe-site-${fingerprint.slice("sha256:".length, "sha256:".length + 16)}`;
  if (placeholders.length === 0 && finalizedMatches[0] !== cacheName) throw new Error("finalized cache literal mismatch");
  const finalized = placeholders.length === 1 ? source.replace(PLACEHOLDER, cacheName.slice("quillframe-site-".length)) : source;
  if (finalized.includes(PLACEHOLDER) || (finalized.match(/quillframe-site-[0-9a-f]{16}/g) ?? []).length !== 1) throw new Error("finalized cache literal invalid");
  const metadata = {
    schema: "quillframe_site_service_worker_finalizer_v1",
    fingerprint,
    cache_name: cacheName,
    source_files: files,
    required_shells: ["docs/", "docs/en/"],
    sw_path: "sw.js",
    authority: false,
  };
  try {
    await atomicWriter(swPath, finalized);
    await fs.mkdir(path.join(distDir, "generated"), { recursive: true });
    await atomicWriter(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
  } catch (primary) {
    try {
      await rollbackWriter(swPath, source);
      if (originalMetadata) await rollbackWriter(metadataPath, originalMetadata);
      else await fs.rm(metadataPath, { force: true });
      const leftovers = await fs.readdir(distDir, { recursive: true });
      for (const leftover of leftovers) if (String(leftover).includes(".tmp-")) await fs.rm(path.join(distDir, leftover), { force: true });
    } catch (rollback) {
      throw new AggregateError([primary, rollback], "service-worker publication failed and rollback failed");
    }
    throw new Error(`service-worker publication failed; rollback completed: ${primary instanceof Error ? primary.message : String(primary)}`, { cause: primary });
  }
  return metadata;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const distDir = path.resolve(new URL("../dist", import.meta.url).pathname);
  console.log(JSON.stringify(await finalizeServiceWorker({ distDir }), null, 2));
}

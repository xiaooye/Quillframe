export type CheckState = "pass" | "warn" | "fail";
export type InspectionStatus = "coherent" | "scaffold" | "incomplete" | "conflict";
export type InspectionCheck = { key: string; state: CheckState; title: string; detail: string };
export type NativeManifest = { schema: "quillframe_project_v1_0"; id: string; title: string; language: string };
export type NativeContext = { context_schema: "quillframe_project_context_v1_0"; manifest: NativeManifest; manifest_fingerprint: string; scope: "novel"; data_boundary: ".quillframe/data"; authority: false };
export type ProjectInspection = { rootName: string; fileCount: number; totalBytes: number; project: NativeManifest; context?: NativeContext; status: InspectionStatus; legacy_metadata_rejected: boolean; checks: InspectionCheck[]; directories: Array<{ name: string; present: boolean }> };

const requiredDirectories = [".quillframe/data"];
const evidenceDirectories = ["evals", "tests", "regressions"];
const rootRelative = (file: File): string => {
  const raw = file.webkitRelativePath || file.name;
  if (!raw || raw.includes("\0") || raw.startsWith("/") || raw.startsWith("\\") || /^[A-Za-z]:/.test(raw)) throw new Error("project_path_invalid");
  const parts = raw.replaceAll("\\", "/").split("/");
  if (parts.some((part) => !part || part === "." || part === "..")) throw new Error("project_path_invalid");
  if (file.webkitRelativePath && parts.length < 2) throw new Error("project_path_invalid");
  return file.webkitRelativePath ? parts.slice(1).join("/") : parts.join("/");
};
const rootName = (files: File[]) => {
  const raw = (files[0]?.webkitRelativePath || files[0]?.name || "Quillframe Project").replaceAll("\\", "/");
  return raw.split("/").filter(Boolean)[0] || "Quillframe Project";
};

function parseManifest(source: string): NativeManifest | undefined {
  const values: Record<string, string> = {};
  for (const raw of source.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, "").trim();
    if (!line) continue;
    const match = line.match(/^([A-Za-z0-9_-]+)\s*=\s*(["'])(.*?)\2$/);
    if (!match || values[match[1]] !== undefined) return undefined;
    values[match[1]] = match[3];
  }
  if (Object.keys(values).length !== 4 || Object.keys(values).some((key) => !["schema", "id", "title", "language"].includes(key))) return undefined;
  const schema = values.schema.trim();
  if (schema !== "quillframe_project_v1_0") return undefined;
  if (!values.id || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(values.id)) return undefined;
  const title = values.title.trim();
  const language = values.language.trim();
  if (!title || !language) return undefined;
  return { schema: "quillframe_project_v1_0", id: values.id, title, language };
}

async function fingerprint(manifest: NativeManifest) {
  const canonical = JSON.stringify({ id: manifest.id, language: manifest.language, schema: manifest.schema, title: manifest.title });
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

export async function inspectProjectFiles(fileList: FileList | File[], zh = false): Promise<ProjectInspection> {
  const files = Array.from(fileList);
  const entries = files.map((file) => ({ file, path: rootRelative(file) }));
  const manifests = entries.filter(({ path }) => path.toLowerCase() === "quillframe.toml");
  const legacy = entries.filter(({ path }) => /(?:^|\/)(?:quillframe|framework)\.(?:lock|attestation)\.json$/i.test(path)).map(({ path }) => path);
  const listedPaths = entries.map(({ path }) => path.toLowerCase());
  const hasDirectory = (directory: string) => listedPaths.some((pathname) => pathname === directory || pathname.startsWith(`${directory}/`));
  const directories = [...requiredDirectories, ...evidenceDirectories].map((name) => ({ name, present: hasDirectory(name) }));
  const base = { rootName: rootName(files), fileCount: files.length, totalBytes: files.reduce((sum, file) => sum + file.size, 0), directories };
  const checks: InspectionCheck[] = [];
  const push = (key: string, state: CheckState, title: string, detail: string) => checks.push({ key, state, title, detail });
  if (legacy.length) {
    push("legacy", "warn", "Legacy metadata rejected", legacy.join(", "));
    return { ...base, project: {} as NativeManifest, status: "conflict", legacy_metadata_rejected: true, checks };
  }
  const manifest = manifests.length === 1 ? parseManifest(await manifests[0].file.text()) : undefined;
  if (!manifest) {
    push("manifest", manifests.length ? "warn" : "fail", "quillframe.toml", manifests.length ? "native four-key manifest is invalid, duplicated, or outside the selected project root" : (zh ? "没有找到 quillframe.toml。" : "Native manifest not found."));
    return { ...base, project: {} as NativeManifest, status: manifests.length ? "scaffold" : "incomplete", legacy_metadata_rejected: false, checks };
  }
  const context: NativeContext = { context_schema: "quillframe_project_context_v1_0", manifest, manifest_fingerprint: await fingerprint(manifest), scope: "novel", data_boundary: ".quillframe/data", authority: false };
  push("manifest", "pass", "quillframe.toml", "quillframe_project_v1_0 · four keys");
  push("context", "pass", "quillframe_project_context_v1_0", "scope=novel · authority=false");
  push("fingerprint", "pass", "manifest_fingerprint", context.manifest_fingerprint);
  push("boundary", hasDirectory(".quillframe/data") ? "pass" : "warn", ".quillframe/data", hasDirectory(".quillframe/data") ? "native data boundary present" : "native data boundary not selected");
  return { ...base, project: manifest, context, status: "coherent", legacy_metadata_rejected: false, checks };
}

import { For, Show, createMemo, createSignal } from "solid-js";
import type { Locale } from "./content";

type CheckState = "pass" | "warn" | "fail";

type InspectionCheck = {
  key: string;
  state: CheckState;
  title: string;
  detail: string;
};

type ProjectIdentity = {
  id?: string;
  title?: string;
  language?: string;
  version?: string;
  schema?: string;
};

type FrameworkIdentity = {
  repository?: string;
  version?: string;
  commit?: string;
  fingerprint?: string;
};

type ProjectInspection = {
  rootName: string;
  fileCount: number;
  totalBytes: number;
  manifestPath?: string;
  lockPath?: string;
  attestationPath?: string;
  project: ProjectIdentity;
  framework: FrameworkIdentity;
  attestation: FrameworkIdentity;
  status: "coherent" | "scaffold" | "incomplete" | "conflict";
  checks: InspectionCheck[];
  directories: Array<{ name: string; present: boolean }>;
};

type Props = {
  locale: Locale;
};

const requiredDirectories = ["profiles", "bible", "state", "plans", "manuscripts", "research"];
const evidenceDirectories = ["evals", "tests", "regressions"];

function normalizePath(file: File) {
  return (file.webkitRelativePath || file.name).replaceAll("\\", "/").replace(/^\.\//, "");
}

function relativeToProject(pathname: string) {
  const parts = pathname.split("/").filter(Boolean);
  return parts.length > 1 ? parts.slice(1).join("/") : parts[0] ?? pathname;
}

function basename(pathname: string) {
  return pathname.split("/").filter(Boolean).at(-1) ?? pathname;
}

function rootNameFor(files: File[]) {
  const first = normalizePath(files[0] ?? new File([], "project"));
  const parts = first.split("/").filter(Boolean);
  return parts.length > 1 ? parts[0] : "NovelForge Project";
}

function pickTomlValue(source: string, keys: string[]) {
  for (const key of keys) {
    const expression = new RegExp(`^\\s*${key.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}\\s*=\\s*[\"']([^\"']+)[\"']\\s*(?:#.*)?$`, "mi");
    const match = source.match(expression);
    if (match?.[1]) return match[1].trim();
  }
  return undefined;
}

function nested(value: unknown, candidates: string[]) {
  if (!value || typeof value !== "object") return undefined;
  for (const candidate of candidates) {
    let current: unknown = value;
    for (const part of candidate.split(".")) {
      if (!current || typeof current !== "object" || !(part in current)) {
        current = undefined;
        break;
      }
      current = (current as Record<string, unknown>)[part];
    }
    if (typeof current === "string" && current.trim()) return current.trim();
  }
  return undefined;
}

function frameworkIdentity(value: unknown): FrameworkIdentity {
  return {
    repository: nested(value, ["framework.repository", "repository", "source.repository", "dependency.repository"]),
    version: nested(value, ["framework.version", "version", "framework_version", "resolved.version", "compatibility.version"]),
    commit: nested(value, ["framework.commit", "commit", "framework_commit", "resolved.commit", "git.commit", "revision"]),
    fingerprint: nested(value, ["framework.bundle_fingerprint", "bundle_fingerprint", "bundle.fingerprint", "resolved.bundle_fingerprint", "fingerprint"]),
  };
}

function fingerprintLooksExact(value?: string) {
  if (!value) return false;
  return /^(?:sha256:)?[a-f0-9]{64}$/i.test(value.trim());
}

function sameIdentityField(a?: string, b?: string) {
  if (!a || !b) return true;
  return a.trim() === b.trim();
}

async function inspectFiles(fileList: FileList | File[]): Promise<ProjectInspection> {
  const files = Array.from(fileList);
  const entries = files.map((file) => ({ file, path: relativeToProject(normalizePath(file)) }));
  const find = (name: string) => entries.find((entry) => basename(entry.path).toLocaleLowerCase() === name.toLocaleLowerCase());

  const manifestEntry = find("novelforge.toml");
  const lockEntry = find("novelforge.lock.json");
  const attestationEntry = find("framework.attestation.json");

  const manifestSource = manifestEntry ? await manifestEntry.file.text() : "";
  const project: ProjectIdentity = manifestEntry ? {
    id: pickTomlValue(manifestSource, ["id", "project_id"]),
    title: pickTomlValue(manifestSource, ["title", "name"]),
    language: pickTomlValue(manifestSource, ["language", "locale"]),
    version: pickTomlValue(manifestSource, ["version", "project_version"]),
    schema: pickTomlValue(manifestSource, ["schema", "project_schema"]),
  } : {};

  let lockValue: unknown;
  let lockParseError = false;
  if (lockEntry) {
    try {
      lockValue = JSON.parse(await lockEntry.file.text());
    } catch {
      lockParseError = true;
    }
  }

  let attestationValue: unknown;
  let attestationParseError = false;
  if (attestationEntry) {
    try {
      attestationValue = JSON.parse(await attestationEntry.file.text());
    } catch {
      attestationParseError = true;
    }
  }

  const framework = frameworkIdentity(lockValue);
  const attestation = frameworkIdentity(attestationValue);
  const normalizedPaths = entries.map((entry) => entry.path.toLocaleLowerCase());
  const hasDirectory = (directory: string) => normalizedPaths.some((pathname) => pathname === directory || pathname.startsWith(`${directory}/`));
  const directories = [...requiredDirectories, ...evidenceDirectories].map((name) => ({ name, present: hasDirectory(name) }));

  const checks: InspectionCheck[] = [];
  const push = (key: string, state: CheckState, title: string, detail: string) => checks.push({ key, state, title, detail });

  push(
    "manifest",
    manifestEntry ? "pass" : "fail",
    "novelforge.toml",
    manifestEntry ? manifestEntry.path : "Project manifest not found.",
  );

  push(
    "lock",
    lockEntry && !lockParseError ? "pass" : "fail",
    "novelforge.lock.json",
    lockParseError ? "Lockfile exists but is not valid JSON." : lockEntry ? lockEntry.path : "Framework lockfile not found.",
  );

  if (lockEntry && !lockParseError) {
    push(
      "commit",
      framework.commit ? "pass" : "warn",
      "Exact framework revision",
      framework.commit ? framework.commit : "No exact commit is resolved yet. This can be valid for a fresh scaffold, but not for governed production bootstrap.",
    );
    push(
      "fingerprint",
      fingerprintLooksExact(framework.fingerprint) ? "pass" : framework.fingerprint ? "fail" : "warn",
      "Bundle fingerprint",
      framework.fingerprint
        ? fingerprintLooksExact(framework.fingerprint) ? framework.fingerprint : "Fingerprint is present but does not look like a SHA-256 identity."
        : "No deterministic bundle fingerprint is resolved yet.",
    );
  }

  const coreDirectoryCount = requiredDirectories.filter(hasDirectory).length;
  push(
    "structure",
    coreDirectoryCount === requiredDirectories.length ? "pass" : coreDirectoryCount >= 3 ? "warn" : "fail",
    "Project authority structure",
    `${coreDirectoryCount}/${requiredDirectories.length} core logical directories detected. Mapped adapters may intentionally use a different physical layout.`,
  );

  const evidenceDirectoryCount = evidenceDirectories.filter(hasDirectory).length;
  push(
    "evidence",
    evidenceDirectoryCount >= 2 ? "pass" : "warn",
    "Quality evidence surface",
    `${evidenceDirectoryCount}/${evidenceDirectories.length} evidence directories detected (evals / tests / regressions).`,
  );

  let attestationConflict = false;
  if (attestationEntry) {
    if (attestationParseError) {
      attestationConflict = true;
      push("attestation", "fail", "Framework attestation", "framework.attestation.json exists but is not valid JSON.");
    } else {
      const matches = sameIdentityField(framework.version, attestation.version)
        && sameIdentityField(framework.commit, attestation.commit)
        && sameIdentityField(framework.fingerprint, attestation.fingerprint);
      attestationConflict = !matches;
      push(
        "attestation",
        matches ? "pass" : "fail",
        "Framework attestation",
        matches ? "Attestation identity is consistent with the lock fields it shares." : "Attestation and lock disagree on version, commit, or bundle fingerprint.",
      );
    }
  } else {
    push("attestation", "warn", "Framework attestation", "No framework.attestation.json detected. Some project contracts require one; others do not.");
  }

  let status: ProjectInspection["status"] = "coherent";
  if (!manifestEntry || !lockEntry || lockParseError) status = "incomplete";
  else if (attestationConflict) status = "conflict";
  else if (!framework.commit || !fingerprintLooksExact(framework.fingerprint)) status = "scaffold";

  return {
    rootName: rootNameFor(files),
    fileCount: files.length,
    totalBytes: files.reduce((sum, file) => sum + file.size, 0),
    manifestPath: manifestEntry?.path,
    lockPath: lockEntry?.path,
    attestationPath: attestationEntry?.path,
    project,
    framework,
    attestation,
    status,
    checks,
    directories,
  };
}

function demoInspection(): ProjectInspection {
  return {
    rootName: "moonlit-archive",
    fileCount: 84,
    totalBytes: 1_842_770,
    manifestPath: "novelforge.toml",
    lockPath: "novelforge.lock.json",
    attestationPath: "framework.attestation.json",
    project: { id: "MOONLIT-ARCHIVE", title: "Moonlit Archive", language: "zh-CN", version: "0.4.0", schema: "novelforge-project-v1" },
    framework: {
      repository: "xiaooye/cn_webnovel_agent",
      version: "8.0-dev",
      commit: "4f18d3c9d4b11cf0d282e108db9fc8f18ad9e67a",
      fingerprint: "sha256:5f0f9e5d522fca33f05a9a00ce940fea864b554d30e70123ec60b3ea981a0ca8",
    },
    attestation: {
      version: "8.0-dev",
      commit: "4f18d3c9d4b11cf0d282e108db9fc8f18ad9e67a",
      fingerprint: "sha256:5f0f9e5d522fca33f05a9a00ce940fea864b554d30e70123ec60b3ea981a0ca8",
    },
    status: "coherent",
    checks: [
      { key: "manifest", state: "pass", title: "novelforge.toml", detail: "novelforge.toml" },
      { key: "lock", state: "pass", title: "novelforge.lock.json", detail: "novelforge.lock.json" },
      { key: "commit", state: "pass", title: "Exact framework revision", detail: "4f18d3c9d4b11cf0d282e108db9fc8f18ad9e67a" },
      { key: "fingerprint", state: "pass", title: "Bundle fingerprint", detail: "SHA-256 bundle identity present." },
      { key: "structure", state: "pass", title: "Project authority structure", detail: "6/6 core logical directories detected." },
      { key: "evidence", state: "pass", title: "Quality evidence surface", detail: "3/3 evidence directories detected." },
      { key: "attestation", state: "pass", title: "Framework attestation", detail: "Attestation identity is consistent with the lock." },
    ],
    directories: [...requiredDirectories, ...evidenceDirectories].map((name) => ({ name, present: true })),
  };
}

function humanBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ProjectInspector(props: Props) {
  const [inspection, setInspection] = createSignal<ProjectInspection>();
  const [busy, setBusy] = createSignal(false);
  const [error, setError] = createSignal("");
  const zh = () => props.locale === "zh-CN";

  const text = createMemo(() => zh() ? {
    eyebrow: "Project Import · Browser-native",
    title: "把项目拖进来，先看它现在到底是什么状态。",
    lede: "只在浏览器里读取文件名、manifest 与 lock。不会上传项目内容，也不会把结构检查伪装成 production bootstrap approval。",
    select: "选择项目文件夹",
    demo: "载入示例项目",
    privacy: "本地读取 · 不上传",
    emptyTitle: "选择一个 NovelForge Project",
    emptyBody: "检查器会识别 novelforge.toml、lock、可选 attestation、核心逻辑目录与质量证据面。",
    cliTitle: "还没有项目？",
    cliBody: "当前 Project SDK 的真实入口是 Python CLI：",
    summary: "项目摘要",
    checks: "结构检查",
    structure: "检测到的逻辑目录",
    framework: "Framework identity",
    project: "Project identity",
    structuralOnly: "这是 browser-side structural inspection，不等于 Framework bootstrap、semantic validation 或 production readiness approval。",
    coherent: "结构一致",
    scaffold: "脚手架已建立 · 精确依赖未完全解析",
    incomplete: "项目结构不完整",
    conflict: "依赖身份冲突",
    files: "文件",
    size: "读取规模",
    reset: "检查另一个项目",
    invalid: "无法读取这些文件，请重新选择项目文件夹。",
  } : {
    eyebrow: "Project Import · Browser-native",
    title: "Drop in a project and inspect what state it is actually in.",
    lede: "Reads filenames, manifest, and lock locally in your browser. Nothing is uploaded, and structural checks are never presented as production bootstrap approval.",
    select: "Choose project folder",
    demo: "Load demo project",
    privacy: "Local read · no upload",
    emptyTitle: "Choose a NovelForge Project",
    emptyBody: "The inspector detects novelforge.toml, the framework lock, optional attestation, core logical directories, and quality evidence surfaces.",
    cliTitle: "No project yet?",
    cliBody: "The current Project SDK entry point is the Python CLI:",
    summary: "Project summary",
    checks: "Structural checks",
    structure: "Detected logical directories",
    framework: "Framework identity",
    project: "Project identity",
    structuralOnly: "This is browser-side structural inspection, not Framework bootstrap, semantic validation, or production-readiness approval.",
    coherent: "Structurally coherent",
    scaffold: "Scaffold present · exact dependency unresolved",
    incomplete: "Project structure incomplete",
    conflict: "Dependency identity conflict",
    files: "Files",
    size: "Read size",
    reset: "Inspect another project",
    invalid: "Could not inspect those files. Choose the project folder again.",
  });

  const statusLabel = () => {
    const current = inspection()?.status;
    if (!current) return "";
    return text()[current];
  };

  const ingest = async (files: FileList | File[]) => {
    if (!files.length) return;
    setBusy(true);
    setError("");
    try {
      setInspection(await inspectFiles(files));
    } catch {
      setError(text().invalid);
    } finally {
      setBusy(false);
    }
  };

  let folderInput: HTMLInputElement | undefined;

  return (
    <div class="project-inspector-shell">
      <section class="project-inspector-intro">
        <div>
          <p class="eyebrow">{text().eyebrow}</p>
          <h1>{text().title}</h1>
          <p>{text().lede}</p>
        </div>
        <span class="wui-badge wui-badge--success inspector-privacy">⌁ {text().privacy}</span>
      </section>

      <Show when={inspection()} fallback={
        <section
          class="wui-card inspector-dropzone"
          onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; }}
          onDrop={(event) => { event.preventDefault(); void ingest(event.dataTransfer.files); }}
        >
          <div class="inspector-drop-icon" aria-hidden="true">⌂</div>
          <h2>{text().emptyTitle}</h2>
          <p>{text().emptyBody}</p>
          <div class="inspector-actions">
            <button class="wui-button wui-button--solid" type="button" disabled={busy()} onClick={() => folderInput?.click()}>{busy() ? "…" : text().select}</button>
            <button class="wui-button wui-button--soft" type="button" onClick={() => setInspection(demoInspection())}>✦ {text().demo}</button>
          </div>
          <input
            ref={(element) => { folderInput = element; element.setAttribute("webkitdirectory", ""); element.setAttribute("directory", ""); }}
            class="inspector-file-input"
            type="file"
            multiple
            onChange={(event) => void ingest(event.currentTarget.files ?? [])}
          />
          <Show when={error()}><p class="inspector-error" role="alert">{error()}</p></Show>
          <div class="inspector-cli">
            <div><strong>{text().cliTitle}</strong><span>{text().cliBody}</span></div>
            <code>python project_sdk.py init ./my-novel --id PROJECT-X --title "My Novel" --framework-version &lt;compatible-version&gt;</code>
          </div>
        </section>
      }>
        {(result) => (
          <>
            <section class="wui-card inspector-summary-card" data-status={result().status}>
              <div class="inspector-summary-heading">
                <div>
                  <p class="eyebrow">{text().summary}</p>
                  <h2>{result().project.title || result().project.id || result().rootName}</h2>
                  <p>{result().rootName}</p>
                </div>
                <span class="inspector-status-badge" data-state={result().status}>{statusLabel()}</span>
              </div>
              <div class="inspector-stat-grid">
                <div><span>{text().files}</span><strong>{result().fileCount}</strong></div>
                <div><span>{text().size}</span><strong>{humanBytes(result().totalBytes)}</strong></div>
                <div><span>Project ID</span><strong>{result().project.id || "—"}</strong></div>
                <div><span>Language</span><strong>{result().project.language || "—"}</strong></div>
              </div>
            </section>

            <div class="inspector-dashboard-grid">
              <section class="wui-card inspector-panel">
                <div class="inspector-panel-heading"><span>✓</span><div><p class="eyebrow">{text().checks}</p><h2>{text().checks}</h2></div></div>
                <div class="inspector-check-list">
                  <For each={result().checks}>{(check) => (
                    <div class="inspector-check" data-state={check.state}>
                      <span class="inspector-check-icon" aria-hidden="true">{check.state === "pass" ? "✓" : check.state === "warn" ? "!" : "×"}</span>
                      <div><strong>{check.title}</strong><p>{check.detail}</p></div>
                    </div>
                  )}</For>
                </div>
              </section>

              <section class="wui-card inspector-panel inspector-identity-panel">
                <div class="inspector-panel-heading"><span>⌘</span><div><p class="eyebrow">{text().framework}</p><h2>{text().framework}</h2></div></div>
                <dl class="inspector-kv">
                  <div><dt>Repository</dt><dd>{result().framework.repository || "—"}</dd></div>
                  <div><dt>Version</dt><dd>{result().framework.version || "—"}</dd></div>
                  <div><dt>Commit</dt><dd><code>{result().framework.commit || "—"}</code></dd></div>
                  <div><dt>Bundle</dt><dd><code>{result().framework.fingerprint || "—"}</code></dd></div>
                </dl>
                <div class="inspector-divider" />
                <p class="eyebrow">{text().project}</p>
                <dl class="inspector-kv compact">
                  <div><dt>Schema</dt><dd>{result().project.schema || "—"}</dd></div>
                  <div><dt>Version</dt><dd>{result().project.version || "—"}</dd></div>
                </dl>
              </section>
            </div>

            <section class="wui-card inspector-structure-panel">
              <div class="inspector-structure-heading"><div><p class="eyebrow">{text().structure}</p><h2>{text().structure}</h2></div><button type="button" class="wui-button wui-button--soft" onClick={() => { setInspection(undefined); queueMicrotask(() => folderInput?.focus()); }}>{text().reset}</button></div>
              <div class="inspector-directory-grid">
                <For each={result().directories}>{(directory) => (
                  <div class="inspector-directory" data-present={directory.present}><span aria-hidden="true">{directory.present ? "●" : "○"}</span><code>{directory.name}/</code></div>
                )}</For>
              </div>
              <p class="inspector-disclaimer">{text().structuralOnly}</p>
            </section>
          </>
        )}
      </Show>
    </div>
  );
}

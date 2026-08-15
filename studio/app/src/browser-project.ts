export type BrowserProjectStatus = "pass" | "warn" | "missing";

export interface BrowserProjectFile {
  name: string;
  path: string;
  size: number;
}

export interface BrowserProjectCheck {
  id: string;
  label: string;
  status: BrowserProjectStatus;
  detail: string;
}

export interface BrowserProjectProjection {
  project?: {
    id?: string;
    title?: string;
    language?: string;
    version?: string;
    schema?: string;
    minimumFrameworkVersion?: string;
  };
  framework?: {
    name?: string;
    version?: string;
    commit?: string;
    bundleFingerprint?: string;
  };
  attestation?: {
    version?: string;
    commit?: string;
    bundleFingerprint?: string;
  };
  checks: BrowserProjectCheck[];
  files: BrowserProjectFile[];
}

const basename = (path: string) => path.replaceAll("\\", "/").split("/").filter(Boolean).at(-1) ?? path;

const filePath = (file: File) => file.webkitRelativePath || file.name;

const findFile = (files: File[], name: string) => files.find((file) => basename(filePath(file)) === name);

const readText = (file?: File) => file ? file.text() : Promise.resolve(undefined);

const unquote = (value: string) => value.trim().replace(/^['"]|['"]$/g, "");

function readTomlValue(source: string, section: string, key: string): string | undefined {
  let current = "";
  for (const raw of source.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, "").trim();
    if (!line) continue;
    const sectionMatch = line.match(/^\[([^\]]+)\]$/);
    if (sectionMatch) {
      current = sectionMatch[1].trim();
      continue;
    }
    if (current !== section) continue;
    const match = line.match(/^([A-Za-z0-9_.-]+)\s*=\s*(.+)$/);
    if (match?.[1] === key) return unquote(match[2]);
  }
  return undefined;
}

function parseJsonObject(source?: string): Record<string, unknown> | undefined {
  if (!source) return undefined;
  try {
    const value = JSON.parse(source);
    return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
  } catch {
    return undefined;
  }
}

const objectAt = (value: Record<string, unknown> | undefined, key: string) => {
  const nested = value?.[key];
  return nested && typeof nested === "object" && !Array.isArray(nested) ? nested as Record<string, unknown> : undefined;
};

const stringAt = (value: Record<string, unknown> | undefined, key: string) => typeof value?.[key] === "string" ? value[key] as string : undefined;

export async function inspectBrowserProject(input: FileList | File[]): Promise<BrowserProjectProjection> {
  const files = Array.from(input);
  const manifestFile = findFile(files, "novelforge.toml");
  const lockFile = findFile(files, "novelforge.lock.json");
  const attestationFile = findFile(files, "framework.attestation.json");

  const [manifestText, lockText, attestationText] = await Promise.all([
    readText(manifestFile),
    readText(lockFile),
    readText(attestationFile),
  ]);

  const lock = parseJsonObject(lockText);
  const lockFramework = objectAt(lock, "framework");
  const attestation = parseJsonObject(attestationText);
  const attestationFramework = objectAt(attestation, "framework");

  const project = manifestText ? {
    schema: readTomlValue(manifestText, "novelforge", "schema"),
    minimumFrameworkVersion: readTomlValue(manifestText, "novelforge", "minimum_framework_version"),
    id: readTomlValue(manifestText, "project", "id"),
    title: readTomlValue(manifestText, "project", "title"),
    language: readTomlValue(manifestText, "project", "language"),
    version: readTomlValue(manifestText, "project", "version"),
  } : undefined;

  const framework = lockFramework ? {
    name: stringAt(lockFramework, "name"),
    version: stringAt(lockFramework, "version"),
    commit: stringAt(lockFramework, "commit"),
    bundleFingerprint: stringAt(lockFramework, "bundle_fingerprint"),
  } : undefined;

  const attested = attestationFramework ? {
    version: stringAt(attestationFramework, "version"),
    commit: stringAt(attestationFramework, "commit"),
    bundleFingerprint: stringAt(attestationFramework, "bundle_fingerprint"),
  } : undefined;

  const lockValid = Boolean(lock && lockFramework && framework?.version && framework.commit && framework.bundleFingerprint);
  const attestationValid = Boolean(attestation && attestationFramework && attested?.version && attested.commit && attested.bundleFingerprint);
  const attestationMatches = Boolean(
    lockValid && attestationValid &&
    framework?.version === attested?.version &&
    framework?.commit === attested?.commit &&
    framework?.bundleFingerprint === attested?.bundleFingerprint
  );

  const checks: BrowserProjectCheck[] = [
    {
      id: "manifest",
      label: "novelforge.toml",
      status: manifestFile && project?.schema === "novelforge_project_v1" ? "pass" : manifestFile ? "warn" : "missing",
      detail: manifestFile ? project?.schema ?? "schema not detected" : "required project manifest not selected",
    },
    {
      id: "lock",
      label: "novelforge.lock.json",
      status: lockValid ? "pass" : lockFile ? "warn" : "missing",
      detail: lockValid ? `${framework?.version} · ${framework?.commit?.slice(0, 12)}…` : lockFile ? "lock JSON is incomplete or invalid" : "framework lock not selected",
    },
    {
      id: "attestation",
      label: "framework.attestation.json",
      status: attestationMatches ? "pass" : attestationFile ? "warn" : "missing",
      detail: attestationMatches ? "version, commit, and bundle fingerprint match lock" : attestationFile ? "attestation does not match the selected lock" : "attestation not selected",
    },
  ];

  return {
    project,
    framework,
    attestation: attested,
    checks,
    files: files.map((file) => ({ name: file.name, path: filePath(file), size: file.size })),
  };
}

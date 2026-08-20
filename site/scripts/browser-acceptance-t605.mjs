#!/usr/bin/env node
/**
 * T605 browser acceptance v1.  The runner is intentionally build/origin
 * agnostic: the runner owns both production builds and preview children.
 * It never discovers a browser, downloads one, skips, or writes evidence into
 * a checkout.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import net from "node:net";
import { spawn, execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const VIEWPORTS = Object.freeze([
  { id: "wide", width: 1440, height: 1000 },
  { id: "laptop", width: 1024, height: 900 },
  { id: "tablet", width: 768, height: 900 },
  { id: "phone", width: 430, height: 844 },
  { id: "small", width: 375, height: 812 },
]);
export const MODES = Object.freeze([
  { id: "light", colorScheme: "light", reducedMotion: "no-preference", forcedColors: "none" },
  { id: "dark", colorScheme: "dark", reducedMotion: "no-preference", forcedColors: "none" },
  { id: "reduced", colorScheme: "light", reducedMotion: "reduce", forcedColors: "none" },
  { id: "forced", colorScheme: "light", reducedMotion: "no-preference", forcedColors: "active" },
]);
export const EXIT = Object.freeze({ PASS: 0, ASSERTION: 1, BLOCKED: 2 });
export const JSON_LIMIT = 64 * 1024;
export const CHAPTER_SCOPE = "CH001";
export const MANIFEST_NAME = "browser-acceptance-v1.json";
export const SURFACES = Object.freeze(["site", "studio"]);
export const DERIVED_ACCEPTANCE_PATHS = Object.freeze([
  "release/acceptance/1.0.0-dev.0.en.md",
  "release/acceptance/1.0.0-dev.0.zh-CN.md",
  "release/acceptance/1.0.0-dev.0.tasks.en.md",
  "release/acceptance/1.0.0-dev.0.tasks.zh-CN.md",
  "release/acceptance/1.0.0-dev.0.json",
]);
// This is the exact input set used by the acceptance compute_subject contract. Keep
// the order stable: the digest is a cross-language contract, not a dist hash.
export const BUILD_INPUT_PATHS = Object.freeze([
  "package.json",
  "pnpm-lock.yaml",
  "site/package.json",
  "studio/app/package.json",
  "cloud/package.json",
]);
export const REQUIRED_GLOBAL_CHECKS = Object.freeze([
  "quick_demo_truth", "machine_contracts", "keyboard", "dialog", "offline", "wcag", "cwv", "local_launch",
]);
export const REQUIRED_MATRIX_CHECKS = Object.freeze([
  "shell", "media_state", "wcag", "cwv", "keyboard", "dialog",
]);
export const HOME_REVEAL_SELECTORS = Object.freeze([
  ".capability-focus-grid",
  ".product-lab .page-width",
  ".portal-grid",
  ".knowledge-preview-grid",
  ".lab-card",
  ".portal-card",
  ".knowledge-preview-copy",
  ".knowledge-preview-list",
]);

const secretKey = /(?:token|secret|cookie|authorization|password|credential|access[_-]?token|api[_-]?key)/i;
const absolutePath = /(?:^|[\\/])(?:tmp|home|var|Users|private|workspace)(?:[\\/]|$)|^[A-Za-z]:[\\/]|^\\\\/;

export const DEFAULT_DEADLINE_MS = 5000;

export function acceptanceTimestamp(now = new Date()) {
  return new Date(now).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function normalizeDeadline(timeoutMs, fallback = DEFAULT_DEADLINE_MS) {
  const value = Number(timeoutMs);
  if (!Number.isFinite(value) || value <= 0) return fallback;
  return Math.max(1, Math.min(Math.floor(value), 120000));
}

export function boundedTimeoutError(code, operation, timeoutMs) {
  const error = new Error(`${operation} timed out`);
  error.code = code;
  error.operation = operation;
  error.timeout_ms = normalizeDeadline(timeoutMs);
  return error;
}

export async function withDeadline(operation, timeoutMs, { code = "T605_TIMEOUT", label = "operation" } = {}) {
  const limit = normalizeDeadline(timeoutMs);
  const controller = new AbortController();
  let timer;
  const work = Promise.resolve().then(() => operation(controller.signal));
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(boundedTimeoutError(code, label, limit));
    }, limit);
  });
  try {
    return await Promise.race([work, timeout]);
  } finally {
    clearTimeout(timer);
  }
}

export async function waitForServiceWorkerReady(page, timeoutMs = DEFAULT_DEADLINE_MS, label = "service_worker_ready") {
  const limit = normalizeDeadline(timeoutMs);
  try {
    await withDeadline(
      () => page.evaluate(async ({ deadlineMs }) => {
        if (!navigator.serviceWorker || !navigator.serviceWorker.ready) throw new Error("SERVICE_WORKER_UNAVAILABLE");
        let timer;
        try {
          await Promise.race([
            navigator.serviceWorker.ready,
            new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("T605_SW_READY_TIMEOUT")), deadlineMs); }),
          ]);
        } finally {
          clearTimeout(timer);
        }
      }, { deadlineMs: limit }),
      limit,
      { code: "SERVICE_WORKER_READY_TIMEOUT", label },
    );
  } catch (error) {
    if (error?.code === "SERVICE_WORKER_READY_TIMEOUT") throw error;
    if (String(error?.message || "") === "T605_SW_READY_TIMEOUT") throw boundedTimeoutError("SERVICE_WORKER_READY_TIMEOUT", label, limit);
    throw Object.assign(new Error("service worker readiness failed"), { code: "SERVICE_WORKER_READY_FAILED", operation: label, timeout_ms: limit });
  }
  return true;
}

export async function boundedBrowserAction(action, timeoutMs = DEFAULT_DEADLINE_MS, operation = "browser_action") {
  try {
    return await withDeadline(action, timeoutMs, { code: "BROWSER_ACTION_TIMEOUT", label: operation });
  } catch (error) {
    if (error?.code === "BROWSER_ACTION_TIMEOUT") throw error;
    throw Object.assign(new Error("browser action failed"), { code: "BROWSER_ACTION_FAILED", operation, timeout_ms: normalizeDeadline(timeoutMs) });
  }
}

function browserEvidenceError(error, fallback = "RUNTIME") {
  const candidate = String(error?.code || error?.name || fallback);
  const code = /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(candidate) ? candidate : fallback;
  const operation = typeof error?.operation === "string" && /^[A-Za-z0-9_-]{1,160}$/.test(error.operation) ? error.operation : null;
  return operation ? `${code}:${operation}` : code;
}

export async function assertVisibleControl(locator, timeoutMs = DEFAULT_DEADLINE_MS, operation = "control") {
  const visible = await boundedBrowserAction(() => locator.isVisible({ timeout: normalizeDeadline(timeoutMs) }), timeoutMs, `${operation}_visibility`);
  if (!visible) throw Object.assign(new Error("required control is not visible"), { code: "CONTROL_NOT_VISIBLE", operation, timeout_ms: normalizeDeadline(timeoutMs) });
  return true;
}

export async function boundedClick(locator, timeoutMs = DEFAULT_DEADLINE_MS, operation = "control_click") {
  await assertVisibleControl(locator, timeoutMs, operation);
  await boundedBrowserAction(() => locator.click({ timeout: normalizeDeadline(timeoutMs) }), timeoutMs, operation);
  return true;
}

export function assertHomeScreenshotReadiness(snapshot) {
  if (!snapshot || snapshot.count !== 6 || !Array.isArray(snapshot.sections) || snapshot.sections.length !== 6 || snapshot.sections.some((section) => !section || section.visible !== true || section.has_text !== true || section.opacity <= 0)) throw new Error("SCREENSHOT_CONTENT_NOT_READY");
  if (!Array.isArray(snapshot.reveal_groups) || snapshot.reveal_groups.length !== HOME_REVEAL_SELECTORS.length || snapshot.reveal_groups.some((group, index) => !group || group.selector !== HOME_REVEAL_SELECTORS[index] || group.count < 1 || group.visible !== true || group.nonempty !== true)) throw new Error("SCREENSHOT_REVEAL_CONTENT_NOT_READY");
  return true;
}

export async function prepareHomeScreenshot(page, timeoutMs = DEFAULT_DEADLINE_MS) {
  await boundedBrowserAction(
    () => page.addStyleTag({ content: `${HOME_REVEAL_SELECTORS.map((selector) => `[data-home-section], ${selector}`).join(",")} { animation: none !important; animation-timeline: none !important; animation-range: normal !important; animation-play-state: running !important; opacity: 1 !important; transform: none !important; filter: none !important; transition: none !important; }` }),
    Math.min(timeoutMs, DEFAULT_DEADLINE_MS),
    "home_screenshot_animation_disable",
  );
  const snapshot = await boundedBrowserAction(
    () => page.evaluate(async () => {
      const sections = [...document.querySelectorAll("[data-home-section]")];
      const revealSelectors = [".capability-focus-grid", ".product-lab .page-width", ".portal-grid", ".knowledge-preview-grid", ".lab-card", ".portal-card", ".knowledge-preview-copy", ".knowledge-preview-list"];
      for (const section of sections) {
        section.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" });
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      }
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      await new Promise((resolve) => setTimeout(resolve, 150));
      const visible = (node) => {
        const rect = node.getBoundingClientRect();
        for (let current = node; current; current = current.parentElement) {
          const style = getComputedStyle(current);
          if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) <= 0) return false;
        }
        return rect.width > 0 && rect.height > 0;
      };
      return {
        count: sections.length,
        sections: sections.map((section) => {
          const style = getComputedStyle(section);
          const rect = section.getBoundingClientRect();
          return { id: section.getAttribute("data-home-section") || "", visible: visible(section), opacity: Number(style.opacity), has_text: Boolean(section.textContent?.trim()) };
        }),
        reveal_groups: revealSelectors.map((selector) => {
          const nodes = [...document.querySelectorAll(selector)];
          return { selector, count: nodes.length, visible: nodes.length > 0 && nodes.every(visible), nonempty: nodes.length > 0 && nodes.every((node) => Boolean(node.textContent?.trim())) };
        }),
        scroll_y: window.scrollY,
      };
    }),
    Math.min(timeoutMs, DEFAULT_DEADLINE_MS),
    "home_screenshot_prepare",
  );
  assertHomeScreenshotReadiness(snapshot);
  return snapshot;
}

function ancestorPaths(target) {
  const absolute = path.resolve(target);
  const output = [];
  let current = absolute;
  while (true) {
    output.push(current);
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return output.reverse();
}

export function assertNoSymlinkAncestors(target, { allowMissingLeaf = false } = {}) {
  const parts = ancestorPaths(target);
  for (const [index, current] of parts.entries()) {
    let info;
    try { info = fs.lstatSync(current); }
    catch (error) {
      if (allowMissingLeaf && index === parts.length - 1 && error?.code === "ENOENT") continue;
      throw Object.assign(new Error(`path component missing: ${current}`), { code: "PATH_INVALID", cause: error });
    }
    if (info.isSymbolicLink()) throw Object.assign(new Error(`symlink path component: ${current}`), { code: "PATH_SYMLINK" });
  }
  return true;
}

export function assertRegularFileNoFollow(file, { executable = false } = {}) {
  assertNoSymlinkAncestors(file);
  const info = fs.lstatSync(file);
  if (!info.isFile() || (executable && (info.mode & 0o111) === 0)) throw Object.assign(new Error(`regular executable required: ${file}`), { code: "PATH_NOT_REGULAR" });
  return info;
}

export function assertRegularDirectoryNoFollow(directory) {
  assertNoSymlinkAncestors(directory);
  const info = fs.lstatSync(directory);
  if (!info.isDirectory()) throw Object.assign(new Error(`regular directory required: ${directory}`), { code: "PATH_NOT_DIRECTORY" });
  return info;
}

export function resolveRepoRoot({ env = process.env, cwd = process.cwd() } = {}) {
  const requested = path.resolve(env.QF_REPO_ROOT || cwd);
  try {
    assertRegularDirectoryNoFollow(requested);
    const top = execFileSync("git", ["-C", requested, "rev-parse", "--show-toplevel"], { encoding: "utf8", timeout: 10000 }).trim();
    if (!top) throw new Error("git toplevel is empty");
    const root = path.resolve(top);
    assertRegularDirectoryNoFollow(root);
    return root;
  } catch (error) {
    if (["PATH_INVALID", "PATH_SYMLINK", "PATH_NOT_DIRECTORY"].includes(error?.code)) throw error;
    throw Object.assign(new Error("repository root unavailable"), { code: "REPO_ROOT_REQUIRED" });
  }
}

export function resolveChrome(env = process.env, stat = fs.statSync) {
  const value = env.CHROME_BIN;
  if (!value) throw Object.assign(new Error("CHROME_BIN is required"), { code: "CHROME_BIN_REQUIRED" });
  if (!path.isAbsolute(value)) throw Object.assign(new Error("CHROME_BIN must be absolute"), { code: "CHROME_BIN_INVALID" });
  let info;
  try { if (stat === fs.statSync) { assertNoSymlinkAncestors(value); info = fs.lstatSync(value); } else info = stat(value); }
  catch { try { info = stat(value); } catch {} }
  if (!info?.isFile?.() || (info.mode & 0o111) === 0) throw Object.assign(new Error("CHROME_BIN is not executable or is a symlink"), { code: "CHROME_BIN_INVALID" });
  if (stat === fs.statSync) try { assertNoSymlinkAncestors(value); } catch { throw Object.assign(new Error("CHROME_BIN symlink is forbidden"), { code: "CHROME_BIN_INVALID" }); }
  return value;
}

export function validateEvidenceRoot(root) {
  if (!path.isAbsolute(root) || (root !== "/tmp" && !root.startsWith("/tmp/"))) throw Object.assign(new Error("evidence root must be under /tmp"), { code: "EVIDENCE_ROOT_INVALID" });
  try { assertNoSymlinkAncestors(root, { allowMissingLeaf: true }); } catch { throw Object.assign(new Error("evidence root symlink or invalid ancestor"), { code: "EVIDENCE_ROOT_INVALID" }); }
  fs.mkdirSync(root, { recursive: true });
  const resolved = fs.realpathSync(root);
  if (resolved !== "/tmp" && !resolved.startsWith("/tmp/")) throw Object.assign(new Error("evidence root realpath escaped /tmp"), { code: "EVIDENCE_ROOT_INVALID" });
  return resolved;
}

function strictJson(text) {
  let index = 0;
  const ws = () => { while (/\s/.test(text[index] || "")) index += 1; };
  const string = () => { const start = index; index += 1; while (index < text.length) { if (text[index] === "\\") index += 2; else if (text[index++] === '"') return JSON.parse(text.slice(start, index)); } throw new Error("JSON_STRING"); };
  const value = () => { ws(); const c = text[index]; if (c === '"') return string(); if (c === "{") { index += 1; const object = {}; const keys = new Set(); ws(); if (text[index] === "}") { index += 1; return object; } while (true) { ws(); const key = string(); if (keys.has(key)) throw new Error(`JSON_DUPLICATE_KEY:${key}`); keys.add(key); ws(); if (text[index++] !== ":") throw new Error("JSON_COLON"); object[key] = value(); ws(); if (text[index] === "}") { index += 1; return object; } if (text[index++] !== ",") throw new Error("JSON_COMMA"); } } if (c === "[") { index += 1; const array = []; ws(); if (text[index] === "]") { index += 1; return array; } while (true) { array.push(value()); ws(); if (text[index] === "]") { index += 1; return array; } if (text[index++] !== ",") throw new Error("JSON_COMMA"); } } const start = index; while (index < text.length && !/[\s,\]}]/.test(text[index])) index += 1; if (start === index) throw new Error("JSON_VALUE"); return JSON.parse(text.slice(start, index)); };
  const parsed = value(); ws(); if (index !== text.length) throw new Error("JSON_TRAILING"); return parsed;
}

function validateShape(value, shape, pathName = "$") {
  if (shape.type === "string" && typeof value !== "string") throw new Error(`JSON_TYPE:${pathName}`);
  if (shape.type === "boolean" && typeof value !== "boolean") throw new Error(`JSON_TYPE:${pathName}`);
  if (shape.type === "number" && (typeof value !== "number" || !Number.isFinite(value))) throw new Error(`JSON_TYPE:${pathName}`);
  if (shape.const !== undefined && value !== shape.const) throw new Error(`JSON_CONST:${pathName}`);
  if (shape.type === "array") { if (!Array.isArray(value) || value.length > (shape.maxItems ?? 100)) throw new Error(`JSON_ARRAY:${pathName}`); if (shape.items) value.forEach((item, i) => validateShape(item, shape.items, `${pathName}[${i}]`)); }
  if (shape.type === "object") { if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`JSON_OBJECT:${pathName}`); const keys = Object.keys(value); for (const required of shape.required ?? []) if (!Object.hasOwn(value, required)) throw new Error(`JSON_REQUIRED:${pathName}.${required}`); if (shape.exact && keys.some((key) => !Object.hasOwn(shape.exact, key))) throw new Error(`JSON_EXTRA:${pathName}.${keys.find((key) => !Object.hasOwn(shape.exact, key))}`); for (const [key, child] of Object.entries(shape.exact ?? {})) if (Object.hasOwn(value, key)) validateShape(value[key], child, `${pathName}.${key}`); }
  return value;
}

export function chromeVersion(executable) {
  try { return execFileSync(executable, ["--version"], { encoding: "utf8", timeout: 5000 }).trim().slice(0, 160); }
  catch { throw Object.assign(new Error("Chrome version probe failed"), { code: "CHROME_VERSION_FAILED" }); }
}

export function browserFingerprint(executable) { return hashArtifact(executable).sha256; }

export function matrix() {
  return VIEWPORTS.flatMap((viewport) => MODES.map((mode) => ({
    id: `${viewport.id}-${mode.id}`, viewport, mode,
    screenshot: ["wide", "tablet", "small"].includes(viewport.id) ? `${viewport.id}-${mode.id}.png` : null,
  })));
}

export async function captureScreenshotEvidence({ page, evidenceRoot, surface, item, timeoutMs, capturedScreenshots, errors }) {
  if (!item?.screenshot || capturedScreenshots.has(item.id)) return false;
  const filename = path.join(evidenceRoot, surface, "screenshots", item.screenshot);
  try {
    fs.mkdirSync(path.dirname(filename), { recursive: true });
    assertNoSymlinkAncestors(path.dirname(filename));
    try {
      assertRegularFileNoFollow(filename);
      fs.unlinkSync(filename);
    } catch (error) {
      if (!(error?.code === "PATH_INVALID" && error?.cause?.code === "ENOENT")) throw error;
    }
    await boundedBrowserAction(
      () => page.screenshot({ path: filename, fullPage: true, animations: "disabled", timeout: timeoutMs }),
      timeoutMs,
      `screenshot_${surface}_${item.id}`,
    );
    const info = assertRegularFileNoFollow(filename);
    if (info.size < 1) throw Object.assign(new Error("screenshot is empty"), { code: "SCREENSHOT_EMPTY" });
    capturedScreenshots.add(item.id);
    return true;
  } catch (error) {
    errors.push({ id: "screenshot", surface, matrix: item.id, message: browserEvidenceError(error, "SCREENSHOT_FAILED") });
    return false;
  }
}

export function statusFor({ blocked = false, failed = false } = {}) {
  return blocked ? EXIT.BLOCKED : failed ? EXIT.ASSERTION : EXIT.PASS;
}

function redact(value, key = "") {
  if (secretKey.test(key)) return "[REDACTED]";
  if (typeof value === "string") {
    if (absolutePath.test(value) && !["executable", "artifacts_root"].includes(key)) return "[REDACTED_PATH]";
    try { const url = new URL(value); if (url.search || url.hash || url.username || url.password) return `${url.origin}${url.pathname}`; } catch {}
    return value.replace(/(Bearer\s+)[^\s]+/gi, "$1[REDACTED]").replace(/[?&](?:token|secret|code|state)=[^&\s]+/gi, "");
  }
  if (Array.isArray(value)) return value.map((item) => redact(item, key));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, redact(v, k)]));
  return value;
}
export function redactEvidence(value) { return redact(value); }

export function assertJsonContract(input, { schema, maxBytes = JSON_LIMIT, exactKeys, requiredFalse = [], shape, contentType = "application/json" } = {}) {
  const body = typeof input === "string" ? input : typeof input?.body === "string" ? input.body : JSON.stringify(input?.body ?? input);
  const actualType = input?.contentType ?? contentType;
  if (Buffer.byteLength(body) > maxBytes) throw new Error("JSON_TOO_LARGE");
  if (!String(actualType).toLowerCase().startsWith("application/json")) throw new Error("JSON_CONTENT_TYPE");
  let value; try { value = strictJson(body); } catch (error) { throw error instanceof Error && error.message.startsWith("JSON_") ? error : new Error("JSON_INVALID"); }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("JSON_OBJECT_REQUIRED");
  if (schema && value.schema !== schema) throw new Error("JSON_SCHEMA");
  if (exactKeys && Object.keys(value).sort().join("\0") !== [...exactKeys].sort().join("\0")) throw new Error("JSON_KEYS");
  for (const key of requiredFalse) if (value[key] !== false) throw new Error(`JSON_FALSE_REQUIRED:${key}`);
  if (shape) validateShape(value, shape);
  return value;
}

export function docsShellForPath(rawPath) {
  const pathname = new URL(rawPath, "http://t.invalid").pathname;
  if (pathname === "/docs/" || pathname.startsWith("/docs/")) {
    if (pathname.startsWith("/docs/en-US") || pathname.startsWith("/docs/zh-CN")) return null;
    return pathname.startsWith("/docs/en/") ? "/docs/en/" : "/docs/";
  }
  return null;
}

export function assertQuickDemoReceipt(text, writes = []) {
  let value;
  try { value = strictJson(text); } catch { throw new Error("QUICK_DEMO_TYPED_RECEIPT"); }
  return assertQuickDemoDom({ receipt: value, schema: value.schema, chapter: `${value.chapter_id} · authority=${value.authority}`, statuses: ["PASS", "FIXTURE", "SAFE"], boundary: "model=false · uploads=0 · canon=false" }, writes, []);
}

export function assertQuickDemoDom(snapshot, writes = [], modelRequests = []) {
  const expected = { schema: "quillframe_ch001_quick_demo_receipt_v1", chapter: "CH001 · authority=false", statuses: ["PASS", "FIXTURE", "SAFE"], boundary: "model=false · uploads=0 · canon=false" };
  const receipt = snapshot?.receipt;
  const fingerprint = (value) => typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);
  if (!receipt || Object.keys(receipt).sort().join("\0") !== ["authority", "canon_mutated", "chapter_id", "deterministic_core", "live_model_called", "schema", "semantic_evidence", "uploads"].join("\0") || receipt.schema !== expected.schema || receipt.chapter_id !== "CH001" || receipt.authority !== false || receipt.live_model_called !== false || receipt.uploads !== 0 || receipt.canon_mutated !== false) throw new Error("QUICK_DEMO_TYPED_RECEIPT");
  const core = receipt.deterministic_core; const evidence = receipt.semantic_evidence;
  if (!core || Object.keys(core).sort().join("\0") !== ["executed", "modules", "packet_fingerprint", "stage", "workflow_fingerprint"].join("\0") || core.executed !== true || !Array.isArray(core.modules) || core.modules.length === 0 || core.modules.length > 32 || !core.modules.every((item) => typeof item === "string" && item.length <= 160) || !fingerprint(core.packet_fingerprint) || !fingerprint(core.workflow_fingerprint) || typeof core.stage !== "string" || !evidence || Object.keys(evidence).sort().join("\0") !== ["authority", "candidate_fingerprint", "findings", "live_model_called", "recorded_at", "schema", "source", "summary"].join("\0") || evidence.authority !== false || !fingerprint(evidence.candidate_fingerprint) || evidence.schema !== "quillframe_recorded_semantic_evidence_v1" || evidence.source !== "recorded_fixture" || evidence.live_model_called !== false || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?\+00:00$/.test(evidence.recorded_at) || typeof evidence.summary !== "string" || evidence.summary.length === 0 || evidence.summary.length > 4096 || !Array.isArray(evidence.findings) || evidence.findings.length > 64 || !evidence.findings.every((item) => item && typeof item.code === "string" && typeof item.severity === "string" && typeof item.owner === "string")) throw new Error("QUICK_DEMO_RECEIPT_SHAPE");
  if (!snapshot || snapshot.schema !== expected.schema || snapshot.chapter !== expected.chapter || JSON.stringify(snapshot.statuses) !== JSON.stringify(expected.statuses) || snapshot.boundary !== expected.boundary) throw new Error("QUICK_DEMO_TYPED_RECEIPT");
  assertNoWrites(writes); if (modelRequests.length) throw new Error("MODEL_URL"); return true;
}

export async function installQuickDemoReceiptProbe(page) {
  await page.addInitScript(() => {
    window.__qfT605Receipts = [];
    let proto = Worker.prototype;
    let descriptor;
    while (proto && !descriptor) { descriptor = Object.getOwnPropertyDescriptor(proto, "onmessage"); proto = Object.getPrototypeOf(proto); }
    if (!descriptor?.set) return;
    Object.defineProperty(Worker.prototype, "onmessage", { configurable: true, get: descriptor.get, set(handler) { descriptor.set.call(this, (event) => { if (event.data?.kind === "result" && typeof event.data.receipt === "string") { try { window.__qfT605Receipts.push(JSON.parse(event.data.receipt)); } catch {} } handler?.call(this, event); }); } });
  });
}

export function assertUnboundStudio(snapshot) {
  return assertUnboundStudioDom(snapshot);
}

export function assertUnboundStudioDom(snapshot) {
  if (!snapshot || snapshot.hostChipText !== "Core unbound" || snapshot.surface !== "hosted_web") throw new Error("STUDIO_NOT_UNBOUND");
  if (snapshot.coreBound || snapshot.projectTitle || snapshot.runId || snapshot.mutationControls) throw new Error("STUDIO_FALSE_AUTHORITY");
  return true;
}

export function assertDialogLifecycle(events) {
  const required = ["open", "focus-initial", "tab", "shift-tab", "outside", "escape", "focus-return", "background-restored"];
  const missing = required.filter((name) => !events.includes(name));
  if (missing.length) throw new Error(`DIALOG_LIFECYCLE:${missing.join(",")}`);
  return true;
}

export function assertMachineManifest(value, schema, { authorityKeys = [], allowedKeys = ["schema", "authority"], shape } = {}) {
  const manifest = assertJsonContract(value, { schema, exactKeys: allowedKeys, shape });
  for (const key of authorityKeys) if (manifest[key] !== false) throw new Error(`MACHINE_AUTHORITY:${key}`);
  return manifest;
}

export function assertNoWrites(methods) {
  if (methods.some((method) => !["GET", "HEAD"].includes(method))) throw new Error("PRODUCT_WRITE");
  return true;
}

export const CWV_BUDGETS = Object.freeze({ lcpMs: 2500, cls: 0.1, tbtMs: 300 });

export function contrastRatio(foreground, background) {
  const parse = (value) => { const text = String(value).trim().toLowerCase(); if (text === "transparent") return { rgb: [0, 0, 0], alpha: 0 }; const match = text.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)/); if (!match) return null; const alpha = match[4] === undefined ? 1 : (match[4].endsWith("%") ? Number(match[4].slice(0, -1)) / 100 : Number(match[4])); return { rgb: match.slice(1, 4).map(Number), alpha: Math.max(0, Math.min(1, alpha)) }; };
  const fg = parse(foreground), bg = parse(background);
  if (!fg || !bg || fg.alpha <= 0 || bg.alpha < 1) throw new Error("CONTRAST_UNSUPPORTED_COLOR");
  const composited = fg.rgb.map((channel, index) => channel * fg.alpha + bg.rgb[index] * (1 - fg.alpha));
  const channel = (value) => { const c = Number(value) / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  const [a, b] = [lum(composited), lum(bg.rgb)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}

export function requiredContrastThreshold({ largeText = false, nonText = false } = {}) { return largeText ? 3 : nonText ? 3 : 4.5; }

export function assertCwv(metrics) {
  if (!metrics || metrics.supported !== true) throw new Error("CWV_UNSUPPORTED");
  if (!Number.isFinite(metrics.lcpMs) || metrics.lcpMs <= 0 || !Number.isFinite(metrics.cls) || !Number.isFinite(metrics.tbtMs) || metrics.settled === false) throw new Error("CWV_MISSING");
  if (metrics.lcpMs > CWV_BUDGETS.lcpMs || metrics.cls > CWV_BUDGETS.cls || metrics.tbtMs > CWV_BUDGETS.tbtMs) throw new Error("CWV_BUDGET");
  return true;
}

export function assertSemantics(snapshot) {
  if (!snapshot || snapshot.mainCount !== 1 || snapshot.namedButtons === 0 || snapshot.headingCount === 0 || snapshot.landmarks === 0 || snapshot.namedLandmarks === 0 || snapshot.headingNames === 0 || !Array.isArray(snapshot.landmarkRoles) || snapshot.landmarkRoles.length === 0) throw new Error("SEMANTIC_STRUCTURE");
  if (!snapshot.ariaCurrent) throw new Error("SEMANTIC_CURRENT");
  return true;
}

function productionPython(repoRoot, script, args = []) {
  assertRegularDirectoryNoFollow(repoRoot);
  try {
    const output = execFileSync(process.env.PYTHON || "python", ["-c", script, ...args], {
      cwd: repoRoot,
      encoding: "utf8",
      timeout: 15000,
      maxBuffer: 256 * 1024,
      env: { ...process.env, PYTHONPATH: repoRoot },
    }).trim();
    return strictJson(output);
  } catch {
    throw Object.assign(new Error("production Host Bridge contract exporter failed"), { code: "BRIDGE_FIXTURE_CONTRACT" });
  }
}

export function productionBridgeSnapshot(repoRoot) {
  const contractPath = path.join(repoRoot, "studio", "host_bridge_contract.json");
  const protocolPath = path.join(repoRoot, "studio", "host_bridge_protocol.py");
  assertRegularFileNoFollow(contractPath);
  assertRegularFileNoFollow(protocolPath);
  let contract;
  try { contract = strictJson(fs.readFileSync(contractPath, "utf8")); } catch { throw Object.assign(new Error("production Host Bridge contract JSON is invalid"), { code: "BRIDGE_FIXTURE_CONTRACT" }); }
  const protocol = fs.readFileSync(protocolPath, "utf8");
  if (!protocol.includes("def fingerprint(") || !protocol.includes('return "sha256:" + hashlib.sha256')) throw Object.assign(new Error("production Host Bridge fingerprint source drifted"), { code: "BRIDGE_FIXTURE_CONTRACT" });
  const description = productionPython(repoRoot, "import json\nfrom studio.host_bridge import _describe\nprint(json.dumps(_describe({}, 'local_app'), ensure_ascii=False, separators=(',', ':')))");
  const expectedContracts = Object.fromEntries(Object.entries(contract.operations).map(([name, metadata]) => [name, {
    kind: metadata.kind,
    required_args: [...(metadata.required_args || [])],
    ...(metadata.allowed_surfaces ? { allowed_surfaces: [...metadata.allowed_surfaces] } : {}),
  }]));
  if (description.schema !== "quillframe_host_bridge_description_v11" || description.framework_version !== contract.framework_version || description.contract_version !== contract.version || description.surface !== "local_app" || JSON.stringify(description.operations) !== JSON.stringify(Object.keys(expectedContracts).sort()) || JSON.stringify(description.operation_contracts) !== JSON.stringify(expectedContracts) || JSON.stringify(description.deferred_operations || {}) !== JSON.stringify(contract.deferred_operations || {}) || JSON.stringify(description.secret_boundary || {}) !== JSON.stringify(contract.secret_boundary || {})) throw Object.assign(new Error("production Host Bridge description does not match contract"), { code: "BRIDGE_FIXTURE_CONTRACT" });
  for (const key of ["authority", "canon_authority", "framework_write_authority", "settlement_authority", "direct_core_store_access"]) if (description[key] !== false) throw Object.assign(new Error("production Host Bridge description authority drifted"), { code: "BRIDGE_FIXTURE_CONTRACT" });
  return { contract, description };
}

export function productionBridgeResult(repoRoot, request, data) {
  assertBridgeRequest(request);
  return productionPython(repoRoot, "import json,sys\nfrom studio.host_bridge_protocol import result\nrequest=json.loads(sys.argv[1])\ndata=json.loads(sys.argv[2])\nprint(json.dumps(result(request, 'ok', data=data), ensure_ascii=False, separators=(',', ':')))", [JSON.stringify(request), JSON.stringify(data)]);
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function reviewFixtureData() {
  const fingerprint = "sha256:" + "a".repeat(64);
  const content = "T605 synthetic released candidate content";
  const releaseBody = { schema: "quillframe_production_release_v1", candidate_fingerprint: fingerprint, ready_for_user_visible_review: true };
  const release = { ...releaseBody, release_fingerprint: `sha256:${crypto.createHash("sha256").update(canonicalJson(releaseBody)).digest("hex")}` };
  const revision = { revision_id: "T605-REVISION", document_id: "CH001", content, content_fingerprint: fingerprint, authority_class: "candidate", source: "production_release" };
  const candidateList = { candidate_id: "T605-CANDIDATE", document_id: "CH001", revision_id: "T605-REVISION", run_id: "T605-RUN", task_mode: "DRAFT", candidate_kind: "chapter", status: "review_draft", effective_status: "review_draft", content_fingerprint: fingerprint, candidate_fingerprint: fingerprint, user_visible_gate: "PASS", created_at: "2026-08-20T00:00:00Z" };
  const reviewCandidate = { candidate_id: candidateList.candidate_id, candidate_fingerprint: fingerprint, document_id: "CH001", run_id: "T605-RUN", task_mode: "DRAFT", candidate_kind: "chapter", persisted_status: "review_draft", effective_status: "review_draft", user_visible_gate: "PASS" };
  const evidence = { reader: { mechanism: "reader_engagement", status: "pass" }, character: { mechanism: "character_simulation", status: "pass" }, continuity: { mechanism: "continuity", status: "pass" }, independent: { mechanism: "independent_semantic_gate", status: "pass" }, production_readiness: null, user_visible_gate: { status: "PASS" }, production_release: release };
  return {
    fingerprint,
    revision,
    candidateList,
    review: { schema: "quillframe_candidate_review_projection_v1", project_id: "T605", candidate: reviewCandidate, candidate_revision: revision, incumbent_revision: null, diff: { diff: [] }, evidence, revision_request: null, private_reasoning_exposed: false, authority: false, canon_authority: false, settlement_authority: false },
    visible: { schema: "quillframe_user_visible_candidate_v1", project_id: "T605", candidate_id: candidateList.candidate_id, candidate_fingerprint: fingerprint, document_id: "CH001", revision_id: "T605-REVISION", content, authority_class: "candidate", production_release: release, content_access: "production_release_only", accepted: false, settled: false, private_reasoning_exposed: false, authority: false, canon_authority: false },
    list: { schema: "quillframe_inspector_projection_v1", kind: "candidates", project_id: "T605", items: [candidateList], authority: false },
  };
}

export async function installReviewFixture(page, { repoRoot = process.cwd(), timeoutMs = DEFAULT_DEADLINE_MS } = {}) {
  const allowed = new Set(["bridge.describe", "inspector.candidates.list", "candidate.review.get", "candidate.visible.get"]);
  const snapshot = productionBridgeSnapshot(repoRoot);
  const fixture = reviewFixtureData();
  const blockedRequests = [];
  const routeFailures = [];
  const token = `t605-${crypto.randomUUID()}`;
  await page.route("**/review?project=T605", async (route) => {
    try {
      const response = await route.fetch({ timeout: normalizeDeadline(timeoutMs) });
      const body = (await response.text()).replaceAll("__QUILLFRAME_STUDIO_TOKEN__", token);
      await route.fulfill({ response, body });
    } catch {
      routeFailures.push({ code: "REVIEW_ROUTE_FETCH_TIMEOUT", operation: "review_route_fetch", timeout_ms: normalizeDeadline(timeoutMs) });
      await route.abort("timedout").catch(() => {});
    }
  });
  await page.route("**/api/bridge/invoke", async (route) => {
    let request; try { request = route.request().postDataJSON(); } catch { await route.abort(); return; }
    const requestKeys = Object.keys(request || {}).sort().join("\0");
    const operation = request?.["operation"];
    if (requestKeys !== ["args", "authority", "bridge_version", "operation", "request_id", "schema", "surface"].join("\0") || request?.schema !== "quillframe_host_bridge_request_v11" || request?.bridge_version !== "11" || request?.surface !== "local_app" || request?.authority !== false || typeof operation !== "string" || !allowed.has(operation)) { blockedRequests.push({ operation: typeof operation === "string" ? operation : null, keys: Object.keys(request || {}).sort() }); await route.abort("blockedbyclient"); return; }
    const data = operation === "bridge.describe" ? snapshot.description : operation === "inspector.candidates.list" ? fixture.list : operation === "candidate.review.get" ? fixture.review : fixture.visible;
    const result = productionBridgeResult(repoRoot, request, data);
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) });
  });
  return { allowed: [...allowed], tokenRedacted: true, blockedRequests, routeFailures, contract: snapshot.contract };
}

export function hashArtifact(file) {
  assertRegularFileNoFollow(file);
  const bytes = fs.readFileSync(file);
  return { path: file, size: bytes.byteLength, sha256: `sha256:${crypto.createHash("sha256").update(bytes).digest("hex")}` };
}

export function fingerprintTrees(paths) {
  const hash = crypto.createHash("sha256");
  for (const root of [...paths].sort()) {
    try { assertRegularDirectoryNoFollow(root); } catch { throw Object.assign(new Error(`build tree missing or unsafe: ${root}`), { code: "BUILD_ARTIFACT_MISSING" }); }
    const files = [];
    const visit = (current) => { assertRegularDirectoryNoFollow(current); for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) { const full = path.join(current, entry.name); if (entry.isDirectory()) visit(full); else { assertRegularFileNoFollow(full); files.push(full); } } };
    visit(root);
    for (const file of files) { hash.update(path.relative(root, file)); hash.update("\0"); hash.update(fs.readFileSync(file)); hash.update("\0"); }
  }
  return `sha256:${hash.digest("hex")}`;
}

function isDerivedAcceptancePath(relative) {
  return DERIVED_ACCEPTANCE_PATHS.includes(String(relative).split(path.sep).join("/"));
}

function normalizedSourceCommit(repoRoot, commit) {
  const parents = execFileSync("git", ["-C", repoRoot, "rev-list", "--parents", "-n", "1", commit], { encoding: "utf8", timeout: 10000 }).trim().split(/\s+/).filter(Boolean);
  if (parents.length !== 2) return commit;
  const changed = execFileSync("git", ["-C", repoRoot, "diff-tree", "--no-commit-id", "--name-only", "-r", commit], { encoding: "utf8", timeout: 10000 }).split("\n").map((value) => value.trim().split(path.sep).join("/")).filter(Boolean).sort();
  const expected = [...DERIVED_ACCEPTANCE_PATHS].sort();
  return changed.length === expected.length && changed.every((value, index) => value === expected[index]) ? parents[1] : commit;
}

function filteredGitDirty(repoRoot) {
  const records = execFileSync("git", ["-C", repoRoot, "status", "--porcelain=v1", "--untracked-files=all", "-z"], { encoding: "buffer", timeout: 10000 }).toString("utf8").split("\0").filter(Boolean);
  const changed = [];
  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    const status = record.slice(0, 2);
    changed.push(record.slice(3));
    if (status.includes("R") || status.includes("C")) changed.push(records[++index] || "");
  }
  return changed.some((value) => !isDerivedAcceptancePath(value));
}

export function gitSubject(repoRoot) {
  try {
    repoRoot = resolveRepoRoot({ env: { QF_REPO_ROOT: repoRoot }, cwd: repoRoot });
    const head = execFileSync("git", ["-C", repoRoot, "rev-parse", "HEAD"], { encoding: "utf8", timeout: 10000 }).trim();
    if (!/^[0-9a-f]{40}$/i.test(head)) throw new Error("commit must be 40 hex");
    const commit = normalizedSourceCommit(repoRoot, head);
    const files = execFileSync("git", ["-C", repoRoot, "ls-files", "-co", "--exclude-standard", "-z"], { encoding: "buffer", timeout: 30000 }).toString("utf8").split("\0").filter(Boolean).filter((relative) => !isDerivedAcceptancePath(relative)).sort();
    const hash = crypto.createHash("sha256"); let dirty = false;
    for (const relative of files) {
      const normalized = relative.split(path.sep).join("/");
      const full = path.join(repoRoot, normalized);
      hash.update(normalized);
      hash.update("\0");
      let stat;
      try { stat = fs.lstatSync(full); } catch (error) {
        if (error?.code !== "ENOENT") throw error;
        hash.update("[DELETED]\0");
        continue;
      }
      if (stat.isSymbolicLink()) throw new Error("git subject symlink");
      if (!stat.isFile()) throw new Error("git subject nonregular");
      hash.update(fs.readFileSync(full));
      hash.update("\0");
    }
    dirty = filteredGitDirty(repoRoot);
    return { commit, dirty, working_tree_fingerprint: `sha256:${hash.digest("hex")}` };
  } catch { throw Object.assign(new Error("git subject unavailable"), { code: "GIT_SUBJECT_FAILED" }); }
}

export function acceptanceInputFingerprint(repoRoot, commit) {
  const hash = crypto.createHash("sha256");
  const sourceCommit = commit || normalizedSourceCommit(repoRoot, execFileSync("git", ["-C", repoRoot, "rev-parse", "HEAD"], { encoding: "utf8", timeout: 10000 }).trim());
  hash.update(sourceCommit);
  hash.update("\0");
  const version = fs.readFileSync(path.join(repoRoot, "VERSION"), "utf8").trim();
  hash.update(version);
  hash.update("\0");
  for (const relative of BUILD_INPUT_PATHS) {
    const file = path.join(repoRoot, relative);
    assertRegularFileNoFollow(file);
    hash.update(relative);
    hash.update("\0");
    hash.update(fs.readFileSync(file));
    hash.update("\0");
  }
  return `sha256:${hash.digest("hex")}`;
}

function finalizerSourceFiles(distDir) {
  const output = [];
  const visit = (current) => {
    assertRegularDirectoryNoFollow(current);
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      const relative = path.relative(distDir, absolute).split(path.sep).join("/");
      if (entry.isDirectory()) visit(absolute);
      else {
        assertRegularFileNoFollow(absolute);
        if (relative !== "sw.js" && relative !== "generated/quillframe-site-service-worker.json" && !entry.name.startsWith(".") && !entry.name.includes(".tmp-") && !entry.name.endsWith(".tmp")) output.push(relative);
      }
    }
  };
  visit(distDir);
  return output.sort();
}

function finalizerFingerprint(distDir, files) {
  const hash = crypto.createHash("sha256");
  for (const relative of [...files].sort()) {
    const bytes = fs.readFileSync(path.join(distDir, relative));
    hash.update(JSON.stringify({ path: relative, byteLength: bytes.byteLength }));
    hash.update(Buffer.from([0]));
    hash.update(bytes);
  }
  return `sha256:${hash.digest("hex")}`;
}

function readStrictJsonFile(file, schema, shape, exactKeys) {
  assertRegularFileNoFollow(file);
  return assertJsonContract({ body: fs.readFileSync(file, "utf8"), contentType: "application/json" }, { schema, shape, exactKeys });
}

export function assertBuildArtifacts(siteDir, studioDir) {
  const siteDist = path.join(siteDir, "dist"); const studioDist = path.join(studioDir, "dist");
  try { assertRegularDirectoryNoFollow(siteDist); assertRegularDirectoryNoFollow(studioDist); } catch { throw Object.assign(new Error("production dist missing or unsafe"), { code: "BUILD_ARTIFACT_MISSING" }); }
  const sw = path.join(siteDist, "sw.js");
  try { assertRegularFileNoFollow(sw); } catch { throw Object.assign(new Error("finalized service worker missing"), { code: "BUILD_ARTIFACT_MISSING" }); }
  const swText = fs.readFileSync(sw, "utf8");
  if (swText.includes("__QF_SITE_CACHE_VERSION__")) throw Object.assign(new Error("service worker finalizer placeholder remains"), { code: "BUILD_ARTIFACT_MISSING" });
  const metadataPath = path.join(siteDist, "generated/quillframe-site-service-worker.json");
  const metadataKeys = ["schema", "fingerprint", "cache_name", "source_files", "required_shells", "sw_path", "authority"];
  const metadataShape = { type: "object", required: metadataKeys, exact: { schema: { type: "string", const: "quillframe_site_service_worker_finalizer_v1" }, fingerprint: { type: "string" }, cache_name: { type: "string" }, source_files: { type: "array", maxItems: 20000, items: { type: "string" } }, required_shells: { type: "array", maxItems: 8, items: { type: "string" } }, sw_path: { type: "string", const: "sw.js" }, authority: { type: "boolean", const: false } } };
  let metadata;
  try { metadata = readStrictJsonFile(metadataPath, "quillframe_site_service_worker_finalizer_v1", metadataShape, metadataKeys); } catch { throw Object.assign(new Error("site finalizer metadata missing or invalid"), { code: "BUILD_ARTIFACT_MISSING" }); }
  const expectedSourceFiles = finalizerSourceFiles(siteDist);
  if (!/^sha256:[0-9a-f]{64}$/.test(metadata.fingerprint) || metadata.required_shells.join("\0") !== ["docs/", "docs/en/"].join("\0") || metadata.source_files.length === 0 || new Set(metadata.source_files).size !== metadata.source_files.length || metadata.source_files.some((value) => path.isAbsolute(value) || value.split("/").includes("..")) || metadata.source_files.join("\0") !== expectedSourceFiles.join("\0") || metadata.source_files.includes("sw.js") || finalizerFingerprint(siteDist, expectedSourceFiles) !== metadata.fingerprint) throw Object.assign(new Error("site finalizer metadata fingerprint mismatch"), { code: "BUILD_ARTIFACT_MISSING" });
  const cache = metadata.cache_name;
  if (!/^quillframe-site-[0-9a-f]{16}$/.test(cache) || !swText.includes(cache)) throw Object.assign(new Error("service worker cache fingerprint mismatch"), { code: "BUILD_ARTIFACT_MISSING" });
  const hostPath = path.join(studioDist, ".well-known/quillframe-host.json");
  const hostKeys = ["schema", "surface", "delivery", "core_host", "authority", "canon_authority", "framework_write_authority", "settlement_authority", "direct_core_store_access"];
  const hostShape = { type: "object", required: hostKeys, exact: Object.fromEntries(hostKeys.map((key) => [key, key === "authority" || key.endsWith("authority") || key === "direct_core_store_access" ? { type: "boolean", const: false } : { type: "string" }])) };
  const footprintPath = path.join(studioDist, ".well-known/quillframe-studio-footprint.json");
  const footprintKeys = ["schema", "generated_at", "measurement", "assets", "runtime_contract", "not_measured"];
  const metricShape = { type: "object", required: ["files", "bytes", "gzip_bytes", "largest_bytes"], exact: { files: { type: "number" }, bytes: { type: "number" }, gzip_bytes: { type: "number" }, largest_bytes: { type: "number" } } };
  const footprintShape = { type: "object", required: footprintKeys, exact: { schema: { type: "string", const: "quillframe_studio_footprint_v1" }, generated_at: { type: "string" }, measurement: { type: "string", const: "production_build_artifacts" }, assets: { type: "object", required: ["javascript", "css"], exact: { javascript: metricShape, css: metricShape } }, runtime_contract: { type: "object", required: ["weiui_runtime_javascript_required", "persistent_database_required_by_hosted_ui", "core_required_for_browser_preflight", "core_required_for_local_playground_preview"], exact: { weiui_runtime_javascript_required: { type: "boolean" }, persistent_database_required_by_hosted_ui: { type: "boolean" }, core_required_for_browser_preflight: { type: "boolean" }, core_required_for_local_playground_preview: { type: "boolean" } } }, not_measured: { type: "array", maxItems: 32, items: { type: "string" } } } };
  try { readStrictJsonFile(hostPath, "quillframe_studio_host_descriptor_v1", hostShape, hostKeys); readStrictJsonFile(footprintPath, "quillframe_studio_footprint_v1", footprintShape, footprintKeys); } catch { throw Object.assign(new Error("Studio machine descriptor missing or invalid"), { code: "BUILD_ARTIFACT_MISSING" }); }
  return { siteFinalizer: metadata, siteFinalizerFingerprint: metadata.fingerprint };
}

export async function reservePort(host = "127.0.0.1") {
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, host, resolve); });
  const address = server.address(); const port = typeof address === "object" && address ? address.port : 0;
  await new Promise((resolve) => server.close(resolve));
  if (!port) throw Object.assign(new Error("no free port"), { code: "PORT_UNAVAILABLE" });
  return port;
}

export function spawnProcess(command, args, cwd, { stdio = "ignore", env = process.env } = {}) {
  const child = spawn(command, args, { cwd, stdio, env, detached: process.platform === "linux" });
  let exited = false; let exitCode = null;
  child.once("exit", (code) => { exited = true; exitCode = code; });
  child.once("error", () => { exited = true; });
  return { child, pid: child.pid, groupId: process.platform === "linux" ? -child.pid : null, exitCode: () => exitCode, hasExited: () => exited };
}

export async function terminateProcess(item, timeoutMs = 2000) {
  if (item.hasExited()) return;
  const signal = (name) => { try { if (item.groupId) process.kill(item.groupId, name); else item.child.kill(name); } catch {} };
  signal("SIGTERM");
  const deadline = Date.now() + timeoutMs;
  while (!item.hasExited() && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 25));
  if (!item.hasExited()) signal("SIGKILL");
  const waitDeadline = Date.now() + 1000;
  while (!item.hasExited() && Date.now() < waitDeadline) await new Promise((resolve) => setTimeout(resolve, 25));
  if (!item.hasExited()) throw Object.assign(new Error("process group did not exit"), { code: "PROCESS_CLEANUP_FAILED" });
}

export async function startPreviews({ env = process.env, cwd = process.cwd() } = {}) {
  if (env.QF_START_PREVIEWS !== "1") throw Object.assign(new Error("T605 owns build/preview lifecycle; QF_START_PREVIEWS=1 is required"), { code: "PREVIEW_START_REQUIRED" });
  const owned = []; let cleaned = false;
  const earlySignal = () => { for (const item of owned) if (!item.hasExited()) { try { if (item.groupId) process.kill(item.groupId, "SIGTERM"); else item.child.kill("SIGTERM"); } catch {} } };
  process.once("SIGTERM", earlySignal); process.once("SIGINT", earlySignal);
  let repoRoot;
  try { repoRoot = resolveRepoRoot({ env, cwd }); } catch (error) { process.removeListener("SIGTERM", earlySignal); process.removeListener("SIGINT", earlySignal); throw error; }
  const siteDir = path.resolve(env.QF_SITE_DIR || path.join(repoRoot, "site"));
  const studioDir = path.resolve(env.QF_STUDIO_DIR || path.join(repoRoot, "studio", "app"));
  try { assertRegularDirectoryNoFollow(repoRoot); assertRegularDirectoryNoFollow(siteDir); assertRegularDirectoryNoFollow(studioDir); } catch (error) { process.removeListener("SIGTERM", earlySignal); process.removeListener("SIGINT", earlySignal); throw Object.assign(new Error("repo/site/studio path is missing or symlinked", { cause: error }), { code: "PATH_INVALID" }); }
  const sitePort = Number(env.QF_SITE_PORT || await reservePort());
  let studioPort = Number(env.QF_STUDIO_PORT || await reservePort());
  if (studioPort === sitePort) studioPort = await reservePort();
  const build = (dir) => spawnProcess("corepack", ["pnpm", "--dir", dir, "build"], repoRoot);
  const builds = [build(siteDir), build(studioDir)]; owned.push(...builds);
  const waitExit = (item) => new Promise((resolve, reject) => {
    item.child.once("error", reject);
    item.child.once("exit", (code) => code === 0 ? resolve() : reject(Object.assign(new Error("build failed"), { code: "BUILD_FAILED" })));
  });
  let buildTimer;
  try {
    await Promise.race([Promise.all(builds.map(waitExit)), new Promise((_, reject) => { buildTimer = setTimeout(() => reject(Object.assign(new Error("build timeout"), { code: "BUILD_TIMEOUT" })), Number(env.QF_T605_BUILD_TIMEOUT_MS || 300000)); })]);
  } catch (error) { for (const item of builds) await terminateProcess(item); process.removeListener("SIGTERM", earlySignal); process.removeListener("SIGINT", earlySignal); throw error; }
  finally { if (buildTimer) clearTimeout(buildTimer); }
  let buildMetadata;
  try { buildMetadata = assertBuildArtifacts(siteDir, studioDir); } catch (error) { for (const item of builds) await terminateProcess(item); process.removeListener("SIGTERM", earlySignal); process.removeListener("SIGINT", earlySignal); throw error; }
  const site = spawnProcess("corepack", ["pnpm", "--dir", siteDir, "preview", "--host", "127.0.0.1", "--port", String(sitePort), "--strictPort"], repoRoot);
  const studio = spawnProcess("corepack", ["pnpm", "--dir", studioDir, "preview", "--host", "127.0.0.1", "--port", String(studioPort), "--strictPort"], repoRoot);
  owned.push(site, studio);
  const cleanup = async () => { if (cleaned) return; cleaned = true; for (const item of [site, studio, ...builds]) await terminateProcess(item); process.removeListener("SIGTERM", earlySignal); process.removeListener("SIGINT", earlySignal); };
  try { await waitForServer(`http://127.0.0.1:${sitePort}`, Number(env.QF_T605_PREVIEW_TIMEOUT_MS || 60000)); await waitForServer(`http://127.0.0.1:${studioPort}`, Number(env.QF_T605_PREVIEW_TIMEOUT_MS || 60000)); } catch (error) { await cleanup(); throw Object.assign(error, { code: "PREVIEW_NOT_READY" }); }
  let buildFingerprint;
  try { buildFingerprint = fingerprintTrees([path.join(siteDir, "dist"), path.join(studioDir, "dist")]); }
  catch (error) { await cleanup(); throw error; }
  return { origins: { site: `http://127.0.0.1:${sitePort}`, studio: `http://127.0.0.1:${studioPort}` }, cleanup, started: true, repoRoot, siteDir, studioDir, buildRoots: [path.join(siteDir, "dist"), path.join(studioDir, "dist")], buildFingerprint, siteFinalizerFingerprint: buildMetadata.siteFinalizerFingerprint };
}

function check(id, status, route, observed = {}, reason = undefined) {
  const aliases = { "media-state": "media_state", "wcag-semantics": "wcag", "cwv-budget": "cwv", "wcag-aa-contrast": "wcag_contrast" };
  const canonicalId = aliases[id] || String(id).replaceAll("-", "_");
  return { id: canonicalId, family: canonicalId.split("_")[0], status: ["pass", "fail", "blocked"].includes(status) ? status : "fail", route, observed: redactEvidence(observed), ...(reason ? { reason } : {}) };
}

export async function waitForServer(url, timeoutMs, { fetchImpl = globalThis.fetch } = {}) {
  const limit = normalizeDeadline(timeoutMs);
  const deadline = Date.now() + limit;
  while (Date.now() < deadline) {
    const remaining = Math.max(1, Math.min(1000, deadline - Date.now()));
    try {
      const response = await withDeadline((signal) => fetchImpl(url, { signal }), remaining, { code: "ORIGIN_FETCH_TIMEOUT", label: "origin_fetch" });
      if (response.ok) return true;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw Object.assign(new Error("origin not ready"), { code: "ORIGIN_NOT_READY", operation: "wait_for_server", timeout_ms: limit });
}

export function assertLaunchReceipt(receipt) {
  const keys = ["authority", "browser_opened", "cloud_upload_started", "process_id", "profile", "project_id", "project_root", "schema", "status", "storage_boundary", "url"];
  if (!receipt || Object.keys(receipt).sort().join("\0") !== keys.join("\0") || receipt.schema !== "quillframe_launch_receipt_v1" || receipt.status !== "ready" || receipt.profile !== "local" || receipt.storage_boundary !== "project_local_sqlite" || receipt.cloud_upload_started !== false || receipt.authority !== false || receipt.browser_opened !== false || !Number.isInteger(receipt.process_id) || receipt.process_id <= 0 || typeof receipt.project_id !== "string" || typeof receipt.project_root !== "string" || !/^http:\/\/127\.0\.0\.1:\d+\/$/.test(receipt.url) || /(?:token|secret|password|api[_-]?key)/i.test(JSON.stringify(receipt))) throw new Error("LOCAL_LAUNCH_RECEIPT");
  return true;
}

export function assertBridgeRequest(request, allowed = ["bridge.describe", "inspector.candidates.list", "candidate.review.get", "candidate.visible.get"]) {
  const keys = ["args", "authority", "bridge_version", "operation", "request_id", "schema", "surface"];
  if (!request || Object.keys(request).sort().join("\0") !== keys.join("\0") || request.schema !== "quillframe_host_bridge_request_v11" || request.bridge_version !== "11" || request.surface !== "local_app" || request.authority !== false || typeof request.operation !== "string" || !allowed.includes(request.operation) || typeof request.request_id !== "string" || request.request_id.length < 1 || !request.args || typeof request.args !== "object" || Array.isArray(request.args)) throw new Error("BRIDGE_REQUEST_SHAPE");
  return true;
}

export function assertBridgeResult(result, request) {
  const keys = ["authority", "bridge_version", "canon_authority", "data", "error", "framework_write_authority", "operation", "request_fingerprint", "request_id", "result_fingerprint", "schema", "secret_values_persisted", "settlement_authority", "status", "surface"];
  if (!result || Object.keys(result).sort().join("\0") !== keys.sort().join("\0") || result.schema !== "quillframe_host_bridge_result_v11" || result.bridge_version !== "11" || result.request_id !== request.request_id || result.operation !== request.operation || result.surface !== "local_app" || result.status !== "ok" || result.error !== null || result.authority !== false || result.canon_authority !== false || result.framework_write_authority !== false || result.settlement_authority !== false || result.secret_values_persisted !== false || !/^sha256:[0-9a-f]{64}$/.test(result.request_fingerprint) || !/^sha256:[0-9a-f]{64}$/.test(result.result_fingerprint) || !result.data || typeof result.data !== "object") throw new Error("BRIDGE_RESULT_SHAPE");
  return true;
}

export async function runLocalLaunch({ browser, repoRoot, chrome, evidenceRoot, timeoutMs }) {
  if (!browser) throw Object.assign(new Error("browser is required for local launch"), { code: "LOCAL_LAUNCH_BROWSER_REQUIRED" });
  assertRegularDirectoryNoFollow(repoRoot); assertRegularFileNoFollow(chrome, { executable: true }); validateEvidenceRoot(evidenceRoot);
  const temporaryRoot = fs.mkdtempSync(path.join("/tmp", "quillframe-t605-launch-"));
  assertNoSymlinkAncestors(temporaryRoot);
  const projectRoot = path.join(temporaryRoot, "novel"); const statePath = path.join(temporaryRoot, "launch-state.json");
  const launch = spawnProcess(process.env.PYTHON || "python", ["-u", "-m", "quillframe.cli", "launch", projectRoot, "--new", "--profile", "local", "--id", "browser-e2e", "--title", "Browser E2E Novel", "--language", "en", "--port", "0", "--no-browser", "--json"], repoRoot, { stdio: ["ignore", "pipe", "pipe"], env: { ...process.env, QUILLFRAME_LAUNCH_STATE: statePath } });
  let stdout = ""; let receipt;
  launch.child.stdout.on("data", (chunk) => { stdout += String(chunk).slice(0, 128 * 1024); });
  const deadline = Date.now() + Math.min(timeoutMs, 30000);
  try {
    while (!receipt && Date.now() < deadline) {
      for (const line of stdout.split("\n")) { try { const parsed = strictJson(line.trim()); if (parsed?.schema === "quillframe_launch_receipt_v1") { receipt = parsed; break; } } catch {} }
      if (!receipt) await new Promise((resolve) => setTimeout(resolve, 50));
    }
    if (!receipt) throw Object.assign(new Error("local launch receipt timeout"), { code: "LOCAL_LAUNCH_TIMEOUT" });
    assertLaunchReceipt(receipt);
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: "light", reducedMotion: "no-preference", forcedColors: "none" });
    const page = await context.newPage(); const nonGet = []; const uploadRequests = []; const external = []; const pageErrors = [];
    page.on("request", (request) => { if (!["GET", "HEAD"].includes(request.method())) nonGet.push({ method: request.method(), url: request.url() }); if (/upload|r2|cloud|bundle/i.test(request.url())) uploadRequests.push(request.url()); try { if (new URL(request.url()).hostname !== "127.0.0.1") external.push(request.url()); } catch {} });
    page.on("pageerror", (error) => pageErrors.push(String(error?.message || "pageerror")));
    try {
      await page.goto(receipt.url, { waitUntil: "networkidle", timeout: timeoutMs });
      const initial = await page.evaluate(() => ({ coreBound: document.querySelector(".nf-host-chip")?.textContent?.includes("Core bound") || document.querySelector(".nf-host-chip")?.textContent?.includes("Core 已绑定"), surface: document.querySelector(".nf-host-chip")?.getAttribute("data-surface") || "", main: document.querySelectorAll("main").length }));
      await page.goto(new URL("/start", receipt.url).href, { waitUntil: "networkidle", timeout: timeoutMs });
      const project = await page.evaluate(() => ({ bodyHasProject: document.body.innerText.includes("Browser E2E Novel"), coreBound: document.querySelector(".nf-host-chip")?.textContent?.includes("Core bound") || document.querySelector(".nf-host-chip")?.textContent?.includes("Core 已绑定") }));
      if (!initial.coreBound || initial.surface !== "local_app" || initial.main !== 1 || !project.bodyHasProject || !project.coreBound || uploadRequests.length || external.length || pageErrors.length) throw new Error("LOCAL_LAUNCH_BROWSER_ASSERTION");
      return { status: "pass", receipt: { schema: receipt.schema, status: receipt.status, profile: receipt.profile, project_id: receipt.project_id, storage_boundary: receipt.storage_boundary, cloud_upload_started: receipt.cloud_upload_started, authority: receipt.authority, loopback: true }, browser: { initial, project }, non_get_requests: nonGet.length, upload_requests: uploadRequests.length, external_requests: external.length, page_errors: pageErrors.length };
    } finally { await page.close().catch(() => {}); await context.close().catch(() => {}); }
  } finally { await terminateProcess(launch).catch(() => {}); fs.rmSync(temporaryRoot, { recursive: true, force: true }); }
}

export async function machineJson(page, url, schema, authorityKeys = [], allowedKeys = ["schema", "authority"], shape, timeoutMs = DEFAULT_DEADLINE_MS) {
  const limit = normalizeDeadline(timeoutMs);
  let payload;
  try {
    payload = await withDeadline(
      () => page.evaluate(async ({ target, limit: byteLimit, deadlineMs }) => {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), deadlineMs);
        try {
          const response = await fetch(target, { method: "GET", credentials: "same-origin", signal: controller.signal });
          const contentType = response.headers.get("content-type") || "";
          const declared = Number(response.headers.get("content-length") || 0);
          if (declared > byteLimit) throw new Error("JSON_TOO_LARGE");
          if (!response.body) throw new Error("JSON_STREAM_UNSUPPORTED");
          const reader = response.body.getReader(); const chunks = []; let size = 0;
          while (true) { const { done, value } = await reader.read(); if (done) break; size += value.byteLength; if (size > byteLimit) { await reader.cancel(); throw new Error("JSON_TOO_LARGE"); } chunks.push(value); }
          const bytes = new Uint8Array(size); let offset = 0; for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
          return { contentType, body: new TextDecoder().decode(bytes) };
        } catch (error) {
          if (controller.signal.aborted) throw new Error("T605_MACHINE_JSON_TIMEOUT");
          throw new Error(error?.message === "JSON_TOO_LARGE" || error?.message === "JSON_STREAM_UNSUPPORTED" ? error.message : "T605_MACHINE_JSON_FETCH_FAILED");
        } finally { clearTimeout(timer); }
      }, { target: url, limit: JSON_LIMIT, deadlineMs: limit }),
      limit,
      { code: "MACHINE_JSON_TIMEOUT", label: "machine_json" },
    );
  } catch (error) {
    if (error?.code === "MACHINE_JSON_TIMEOUT") throw error;
    const message = String(error?.message || "");
    if (message === "T605_MACHINE_JSON_TIMEOUT") throw boundedTimeoutError("MACHINE_JSON_TIMEOUT", "machine_json", limit);
    if (message === "JSON_TOO_LARGE" || message === "JSON_STREAM_UNSUPPORTED") throw new Error(message);
    throw Object.assign(new Error("machine JSON fetch failed"), { code: "MACHINE_JSON_FETCH_FAILED", operation: "machine_json", timeout_ms: limit });
  }
  return assertMachineManifest(payload, schema, { authorityKeys, allowedKeys, shape });
}

export async function pageFetchProbe(page, target, { method = "GET", body = undefined, timeoutMs = DEFAULT_DEADLINE_MS, operation = "page_fetch" } = {}) {
  const limit = normalizeDeadline(timeoutMs);
  try {
    return await withDeadline(
      () => page.evaluate(async ({ target: requestTarget, requestMethod, requestBody, deadlineMs, probeOperation }) => {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), deadlineMs);
        try {
          const response = await fetch(requestTarget, { method: requestMethod, body: requestBody, signal: controller.signal });
          return { status: "fail", mode: "response", response_status: response.status, operation: probeOperation };
        } catch (error) {
          if (controller.signal.aborted) return { status: "fail", mode: "timeout", error: "T605_FETCH_TIMEOUT", operation: probeOperation };
          return { status: "pass", mode: "network_failure", error: String(error?.name || "NETWORK_FAILURE"), operation: probeOperation };
        } finally { clearTimeout(timer); }
      }, { target, requestMethod: method, requestBody: body, deadlineMs: limit, probeOperation: operation }),
      limit,
      { code: "PAGE_FETCH_TIMEOUT", label: operation },
    );
  } catch (error) {
    if (error?.code === "PAGE_FETCH_TIMEOUT") return { status: "fail", mode: "timeout", error: "T605_FETCH_TIMEOUT", operation };
    throw Object.assign(new Error("page fetch probe failed"), { code: "PAGE_FETCH_FAILED", operation, timeout_ms: limit });
  }
}

async function freshOfflineDocument(context, url, expectedLocale, timeoutMs) {
  const page = await context.newPage();
  try {
    await page.evaluate(() => { document.documentElement.innerHTML = "<head><title>T605 sentinel</title></head><body><main data-t605-sentinel>stale</main></body>"; });
    const before = await page.evaluate(() => ({ url: location.href, sentinel: Boolean(document.querySelector("[data-t605-sentinel]")) }));
    if (!before.sentinel) throw new Error("OFFLINE_SENTINEL_SETUP");
    const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    if (!response) throw new Error("OFFLINE_NO_RESPONSE");
    const observed = await page.evaluate(() => ({ url: location.href, lang: document.documentElement.lang, title: document.title, main: document.querySelectorAll("main").length, sentinel: Boolean(document.querySelector("[data-t605-sentinel]")), controller: Boolean(navigator.serviceWorker?.controller) }));
    if (observed.sentinel || !observed.controller || !observed.lang.startsWith(expectedLocale) || observed.main < 1) throw new Error("OFFLINE_STALE_OR_LOCALE");
    return { status: "pass", mode: "sw_response", response_status: response.status(), before, observed };
  } catch (error) {
    return { status: "fail", mode: error?.message === "OFFLINE_NO_RESPONSE" ? "network_failure" : "assertion_failure", error: String(error?.message || error) };
  } finally { await page.close().catch(() => {}); }
}

async function offlineDeny(context, url, timeoutMs) {
  const page = await context.newPage();
  try {
    await page.evaluate(() => { document.documentElement.innerHTML = "<head><title>T605 sentinel</title></head><body><main data-t605-sentinel>stale</main></body>"; });
    let response;
    try { response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs }); }
    catch (error) { return { status: "pass", mode: "network_failure", error: String(error?.name || "NETWORK_FAILURE") }; }
    const observed = await page.evaluate(() => ({ url: location.href, lang: document.documentElement.lang, main: document.querySelectorAll("main").length, sentinel: Boolean(document.querySelector("[data-t605-sentinel]")), body: document.body.innerText.slice(0, 256) }));
    const shell = observed.main > 0 && !observed.sentinel && Boolean(observed.lang);
    return { status: shell ? "fail" : "pass", mode: "sw_response", response_status: response.status(), observed };
  } finally { await page.close().catch(() => {}); }
}

async function freshOfflineStudio(context, url, timeoutMs) {
  const page = await context.newPage();
  try {
    await page.evaluate(() => { document.documentElement.innerHTML = "<head><title>T605 sentinel</title></head><body><main data-t605-sentinel>stale</main></body>"; });
    const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    await withDeadline(() => page.waitForSelector("main#main-content", { state: "visible", timeout: normalizeDeadline(timeoutMs) }), timeoutMs, { code: "STUDIO_OFFLINE_READY_TIMEOUT", label: "studio_offline_main" });
    const state = await page.evaluate(() => ({ controller: Boolean(navigator.serviceWorker?.controller), main: document.querySelectorAll("main#main-content").length, sentinel: Boolean(document.querySelector("[data-t605-sentinel]")), url: location.href }));
    if (!response || response.status() >= 500 || !state.controller || state.main !== 1 || state.sentinel) throw new Error("STUDIO_OFFLINE_SHELL");
    return { status: "pass", mode: "sw_response", response_status: response.status(), state };
  } catch (error) { return { status: "fail", mode: "navigation_failure", error: String(error?.message || error) }; }
  finally { await page.close().catch(() => {}); }
}

async function runSurface(browser, origin, surface, evidenceRoot, timeoutMs, repoRoot) {
  const checks = [], errors = [], capturedScreenshots = new Set();
  for (const item of matrix()) {
    const matrixTimeout = Math.min(timeoutMs, 30000);
    const nonGet = [];
    const modelRequests = [];
    const checkStart = checks.length;
    let context = null, page = null;
    try {
      context = await boundedBrowserAction(() => browser.newContext({ viewport: item.viewport, colorScheme: item.mode.colorScheme, reducedMotion: item.mode.reducedMotion, forcedColors: item.mode.forcedColors }), matrixTimeout, `context_${surface}_${item.id}`);
      page = await boundedBrowserAction(() => context.newPage(), matrixTimeout, `page_${surface}_${item.id}`);
      if (surface === "site") await boundedBrowserAction(() => installQuickDemoReceiptProbe(page), matrixTimeout, `quick_demo_probe_${item.id}`);
      page.on("pageerror", (error) => errors.push({ id: "pageerror", surface, matrix: item.id, message: String(error?.name || "PageError") }));
      page.on("request", (request) => { if (!["GET", "HEAD"].includes(request.method())) nonGet.push(request.method()); if (/\/api\/(?:model|responses|chat)|\/v1\/(?:responses|chat)|anthropic/i.test(request.url())) modelRequests.push(request.url()); });
      const route = surface === "site" ? "/" : "/manuscript";
      await page.goto(new URL(route, origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
      if (surface === "studio") await boundedBrowserAction(() => page.waitForSelector("main#main-content h1, main#main-content h2", { state: "visible", timeout: matrixTimeout }), matrixTimeout, `studio_heading_ready_${item.id}`);
      const shell = await page.evaluate(() => {
        const main = document.querySelector("main#main-content, main");
        return { main: Boolean(main), mainCount: document.querySelectorAll("main").length, scrollWidth: document.documentElement.scrollWidth, innerWidth: innerWidth, bodyText: document.body.innerText.slice(0, 4096), lang: document.documentElement.lang, reduced: matchMedia("(prefers-reduced-motion: reduce)").matches, forced: matchMedia("(forced-colors: active)").matches, dark: matchMedia("(prefers-color-scheme: dark)").matches };
      });
      checks.push(check("shell", shell.main && shell.mainCount === 1 && shell.scrollWidth <= shell.innerWidth + 1 ? "pass" : "fail", route, shell));
      const mediaExpected = { reduced: item.mode.reducedMotion === "reduce", forced: item.mode.forcedColors === "active", dark: item.mode.colorScheme === "dark" };
      checks.push(check("media-state", shell.reduced === mediaExpected.reduced && shell.forced === mediaExpected.forced && shell.dark === mediaExpected.dark ? "pass" : "fail", route, { expected: mediaExpected, actual: { reduced: shell.reduced, forced: shell.forced, dark: shell.dark } }));
      const semantics = await page.evaluate(() => {
        const named = (node) => (node.getAttribute("aria-label") || (node.getAttribute("aria-labelledby") && document.getElementById(node.getAttribute("aria-labelledby"))?.textContent) || node.textContent || "").trim();
        const landmarkNodes = [...document.querySelectorAll("nav,header,main,footer,aside,[role=\"banner\"],[role=\"navigation\"],[role=\"contentinfo\"],[role=\"complementary\"]")];
        const headingNodes = [...document.querySelectorAll("h1,h2,h3,[role=\"heading\"]")];
        return { mainCount: document.querySelectorAll("main").length, namedButtons: [...document.querySelectorAll("button")].filter(named).length, headingCount: headingNodes.length, headingNames: headingNodes.filter(named).length, landmarks: landmarkNodes.length, namedLandmarks: landmarkNodes.filter(named).length, landmarkRoles: landmarkNodes.map((node) => node.getAttribute("role") || node.tagName.toLowerCase()).filter(Boolean), ariaCurrent: Boolean(document.querySelector("[aria-current]")) };
      });
      checks.push(check("wcag-semantics", (() => { try { return assertSemantics(semantics), "pass"; } catch { return "fail"; } })(), route, semantics));
      const performance = await page.evaluate(async () => {
        if (typeof PerformanceObserver === "undefined") return { supported: false };
        let lcpMs = 0, cls = 0, tbtMs = 0;
        try {
          const lcp = new PerformanceObserver((list) => { const last = list.getEntries().at(-1); if (last) lcpMs = last.startTime; }); lcp.observe({ type: "largest-contentful-paint", buffered: true });
          const shifts = new PerformanceObserver((list) => { for (const entry of list.getEntries()) if (!entry.hadRecentInput) cls += entry.value; }); shifts.observe({ type: "layout-shift", buffered: true });
          const tasks = new PerformanceObserver((list) => { for (const entry of list.getEntries()) tbtMs += Math.max(0, entry.duration - 50); }); tasks.observe({ type: "longtask", buffered: true });
          await new Promise((resolve) => setTimeout(resolve, 2000)); lcp.disconnect(); shifts.disconnect(); tasks.disconnect();
          return { supported: lcpMs > 0, lcpMs, cls, tbtMs, inpMs: null, inp_supported: false, sampleMs: 2000, settled: true };
        } catch { return { supported: false }; }
      });
      checks.push(check("cwv-budget", (() => { try { return assertCwv(performance), "pass"; } catch { return "fail"; } })(), route, performance));
      const contrast = await page.evaluate(() => {
        const selectors = "body,button,a,[role],input,textarea,select";
        const visible = [...document.querySelectorAll(selectors)].filter((node) => (node.textContent?.trim() || ["INPUT", "TEXTAREA", "SELECT"].includes(node.tagName)) && getComputedStyle(node).visibility !== "hidden" && getComputedStyle(node).display !== "none");
        const canvas = document.createElement("canvas"); canvas.width = 1; canvas.height = 1;
        const context = canvas.getContext("2d", { willReadFrequently: true });
        const pixel = () => { if (!context) throw new Error("CONTRAST_CANVAS_UNSUPPORTED"); const data = context.getImageData(0, 0, 1, 1).data; return `rgb(${data[0]}, ${data[1]}, ${data[2]})`; };
        const paint = (color) => { if (!context || typeof color !== "string") throw new Error("CONTRAST_COLOR_UNSUPPORTED"); context.fillStyle = color; if (!context.fillStyle) throw new Error("CONTRAST_COLOR_UNSUPPORTED"); context.fillRect(0, 0, 1, 1); };
        const rasterize = (node, style) => {
          if (!context) throw new Error("CONTRAST_CANVAS_UNSUPPORTED");
          context.clearRect(0, 0, 1, 1); context.fillStyle = "rgb(255, 255, 255)"; context.fillRect(0, 0, 1, 1);
          const ancestors = []; for (let current = node; current; current = current.parentElement) ancestors.unshift(current);
          for (const ancestor of ancestors) { const background = getComputedStyle(ancestor).backgroundColor; if (background !== "transparent" && !/^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*0\s*\)$/i.test(background)) paint(background); }
          const background = pixel(); paint(style.color); const foreground = pixel(); return { foreground, background };
        };
        return visible.map((node) => {
          const style = getComputedStyle(node); const colors = rasterize(node, style);
          const largeText = Number.parseFloat(style.fontSize) >= 18.66 || (Number.parseFloat(style.fontSize) >= 14 && Number.parseInt(style.fontWeight, 10) >= 700);
          const nonText = ["BUTTON", "INPUT", "TEXTAREA", "SELECT"].includes(node.tagName); const focus = node.matches(":focus-visible") || nonText;
          return { selector: node.tagName.toLowerCase(), foreground: colors.foreground, background: colors.background, source_foreground: style.color, source_background: style.backgroundColor, largeText, nonText, focus, forcedSystemColor: CSS.supports("color", "CanvasText") && CSS.supports("color", "Canvas") };
        });
      });
      const contrastResults = []; let contrastStatus = contrast.length > 0 ? "pass" : "fail";
      for (const sample of contrast) { const threshold = requiredContrastThreshold(sample); if (item.mode.forcedColors === "active") { if (!sample.forcedSystemColor || (sample.focus && !sample.nonText)) contrastStatus = "fail"; contrastResults.push({ ...sample, mode: "forced-colors", threshold: "system-colors" }); continue; } try { const ratio = contrastRatio(sample.foreground, sample.background); contrastResults.push({ ...sample, ratio, threshold }); if (ratio < threshold) contrastStatus = "fail"; } catch { contrastStatus = "fail"; contrastResults.push({ ...sample, supported: false, threshold }); } }
      checks.push(check("wcag-aa-contrast", contrastStatus, route, { supported: contrast.length > 0, samples: contrastResults, thresholds: { normal: 4.5, large: 3, non_text: 3 } }));
      if (surface === "site") {
        const sections = await page.locator("[data-home-section]").count();
        checks.push(check("home-sections", sections === 6 ? "pass" : "fail", route, { count: sections }));
        const demo = await page.locator("#quick-demo").count();
        checks.push(check("quick-demo-present", demo === 1 ? "pass" : "fail", route, { count: demo }));
        const inspector = await page.goto(new URL("/inspect", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
        void inspector;
        const inspectorDemo = page.getByRole("button", { name: /Load demo project|载入示例项目/i }).first();
        const inspectorDemoCount = await boundedBrowserAction(() => inspectorDemo.count(), matrixTimeout, `inspector_demo_count_${item.id}`);
        const inspectorDemoVisible = inspectorDemoCount > 0 && await boundedBrowserAction(() => inspectorDemo.isVisible({ timeout: matrixTimeout }), matrixTimeout, `inspector_demo_visibility_${item.id}`).catch(() => false);
        if (inspectorDemoVisible) await boundedClick(inspectorDemo, matrixTimeout, `inspector_demo_click_${item.id}`);
        checks.push(check("native-inspector-demo", inspectorDemoVisible ? "pass" : "fail", "/inspect", { clicked: Boolean(inspectorDemoVisible), present: inspectorDemoCount > 0, visible: inspectorDemoVisible }, inspectorDemoCount > 0 && !inspectorDemoVisible ? "required Inspector demo control is hidden" : undefined));
        const inspectorText = await page.locator("body").innerText().catch(() => "");
        const inspectorFields = await page.evaluate(() => ({ schema: document.body.innerText.includes("quillframe_project_v1_0"), context: document.body.innerText.includes("quillframe_project_context_v1_0"), chapter: document.body.innerText.includes("CH001"), fingerprint: document.body.innerText.includes("manifest_fingerprint"), data: document.body.innerText.includes(".quillframe/data"), authority: !document.body.innerText.includes("authority=true"), legacy: !document.body.innerText.includes("quillframe.lock.json") && !document.body.innerText.includes("framework.attestation.json") }));
        checks.push(check("native-inspector", Object.values(inspectorFields).every(Boolean) ? "pass" : "fail", "/inspect", inspectorFields));
        await page.goto(new URL("/", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
        let machineContracts = true;
        for (const [endpoint, schema, authority, keys] of [["/.well-known/ai-catalog.json", "quillframe_ai_catalog_v1", ["authority"], ["schema", "product", "version_line", "canonical", "documentation", "studio", "repository", "sitemap_xml", "sitemap_markdown", "llms", "llms_full", "agent_skills_index", "content_signal", "public_service_contracts", "authority", "notes"]], ["/.well-known/agent-skills/index.json", "quillframe_agent_skills_index_v1", [], ["schema", "product", "skills"]]]) {
          try { await machineJson(page, new URL(endpoint, origin).href, schema, authority, keys, undefined, Math.min(timeoutMs, DEFAULT_DEADLINE_MS)); checks.push(check(`machine-${schema}`, "pass", endpoint, { schema })); }
          catch (error) { machineContracts = false; checks.push(check(`machine-${schema}`, "fail", endpoint, {}, String(error?.message || "MACHINE_JSON"))); }
        }
        checks.push(check("machine_contracts", machineContracts ? "pass" : "fail", "/.well-known/", { endpoints: 2 }));
        await page.goto(new URL("/", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
        const skip = page.locator('a[href="#main-content"]').first();
        const skipPresent = await boundedBrowserAction(() => skip.count(), matrixTimeout, `skip_count_${item.id}`);
        const skipVisible = skipPresent > 0 && await boundedBrowserAction(() => skip.isVisible({ timeout: matrixTimeout }), matrixTimeout, `skip_visibility_${item.id}`).catch(() => false);
        if (skipVisible) { await boundedBrowserAction(() => skip.focus(), matrixTimeout, `skip_focus_${item.id}`); await boundedBrowserAction(() => skip.press("Enter"), matrixTimeout, `skip_press_${item.id}`); }
        checks.push(check("keyboard", skipVisible && await page.evaluate(() => document.activeElement?.id === "main-content") ? "pass" : "fail", "/", { skip_present: Boolean(skipPresent), skip_visible: skipVisible }));
        const search = page.locator(".header-search:visible, .launcher-search:visible").first();
        const searchPresent = await boundedBrowserAction(() => search.count(), matrixTimeout, `search_count_${item.id}`);
        const searchVisible = searchPresent > 0 && await boundedBrowserAction(() => search.isVisible({ timeout: matrixTimeout }), matrixTimeout, `search_visibility_${item.id}`).catch(() => false);
        if (searchVisible) {
          await boundedClick(search, matrixTimeout, `search_click_${item.id}`);
          const dialog = page.locator("dialog.command-dialog").first();
          const open = await dialog.getAttribute("open").catch(() => null);
          const modal = await dialog.evaluate((node) => typeof node.matches === "function" && node.matches(":modal")).catch(() => false);
          checks.push(check("site-native-dialog", open !== null && modal ? "pass" : "fail", "/", { open: Boolean(open), modal }));
          const input = dialog.locator("input").first(); const inputFocused = await input.evaluate((node) => node === document.activeElement).catch(() => false);
          await boundedBrowserAction(() => page.keyboard.press("Tab"), matrixTimeout, `search_tab_${item.id}`); const tabInside = await dialog.evaluate((node) => node.contains(document.activeElement)).catch(() => false);
          await boundedBrowserAction(() => page.keyboard.press("Shift+Tab"), matrixTimeout, `search_shift_tab_${item.id}`); const reverseInside = await dialog.evaluate((node) => node.contains(document.activeElement)).catch(() => false);
          checks.push(check("site-dialog-focus-trap", inputFocused && tabInside && reverseInside ? "pass" : "fail", "/", { inputFocused, tabInside, reverseInside }));
          await boundedBrowserAction(() => page.keyboard.press("Escape"), matrixTimeout, `search_escape_${item.id}`);
          checks.push(check("site-dialog-close", await search.evaluate((node) => node === document.activeElement).catch(() => false) ? "pass" : "fail", "/", {}));
          const backgroundRestored = await page.evaluate(() => ({ hidden: document.querySelector("#app")?.getAttribute("aria-hidden") || null, inert: Boolean(document.querySelector("#app")?.inert) }));
          checks.push(check("dialog", open !== null && modal && inputFocused && tabInside && reverseInside && backgroundRestored.hidden !== "true" && !backgroundRestored.inert ? "pass" : "fail", "/", { open: Boolean(open), modal, inputFocused, tabInside, reverseInside, backgroundRestored }));
          await boundedBrowserAction(() => page.keyboard.press(process.platform === "darwin" ? "Meta+KeyK" : "Control+KeyK"), matrixTimeout, `search_shortcut_${item.id}`);
          checks.push(check("site-dialog-shortcut", await page.locator("dialog.command-dialog[open]").count() === 1 ? "pass" : "fail", "/", {}));
          await boundedBrowserAction(() => page.keyboard.press("Escape"), matrixTimeout, `search_shortcut_escape_${item.id}`);
        } else checks.push(check("dialog", "fail", "/", { search_present: Boolean(searchPresent), search_visible: searchVisible }, searchPresent ? "required product search/dialog trigger is hidden" : "required product search/dialog trigger missing"));
        if (["wide-light", "wide-reduced", "small-light"].includes(item.id)) {
          const demoButton = page.locator(".quick-demo-run").first();
          const demoPresent = await boundedBrowserAction(() => demoButton.count(), matrixTimeout, `quick_demo_count_${item.id}`);
          const demoVisible = demoPresent > 0 && await boundedBrowserAction(() => demoButton.isVisible({ timeout: matrixTimeout }), matrixTimeout, `quick_demo_visibility_${item.id}`).catch(() => false);
          if (demoVisible) {
            await boundedClick(demoButton, matrixTimeout, `quick_demo_click_${item.id}`);
            await boundedBrowserAction(() => page.waitForFunction(() => document.querySelector(".quick-demo-result")?.textContent?.includes("PASS") && window.__qfT605Receipts?.length > 0, { timeout: matrixTimeout }), matrixTimeout, `quick_demo_wait_${item.id}`).catch(() => {});
            const receipt = await page.evaluate(() => ({ receipt: window.__qfT605Receipts?.at(-1) || null, schema: document.querySelector(".quick-demo-receipt small")?.textContent?.trim() || "", chapter: document.querySelector(".quick-demo-receipt header strong")?.textContent?.trim() || "", statuses: [...document.querySelectorAll(".quick-demo-result article > b")].map((node) => node.textContent?.trim() || ""), boundary: document.querySelector(".quick-demo-boundary code")?.textContent?.trim() || "" }));
            checks.push(check("quick_demo_truth", (() => { try { assertQuickDemoDom(receipt, nonGet.map((request) => request.method || request), modelRequests); return "pass"; } catch { return "fail"; } })(), "/#quick-demo", { receipt, writes: nonGet.length, model_requests: modelRequests.length }));
          } else checks.push(check("quick_demo_truth", "fail", "/#quick-demo", { demo_present: Boolean(demoPresent), demo_visible: demoVisible }, demoPresent ? "required Quick Demo control is hidden" : "required Quick Demo control missing"));
        }
        if (item.id === "wide-light") {
          const docsContext = await browser.newContext({ viewport: item.viewport, colorScheme: "light", reducedMotion: "no-preference", forcedColors: "none" });
          const docs = await docsContext.newPage();
          try {
            const homeResponse = await docs.goto(new URL("/", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            await waitForServiceWorkerReady(docs, Math.min(timeoutMs, DEFAULT_DEADLINE_MS), "docs_home_ready");
            const homeControlled = await docs.evaluate(() => Boolean(navigator.serviceWorker?.controller));
            if (!homeResponse || !homeControlled) throw new Error("DOCS_SW_HOME_NOT_CONTROLLED");
            const onlineResponse = await docs.goto(new URL("/docs/", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            const controlled = await docs.evaluate(() => Boolean(navigator.serviceWorker?.controller));
            if (!onlineResponse || !controlled) throw new Error("DOCS_SW_NOT_CONTROLLED");
            await waitForServiceWorkerReady(docs, Math.min(timeoutMs, DEFAULT_DEADLINE_MS), "docs_zh_ready");
            const docsEn = await docsContext.newPage();
            await docsEn.goto(new URL("/docs/en/", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            await waitForServiceWorkerReady(docsEn, Math.min(timeoutMs, DEFAULT_DEADLINE_MS), "docs_en_ready");
            const secondControlled = await docsEn.evaluate(() => Boolean(navigator.serviceWorker?.controller));
            checks.push(check("offline", controlled && secondControlled ? "pass" : "fail", "/docs/", { controlled, second_page_controlled: secondControlled }));
            await docsContext.setOffline(true);
            const offlineEnglish = await freshOfflineDocument(docsContext, new URL("/docs/en/route?x=1", origin).href, "en", timeoutMs);
            const offlineChinese = await freshOfflineDocument(docsContext, new URL("/docs/?q=1", origin).href, "zh", timeoutMs);
            checks.push(check("docs-offline-english", offlineEnglish.status, "/docs/en/route?x=1", offlineEnglish));
            checks.push(check("docs-offline-chinese", offlineChinese.status, "/docs/?q=1", offlineChinese));
            for (const denied of ["/docs/en-US/route", "/docs/zh-CN/route", "/api/status"]) {
              const deny = await offlineDeny(docsContext, new URL(denied, origin).href, Math.min(timeoutMs, 5000));
              checks.push(check(`docs-offline-deny-${denied.replaceAll("/", "_")}`, deny.status, denied, deny));
            }
            const crossOrigin = await pageFetchProbe(docs, "https://cross-origin.invalid/docs", { timeoutMs: Math.min(timeoutMs, DEFAULT_DEADLINE_MS), operation: "docs_cross_origin" });
            checks.push(check("docs-offline-cross-origin", crossOrigin.status, "https://cross-origin.invalid/docs", crossOrigin));
            const nonGet = await pageFetchProbe(docs, "/api/status", { method: "POST", body: "x", timeoutMs: Math.min(timeoutMs, DEFAULT_DEADLINE_MS), operation: "docs_offline_non_get" });
            checks.push(check("docs-offline-non-get", nonGet.status, "/api/status", nonGet));
            await docsEn.close().catch(() => {});
          } catch (error) { errors.push({ id: "docs-offline", surface, message: String(error?.code || error?.name || "DOCS_OFFLINE") }); }
          finally { await docs.close().catch(() => {}); await docsContext.close().catch(() => {}); }
        }
      } else {
        const unboundDom = await page.evaluate(() => ({ hostChipText: document.querySelector(".nf-host-chip")?.textContent?.trim() || "", surface: document.querySelector(".nf-host-chip")?.getAttribute("data-surface") || "", coreBound: Boolean(document.querySelector('[data-core-bound="true"]')), projectTitle: Boolean(document.querySelector("[data-project-title]")), runId: Boolean(document.querySelector("[data-run-id]")), mutationControls: Boolean(document.querySelector('[data-authority="true"]')) }));
        checks.push(check("studio-unbound", (() => { try { return assertUnboundStudioDom(unboundDom), "pass"; } catch { return "fail"; } })(), route, unboundDom));
        let machineContracts = true;
        for (const endpoint of ["/.well-known/quillframe-host.json", "/.well-known/quillframe-studio-footprint.json"]) {
          try {
            const host = endpoint.includes("host.json"); const schema = host ? "quillframe_studio_host_descriptor_v1" : "quillframe_studio_footprint_v1";
            const keys = host ? ["schema", "surface", "delivery", "core_host", "authority", "canon_authority", "framework_write_authority", "settlement_authority", "direct_core_store_access"] : ["schema", "generated_at", "measurement", "assets", "runtime_contract", "not_measured"];
            const shape = host ? { type: "object", required: keys, exact: Object.fromEntries(keys.map((key) => [key, key === "authority" || key.endsWith("authority") || key === "direct_core_store_access" ? { type: "boolean", const: false } : { type: "string" }])) } : { type: "object", required: keys, exact: { schema: { type: "string", const: schema }, generated_at: { type: "string" }, measurement: { type: "string", const: "production_build_artifacts" }, assets: { type: "object", required: ["javascript", "css"], exact: { javascript: { type: "object", required: ["files", "bytes", "gzip_bytes", "largest_bytes"], exact: Object.fromEntries(["files", "bytes", "gzip_bytes", "largest_bytes"].map((key) => [key, { type: "number" }])) }, css: { type: "object", required: ["files", "bytes", "gzip_bytes", "largest_bytes"], exact: Object.fromEntries(["files", "bytes", "gzip_bytes", "largest_bytes"].map((key) => [key, { type: "number" }])) } } }, runtime_contract: { type: "object", required: ["weiui_runtime_javascript_required", "persistent_database_required_by_hosted_ui", "core_required_for_browser_preflight", "core_required_for_local_playground_preview"], exact: Object.fromEntries(["weiui_runtime_javascript_required", "persistent_database_required_by_hosted_ui", "core_required_for_browser_preflight", "core_required_for_local_playground_preview"].map((key) => [key, { type: "boolean" }])) }, not_measured: { type: "array", maxItems: 32, items: { type: "string" } } } };
            await machineJson(page, new URL(endpoint, origin).href, schema, host ? ["authority", "canon_authority", "framework_write_authority", "settlement_authority", "direct_core_store_access"] : [], keys, shape, Math.min(timeoutMs, DEFAULT_DEADLINE_MS)); checks.push(check(`machine-${schema}`, "pass", endpoint, { schema }));
          }
          catch (error) { machineContracts = false; checks.push(check(`machine-${endpoint}`, "fail", endpoint, {}, String(error?.message || "MACHINE_JSON"))); }
        }
        checks.push(check("machine_contracts", machineContracts ? "pass" : "fail", "/.well-known/", { endpoints: 2 }));
        const skip = page.locator(".nf-studio-skip-link").first();
        const skipPresent = await boundedBrowserAction(() => skip.count(), matrixTimeout, `studio_skip_count_${item.id}`);
        const skipVisible = skipPresent > 0 && await boundedBrowserAction(() => skip.isVisible({ timeout: matrixTimeout }), matrixTimeout, `studio_skip_visibility_${item.id}`).catch(() => false);
        if (skipVisible) { await boundedBrowserAction(() => skip.focus(), matrixTimeout, `studio_skip_focus_${item.id}`); await boundedBrowserAction(() => skip.press("Enter"), matrixTimeout, `studio_skip_press_${item.id}`); }
        checks.push(check("keyboard", skipVisible && await page.evaluate(() => document.activeElement?.id === "main-content") ? "pass" : "fail", route, { skip_present: Boolean(skipPresent), skip_visible: skipVisible }));
        const command = page.locator(".nf-command-trigger").first();
        const commandPresent = await boundedBrowserAction(() => command.count(), matrixTimeout, `command_count_${item.id}`);
        const commandVisible = commandPresent > 0 && await boundedBrowserAction(() => command.isVisible({ timeout: matrixTimeout }), matrixTimeout, `command_visibility_${item.id}`).catch(() => false);
        if (commandVisible) {
          await boundedClick(command, matrixTimeout, `command_click_${item.id}`);
          const dialog = page.locator('.nf-command[role="dialog"][aria-modal="true"]').first();
          checks.push(check("studio-command-dialog", await dialog.isVisible().catch(() => false) ? "pass" : "fail", route, {}));
          const isolated = await page.locator("#app").evaluate((node) => ({ inert: Boolean(node.inert), ariaHidden: node.getAttribute("aria-hidden") === "true" })).catch(() => ({ inert: false, ariaHidden: false }));
          checks.push(check("studio-command-inert", isolated.inert || isolated.ariaHidden ? "pass" : "fail", route, isolated));
          await boundedBrowserAction(() => page.keyboard.press("Tab"), matrixTimeout, `command_tab_${item.id}`); const tabInside = await dialog.evaluate((node) => node.contains(document.activeElement)).catch(() => false);
          await boundedBrowserAction(() => page.keyboard.press("Shift+Tab"), matrixTimeout, `command_shift_tab_${item.id}`); const reverseInside = await dialog.evaluate((node) => node.contains(document.activeElement)).catch(() => false);
          checks.push(check("studio-command-tab-trap", tabInside && reverseInside ? "pass" : "fail", route, { tabInside, reverseInside }));
          await boundedBrowserAction(() => page.keyboard.press("Escape"), matrixTimeout, `command_escape_${item.id}`);
          const restored = await page.evaluate(() => ({ inert: Boolean(document.querySelector("#app")?.inert), hidden: document.querySelector("#app")?.getAttribute("aria-hidden") || null }));
        checks.push(check("dialog", await command.evaluate((node) => node === document.activeElement).catch(() => false) && !restored.inert && restored.hidden !== "true" ? "pass" : "fail", route, { restored }));
        } else checks.push(check("dialog", "fail", route, { command_present: Boolean(commandPresent), command_visible: commandVisible }, commandPresent ? "required Studio command trigger is hidden" : "required Studio command trigger missing"));
        if (item.id === "wide-light") {
          const unboundRoutes = [];
          for (const studioRoute of ["/", "/start", "/review?project=T605", "/context", "/capabilities", "/settings?section=models"]) {
            await page.goto(new URL(studioRoute, origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            const routeDom = await page.evaluate(() => ({ main: document.querySelectorAll("main#main-content").length, hostChipText: document.querySelector(".nf-host-chip")?.textContent?.trim() || "", surface: document.querySelector(".nf-host-chip")?.getAttribute("data-surface") || "", coreBound: Boolean(document.querySelector('[data-core-bound="true"]')), projectTitle: Boolean(document.querySelector("[data-project-title]")), runId: Boolean(document.querySelector("[data-run-id]")), mutationControls: Boolean(document.querySelector('[data-authority="true"]')) }));
            let routeStatus = "pass"; try { assertUnboundStudioDom(routeDom); if (routeDom.main !== 1) throw new Error("MAIN"); } catch { routeStatus = "fail"; }
            unboundRoutes.push({ route: studioRoute, status: routeStatus, ...routeDom });
          }
          checks.push(check("studio-unbound-routes", unboundRoutes.every((entry) => entry.status === "pass") ? "pass" : "fail", "/studio-routes", { routes: unboundRoutes }));
          await page.goto(new URL(route, origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
          // The main matrix context may already be controlled by the Studio
          // service worker.  Review's route fixture must own the initial HTML
          // response, so give it a clean, independent context with SW blocked.
          const reviewContext = await browser.newContext({ viewport: item.viewport, colorScheme: item.mode.colorScheme, reducedMotion: item.mode.reducedMotion, forcedColors: item.mode.forcedColors, serviceWorkers: "block" });
          const review = await reviewContext.newPage();
          const queryRequests = []; const bridgeResults = []; const bridgeResultByRequestId = new Map(); const bridgeFailures = [];
          review.on("request", (request) => { if (request.url().includes("/api/bridge/invoke")) { try { queryRequests.push(request.postDataJSON()); } catch { bridgeFailures.push("request_json"); } } });
          review.on("response", async (response) => { if (response.url().includes("/api/bridge/invoke")) { try { const result = await response.json(); bridgeResults.push(result); if (result?.request_id) bridgeResultByRequestId.set(result.request_id, result); } catch { bridgeFailures.push("response_json"); } } });
          try {
            const reviewFixture = await installReviewFixture(review, { repoRoot, timeoutMs: Math.min(timeoutMs, DEFAULT_DEADLINE_MS) });
            await review.goto(new URL("/review?project=T605", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            const accept = review.getByRole("button", { name: /Accept/i }).first();
            const acceptInitialCount = await boundedBrowserAction(() => accept.count(), matrixTimeout, "review_accept_initial_count");
            if (acceptInitialCount === 0) await boundedBrowserAction(() => review.waitForFunction(() => [...document.querySelectorAll("button")].some((node) => /Accept/i.test(node.textContent || "")), { timeout: matrixTimeout }), matrixTimeout, "review_accept_ready");
            const acceptPresent = await boundedBrowserAction(() => accept.count(), matrixTimeout, "review_accept_count");
            const acceptVisible = acceptPresent > 0 && await boundedBrowserAction(() => accept.isVisible({ timeout: matrixTimeout }), matrixTimeout, "review_accept_visibility").catch(() => false);
            if (!acceptVisible) { checks.push(check("review-accept-entry", "fail", "/review?project=T605", { accept_present: Boolean(acceptPresent), accept_visible: acceptVisible }, acceptPresent ? "required Review Accept control is hidden" : "required Review Accept control missing")); throw new Error("REVIEW_ACCEPT_MISSING"); }
            await boundedClick(accept, matrixTimeout, "review_accept_click");
            await boundedBrowserAction(() => review.waitForTimeout(50), matrixTimeout, "review_accept_open_settle");
            const dialog = review.locator('[role="alertdialog"][aria-modal="true"]').first();
            const dialogState = await dialog.evaluate((node) => ({ label: node.getAttribute("aria-labelledby") || node.getAttribute("aria-label"), modal: node.getAttribute("aria-modal"), visible: Boolean(node.getClientRects().length), cancel: Boolean(node.querySelector("button")), modalCount: document.querySelectorAll('[role="alertdialog"][aria-modal="true"]').length, ancestorIsolation: Boolean(document.querySelector("#app")?.inert || document.querySelector("#app")?.getAttribute("aria-hidden") === "true"), acceptDisabled: Boolean(node.querySelector("button:not(:last-child)")?.disabled), checkboxUnchecked: node.querySelector('input[type="checkbox"]')?.checked === false })).catch(() => ({ visible: false }));
            checks.push(check("review-accept-dialog", dialogState.visible && dialogState.modal === "true" && Boolean(dialogState.label) ? "pass" : "fail", "/review?project=T605", dialogState));
            if (dialogState.visible) {
              const overlay = review.locator(".qf-modal-overlay").first();
              await boundedBrowserAction(() => overlay.click({ position: { x: 2, y: 2 }, timeout: matrixTimeout }), matrixTimeout, "review_modal_outside").catch(() => {});
              const outsideClosed = !(await dialog.isVisible().catch(() => true));
              if (!outsideClosed) await boundedBrowserAction(() => review.keyboard.press("Escape"), matrixTimeout, "review_modal_escape");
              await boundedClick(accept, matrixTimeout, "review_accept_reopen"); await boundedBrowserAction(() => review.waitForTimeout(20), matrixTimeout, "review_accept_settle");
              const cancelFocused = await dialog.locator("button").last().evaluate((node) => node === document.activeElement).catch(() => false);
              const inert = await review.locator("#app").evaluate((node) => Boolean(node.inert) || node.getAttribute("aria-hidden") === "true").catch(() => false);
              await boundedBrowserAction(() => review.keyboard.press("Tab"), matrixTimeout, "review_modal_tab"); const tabInside = await dialog.evaluate((node) => node.contains(document.activeElement)).catch(() => false);
              await boundedBrowserAction(() => review.keyboard.press("Shift+Tab"), matrixTimeout, "review_modal_shift_tab"); const reverseInside = await dialog.evaluate((node) => node.contains(document.activeElement)).catch(() => false);
              checks.push(check("review-dialog-a11y", cancelFocused && inert && tabInside && reverseInside && outsideClosed && dialogState.modalCount === 1 && dialogState.acceptDisabled && dialogState.checkboxUnchecked ? "pass" : "fail", "/review?project=T605", { cancelFocused, inert, tabInside, reverseInside, outsideClosed, modalCount: dialogState.modalCount, acceptDisabled: dialogState.acceptDisabled, checkboxUnchecked: dialogState.checkboxUnchecked }));
              await boundedBrowserAction(() => review.keyboard.press("Escape"), matrixTimeout, "review_modal_close");
              const triggerReturned = await accept.evaluate((node) => node === document.activeElement).catch(() => false);
              const restored = await review.locator("#app").evaluate((node) => ({ inert: Boolean(node.inert), hidden: node.getAttribute("aria-hidden") })).catch(() => ({ inert: true, hidden: "true" }));
              checks.push(check("review-dialog-close", !(await dialog.isVisible().catch(() => true)) && triggerReturned && !restored.inert && restored.hidden !== "true" ? "pass" : "fail", "/review?project=T605", { triggerReturned, restored }));
            }
            let bridgeStatus = "pass";
            try { if (queryRequests.length === 0 || bridgeResults.length !== queryRequests.length || queryRequests.some((request) => assertBridgeRequest(request) === false)) throw new Error("BRIDGE_QUERY_EMPTY"); for (const request of queryRequests) assertBridgeResult(bridgeResultByRequestId.get(request.request_id), request); } catch { bridgeStatus = "fail"; }
            checks.push(check("review_bridge_contract", bridgeStatus, "/review?project=T605", { request_count: queryRequests.length, response_count: bridgeResults.length, failures: bridgeFailures }));
            checks.push(check("review_query_only", queryRequests.length > 0 && queryRequests.every((request) => ["bridge.describe", "inspector.candidates.list", "candidate.review.get", "candidate.visible.get"].includes(request.operation)) && reviewFixture.blockedRequests.length === 0 && reviewFixture.routeFailures.length === 0 ? "pass" : "fail", "/review?project=T605", { operations: queryRequests.map((request) => request.operation), blocked: reviewFixture.blockedRequests, route_failures: reviewFixture.routeFailures }));
          } catch (error) { checks.push(check("review-accept-dialog", "fail", "/review?project=T605", { matrix: item.id, operation: error?.operation || null, timeout_ms: error?.timeout_ms || null }, String(error?.code || error?.name || "REVIEW_DIALOG"))); }
          finally { await review.close().catch(() => {}); await reviewContext.close().catch(() => {}); }
          const offlineContext = await browser.newContext({ viewport: item.viewport, colorScheme: "light", reducedMotion: "no-preference", forcedColors: "none" });
          const offline = await offlineContext.newPage();
          try {
            const homeResponse = await offline.goto(new URL("/", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            await waitForServiceWorkerReady(offline, Math.min(timeoutMs, DEFAULT_DEADLINE_MS), "studio_home_ready");
            const homeControlled = await offline.evaluate(() => Boolean(navigator.serviceWorker?.controller));
            const startResponse = await offline.goto(new URL("/start", origin).href, { waitUntil: "domcontentloaded", timeout: timeoutMs });
            await waitForServiceWorkerReady(offline, Math.min(timeoutMs, DEFAULT_DEADLINE_MS), "studio_ready");
            const controlled = await offline.evaluate(() => Boolean(navigator.serviceWorker?.controller));
            if (!homeResponse || !homeControlled || !startResponse || !controlled) throw new Error("STUDIO_SW_NOT_CONTROLLED");
            await offline.context().setOffline(true);
            const offlineShell = controlled ? await freshOfflineStudio(offlineContext, new URL("/start?offline=1", origin).href, Math.min(timeoutMs, 5000)) : { status: "fail", mode: "not_controlled" };
            checks.push(check("offline", offlineShell.status, "/start", { controlled, ...offlineShell }));
          } catch (error) { checks.push(check("studio-offline-shell", "fail", "/start", {}, String(error?.code || "STUDIO_OFFLINE"))); }
          finally { await offline.close().catch(() => {}); await offlineContext.close().catch(() => {}); }
        }
      }
      if (["wide", "tablet", "small"].includes(item.viewport.id)) {
        if (surface === "site") {
          const readiness = await prepareHomeScreenshot(page, matrixTimeout);
          checks.push(check("screenshot-content", "pass", route, { count: readiness.count, reveal_groups: readiness.reveal_groups.map((group) => ({ selector: group.selector, count: group.count, visible: group.visible, nonempty: group.nonempty })) }));
        }
        else await boundedBrowserAction(() => page.evaluate(() => { window.scrollTo({ top: 0, left: 0, behavior: "auto" }); return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); }), Math.min(matrixTimeout, DEFAULT_DEADLINE_MS), `studio_screenshot_prepare_${item.id}`);
      }
      if (nonGet.length) checks.push(check("no-product-writes", "fail", route, { methods: nonGet }));
    } catch (error) {
      errors.push({ id: "runtime", surface, matrix: item.id, message: browserEvidenceError(error) });
    } finally {
      if (page) await captureScreenshotEvidence({ page, evidenceRoot, surface, item, timeoutMs: matrixTimeout, capturedScreenshots, errors });
      for (let index = checkStart; index < checks.length; index += 1) checks[index].observed = { ...(checks[index].observed || {}), matrix: item.id };
      if (page) await page.close().catch(() => {}); if (context) await context.close().catch(() => {});
    }
  }
  for (const item of matrix()) {
    for (const id of REQUIRED_MATRIX_CHECKS) {
      if (!checks.some((entry) => entry.id === id && entry.observed?.matrix === item.id)) checks.push(check(id, "fail", surface === "site" ? "/" : "/manuscript", { matrix: item.id }, "required matrix check was not produced"));
    }
  }
  const viewports = matrix().map((item) => ({ id: item.id, width: item.viewport.width, height: item.viewport.height, mode: { id: item.mode.id, color_scheme: item.mode.colorScheme, reduced_motion: item.mode.reducedMotion, forced_colors: item.mode.forcedColors }, route: surface === "site" ? "/" : "/manuscript", checks: checks.filter((entry) => entry.observed?.matrix === item.id), screenshot: item.screenshot && capturedScreenshots.has(item.id) ? { path: `${surface}/screenshots/${item.screenshot}` } : null }));
  return { surface, status: errors.length || checks.some((item) => item.status === "fail") ? "fail" : "pass", matrix_count: viewports.length, viewports, checks, errors };
}

export async function runAcceptance({ env = process.env } = {}) {
  const chrome = resolveChrome(env);
  const evidenceRoot = env.QF_BROWSER_EVIDENCE_DIR || "/tmp/quillframe-t605-evidence";
  validateEvidenceRoot(evidenceRoot);
  const timeoutMs = Math.min(Number(env.QF_T605_TIMEOUT_MS || 45000), 120000);
  const repoRoot = resolveRepoRoot({ env });
  const subjectStart = gitSubject(repoRoot);
  const previews = await startPreviews({ env: { ...env, QF_REPO_ROOT: repoRoot }, cwd: repoRoot });
  if (!previews.started || !previews.origins?.site || !previews.origins?.studio) throw Object.assign(new Error("preview origins are runner-owned and required"), { code: "PREVIEW_START_REQUIRED" });
  const siteOrigin = previews.origins.site;
  const studioOrigin = previews.origins.studio;
  const onSignal = () => { void previews.cleanup(); };
  process.once("SIGTERM", onSignal); process.once("SIGINT", onSignal);
  let browser;
  try {
    const subjectBeforeBrowser = gitSubject(previews.repoRoot);
    if (JSON.stringify(subjectStart) !== JSON.stringify(subjectBeforeBrowser)) throw Object.assign(new Error("subject changed during build"), { code: "SUBJECT_CHANGED" });
    const buildStartFingerprint = fingerprintTrees(previews.buildRoots);
    await waitForServer(siteOrigin, timeoutMs); await waitForServer(studioOrigin, timeoutMs);
    let playwright; try { playwright = await import("playwright-core"); } catch { throw Object.assign(new Error("playwright-core is unavailable"), { code: "PLAYWRIGHT_REQUIRED" }); }
    try { browser = await playwright.chromium.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] }); }
    catch { throw Object.assign(new Error("Chromium launch failed"), { code: "BROWSER_LAUNCH_FAILED" }); }
    fs.mkdirSync(evidenceRoot, { recursive: true });
    const localLaunch = await runLocalLaunch({ browser, repoRoot: previews.repoRoot, chrome, evidenceRoot, timeoutMs });
    const launchReceiptPath = path.join(evidenceRoot, "local-launch", "receipt.json"); fs.mkdirSync(path.dirname(launchReceiptPath), { recursive: true }); fs.writeFileSync(launchReceiptPath, `${JSON.stringify(localLaunch, null, 2)}\n`, { mode: 0o600 });
    const surfaces = [await runSurface(browser, siteOrigin, "site", evidenceRoot, timeoutMs, previews.repoRoot), await runSurface(browser, studioOrigin, "studio", evidenceRoot, timeoutMs, previews.repoRoot)];
    const buildEndFingerprint = fingerprintTrees(previews.buildRoots); const subjectEnd = gitSubject(previews.repoRoot);
    const globalChecks = REQUIRED_GLOBAL_CHECKS.map((id) => {
      if (id === "local_launch") return check(id, localLaunch.status, "quillframe launch", localLaunch);
      if (id === "quick_demo_truth") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "quick_demo_truth"); return check(id, checks.length === 3 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "/#quick-demo", { cases: checks.map((entry) => entry.observed?.matrix) }); }
      if (id === "machine_contracts") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "machine_contracts"); return check(id, checks.length >= 2 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "/.well-known/", { checks: checks.length }); }
      if (id === "offline") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "offline" || entry.id.startsWith("docs_offline") || entry.id === "studio_offline_shell"); return check(id, checks.length > 0 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "/offline", { checks: checks.length }); }
      if (id === "keyboard") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "keyboard"); return check(id, checks.length === 40 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "matrix", { checks: checks.length }); }
      if (id === "dialog") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "dialog"); return check(id, checks.length === 40 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "matrix", { checks: checks.length }); }
      if (id === "wcag") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "wcag"); return check(id, checks.length === 40 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "matrix", { checks: checks.length }); }
      if (id === "cwv") { const checks = surfaces.flatMap((surface) => surface.checks).filter((entry) => entry.id === "cwv"); return check(id, checks.length === 40 && checks.every((entry) => entry.status === "pass") ? "pass" : "fail", "matrix", { checks: checks.length }); }
      return check(id, "fail", "global", {}, "unhandled required global check");
    });
    const inputFingerprint = acceptanceInputFingerprint(previews.repoRoot, subjectStart.commit);
    return writeManifest({ evidenceRoot, chrome, surfaces, subjectStart, subjectEnd, buildStartFingerprint, buildEndFingerprint, inputFingerprint, siteFinalizerFingerprint: previews.siteFinalizerFingerprint, globalChecks, extraArtifacts: [{ path: "local-launch/receipt.json", id: "local-launch:receipt", kind: "receipt", surface: "studio", matrix: null }] });
  } finally { if (browser) await browser.close().catch(() => {}); await previews.cleanup(); process.removeListener("SIGTERM", onSignal); process.removeListener("SIGINT", onSignal); }
}

function artifactRecord(evidenceRoot, relative, { id, kind = "screenshot", surface = null, matrix = null } = {}) {
  if (path.isAbsolute(relative) || relative.split(path.sep).includes("..")) throw new Error("ARTIFACT_RELATIVE_PATH");
  const file = path.join(evidenceRoot, relative); const hash = hashArtifact(file);
  return { id, path: relative.split(path.sep).join("/"), kind, surface, matrix, size: hash.size, sha256: hash.sha256 };
}

function optionalScreenshotArtifactRecord(evidenceRoot, relative, metadata) {
  try { return artifactRecord(evidenceRoot, relative, metadata); }
  catch (error) {
    if (error?.code === "PATH_INVALID" && error?.cause?.code === "ENOENT") return null;
    throw error;
  }
}

function subjectShape(subject) {
  if (!subject || !/^[0-9a-f]{40}$/i.test(subject.commit) || typeof subject.dirty !== "boolean" || !/^sha256:[0-9a-f]{64}$/.test(subject.working_tree_fingerprint)) throw new Error("MANIFEST_SUBJECT");
}

export function validateManifestContract(manifest) {
  const top = ["artifacts", "artifacts_root", "browser", "build", "chapter_scope", "errors", "gate", "generated_at", "global_checks", "matrix_count", "schema", "status", "subject", "surfaces", "task"];
  if (!manifest || Object.keys(manifest).sort().join("\0") !== top.sort().join("\0") || manifest.schema !== "quillframe_browser_acceptance_v1" || !["pass", "fail", "blocked"].includes(manifest.status) || manifest.task !== "T605" || manifest.gate !== "T605_BROWSER_ACCEPTANCE" || manifest.chapter_scope !== CHAPTER_SCOPE || manifest.artifacts_root !== "." || manifest.matrix_count !== 40 || typeof manifest.generated_at !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(manifest.generated_at)) throw new Error("MANIFEST_TOP_SCHEMA");
  subjectShape(manifest.subject.start); subjectShape(manifest.subject.end); if (manifest.subject.stable !== true || JSON.stringify(manifest.subject.start) !== JSON.stringify(manifest.subject.end)) throw new Error("MANIFEST_SUBJECT_UNSTABLE");
  if (!manifest.build || Object.keys(manifest.build).sort().join("\0") !== ["end_fingerprint", "input_fingerprint", "site_finalizer_fingerprint", "stable", "start_fingerprint"].sort().join("\0") || !/^sha256:[0-9a-f]{64}$/.test(manifest.build.start_fingerprint) || !/^sha256:[0-9a-f]{64}$/.test(manifest.build.end_fingerprint) || !/^sha256:[0-9a-f]{64}$/.test(manifest.build.input_fingerprint) || !/^sha256:[0-9a-f]{64}$/.test(manifest.build.site_finalizer_fingerprint) || manifest.build.stable !== true || manifest.build.start_fingerprint !== manifest.build.end_fingerprint) throw new Error("MANIFEST_BUILD");
  if (!manifest.browser || Object.keys(manifest.browser).sort().join("\0") !== ["fingerprint", "name", "version"].join("\0") || manifest.browser.name !== "chromium" || typeof manifest.browser.version !== "string" || !/^sha256:[0-9a-f]{64}$/.test(manifest.browser.fingerprint)) throw new Error("MANIFEST_BROWSER");
  const globalIds = REQUIRED_GLOBAL_CHECKS;
  if (!Array.isArray(manifest.global_checks) || manifest.global_checks.length !== globalIds.length || manifest.global_checks.map((entry) => entry.id).join("\0") !== globalIds.join("\0")) throw new Error("MANIFEST_GLOBAL_CHECKS");
  for (const entry of manifest.global_checks) if (!checkShape(entry) || entry.status !== "pass") throw new Error("MANIFEST_GLOBAL_CHECK");
  if (!Array.isArray(manifest.errors) || manifest.errors.some((entry) => {
    if (!entry || typeof entry !== "object") return true;
    const keys = Object.keys(entry).sort().join("\0");
    if (keys === ["id", "message", "matrix", "surface"].join("\0")) return typeof entry.id === "string" && typeof entry.message === "string" && typeof entry.matrix === "string" && typeof entry.surface === "string";
    if (keys === ["code", "family", "id", "observed", "route", "status"].join("\0")) return typeof entry.code === "string" && typeof entry.family === "string" && typeof entry.id === "string" && entry.observed && typeof entry.observed === "object" && typeof entry.route === "string" && ["pass", "fail", "blocked"].includes(entry.status);
    return true;
  })) throw new Error("MANIFEST_ERRORS");
  if (!Array.isArray(manifest.surfaces) || manifest.surfaces.length !== 2 || manifest.surfaces.map((surface) => surface.surface).join("\0") !== SURFACES.join("\0")) throw new Error("MANIFEST_SURFACES");
  for (const surface of manifest.surfaces) { if (!surfaceShape(surface)) throw new Error("MANIFEST_SURFACE"); }
  for (const artifact of manifest.artifacts) { if (!artifact || Object.keys(artifact).sort().join("\0") !== ["id", "kind", "matrix", "path", "sha256", "size", "surface"].join("\0") || typeof artifact.id !== "string" || !artifact.path || !/^sha256:[0-9a-f]{64}$/.test(artifact.sha256) || !Number.isSafeInteger(artifact.size) || artifact.size < 1 || path.isAbsolute(artifact.path) || artifact.path.split("/").includes("..")) throw new Error("MANIFEST_ARTIFACT"); }
  const screenshotArtifacts = manifest.artifacts.filter((artifact) => artifact.kind === "screenshot");
  if (screenshotArtifacts.length !== 24 || new Set(screenshotArtifacts.map((artifact) => artifact.path)).size !== 24) throw new Error("MANIFEST_SCREENSHOTS");
  for (const surface of SURFACES) for (const item of matrix()) { const expected = item.screenshot ? `${surface}/screenshots/${item.screenshot}` : null; const entry = manifest.surfaces.find((value) => value.surface === surface).viewports.find((value) => value.id === item.id); if (!entry || entry.width !== item.viewport.width || entry.height !== item.viewport.height || entry.mode.id !== item.mode.id || entry.mode.color_scheme !== item.mode.colorScheme || entry.mode.reduced_motion !== item.mode.reducedMotion || entry.mode.forced_colors !== item.mode.forcedColors || (entry.screenshot?.path || null) !== expected) throw new Error("MANIFEST_MATRIX_IDENTITY"); if (expected && !screenshotArtifacts.some((artifact) => artifact.path === expected && artifact.surface === surface && artifact.matrix === item.id)) throw new Error("MANIFEST_SCREENSHOT_BINDING"); }
  return true;
}

function checkShape(entry) { return entry && Object.keys(entry).sort().join("\0") === ["family", "id", "observed", "reason", "route", "status"].join("\0") || entry && Object.keys(entry).sort().join("\0") === ["family", "id", "observed", "route", "status"].join("\0"); }

function surfaceShape(surface) {
  if (!surface || Object.keys(surface).sort().join("\0") !== ["checks", "errors", "matrix_count", "status", "surface", "viewports"].join("\0") || !SURFACES.includes(surface.surface) || surface.matrix_count !== 20 || !["pass", "fail", "blocked"].includes(surface.status) || !Array.isArray(surface.viewports) || surface.viewports.length !== 20 || !Array.isArray(surface.checks) || !Array.isArray(surface.errors)) return false;
  const expectedIds = matrix().map((item) => item.id); if (surface.viewports.map((item) => item.id).join("\0") !== expectedIds.join("\0")) return false;
  for (const item of surface.viewports) { const keys = ["checks", "height", "id", "mode", "route", "screenshot", "width"]; if (!item || Object.keys(item).sort().join("\0") !== keys.join("\0") || !item.checks.every(checkShape)) return false; for (const id of REQUIRED_MATRIX_CHECKS) if (!item.checks.some((entry) => entry.id === id && entry.status === "pass")) return false; }
  return surface.checks.every(checkShape);
}

export function writeManifest({ evidenceRoot, chrome, browserVersion = null, surfaces, subjectStart, subjectEnd, buildStartFingerprint, buildEndFingerprint, inputFingerprint, siteFinalizerFingerprint, globalChecks, extraArtifacts = [], now = new Date() }) {
  evidenceRoot = validateEvidenceRoot(evidenceRoot);
  const artifacts = [];
  const normalizedSurfaces = surfaces.map((surface) => ({
    ...surface,
    viewports: surface.viewports.map((viewport) => {
      if (!viewport.screenshot) return viewport;
      const artifact = optionalScreenshotArtifactRecord(evidenceRoot, viewport.screenshot.path, { id: `${surface.surface}:${viewport.id}:screenshot`, kind: "screenshot", surface: surface.surface, matrix: viewport.id });
      if (!artifact) return { ...viewport, screenshot: null };
      artifacts.push(artifact);
      return viewport;
    }),
  }));
  for (const item of extraArtifacts) artifacts.push(artifactRecord(evidenceRoot, item.path, item));
  const start = subjectStart; const end = subjectEnd; const subjectStable = start && end && JSON.stringify(start) === JSON.stringify(end);
  const buildStable = Boolean(buildStartFingerprint && buildEndFingerprint && buildStartFingerprint === buildEndFingerprint);
  const identity = start && end && /^sha256:[0-9a-f]{64}$/.test(buildStartFingerprint || "") && /^sha256:[0-9a-f]{64}$/.test(buildEndFingerprint || "") && /^sha256:[0-9a-f]{64}$/.test(inputFingerprint || "") && /^sha256:[0-9a-f]{64}$/.test(siteFinalizerFingerprint || "");
  const expectedScreenshotBindings = new Set(SURFACES.flatMap((surface) => matrix().filter((item) => item.screenshot).map((item) => `${surface}\0${item.id}\0${surface}/screenshots/${item.screenshot}`)));
  const screenshotArtifacts = artifacts.filter((artifact) => artifact.kind === "screenshot");
  const actualScreenshotBindings = new Set(screenshotArtifacts.map((artifact) => `${artifact.surface}\0${artifact.matrix}\0${artifact.path}`));
  const screenshotsComplete = actualScreenshotBindings.size === expectedScreenshotBindings.size && [...expectedScreenshotBindings].every((binding) => actualScreenshotBindings.has(binding));
  const failures = normalizedSurfaces.some((surface) => surface.status !== "pass") || (globalChecks || []).some((checkItem) => checkItem.status !== "pass") || !subjectStable || !buildStable || !identity || !screenshotsComplete;
  const manifest = redactEvidence({ schema: "quillframe_browser_acceptance_v1", status: failures ? "fail" : "pass", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: CHAPTER_SCOPE, subject: { start, end, stable: subjectStable }, build: { start_fingerprint: buildStartFingerprint, end_fingerprint: buildEndFingerprint, input_fingerprint: inputFingerprint, site_finalizer_fingerprint: siteFinalizerFingerprint, stable: buildStable }, browser: { name: "chromium", version: browserVersion || chromeVersion(chrome), fingerprint: browserFingerprint(chrome) }, matrix_count: normalizedSurfaces.reduce((total, surface) => total + surface.matrix_count, 0), surfaces: normalizedSurfaces, global_checks: globalChecks || [], artifacts, errors: normalizedSurfaces.flatMap((surface) => surface.errors), generated_at: acceptanceTimestamp(now), artifacts_root: "." });
  if (manifest.status === "pass") validateManifestContract(manifest);
  fs.mkdirSync(evidenceRoot, { recursive: true }); fs.writeFileSync(path.join(evidenceRoot, MANIFEST_NAME), `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o600 });
  return manifest;
}

export function writeFailureManifest({ evidenceRoot, code, chrome = null, now = new Date() }) {
  try { evidenceRoot = validateEvidenceRoot(evidenceRoot); } catch { return null; }
  let browser = null; try { if (chrome) { assertRegularFileNoFollow(chrome, { executable: true }); browser = { name: "chromium", version: "unknown", fingerprint: browserFingerprint(chrome) }; } } catch {}
  const manifest = redactEvidence({ schema: "quillframe_browser_acceptance_v1", status: "blocked", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: CHAPTER_SCOPE, subject: { start: null, end: null, stable: false }, build: { start_fingerprint: null, end_fingerprint: null, input_fingerprint: null, site_finalizer_fingerprint: null, stable: false }, browser, matrix_count: 0, surfaces: [], global_checks: REQUIRED_GLOBAL_CHECKS.map((id) => check(id, "blocked", "runner", {}, code)), artifacts: [], errors: [{ id: "runner", family: "runner", status: "blocked", route: "runner", observed: {}, code }], generated_at: acceptanceTimestamp(now), artifacts_root: "." });
  fs.writeFileSync(path.join(evidenceRoot, MANIFEST_NAME), `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o600 });
  return manifest;
}

export function parseExit(error) { return ["CHROME_BIN_REQUIRED", "CHROME_BIN_INVALID", "CHROME_VERSION_FAILED", "ORIGIN_NOT_READY", "PREVIEW_NOT_READY", "BUILD_TIMEOUT", "PLAYWRIGHT_REQUIRED", "BUILD_FAILED", "BUILD_ARTIFACT_MISSING", "PORT_UNAVAILABLE", "EVIDENCE_ROOT_INVALID", "PREVIEW_START_REQUIRED", "PATH_INVALID", "PATH_SYMLINK", "PATH_NOT_REGULAR", "PATH_NOT_DIRECTORY", "GIT_SUBJECT_FAILED", "SUBJECT_CHANGED", "PROCESS_CLEANUP_FAILED", "BRIDGE_FIXTURE_CONTRACT", "BROWSER_LAUNCH_FAILED", "LOCAL_LAUNCH_BROWSER_REQUIRED", "LOCAL_LAUNCH_TIMEOUT"].includes(error?.code) ? EXIT.BLOCKED : EXIT.ASSERTION; }

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runAcceptance().then((manifest) => { console.log(JSON.stringify({ schema: manifest.schema, status: manifest.status, evidence: manifest.artifacts_root })); process.exitCode = manifest.status === "pass" ? EXIT.PASS : EXIT.ASSERTION; }).catch((error) => { const code = error.code || "T605_BLOCKED"; const root = process.env.QF_BROWSER_EVIDENCE_DIR || "/tmp/quillframe-t605-evidence"; try { writeFailureManifest({ evidenceRoot: root, code, chrome: process.env.CHROME_BIN || null }); } catch {} console.error(JSON.stringify({ schema: "quillframe_browser_acceptance_v1", status: "blocked", code })); process.exitCode = parseExit(error); });
}

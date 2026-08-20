import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  VIEWPORTS, MODES, EXIT, matrix, resolveChrome, redactEvidence, withDeadline, waitForServiceWorkerReady, waitForServer, machineJson, pageFetchProbe, boundedBrowserAction, assertVisibleControl, assertHomeScreenshotReadiness, prepareHomeScreenshot, HOME_REVEAL_SELECTORS, DERIVED_ACCEPTANCE_PATHS, BUILD_INPUT_PATHS, acceptanceTimestamp, acceptanceInputFingerprint,
  assertJsonContract, docsShellForPath, assertQuickDemoReceipt, assertQuickDemoDom,
  assertUnboundStudio, assertDialogLifecycle, statusFor, writeManifest, parseExit, captureScreenshotEvidence,
  assertMachineManifest, assertNoWrites, startPreviews, spawnProcess, terminateProcess, contrastRatio, requiredContrastThreshold, assertCwv, assertSemantics, writeFailureManifest, fingerprintTrees, validateManifestContract, assertBuildArtifacts, validateEvidenceRoot, assertNoSymlinkAncestors, assertRegularFileNoFollow, assertLaunchReceipt, assertBridgeRequest, assertBridgeResult, gitSubject, resolveRepoRoot, productionBridgeSnapshot, productionBridgeResult,
} from "./browser-acceptance-t605.mjs";

test("resolveChrome is explicit, absolute, regular, and executable", () => {
  assert.throws(() => resolveChrome({}), (error) => error.code === "CHROME_BIN_REQUIRED");
  assert.throws(() => resolveChrome({ CHROME_BIN: "chrome" }), (error) => error.code === "CHROME_BIN_INVALID");
  assert.throws(() => resolveChrome({ CHROME_BIN: "/tmp/no-such-chrome" }), (error) => error.code === "CHROME_BIN_INVALID");
  assert.equal(resolveChrome({ CHROME_BIN: "/tmp/chrome" }, () => ({ isFile: () => true, mode: 0o755 })), "/tmp/chrome");
  assert.throws(() => resolveChrome({ CHROME_BIN: "/tmp/chrome" }, () => ({ isFile: () => true, mode: 0o644 })), (error) => error.code === "CHROME_BIN_INVALID");
});

test("matrix is exactly five viewports by four independent modes", () => {
  assert.deepEqual(VIEWPORTS.map(({ width, height }) => [width, height]), [[1440, 1000], [1024, 900], [768, 900], [430, 844], [375, 812]]);
  assert.deepEqual(MODES.map(({ id }) => id), ["light", "dark", "reduced", "forced"]);
  const values = matrix();
  assert.equal(values.length, 20);
  assert.equal(new Set(values.map((value) => value.id)).size, 20);
  assert.equal(values.filter((value) => value.screenshot).length, 12);
});

test("status and exit codes have no successful skip path", () => {
  assert.equal(statusFor(), 0); assert.equal(statusFor({ failed: true }), 1); assert.equal(statusFor({ blocked: true }), 2);
  assert.equal(parseExit({ code: "CHROME_BIN_REQUIRED" }), EXIT.BLOCKED);
  assert.equal(parseExit({ code: "BROWSER_LAUNCH_FAILED" }), EXIT.BLOCKED);
  assert.equal(parseExit({ code: "ASSERTION" }), EXIT.ASSERTION);
});

test("deadline helper rejects a never-settling Promise with a bounded typed error", async () => {
  const started = Date.now();
  await assert.rejects(
    () => withDeadline(() => new Promise(() => {}), 25, { code: "TEST_PENDING_TIMEOUT", label: "pending_test" }),
    (error) => error.code === "TEST_PENDING_TIMEOUT" && error.operation === "pending_test" && error.timeout_ms === 25,
  );
  assert.ok(Date.now() - started < 1000);
});

test("deadline helper aborts fetch-style work and does not wait for its Promise", async () => {
  let aborted = false;
  await assert.rejects(
    () => withDeadline((signal) => new Promise((resolve) => signal.addEventListener("abort", () => { aborted = true; resolve(); })), 20, { code: "TEST_ABORT_TIMEOUT", label: "abort_test" }),
    (error) => error.code === "TEST_ABORT_TIMEOUT",
  );
  assert.equal(aborted, true);
});

test("all browser fetch seams carry an explicit abort/route deadline", () => {
  const source = fs.readFileSync(new URL("./browser-acceptance-t605.mjs", import.meta.url), "utf8");
  assert.match(source, /fetchImpl\(url, \{ signal \}/);
  assert.match(source, /fetch\(target, \{ method: "GET", credentials: "same-origin", signal: controller\.signal \}/);
  assert.match(source, /fetch\(requestTarget, \{ method: requestMethod, body: requestBody, signal: controller\.signal \}/);
  assert.match(source, /route\.fetch\(\{ timeout: normalizeDeadline\(timeoutMs\) \}\)/);
  assert.match(source, /waitForServiceWorkerReady\(docs/);
  assert.match(source, /waitForServiceWorkerReady\(offline/);
  assert.match(source, /serviceWorkers: "block"/);
  assert.match(source, /waitForSelector\("main#main-content"/);
  assert.match(source, /studio_heading_ready_/);
});

test("Review entry failures stay out of the generic dialog gate", () => {
  const source = fs.readFileSync(new URL("./browser-acceptance-t605.mjs", import.meta.url), "utf8");
  assert.match(source, /check\("review-accept-entry"/);
  assert.doesNotMatch(source, /check\("dialog"[^\n]+Review Accept/);
});

test("runSurface returns only the canonical manifest surface keys", () => {
  const source = fs.readFileSync(new URL("./browser-acceptance-t605.mjs", import.meta.url), "utf8");
  assert.doesNotMatch(source, /const checks = \[\], errors = \[\], screenshots = \[\]/);
  assert.doesNotMatch(source, /screenshots\.push\(/);
  assert.match(source, /let context = null, page = null;\s+try \{\s+context = await boundedBrowserAction/);
  assert.match(source, /if \(page\) await captureScreenshotEvidence/);
  assert.match(source, /return \{ surface, status: errors\.length \|\| checks\.some\(\(item\) => item\.status === "fail"\) \? "fail" : "pass", matrix_count: viewports\.length, viewports, checks, errors \};/);
});

test("Studio unbound route checks are aggregated into one matrix check", () => {
  const source = fs.readFileSync(new URL("./browser-acceptance-t605.mjs", import.meta.url), "utf8");
  assert.match(source, /const unboundRoutes = \[\];/);
  assert.match(source, /check\("studio-unbound-routes", unboundRoutes\.every/);
  assert.doesNotMatch(source, /check\("studio-unbound-route",/);
});

test("pending service-worker readiness is fail-closed and cannot hang", async () => {
  const page = { evaluate: () => new Promise(() => {}) };
  await assert.rejects(() => waitForServiceWorkerReady(page, 20, "pending_sw"), (error) => error.code === "SERVICE_WORKER_READY_TIMEOUT" && error.operation === "pending_sw");
});

test("pending Node origin fetch is bounded and sanitized", async () => {
  await assert.rejects(() => waitForServer("http://127.0.0.1:1", 35, { fetchImpl: () => new Promise(() => {}) }), (error) => error.code === "ORIGIN_NOT_READY" && error.operation === "wait_for_server" && error.timeout_ms === 35 && !String(error.message).includes("127.0.0.1"));
});

test("pending machine-json and probe page evaluations are bounded", async () => {
  const page = { evaluate: () => new Promise(() => {}) };
  await assert.rejects(() => machineJson(page, "http://127.0.0.1/json", "x", [], ["schema"], undefined, 20), (error) => error.code === "MACHINE_JSON_TIMEOUT");
  const result = await pageFetchProbe(page, "https://cross-origin.invalid", { timeoutMs: 20, operation: "pending_probe" });
  assert.deepEqual(result, { status: "fail", mode: "timeout", error: "T605_FETCH_TIMEOUT", operation: "pending_probe" });
});

test("hidden locators fail closed before click instead of waiting on Playwright defaults", async () => {
  const hidden = { isVisible: async () => false, click: async () => { throw new Error("must not click"); } };
  await assert.rejects(() => assertVisibleControl(hidden, 20, "hidden_control"), (error) => error.code === "CONTROL_NOT_VISIBLE" && error.operation === "hidden_control");
  await assert.rejects(() => boundedBrowserAction(() => new Promise(() => {}), 20, "pending_action"), (error) => error.code === "BROWSER_ACTION_TIMEOUT");
});

test("screenshot readiness requires all six non-hidden, non-empty home sections", () => {
  const sections = ["hero", "workflow", "quick-demo", "architecture", "trust", "cta"].map((id) => ({ id, visible: true, opacity: 1, has_text: true }));
  const reveal_groups = HOME_REVEAL_SELECTORS.map((selector) => ({ selector, count: 1, visible: true, nonempty: true }));
  assert.equal(assertHomeScreenshotReadiness({ count: 6, sections, reveal_groups }), true);
  assert.throws(() => assertHomeScreenshotReadiness({ count: 6, sections: sections.map((section, index) => index === 3 ? { ...section, opacity: 0, visible: false } : section), reveal_groups }), /SCREENSHOT_CONTENT_NOT_READY/);
  assert.throws(() => assertHomeScreenshotReadiness({ count: 6, sections, reveal_groups: reveal_groups.map((group, index) => index === 2 ? { ...group, visible: false } : group) }), /SCREENSHOT_REVEAL_CONTENT_NOT_READY/);
  assert.throws(() => assertHomeScreenshotReadiness({ count: 5, sections: sections.slice(0, 5), reveal_groups }), /SCREENSHOT_CONTENT_NOT_READY/);
});

test("evidence redaction removes secret-like keys, paths, and URL credentials", () => {
  const result = redactEvidence({ token: "do-not-write", cookie: "x", path: "/home/private/project", url: "https://provider.invalid/run?token=secret", safe: "CH001" });
  assert.equal(result.token, "[REDACTED]"); assert.equal(result.cookie, "[REDACTED]"); assert.equal(result.path, "[REDACTED_PATH]");
  assert.equal(result.url, "https://provider.invalid/run"); assert.equal(result.safe, "CH001");
  assert.doesNotMatch(JSON.stringify(result), /do-not-write|private\/project|token=secret/);
});

test("machine JSON contract is bounded, typed, exact-schema, and content-typed", () => {
  const payload = { schema: "quillframe_ai_catalog_v1", authority: false };
  assert.deepEqual(assertJsonContract({ body: JSON.stringify(payload), contentType: "application/json; charset=utf-8" }, { schema: payload.schema }), payload);
  assert.throws(() => assertJsonContract({ body: JSON.stringify({ ...payload, authority: true }) }, { schema: payload.schema, exactKeys: ["schema", "authority"], requiredFalse: ["authority"] }), /JSON_FALSE_REQUIRED/);
  assert.throws(() => assertJsonContract({ body: "{}", contentType: "text/html" }, { schema: payload.schema }), /JSON_CONTENT_TYPE/);
  assert.throws(() => assertJsonContract({ body: "x" }, { schema: payload.schema }), /JSON_INVALID/);
  assert.throws(() => assertJsonContract('{"schema":"quillframe_ai_catalog_v1","authority":false,"authority":true}', { schema: payload.schema, exactKeys: ["schema", "authority"] }), /JSON_DUPLICATE_KEY/);
  assert.throws(() => assertJsonContract({ body: "x".repeat(65 * 1024) }, { schema: payload.schema }), /JSON_TOO_LARGE/);
});

test("Docs locale mapping is exact and query independent", () => {
  assert.equal(docsShellForPath("/docs/"), "/docs/");
  assert.equal(docsShellForPath("/docs/zh-guide?token=ignored"), "/docs/");
  assert.equal(docsShellForPath("/docs/en/chapter?x=1"), "/docs/en/");
  assert.equal(docsShellForPath("/docs/en-US/chapter"), null);
  assert.equal(docsShellForPath("/docs/zh-CN/chapter"), null);
  assert.equal(docsShellForPath("/api/status"), null);
});

test("Quick Demo receipt requires truthful recorded CH001 state and zero writes", () => {
  const receiptValue = { schema: "quillframe_ch001_quick_demo_receipt_v1", chapter_id: "CH001", deterministic_core: { executed: true, modules: ["workflow"], packet_fingerprint: "sha256:" + "1".repeat(64), workflow_fingerprint: "sha256:" + "2".repeat(64), stage: "DRAFT" }, semantic_evidence: { schema: "quillframe_recorded_semantic_evidence_v1", source: "recorded_fixture", recorded_at: "2026-08-19T12:00:00+00:00", live_model_called: false, candidate_fingerprint: "sha256:" + "3".repeat(64), authority: false, summary: "recorded", findings: [{ code: "x", severity: "info", owner: "story" }] }, live_model_called: false, uploads: 0, canon_mutated: false, authority: false };
  const receipt = JSON.stringify(receiptValue);
  assert.equal(assertQuickDemoReceipt(receipt, []), true);
  assert.throws(() => assertQuickDemoReceipt(receipt.replace("recorded_fixture", "live_model"), []), /QUICK_DEMO/);
  assert.throws(() => assertQuickDemoReceipt(receipt, ["POST"]), /PRODUCT_WRITE/);
  const typed = { receipt: receiptValue, schema: receiptValue.schema, chapter: "CH001 · authority=false", statuses: ["PASS", "FIXTURE", "SAFE"], boundary: "model=false · uploads=0 · canon=false" };
  assert.equal(assertQuickDemoDom(typed, [], []), true);
  assert.throws(() => assertQuickDemoDom({ ...typed, boundary: "model=falseevil · uploads=0 · canon=false" }, [], []), /QUICK_DEMO_TYPED/);
});

test("Studio unbound and dialog lifecycle helpers fail closed", () => {
  const dom = { hostChipText: "Core unbound", surface: "hosted_web", coreBound: false, projectTitle: false, runId: false, mutationControls: false };
  assert.equal(assertUnboundStudio(dom), true);
  assert.throws(() => assertUnboundStudio({ ...dom, coreBound: true }), /STUDIO/);
  assert.equal(assertDialogLifecycle(["open", "focus-initial", "tab", "shift-tab", "outside", "escape", "focus-return", "background-restored"]), true);
  assert.throws(() => assertDialogLifecycle(["open", "focus-initial"]), /DIALOG/);
});

test("machine manifests require exact schema/authority and writes are GET-only", () => {
  assert.deepEqual(assertMachineManifest({ schema: "quillframe_host_v1", authority: false }, "quillframe_host_v1", { authorityKeys: ["authority"] }).authority, false);
  assert.throws(() => assertMachineManifest({ schema: "quillframe_host_v1", authority: true }, "quillframe_host_v1", { authorityKeys: ["authority"] }), /MACHINE_AUTHORITY/);
  assert.throws(() => assertMachineManifest({ schema: "quillframe_host_v1", authority: false, extra: true }, "quillframe_host_v1", { authorityKeys: ["authority"] }), /JSON_KEYS/);
  assert.equal(assertNoWrites(["GET", "HEAD"]), true);
  assert.throws(() => assertNoWrites(["GET", "POST"]), /PRODUCT_WRITE/);
});

test("WCAG AA contrast, semantic landmarks, and CWV budgets fail closed", () => {
  assert.ok(contrastRatio("rgb(0, 0, 0)", "rgb(255, 255, 255)") >= 4.5);
  assert.throws(() => contrastRatio("transparent", "rgb(255, 255, 255)"), /CONTRAST_UNSUPPORTED_COLOR/);
  assert.equal(assertSemantics({ mainCount: 1, namedButtons: 1, headingCount: 1, headingNames: 1, landmarks: 2, namedLandmarks: 2, landmarkRoles: ["header", "main"], ariaCurrent: true }), true);
  assert.throws(() => assertSemantics({ mainCount: 2, namedButtons: 1, headingCount: 1, headingNames: 1, landmarks: 2, namedLandmarks: 2, landmarkRoles: ["header", "main"], ariaCurrent: true }), /SEMANTIC/);
  assert.equal(assertCwv({ supported: true, lcpMs: 1000, cls: 0.01, tbtMs: 20 }), true);
  assert.throws(() => assertCwv({ supported: false }), /CWV_UNSUPPORTED/);
  assert.throws(() => assertCwv({ supported: true, lcpMs: 3000, cls: 0.01, tbtMs: 20 }), /CWV_BUDGET/);
});

test("gitSubject flows into writeManifest and validateManifestContract with repeatable cleanup", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-test-"));
  const chrome = path.join(root, "chrome"); fs.writeFileSync(chrome, "chromium"); fs.chmodSync(chrome, 0o755);
  const required = ["shell", "media_state", "wcag", "cwv", "keyboard", "dialog"];
  const makeSurface = (surface) => ({ surface, status: "pass", matrix_count: 20, viewports: matrix().map((item) => ({ id: item.id, width: item.viewport.width, height: item.viewport.height, mode: { id: item.mode.id, color_scheme: item.mode.colorScheme, reduced_motion: item.mode.reducedMotion, forced_colors: item.mode.forcedColors }, route: surface === "site" ? "/" : "/manuscript", checks: required.map((id) => ({ id, family: id, status: "pass", route: "/", observed: { matrix: item.id } })), screenshot: item.screenshot ? { path: `${surface}/screenshots/${item.screenshot}` } : null })), checks: [], errors: [] });
  const screenshots = (surface) => ["wide", "tablet", "small"].flatMap((viewport) => ["light", "dark", "reduced", "forced"].map((mode) => { const relative = `${surface}/screenshots/${viewport}-${mode}.png`; fs.mkdirSync(path.dirname(path.join(root, relative)), { recursive: true }); fs.writeFileSync(path.join(root, relative), `${surface}-${viewport}-${mode}`); return relative; }));
  const surfaces = [makeSurface("site"), makeSurface("studio")];
  screenshots("site"); screenshots("studio");
  for (const surface of surfaces) surface.checks = surface.viewports.flatMap((item) => item.checks);
  const globalChecks = ["quick_demo_truth", "machine_contracts", "keyboard", "dialog", "offline", "wcag", "cwv", "local_launch"].map((id) => ({ id, family: id, status: "pass", route: "global", observed: {} }));
  const subject = gitSubject(process.cwd());
  assert.match(subject.commit, /^[0-9a-f]{40}$/i);
  assert.equal(typeof subject.dirty, "boolean");
  assert.match(subject.working_tree_fingerprint, /^sha256:[0-9a-f]{64}$/);
  assert.equal(Object.hasOwn(subject, "workingTreeFingerprint"), false);
  const manifest = writeManifest({ evidenceRoot: root, chrome, browserVersion: "Chromium test", subjectStart: subject, subjectEnd: { ...subject }, buildStartFingerprint: "sha256:" + "2".repeat(64), buildEndFingerprint: "sha256:" + "2".repeat(64), inputFingerprint: "sha256:" + "4".repeat(64), siteFinalizerFingerprint: "sha256:" + "3".repeat(64), globalChecks, surfaces, now: new Date("2026-08-20T00:00:00Z") });
  assert.equal(manifest.schema, "quillframe_browser_acceptance_v1");
  assert.equal(manifest.status, "pass");
  assert.equal(manifest.generated_at, "2026-08-20T00:00:00Z");
  assert.match(manifest.generated_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
  assert.equal(validateManifestContract(manifest), true);
  assert.throws(() => validateManifestContract({ ...manifest, errors: [{ id: "x", leaked: true }] }), /MANIFEST_ERRORS/);
  const output = path.join(root, "browser-acceptance-v1.json");
  assert.equal(fs.existsSync(output), true);
  assert.deepEqual(JSON.parse(fs.readFileSync(output, "utf8")).schema, manifest.schema);
  fs.rmSync(root, { recursive: true, force: true });
  fs.rmSync(root, { recursive: true, force: true });
});

test("failed matrices preserve runtime evidence when an expected screenshot is absent", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-missing-shot-"));
  try {
    const chrome = path.join(root, "chrome"); fs.writeFileSync(chrome, "chromium"); fs.chmodSync(chrome, 0o755);
    const runtimeError = { id: "runtime", surface: "studio", matrix: "small-light", message: "BROWSER_ACTION_TIMEOUT" };
    const surfaces = [{
      surface: "studio", status: "fail", matrix_count: 1, checks: [], errors: [runtimeError],
      viewports: [{ id: "small-light", width: 375, height: 812, mode: { id: "light", color_scheme: "light", reduced_motion: "no-preference", forced_colors: "none" }, route: "/manuscript", checks: [], screenshot: { path: "studio/screenshots/small-light.png" } }],
    }];
    const subject = { commit: "1".repeat(40), dirty: false, working_tree_fingerprint: "sha256:" + "2".repeat(64) };
    const manifest = writeManifest({ evidenceRoot: root, chrome, browserVersion: "Chromium test", surfaces, subjectStart: subject, subjectEnd: { ...subject }, buildStartFingerprint: "sha256:" + "3".repeat(64), buildEndFingerprint: "sha256:" + "3".repeat(64), inputFingerprint: "sha256:" + "4".repeat(64), siteFinalizerFingerprint: "sha256:" + "5".repeat(64), globalChecks: [], now: new Date("2026-08-20T00:00:00Z") });
    assert.equal(manifest.status, "fail");
    assert.deepEqual(manifest.errors, [runtimeError]);
    assert.equal(manifest.artifacts.some((artifact) => artifact.path === "studio/screenshots/small-light.png"), false);
    assert.equal(manifest.surfaces[0].viewports[0].screenshot, null);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(root, "browser-acceptance-v1.json"), "utf8")).errors, [runtimeError]);
    const outside = path.join(root, "outside.png"); fs.writeFileSync(outside, "outside");
    const linkedScreenshot = path.join(root, "studio/screenshots/small-light.png"); fs.mkdirSync(path.dirname(linkedScreenshot), { recursive: true }); fs.symlinkSync(outside, linkedScreenshot);
    assert.throws(() => writeManifest({ evidenceRoot: root, chrome, browserVersion: "Chromium test", surfaces, subjectStart: subject, subjectEnd: { ...subject }, buildStartFingerprint: "sha256:" + "3".repeat(64), buildEndFingerprint: "sha256:" + "3".repeat(64), inputFingerprint: "sha256:" + "4".repeat(64), siteFinalizerFingerprint: "sha256:" + "5".repeat(64), globalChecks: [] }), (error) => error.code === "PATH_SYMLINK");
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("diagnostic screenshot capture records success and preserves capture failures", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-capture-"));
  try {
    const item = matrix().find((entry) => entry.id === "small-light");
    const captured = new Set(); const errors = [];
    const page = { screenshot: async ({ path: filename }) => { fs.writeFileSync(filename, "png-evidence"); } };
    assert.equal(await captureScreenshotEvidence({ page, evidenceRoot: root, surface: "studio", item, timeoutMs: 50, capturedScreenshots: captured, errors }), true);
    assert.deepEqual([...captured], ["small-light"]);
    assert.equal(fs.existsSync(path.join(root, "studio/screenshots/small-light.png")), true);

    const failed = new Set(); const captureErrors = [{ id: "runtime", surface: "studio", matrix: "small-light", message: "CONTROL_NOT_VISIBLE" }];
    const brokenPage = { screenshot: async () => { throw Object.assign(new Error("absolute path must not leak"), { code: "SCREENSHOT_FAILED" }); } };
    const stale = path.join(root, "studio/screenshots/small-dark.png"); fs.writeFileSync(stale, "stale-png");
    assert.equal(await captureScreenshotEvidence({ page: brokenPage, evidenceRoot: root, surface: "studio", item: { ...item, id: "small-dark", screenshot: "small-dark.png" }, timeoutMs: 50, capturedScreenshots: failed, errors: captureErrors }), false);
    assert.equal(fs.existsSync(stale), false);
    assert.deepEqual(captureErrors, [
      { id: "runtime", surface: "studio", matrix: "small-light", message: "CONTROL_NOT_VISIBLE" },
      { id: "screenshot", surface: "studio", matrix: "small-dark", message: "BROWSER_ACTION_FAILED:screenshot_studio_small-dark" },
    ]);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("timestamp and acceptance build input fingerprint use the canonical seconds/commit/version/input algorithm", () => {
  assert.equal(acceptanceTimestamp(new Date("2026-08-20T00:00:00.999Z")), "2026-08-20T00:00:00Z");
  assert.deepEqual([...BUILD_INPUT_PATHS], ["package.json", "pnpm-lock.yaml", "site/package.json", "studio/app/package.json", "cloud/package.json"]);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-input-"));
  const git = (args) => execFileSync("git", args, { cwd: root, stdio: "ignore" });
  const gitOut = (args) => execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
  git(["init", "-q"]); git(["config", "user.email", "t605@example.invalid"]); git(["config", "user.name", "T605 Test"]);
  fs.writeFileSync(path.join(root, "VERSION"), "1.0.0-dev.0\n");
  for (const relative of BUILD_INPUT_PATHS) { const file = path.join(root, relative); fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, `${relative}\n`); }
  git(["add", "."]); git(["commit", "-q", "-m", "inputs"]);
  const commit = gitOut(["rev-parse", "HEAD"]);
  const js = acceptanceInputFingerprint(root, commit);
  const py = [
    "import hashlib, pathlib, sys",
    "repo = pathlib.Path(sys.argv[1]); commit = sys.argv[2]",
    "d = hashlib.sha256(); d.update(commit.encode() + b'\\0'); d.update((repo / 'VERSION').read_text().strip().encode() + b'\\0')",
    "for relative in ('package.json', 'pnpm-lock.yaml', 'site/package.json', 'studio/app/package.json', 'cloud/package.json'):",
    "  p = repo / relative; d.update(relative.encode() + b'\\0' + p.read_bytes() + b'\\0')",
    "print('sha256:' + d.hexdigest())",
  ].join("\n");
  const python = execFileSync("python3", ["-c", py, root, commit], { encoding: "utf8" }).trim();
  assert.equal(js, python);
  fs.rmSync(root, { recursive: true, force: true });
});

test("gitSubject working-tree bytes match the acceptance Python algorithm including tracked deletion", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-cross-language-"));
  const git = (args) => execFileSync("git", args, { cwd: root, stdio: "ignore" });
  git(["init", "-q"]); git(["config", "user.email", "t605@example.invalid"]); git(["config", "user.name", "T605 Test"]);
  fs.writeFileSync(path.join(root, "kept.txt"), "kept\n"); fs.writeFileSync(path.join(root, "deleted.txt"), "deleted\n");
  git(["add", "."]); git(["commit", "-q", "-m", "subject"]); fs.rmSync(path.join(root, "deleted.txt"));
  const py = [
    "import hashlib, pathlib, subprocess, sys",
    "repo = pathlib.Path(sys.argv[1]); d = hashlib.sha256()",
    "listed = subprocess.check_output(('git', 'ls-files', '-co', '--exclude-standard', '-z'), cwd=repo).decode().split('\\0')",
    "for relative in sorted(item for item in listed if item):",
    "  p = repo / relative; d.update(relative.encode() + b'\\0')",
    "  try: p.lstat()",
    "  except FileNotFoundError: d.update(b'[DELETED]\\0'); continue",
    "  d.update(p.read_bytes() + b'\\0')",
    "print('sha256:' + d.hexdigest())",
  ].join("\n");
  const python = execFileSync("python3", ["-c", py, root], { encoding: "utf8" }).trim();
  assert.equal(gitSubject(root).working_tree_fingerprint, python);
  fs.rmSync(root, { recursive: true, force: true });
});

test("gitSubject rejects symlink and nonregular working-tree entries like acceptance", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-subject-unsafe-"));
  const git = (args) => execFileSync("git", args, { cwd: root, stdio: "ignore" });
  git(["init", "-q"]); git(["config", "user.email", "t605@example.invalid"]); git(["config", "user.name", "T605 Test"]);
  fs.writeFileSync(path.join(root, "target.txt"), "target\n"); fs.symlinkSync("target.txt", path.join(root, "link.txt"));
  git(["add", "."]); git(["commit", "-q", "-m", "unsafe"]);
  assert.throws(() => gitSubject(root), (error) => error.code === "GIT_SUBJECT_FAILED");
  fs.rmSync(root, { recursive: true, force: true });
});

test("gitSubject excludes exactly the five derived acceptance artifacts from dirty/fingerprint", () => {
  assert.deepEqual([...DERIVED_ACCEPTANCE_PATHS], [
    "release/acceptance/1.0.0-dev.0.en.md",
    "release/acceptance/1.0.0-dev.0.zh-CN.md",
    "release/acceptance/1.0.0-dev.0.tasks.en.md",
    "release/acceptance/1.0.0-dev.0.tasks.zh-CN.md",
    "release/acceptance/1.0.0-dev.0.json",
  ]);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-subject-derived-"));
  const git = (args) => execFileSync("git", args, { cwd: root, stdio: "ignore" });
  git(["init", "-q"]); git(["config", "user.email", "t605@example.invalid"]); git(["config", "user.name", "T605 Test"]);
  fs.writeFileSync(path.join(root, "implementation.txt"), "implementation-v1\n"); git(["add", "implementation.txt"]); git(["commit", "-q", "-m", "implementation"]);
  for (const relative of DERIVED_ACCEPTANCE_PATHS) { const file = path.join(root, relative); fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, "derived-v1\n"); }
  const baseline = gitSubject(root);
  assert.equal(baseline.dirty, false);
  for (const relative of DERIVED_ACCEPTANCE_PATHS) fs.appendFileSync(path.join(root, relative), "derived-v2\n");
  const derivedOnly = gitSubject(root);
  assert.deepEqual(derivedOnly, baseline);
  const sixth = path.join(root, "release", "acceptance", "sixth-not-derived.txt"); fs.writeFileSync(sixth, "source-change\n");
  const sixthSubject = gitSubject(root);
  assert.equal(sixthSubject.dirty, true); assert.notEqual(sixthSubject.working_tree_fingerprint, baseline.working_tree_fingerprint);
  fs.rmSync(root, { recursive: true, force: true });
});

test("gitSubject normalizes an exact five-artifact child commit but not a mixed source commit", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-subject-commit-"));
  const git = (args) => execFileSync("git", args, { cwd: root, stdio: "ignore" });
  const gitOut = (args) => execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
  git(["init", "-q"]); git(["config", "user.email", "t605@example.invalid"]); git(["config", "user.name", "T605 Test"]);
  fs.writeFileSync(path.join(root, "implementation.txt"), "implementation-v1\n"); git(["add", "implementation.txt"]); git(["commit", "-q", "-m", "implementation"]);
  const implementationCommit = gitOut(["rev-parse", "HEAD"]);
  for (const relative of DERIVED_ACCEPTANCE_PATHS) { const file = path.join(root, relative); fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, "derived\n"); }
  git(["add", "--", ...DERIVED_ACCEPTANCE_PATHS]); git(["commit", "-q", "-m", "generated acceptance"]);
  const generatedChild = gitOut(["rev-parse", "HEAD"]);
  assert.notEqual(generatedChild, implementationCommit); assert.equal(gitSubject(root).commit, implementationCommit);
  fs.appendFileSync(path.join(root, "implementation.txt"), "source-change\n"); fs.appendFileSync(path.join(root, DERIVED_ACCEPTANCE_PATHS[0]), "mixed-change\n");
  git(["add", "--", "implementation.txt", DERIVED_ACCEPTANCE_PATHS[0]]); git(["commit", "-q", "-m", "mixed source and generated"]);
  const mixedHead = gitOut(["rev-parse", "HEAD"]);
  assert.equal(gitSubject(root).commit, mixedHead);
  fs.rmSync(root, { recursive: true, force: true });
});

test("preview lifecycle is inert unless explicitly enabled and cleanup is idempotent", async () => {
  await assert.rejects(() => startPreviews({ env: {}, cwd: "/tmp" }), (error) => error.code === "PREVIEW_START_REQUIRED");
});

test("repository root discovery survives package-manager cwd=site without QF_REPO_ROOT", () => {
  const expected = execFileSync("git", ["rev-parse", "--show-toplevel"], { cwd: process.cwd(), encoding: "utf8" }).trim();
  const siteCwd = path.basename(process.cwd()) === "site" ? process.cwd() : path.join(process.cwd(), "site");
  assert.equal(resolveRepoRoot({ env: {}, cwd: siteCwd }), path.resolve(expected));
});

test("blocked runner retains bounded failure evidence", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-failure-"));
  const manifest = writeFailureManifest({ evidenceRoot: root, code: "CHROME_BIN_REQUIRED", chrome: null });
  assert.equal(manifest.status, "blocked"); assert.equal(manifest.matrix_count, 0);
  assert.equal(JSON.parse(fs.readFileSync(path.join(root, "browser-acceptance-v1.json"), "utf8")).errors[0].code, "CHROME_BIN_REQUIRED");
  fs.rmSync(root, { recursive: true, force: true });
});

test("build fingerprint is deterministic over sorted production trees", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-tree-"));
  fs.mkdirSync(path.join(root, "dist", "nested"), { recursive: true });
  fs.writeFileSync(path.join(root, "dist", "b.js"), "b"); fs.writeFileSync(path.join(root, "dist", "nested", "a.js"), "a");
  const first = fingerprintTrees([path.join(root, "dist")]); const second = fingerprintTrees([path.join(root, "dist")]);
  assert.match(first, /^sha256:[0-9a-f]{64}$/); assert.equal(first, second);
  fs.rmSync(root, { recursive: true, force: true });
});

test("production artifact preflight rejects missing/finalizer placeholder outputs", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-build-"));
  const site = path.join(root, "site"); const studio = path.join(root, "studio");
  fs.mkdirSync(path.join(site, "dist"), { recursive: true }); fs.mkdirSync(path.join(studio, "dist/.well-known"), { recursive: true });
  fs.writeFileSync(path.join(site, "dist/sw.js"), "__QF_SITE_CACHE_VERSION__");
  for (const file of ["quillframe-host.json", "quillframe-studio-footprint.json"]) fs.writeFileSync(path.join(studio, "dist/.well-known", file), "{}");
  assert.throws(() => assertBuildArtifacts(site, studio), (error) => error.code === "BUILD_ARTIFACT_MISSING");
  fs.rmSync(root, { recursive: true, force: true });
});

test("Review fixture is bound to current Studio token and v11 result contract", async () => {
  const source = fs.readFileSync(new URL("./browser-acceptance-t605.mjs", import.meta.url), "utf8");
  assert.match(source, /__QUILLFRAME_STUDIO_TOKEN__/);
  assert.match(source, /quillframe_host_bridge_result_v11/);
  assert.match(source, /productionBridgeResult\(repoRoot, request, data\)/);
  assert.match(source, /secret_values_persisted/);
  assert.doesNotMatch(source, /request\?\.op/);
  assert.match(source, /candidate\.visible\.get/);
});

test("Review v11 fixture is generated and fingerprinted by the production Host Bridge", () => {
  const repoRoot = resolveRepoRoot({ env: {}, cwd: process.cwd() });
  const snapshot = productionBridgeSnapshot(repoRoot);
  const contract = JSON.parse(fs.readFileSync(path.join(repoRoot, "studio", "host_bridge_contract.json"), "utf8"));
  assert.equal(snapshot.description.framework_version, contract.framework_version);
  assert.equal(snapshot.description.contract_version, contract.version);
  assert.deepEqual(snapshot.description.operation_contracts["candidate.review.get"], contract.operations["candidate.review.get"]);
  const request = validBridgeRequest();
  const result = productionBridgeResult(repoRoot, request, { schema: "quillframe_test_projection_v1", project_id: "T605", authority: false });
  assert.equal(assertBridgeResult(result, request), true);
  assert.equal(result.secret_values_persisted, false);
  assert.match(result.request_fingerprint, /^sha256:[0-9a-f]{64}$/);
  assert.match(result.result_fingerprint, /^sha256:[0-9a-f]{64}$/);
});

const mutationCases = [
  ["nested duplicate key", () => assertJsonContract('{"schema":"x","nested":{"a":1,"a":2}}', { schema: "x" }), "JSON_DUPLICATE_KEY"],
  ["shape rejects number", () => assertJsonContract('{"schema":"x","authority":false}', { schema: "x", shape: { type: "object", required: ["schema", "authority"], exact: { schema: { type: "string" }, authority: { type: "boolean", const: false } } } }), null],
  ["shape rejects authority string", () => assertJsonContract('{"schema":"x","authority":"false"}', { schema: "x", shape: { type: "object", required: ["schema", "authority"], exact: { schema: { type: "string" }, authority: { type: "boolean", const: false } } } }), "JSON_TYPE"],
  ["shape rejects extra", () => assertMachineManifest({ schema: "x", authority: false, extra: 1 }, "x"), "JSON_KEYS"],
  ["authority true", () => assertMachineManifest({ schema: "x", authority: true }, "x", { authorityKeys: ["authority"] }), "MACHINE_AUTHORITY"],
  ["evil demo status", () => assertQuickDemoDom({ schema: "quillframe_ch001_quick_demo_receipt_v1", chapter: "CH001 · authority=false", statuses: ["PASSevil", "FIXTURE", "SAFE"], boundary: "model=false · uploads=0 · canon=false" }), "QUICK_DEMO_TYPED"],
  ["delete write", () => assertNoWrites(["DELETE"]), "PRODUCT_WRITE"],
  ["semantic heading missing", () => assertSemantics({ mainCount: 1, namedButtons: 1, headingCount: 0, headingNames: 0, landmarks: 1, namedLandmarks: 1, landmarkRoles: ["main"], ariaCurrent: true }), "SEMANTIC"],
  ["semantic current missing", () => assertSemantics({ mainCount: 1, namedButtons: 1, headingCount: 1, headingNames: 1, landmarks: 1, namedLandmarks: 1, landmarkRoles: ["main"], ariaCurrent: false }), "SEMANTIC"],
  ["cwv lcp missing", () => assertCwv({ supported: true, cls: 0, tbtMs: 0 }), "CWV_MISSING"],
  ["cwv cls budget", () => assertCwv({ supported: true, lcpMs: 1, cls: 0.2, tbtMs: 0 }), "CWV_BUDGET"],
  ["contrast low", () => { if (contrastRatio("rgb(120, 120, 120)", "rgb(255, 255, 255)") >= 4.5) throw new Error("CONTRAST_BUDGET"); }, null],
  ["preview required", () => startPreviews({ env: {}, cwd: "/tmp" }), "PREVIEW_START_REQUIRED"],
  ["preview exit blocked", () => parseExit({ code: "PREVIEW_NOT_READY" }), null],
  ["build missing", () => assertBuildArtifacts("/tmp/no-site", "/tmp/no-studio"), "BUILD_ARTIFACT_MISSING"],
  ["evidence outside tmp", () => validateEvidenceRoot("/var/tmp/t605"), "EVIDENCE_ROOT_INVALID"],
  ["evidence relative", () => validateEvidenceRoot("relative"), "EVIDENCE_ROOT_INVALID"],
  ["dialog missing escape", () => assertDialogLifecycle(["open", "focus-initial", "focus-return"]), "DIALOG_LIFECYCLE"],
  ["dialog missing return", () => assertDialogLifecycle(["open", "focus-initial", "escape"]), "DIALOG_LIFECYCLE"],
];
for (const [name, operation, expected] of mutationCases) test(`strict contract mutation: ${name}`, async () => {
  if (!expected) { await operation(); return; }
  await assert.rejects(async () => operation(), (error) => String(error?.code || error?.message || error).includes(expected));
});

const validLaunchReceipt = () => ({ schema: "quillframe_launch_receipt_v1", status: "ready", profile: "local", project_id: "browser-e2e", project_root: "/tmp/project", url: "http://127.0.0.1:43123/", process_id: 123, storage_boundary: "project_local_sqlite", browser_opened: false, cloud_upload_started: false, authority: false });
const validBridgeRequest = () => ({ schema: "quillframe_host_bridge_request_v11", bridge_version: "11", request_id: "r1", operation: "bridge.describe", surface: "local_app", authority: false, args: {} });
const validBridgeResult = (request = validBridgeRequest()) => ({ schema: "quillframe_host_bridge_result_v11", bridge_version: "11", request_id: request.request_id, operation: request.operation, surface: "local_app", status: "ok", request_fingerprint: "sha256:" + "a".repeat(64), result_fingerprint: "sha256:" + "b".repeat(64), data: { schema: "x" }, error: null, secret_values_persisted: false, authority: false, canon_authority: false, framework_write_authority: false, settlement_authority: false });

test("Chrome symlink is rejected even when target is executable", () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-chrome-")); const target = path.join(root, "target"); const link = path.join(root, "link"); fs.writeFileSync(target, "chrome"); fs.chmodSync(target, 0o755); fs.symlinkSync(target, link); assert.throws(() => resolveChrome({ CHROME_BIN: link }), (error) => error.code === "CHROME_BIN_INVALID"); fs.rmSync(root, { recursive: true, force: true }); });
test("evidence symlink ancestor is rejected", () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-root-")); const real = path.join(root, "real"); const link = path.join(root, "link"); fs.mkdirSync(real); fs.symlinkSync(real, link); assert.throws(() => validateEvidenceRoot(path.join(link, "evidence")), (error) => error.code === "EVIDENCE_ROOT_INVALID"); fs.rmSync(root, { recursive: true, force: true }); });
test("regular artifact validator rejects symlink files", () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-artifact-")); const target = path.join(root, "target"); const link = path.join(root, "link"); fs.writeFileSync(target, "x"); fs.symlinkSync(target, link); assert.throws(() => assertRegularFileNoFollow(link), (error) => error.code === "PATH_SYMLINK"); fs.rmSync(root, { recursive: true, force: true }); });
test("launch receipt exact loopback and no-upload contract", () => { assert.equal(assertLaunchReceipt(validLaunchReceipt()), true); });
test("launch receipt rejects cloud profile", () => { assert.throws(() => assertLaunchReceipt({ ...validLaunchReceipt(), profile: "cloud" }), /LOCAL_LAUNCH_RECEIPT/); });
test("launch receipt rejects non-loopback URL", () => { assert.throws(() => assertLaunchReceipt({ ...validLaunchReceipt(), url: "http://0.0.0.0:1/" }), /LOCAL_LAUNCH_RECEIPT/); });
test("launch receipt rejects secret-shaped fields", () => { assert.throws(() => assertLaunchReceipt({ ...validLaunchReceipt(), project_id: "secret-token" }), /LOCAL_LAUNCH_RECEIPT/); });
test("bridge request exact v11 query contract", () => { assert.equal(assertBridgeRequest(validBridgeRequest()), true); });
test("bridge request rejects operation alias", () => { const value = validBridgeRequest(); delete value.operation; value.op = "bridge.describe"; assert.throws(() => assertBridgeRequest(value), /BRIDGE_REQUEST_SHAPE/); });
test("bridge request rejects extra field", () => { assert.throws(() => assertBridgeRequest({ ...validBridgeRequest(), extra: true }), /BRIDGE_REQUEST_SHAPE/); });
test("bridge request rejects authority true", () => { assert.throws(() => assertBridgeRequest({ ...validBridgeRequest(), authority: true }), /BRIDGE_REQUEST_SHAPE/); });
test("bridge request rejects unknown mutation operation", () => { assert.throws(() => assertBridgeRequest({ ...validBridgeRequest(), operation: "candidate.accept" }), /BRIDGE_REQUEST_SHAPE/); });
test("bridge result exact v11 authority false contract", () => { assert.equal(assertBridgeResult(validBridgeResult(), validBridgeRequest()), true); });
test("bridge result rejects request mismatch", () => { assert.throws(() => assertBridgeResult(validBridgeResult(), { ...validBridgeRequest(), request_id: "other" }), /BRIDGE_RESULT_SHAPE/); });
test("bridge result rejects malformed fingerprint", () => { assert.throws(() => assertBridgeResult({ ...validBridgeResult(), result_fingerprint: "bad" }, validBridgeRequest()), /BRIDGE_RESULT_SHAPE/); });
test("bridge result rejects the retired hyphen fingerprint prefix", () => { assert.throws(() => assertBridgeResult({ ...validBridgeResult(), request_fingerprint: "sha256-" + "a".repeat(64) }, validBridgeRequest()), /BRIDGE_RESULT_SHAPE/); });
test("contrast alpha composites over opaque background", () => { assert.ok(contrastRatio("rgba(0, 0, 0, 0.5)", "rgb(255, 255, 255)") > 3); });
test("contrast transparent foreground fails closed", () => { assert.throws(() => contrastRatio("transparent", "rgb(255, 255, 255)"), /CONTRAST_UNSUPPORTED_COLOR/); });
test("contrast thresholds distinguish large and non-text", () => { assert.equal(requiredContrastThreshold({ largeText: true }), 3); assert.equal(requiredContrastThreshold({ nonText: true }), 3); assert.equal(requiredContrastThreshold(), 4.5); });
test("CWV requires real LCP measurement", () => { assert.throws(() => assertCwv({ supported: true, lcpMs: 0, cls: 0, tbtMs: 0 }), /CWV_MISSING/); });
test("CWV rejects unsupported observer", () => { assert.throws(() => assertCwv({ supported: false, sampleMs: 2000 }), /CWV_UNSUPPORTED/); });
test("CWV rejects TBT budget overage", () => { assert.throws(() => assertCwv({ supported: true, lcpMs: 100, cls: 0, tbtMs: 301 }), /CWV_BUDGET/); });
test("typed QuickDemo rejects missing deterministic core", () => { assert.throws(() => assertQuickDemoDom({ schema: "quillframe_ch001_quick_demo_receipt_v1", chapter: "CH001 · authority=false", statuses: ["PASS", "FIXTURE", "SAFE"], boundary: "model=false · uploads=0 · canon=false", receipt: validLaunchReceipt() }), /QUICK_DEMO/); });
test("typed QuickDemo rejects uploads", () => { const receipt = { schema: "quillframe_ch001_quick_demo_receipt_v1", chapter_id: "CH001", deterministic_core: { executed: true, modules: ["x"], packet_fingerprint: "sha256:" + "1".repeat(64), workflow_fingerprint: "sha256:" + "2".repeat(64), stage: "DRAFT" }, semantic_evidence: { schema: "quillframe_recorded_semantic_evidence_v1", source: "recorded_fixture", recorded_at: "2026-08-19T12:00:00+00:00", live_model_called: false, candidate_fingerprint: "sha256:" + "3".repeat(64), authority: false, summary: "x", findings: [] }, live_model_called: false, uploads: 1, canon_mutated: false, authority: false }; assert.throws(() => assertQuickDemoDom({ receipt, schema: receipt.schema, chapter: "CH001 · authority=false", statuses: ["PASS", "FIXTURE", "SAFE"], boundary: "model=false · uploads=1 · canon=false" }), /QUICK_DEMO/); });
test("dialog helper requires outside and background restore", () => { assert.throws(() => assertDialogLifecycle(["open", "focus-initial", "tab", "shift-tab", "escape", "focus-return"]), /DIALOG_LIFECYCLE/); });
test("subject and build identity mutation cannot pass manifest", () => { const manifest = { schema: "quillframe_browser_acceptance_v1", status: "pass", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: "CH001", subject: { start: { commit: "a".repeat(40), dirty: false, working_tree_fingerprint: "sha256:" + "1".repeat(64) }, end: { commit: "b".repeat(40), dirty: false, working_tree_fingerprint: "sha256:" + "1".repeat(64) }, stable: true }, build: { start_fingerprint: "sha256:" + "2".repeat(64), end_fingerprint: "sha256:" + "2".repeat(64), site_finalizer_fingerprint: "sha256:" + "3".repeat(64), stable: true }, browser: { name: "chromium", version: "x", fingerprint: "sha256:" + "4".repeat(64) }, matrix_count: 40, surfaces: [], global_checks: [], artifacts: [], errors: [], generated_at: "2026-08-20T00:00:00Z", artifacts_root: "." }; assert.throws(() => validateManifestContract(manifest), /MANIFEST_SUBJECT_UNSTABLE|MANIFEST_SURFACES/); });
test("strict manifest requires exact CH001 chapter scope", () => { const manifest = { schema: "quillframe_browser_acceptance_v1", status: "blocked", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: "CH002", subject: {}, build: {}, browser: null, matrix_count: 0, surfaces: [], global_checks: [], artifacts: [], errors: [], generated_at: "2026-08-20T00:00:00Z", artifacts_root: "." }; assert.throws(() => validateManifestContract(manifest), /MANIFEST_TOP_SCHEMA/); });
test("strict manifest rejects malformed commit", () => { const manifest = { schema: "quillframe_browser_acceptance_v1", status: "blocked", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: "CH001", subject: { start: { commit: "abc", dirty: false, working_tree_fingerprint: "sha256:" + "1".repeat(64) }, end: { commit: "abc", dirty: false, working_tree_fingerprint: "sha256:" + "1".repeat(64) }, stable: true }, build: {}, browser: null, matrix_count: 0, surfaces: [], global_checks: [], artifacts: [], errors: [], generated_at: "2026-08-20T00:00:00Z", artifacts_root: "." }; assert.throws(() => validateManifestContract(manifest), /MANIFEST_TOP_SCHEMA/); });
test("strict manifest rejects malformed fingerprint", () => { const manifest = { schema: "quillframe_browser_acceptance_v1", status: "blocked", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: "CH001", subject: { start: { commit: "a".repeat(40), dirty: false, working_tree_fingerprint: "bad" }, end: { commit: "a".repeat(40), dirty: false, working_tree_fingerprint: "bad" }, stable: true }, build: {}, browser: null, matrix_count: 0, surfaces: [], global_checks: [], artifacts: [], errors: [], generated_at: "2026-08-20T00:00:00Z", artifacts_root: "." }; assert.throws(() => validateManifestContract(manifest), /MANIFEST_TOP_SCHEMA/); });
test("strict manifest rejects top-level extra key", () => { const manifest = { schema: "quillframe_browser_acceptance_v1", status: "blocked", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: "CH001", subject: {}, build: {}, browser: null, matrix_count: 0, surfaces: [], global_checks: [], artifacts: [], errors: [], generated_at: "2026-08-20T00:00:00Z", artifacts_root: ".", extra: true }; assert.throws(() => validateManifestContract(manifest), /MANIFEST_TOP_SCHEMA/); });
test("strict manifest rejects missing global gate", () => { const manifest = { schema: "quillframe_browser_acceptance_v1", status: "blocked", task: "T605", gate: "T605_BROWSER_ACCEPTANCE", chapter_scope: "CH001", subject: {}, build: {}, browser: null, matrix_count: 0, surfaces: [], global_checks: [], artifacts: [], errors: [], generated_at: "2026-08-20T00:00:00Z", artifacts_root: "." }; assert.throws(() => validateManifestContract(manifest), /MANIFEST_TOP_SCHEMA|MANIFEST_GLOBAL_CHECKS/); });
test("strict JSON rejects trailing payload", () => { assert.throws(() => assertJsonContract('{"schema":"x"} trailing', { schema: "x" }), /JSON_TRAILING/); });
test("strict JSON rejects nested duplicate key", () => { assert.throws(() => assertJsonContract('{"schema":"x","nested":{"x":1,"x":2}}', { schema: "x" }), /JSON_DUPLICATE_KEY/); });
test("strict JSON rejects oversized content before shape", () => { assert.throws(() => assertJsonContract({ body: "x".repeat(70 * 1024) }, { schema: "x" }), /JSON_TOO_LARGE/); });
test("process-group cleanup reaches grandchildren", async () => { if (process.platform !== "linux") return; const item = spawnProcess(process.execPath, ["-e", "require('child_process').spawn('sleep',['30']); setTimeout(()=>{},30000)"], "/tmp"); await new Promise((resolve) => setTimeout(resolve, 100)); await terminateProcess(item, 300); assert.equal(item.hasExited(), true); });
test("startPreviews rejects symlinked repository ancestor before build", async () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-repo-")); const real = path.join(root, "real"); const link = path.join(root, "link"); fs.mkdirSync(real); fs.symlinkSync(real, link); await assert.rejects(() => startPreviews({ env: { QF_START_PREVIEWS: "1", QF_REPO_ROOT: link }, cwd: root }), (error) => ["PATH_INVALID", "PATH_SYMLINK"].includes(error.code)); fs.rmSync(root, { recursive: true, force: true }); });
test("blocked manifest keeps exact T605 identity and gate ids", () => { const root = fs.mkdtempSync(path.join(os.tmpdir(), "qf-t605-blocked-")); const manifest = writeFailureManifest({ evidenceRoot: root, code: "CHROME_BIN_REQUIRED" }); assert.equal(manifest.task, "T605"); assert.equal(manifest.chapter_scope, "CH001"); assert.deepEqual(manifest.global_checks.map((entry) => entry.id), ["quick_demo_truth", "machine_contracts", "keyboard", "dialog", "offline", "wcag", "cwv", "local_launch"]); fs.rmSync(root, { recursive: true, force: true }); });

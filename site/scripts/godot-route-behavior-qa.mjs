#!/usr/bin/env node
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function arg(name, fallback = "") {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

const chrome = process.env.CHROME || arg("chrome");
const url = arg("url", "http://127.0.0.1:4190/");
const output = arg("output", "/tmp/novelforge-route-parity/behavior.json");
const timeoutMs = Number(arg("timeout-ms", "90000"));
if (!chrome) {
  console.error("CHROME is required");
  process.exit(2);
}

const port = 23000 + (process.pid % 1000);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-godot-behavior-"));
const evidenceDir = path.dirname(output);
fs.mkdirSync(evidenceDir, { recursive: true });
const pending = new Map();
const diagnostics = [];
const results = {
  schema: "novelforge_godot_route_behavior_v2",
  status: "fail",
  routes: {},
  responsive: [],
  diagnostics: [],
};
let browser;
let socket;
let nextId = 1;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function cleanup() {
  try { socket?.close(); } catch {}
  try { browser?.kill("SIGTERM"); } catch {}
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
}

async function connect() {
  const deadline = Date.now() + 15000;
  let target;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await response.json();
      target = targets.find((item) => item.type === "page" && item.webSocketDebuggerUrl);
      if (target) break;
    } catch {}
    await sleep(120);
  }
  if (!target) throw new Error("Chrome DevTools target unavailable");
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("DevTools WebSocket timeout")), 10000);
    socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("DevTools WebSocket failed")); }, { once: true });
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const item = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error.message));
      else item.resolve(message.result ?? {});
      return;
    }
    if (message.method === "Runtime.exceptionThrown") {
      diagnostics.push(message.params?.exceptionDetails?.exception?.description ?? message.params?.exceptionDetails?.text ?? "runtime exception");
    }
  });
}

function command(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`timeout: ${method}`));
    }, 20000);
    pending.set(id, {
      resolve: (value) => { clearTimeout(timer); resolve(value); },
      reject: (error) => { clearTimeout(timer); reject(error); },
    });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (response?.exceptionDetails) throw new Error(response.exceptionDetails.text || "Runtime.evaluate exception");
  return response?.result?.value;
}

async function snapshot() {
  const raw = await evaluate(`JSON.stringify({
    ready: document.documentElement.dataset.novelforgeRuntime || null,
    interaction: document.documentElement.dataset.novelforgeInteraction || null,
    layout: document.documentElement.dataset.novelforgeLayout || null,
    responsive: document.documentElement.dataset.novelforgeResponsive || null,
    responsiveRevision: document.documentElement.dataset.novelforgeResponsiveRevision || '0',
    responsiveWidth: document.documentElement.dataset.novelforgeResponsiveWidth || null,
    accessibility: document.documentElement.dataset.novelforgeAccessibility || null,
    accessibilityRoute: document.documentElement.dataset.novelforgeAccessibilityRoute || null,
    locale: document.documentElement.dataset.locale || null,
    appearance: document.documentElement.dataset.novelforgeAppearance || null,
    interactionRevision: document.documentElement.dataset.novelforgeInteractionRevision || '0',
    focusedControl: document.documentElement.dataset.novelforgeFocusedControl || '',
    publicationProfile: document.documentElement.dataset.novelforgePublicationProfile || null,
    publicationArtifact: document.documentElement.dataset.novelforgePublicationArtifact || null,
    publicationHeroTargets: document.documentElement.dataset.novelforgePublicationHeroTargets || '',
    publicationRailTargets: document.documentElement.dataset.novelforgePublicationRailTargets || '',
    homeCapability: document.documentElement.dataset.novelforgeHomeCapability || null,
    homeBudget: document.documentElement.dataset.novelforgeHomeBudget || null,
    homeReady: document.documentElement.dataset.novelforgeHomeReady || null,
    homeTargets: document.documentElement.dataset.novelforgeHomeTargets || '',
    architectureNode: document.documentElement.dataset.novelforgeArchitectureNode || null,
    architectureRunStep: document.documentElement.dataset.novelforgeArchitectureRunStep || null,
    architectureTargets: document.documentElement.dataset.novelforgeArchitectureTargets || '',
    agentHost: document.documentElement.dataset.novelforgeAgentHost || null,
    agentTargets: document.documentElement.dataset.novelforgeAgentTargets || '',
    glyphAudit: document.documentElement.dataset.novelforgeGlyphAudit || null,
    scrollY: document.documentElement.dataset.novelforgeScrollY || '0',
    wideDesktop: document.documentElement.dataset.novelforgeWideDesktop || null,
    wideDesktopInner: document.documentElement.dataset.novelforgeWideDesktopInner || null,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    canvasWidth: Math.round(document.querySelector('#canvas')?.getBoundingClientRect().width || 0),
    canvasHeight: Math.round(document.querySelector('#canvas')?.getBoundingClientRect().height || 0),
    path: location.pathname
  })`);
  return JSON.parse(raw);
}

async function waitFor(label, predicate, timeout = timeoutMs) {
  const deadline = Date.now() + timeout;
  let current;
  while (Date.now() < deadline) {
    current = await snapshot();
    if (predicate(current)) return current;
    await sleep(120);
  }
  throw new Error(`${label} timeout: ${JSON.stringify(current)}`);
}

function parseTargets(value) {
  const map = new Map();
  for (const record of String(value || "").split(";").filter(Boolean)) {
    const [name, x, y, w, h] = record.split(",");
    if (!name) continue;
    map.set(name, { name, x: Number(x), y: Number(y), w: Number(w), h: Number(h) });
  }
  return map;
}

async function screenshot(name) {
  const result = await command("Page.captureScreenshot", { format: "png", fromSurface: true });
  const target = path.join(evidenceDir, `${name}.png`);
  const data = Buffer.from(result.data, "base64");
  fs.writeFileSync(target, data);
  if (data.length < 1024) throw new Error(`screenshot too small: ${name}`);
  return crypto.createHash("sha256").update(data).digest("hex");
}

async function mouseClick(x, y) {
  await command("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await command("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await command("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function touchClick(x, y) {
  await command("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y, id: 1, radiusX: 2, radiusY: 2, force: 1 }] });
  await sleep(50);
  await command("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
}

async function wheel(deltaY) {
  await command("Input.dispatchMouseEvent", { type: "mouseWheel", x: 720, y: 450, deltaX: 0, deltaY });
}

async function keyPress(key, code, virtualKeyCode) {
  const params = { key, code, windowsVirtualKeyCode: virtualKeyCode, nativeVirtualKeyCode: virtualKeyCode };
  await command("Input.dispatchKeyEvent", { type: "rawKeyDown", ...params });
  await command("Input.dispatchKeyEvent", { type: "keyUp", ...params });
}

async function navigateRoute(route) {
  await evaluate(`history.pushState({}, '', ${JSON.stringify(route)}); window.dispatchEvent(new PopStateEvent('popstate'));`);
  return waitFor(`route ${route}`, (s) => s.path === route && s.ready === "ready" && s.interaction === "ready" && s.accessibilityRoute === route, 20000);
}

async function resizeAndWait(width, height, expectedLayout) {
  const initial = await snapshot();
  const beforeRevision = Number(initial.responsiveRevision || 0);
  const beforeCanvasWidth = Number(initial.canvasWidth || 0);
  const beforeCanvasHeight = Number(initial.canvasHeight || 0);

  await command("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
    screenWidth: width,
    screenHeight: height,
  });

  return waitFor(`responsive ${width}x${height}`, (s) => {
    const runtimeWidth = Number(s.responsiveWidth || NaN);
    const canvasWidth = Number(s.canvasWidth || NaN);
    const canvasHeight = Number(s.canvasHeight || NaN);
    const geometryChanged = canvasWidth !== beforeCanvasWidth || canvasHeight !== beforeCanvasHeight;
    const revisionSettled = !geometryChanged || Number(s.responsiveRevision || 0) > beforeRevision;
    return s.ready === "ready"
      && s.interaction === "ready"
      && s.responsive === "ready"
      && s.accessibility === "ready"
      && s.layout === expectedLayout
      && Number(s.innerWidth) === width
      && Number(s.innerHeight) === height
      && Number.isFinite(runtimeWidth)
      && Number.isFinite(canvasWidth)
      && canvasWidth > 0
      && Math.abs(runtimeWidth - canvasWidth) <= 1
      && revisionSettled;
  }, 25000);
}

async function scrollToTarget(datasetKey, name) {
  for (let attempt = 0; attempt < 18; attempt += 1) {
    const state = await snapshot();
    const target = parseTargets(state[datasetKey]).get(name);
    if (!target) throw new Error(`missing target ${name} in ${datasetKey}: ${state[datasetKey]}`);
    const cy = target.y + target.h / 2;
    if (cy >= 95 && cy <= 805 && target.h >= 30 && target.w >= 30) return { state, target };
    const delta = Math.max(-600, Math.min(600, cy - 450));
    await wheel(delta);
    await sleep(120);
  }
  const state = await snapshot();
  throw new Error(`target ${name} never entered viewport: ${state[datasetKey]}`);
}

async function activateTarget(datasetKey, name, kind = "mouse") {
  const { target } = await scrollToTarget(datasetKey, name);
  const x = target.x + target.w / 2;
  const y = target.y + target.h / 2;
  if (kind === "touch") await touchClick(x, y);
  else await mouseClick(x, y);
}

async function scrollTop() {
  for (let i = 0; i < 10; i += 1) {
    const state = await snapshot();
    if (Number(state.scrollY || 0) <= 2) return state;
    await wheel(-700);
    await sleep(100);
  }
  return snapshot();
}

async function focusControlByTab(name) {
  await scrollTop();
  await evaluate(`document.querySelector('#canvas')?.focus({preventScroll:true})`);
  const canvasFocused = await evaluate(`document.activeElement === document.querySelector('#canvas')`);
  if (!canvasFocused) throw new Error("production canvas is not keyboard focusable");
  for (let i = 0; i < 80; i += 1) {
    await keyPress("Tab", "Tab", 9);
    const state = await waitFor(`focus progress ${name}`, () => true, 1000);
    if (state.focusedControl === name) return state;
    await sleep(25);
  }
  throw new Error(`Tab navigation never focused ${name}; last=${JSON.stringify(await snapshot())}`);
}

function assertChanged(label, before, after) {
  if (before === after) throw new Error(`${label} did not change: ${JSON.stringify(before)}`);
}

async function runPublication() {
  await navigateRoute("/publication");
  await resizeAndWait(1440, 900, "desktop");
  const baseline = await waitFor("publication EPUB default", (s) => s.publicationProfile === "EPUB" && s.glyphAudit === "pass");
  const invariant = { locale: baseline.locale, appearance: baseline.appearance, path: baseline.path };
  const hashes = [await screenshot("behavior-publication-epub-default")];

  let before = baseline;
  await activateTarget("publicationHeroTargets", "PublicationHeroHitTXT", "mouse");
  let after = await waitFor("publication TXT", (s) => s.publicationProfile === "TXT" && Number(s.interactionRevision) > Number(before.interactionRevision));
  assertChanged("TXT artifact", before.publicationArtifact, after.publicationArtifact);
  hashes.push(await screenshot("behavior-publication-txt-pointer"));

  before = after;
  await activateTarget("publicationHeroTargets", "PublicationHeroHitWEB", "touch");
  after = await waitFor("publication WEB touch", (s) => s.publicationProfile === "WEB" && Number(s.interactionRevision) > Number(before.interactionRevision));
  assertChanged("WEB artifact", before.publicationArtifact, after.publicationArtifact);
  hashes.push(await screenshot("behavior-publication-web-touch"));

  const beforeRail = after;
  await activateTarget("publicationRailTargets", "PublicationRailPRINT", "mouse");
  after = await waitFor("publication PRINT rail", (s) => s.publicationProfile === "PRINT" && Number(s.interactionRevision) > Number(beforeRail.interactionRevision));
  if (Number(after.scrollY) <= 0) throw new Error(`Publication rail rebuild lost scroll: ${JSON.stringify(after)}`);
  assertChanged("PRINT artifact", beforeRail.publicationArtifact, after.publicationArtifact);
  hashes.push(await screenshot("behavior-publication-print-rail"));

  await focusControlByTab("PublicationHeroHitEPUB");
  before = await snapshot();
  await keyPress("Enter", "Enter", 13);
  after = await waitFor("publication EPUB keyboard Enter", (s) => s.publicationProfile === "EPUB" && Number(s.interactionRevision) > Number(before.interactionRevision));
  assertChanged("EPUB artifact", before.publicationArtifact, after.publicationArtifact);
  hashes.push(await screenshot("behavior-publication-epub-enter"));

  await focusControlByTab("PublicationHeroHitTXT");
  before = await snapshot();
  await keyPress(" ", "Space", 32);
  after = await waitFor("publication TXT keyboard Space", (s) => s.publicationProfile === "TXT" && Number(s.interactionRevision) > Number(before.interactionRevision));
  await activateTarget("publicationHeroTargets", "PublicationHeroHitEPUB", "mouse");
  after = await waitFor("publication EPUB restored", (s) => s.publicationProfile === "EPUB");

  if (after.locale !== invariant.locale || after.appearance !== invariant.appearance || after.path !== invariant.path) {
    throw new Error(`Publication rebuild lost shell state: ${JSON.stringify({ invariant, after })}`);
  }
  if (new Set(hashes).size !== hashes.length) {
    throw new Error(`Publication rendered evidence did not change for every profile: ${JSON.stringify(hashes)}`);
  }
  results.routes.publication = {
    status: "pass",
    sequence: ["EPUB", "TXT", "WEB", "PRINT", "EPUB"],
    pointer: true,
    touch: true,
    keyboardEnter: true,
    keyboardSpace: true,
    scrollPreserved: true,
    shellStatePreserved: true,
    screenshotHashes: hashes,
  };
}

async function runHome() {
  await navigateRoute("/");
  await resizeAndWait(1440, 900, "desktop");
  let before = await snapshot();
  const nextCapability = Number(before.homeCapability) === 1 ? 2 : 1;
  await activateTarget("homeTargets", `HomeCapability${nextCapability}`);
  let after = await waitFor("home capability", (s) => Number(s.homeCapability) === nextCapability && Number(s.interactionRevision) > Number(before.interactionRevision));
  const capability = { before: before.homeCapability, after: after.homeCapability };

  before = after;
  await activateTarget("homeTargets", "HomeBudgetPlus");
  after = await waitFor("home budget", (s) => Number(s.homeBudget) > Number(before.homeBudget) && Number(s.interactionRevision) > Number(before.interactionRevision));
  const budget = { before: before.homeBudget, after: after.homeBudget };

  before = after;
  await activateTarget("homeTargets", "HomeGateContinuity");
  after = await waitFor("home readiness", (s) => s.homeReady === "true" && s.homeReady !== before.homeReady && Number(s.interactionRevision) > Number(before.interactionRevision));
  const ready = { before: before.homeReady, after: after.homeReady };
  await screenshot("behavior-home-updated");
  results.routes.home = { status: "pass", capability, budget, ready };
}

async function runArchitecture() {
  await navigateRoute("/architecture");
  await resizeAndWait(1440, 900, "desktop");
  let before = await snapshot();
  const nodeIndex = Number(before.architectureNode) === 1 ? 2 : 1;
  await activateTarget("architectureTargets", `ArchitectureNode${nodeIndex}`);
  let after = await waitFor("architecture node", (s) => Number(s.architectureNode) === nodeIndex && Number(s.interactionRevision) > Number(before.interactionRevision));

  before = after;
  await activateTarget("architectureTargets", "ArchitectureNext");
  after = await waitFor("architecture run start", (s) => Number(s.architectureRunStep) > Number(before.architectureRunStep) && Number(s.interactionRevision) > Number(before.interactionRevision));
  const step1 = Number(after.architectureRunStep);

  before = after;
  await activateTarget("architectureTargets", "ArchitectureNext");
  after = await waitFor("architecture run advance", (s) => Number(s.architectureRunStep) > step1 && Number(s.interactionRevision) > Number(before.interactionRevision));
  const step2 = Number(after.architectureRunStep);

  await activateTarget("architectureTargets", "ArchitectureReset");
  after = await waitFor("architecture reset", (s) => Number(s.architectureRunStep) === -1);
  await screenshot("behavior-architecture-reset");
  results.routes.architecture = { status: "pass", selectedNode: nodeIndex, step1, step2, reset: Number(after.architectureRunStep) };
}

async function runAgents() {
  await navigateRoute("/agents");
  await resizeAndWait(1440, 900, "desktop");
  const before = await snapshot();
  const targetIndex = before.agentHost === "Claude Code" ? 2 : 0;
  await activateTarget("agentTargets", `AgentHost${targetIndex}`);
  const after = await waitFor("agent host", (s) => s.agentHost !== before.agentHost && Number(s.interactionRevision) > Number(before.interactionRevision));
  await screenshot("behavior-agents-selected");
  results.routes.agents = { status: "pass", before: before.agentHost, after: after.agentHost };
}

async function runResponsiveMatrix() {
  await navigateRoute("/publication");
  const matrix = [
    [2560, 1440, "desktop"],
    [1920, 1080, "desktop"],
    [1600, 900, "desktop"],
    [1440, 900, "desktop"],
    [1280, 800, "desktop"],
    [1024, 768, "compact"],
    [768, 1024, "compact"],
    [430, 932, "phone"],
    [390, 844, "phone"],
    [360, 800, "phone"],
  ];
  for (const [width, height, layout] of matrix) {
    const state = await resizeAndWait(width, height, layout);
    if (state.glyphAudit !== "pass") throw new Error(`glyph runtime audit failed at ${width}x${height}: ${JSON.stringify(state)}`);
    if (width >= 1600 && (state.wideDesktop !== "solid-page-clamped" || Number(state.wideDesktopInner) !== 1384)) {
      throw new Error(`wide desktop contract missing at ${width}x${height}: ${JSON.stringify(state)}`);
    }
    const hash = await screenshot(`behavior-publication-${width}x${height}`);
    results.responsive.push({
      width,
      height,
      layout,
      innerWidth: Number(state.innerWidth),
      canvasWidth: Number(state.canvasWidth),
      responsiveWidth: Number(state.responsiveWidth),
      wideDesktop: state.wideDesktop,
      glyphAudit: state.glyphAudit,
      screenshotHash: hash,
    });
  }
}

try {
  browser = spawn(chrome, [
    "--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking",
    "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  browser.stderr.setEncoding("utf8");
  browser.stderr.on("data", (chunk) => {
    for (const line of chunk.split(/\r?\n/)) if (line.trim()) diagnostics.push(line.trim());
  });

  await connect();
  await command("Runtime.enable");
  await command("Page.enable");
  await command("Input.setIgnoreInputEvents", { ignore: false });
  await command("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false, screenWidth: 1440, screenHeight: 900 });
  await command("Page.navigate", { url });
  await waitFor("behavior runtime ready", (s) => s.ready === "ready" && s.interaction === "ready" && s.responsive === "ready" && s.accessibility === "ready", timeoutMs);

  await runPublication();
  await runHome();
  await runArchitecture();
  await runAgents();
  await runResponsiveMatrix();

  const fatalDiagnostics = diagnostics.filter((line) => /memory access out of bounds|RuntimeError|SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i.test(line));
  if (fatalDiagnostics.length) throw new Error(`fatal runtime diagnostics: ${fatalDiagnostics.join("\n")}`);
  results.status = "pass";
  results.diagnostics = diagnostics.filter((line) => /error|warning|exception/i.test(line)).slice(-80);
  fs.writeFileSync(output, JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
} catch (error) {
  results.status = "fail";
  results.error = error?.stack || String(error);
  results.diagnostics = diagnostics.slice(-120);
  fs.writeFileSync(output, JSON.stringify(results, null, 2));
  console.error(results.error);
  process.exitCode = 1;
} finally {
  cleanup();
}

#!/usr/bin/env node
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function arg(name, fallback = "") {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

const chrome = process.env.CHROME || arg("chrome");
const url = arg("url", "http://127.0.0.1:4190/");
const output = arg("output", "/tmp/novelforge-route-parity/workbench-behavior.json");
const timeoutMs = Number(arg("timeout-ms", "90000"));
if (!chrome) process.exit(2);

const port = 24000 + (process.pid % 1000);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-workbench-behavior-"));
const pending = new Map();
const diagnostics = [];
let browser;
let socket;
let nextId = 1;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const results = { schema: "novelforge_godot_workbench_behavior_v1", status: "fail", inspector: {}, playground: {}, diagnostics: [] };

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
      const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
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
      if (message.error) item.reject(new Error(message.error.message)); else item.resolve(message.result ?? {});
      return;
    }
    if (message.method === "Runtime.exceptionThrown") diagnostics.push(message.params?.exceptionDetails?.exception?.description ?? message.params?.exceptionDetails?.text ?? "exception");
  });
}

function command(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`timeout: ${method}`)); }, 20000);
    pending.set(id, { resolve: (value) => { clearTimeout(timer); resolve(value); }, reject: (error) => { clearTimeout(timer); reject(error); } });
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
    accessibility: document.documentElement.dataset.novelforgeAccessibility || null,
    accessibilityRoute: document.documentElement.dataset.novelforgeAccessibilityRoute || null,
    interactionRevision: document.documentElement.dataset.novelforgeInteractionRevision || '0',
    inspectorState: document.documentElement.dataset.novelforgeInspectorState || null,
    inspectorTargets: document.documentElement.dataset.novelforgeInspectorTargets || '',
    playgroundMode: document.documentElement.dataset.novelforgePlaygroundMode || null,
    playgroundChars: document.documentElement.dataset.novelforgePlaygroundChars || '0',
    playgroundRan: document.documentElement.dataset.novelforgePlaygroundRan || 'false',
    playgroundTargets: document.documentElement.dataset.novelforgePlaygroundTargets || '',
    playgroundEditor: document.documentElement.dataset.novelforgePlaygroundEditor || '',
    scrollY: document.documentElement.dataset.novelforgeScrollY || '0',
    glyphAudit: document.documentElement.dataset.novelforgeGlyphAudit || null,
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
    map.set(name, { name, x: Number(x), y: Number(y), w: Number(w), h: Number(h) });
  }
  return map;
}

function parseRect(value) {
  const [x, y, w, h] = String(value || "").split(",").map(Number);
  return Number.isFinite(x + y + w + h) ? { x, y, w, h } : null;
}

async function click(x, y) {
  await command("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await command("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await command("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function wheel(deltaY) {
  await command("Input.dispatchMouseEvent", { type: "mouseWheel", x: 720, y: 450, deltaX: 0, deltaY });
}

async function navigate(route) {
  await evaluate(`history.pushState({}, '', ${JSON.stringify(route)}); window.dispatchEvent(new PopStateEvent('popstate'));`);
  return waitFor(`route ${route}`, (s) => s.path === route && s.ready === "ready" && s.interaction === "ready" && s.accessibility === "ready" && s.accessibilityRoute === route, 20000);
}

async function visibleTarget(datasetKey, name) {
  for (let attempt = 0; attempt < 18; attempt += 1) {
    const state = await snapshot();
    const target = parseTargets(state[datasetKey]).get(name);
    if (!target) throw new Error(`missing ${name}: ${state[datasetKey]}`);
    const cy = target.y + target.h / 2;
    if (cy >= 90 && cy <= 820 && target.w >= 30 && target.h >= 30) return target;
    await wheel(Math.max(-600, Math.min(600, cy - 450)));
    await sleep(100);
  }
  throw new Error(`${name} never entered viewport`);
}

async function clickTarget(datasetKey, name) {
  const target = await visibleTarget(datasetKey, name);
  await click(target.x + target.w / 2, target.y + target.h / 2);
}

async function visibleEditor() {
  for (let attempt = 0; attempt < 18; attempt += 1) {
    const state = await snapshot();
    const rect = parseRect(state.playgroundEditor);
    if (!rect) throw new Error(`missing playground editor: ${JSON.stringify(state)}`);
    const cy = rect.y + rect.h / 2;
    if (cy >= 90 && cy <= 820) return rect;
    await wheel(Math.max(-600, Math.min(600, cy - 450)));
    await sleep(100);
  }
  throw new Error("playground editor never entered viewport");
}

async function typeText(text) {
  for (const char of text) {
    const isLetter = /[A-Za-z]/.test(char);
    const isDigit = /[0-9]/.test(char);
    const code = char === " " ? "Space" : isLetter ? `Key${char.toUpperCase()}` : isDigit ? `Digit${char}` : "Unidentified";
    const keyCode = char === " " ? 32 : isLetter ? char.toUpperCase().charCodeAt(0) : isDigit ? char.charCodeAt(0) : 0;
    await command("Input.dispatchKeyEvent", { type: "rawKeyDown", key: char, code, text: char, unmodifiedText: char, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await command("Input.dispatchKeyEvent", { type: "keyUp", key: char, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
}

async function screenshot(name) {
  const shot = await command("Page.captureScreenshot", { format: "png", fromSurface: true });
  const target = path.join(path.dirname(output), `${name}.png`);
  fs.writeFileSync(target, Buffer.from(shot.data, "base64"));
}

try {
  browser = spawn(chrome, [
    "--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking",
    "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  browser.stderr.setEncoding("utf8");
  browser.stderr.on("data", (chunk) => { for (const line of chunk.split(/\r?\n/)) if (line.trim()) diagnostics.push(line.trim()); });
  await connect();
  await command("Runtime.enable");
  await command("Page.enable");
  await command("Input.setIgnoreInputEvents", { ignore: false });
  await command("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false, screenWidth: 1440, screenHeight: 900 });
  await command("Page.navigate", { url });
  await waitFor("runtime ready", (s) => s.ready === "ready" && s.interaction === "ready" && s.accessibility === "ready", timeoutMs);

  await navigate("/inspect");
  let before = await waitFor("inspector empty", (s) => s.inspectorState === "empty" && s.glyphAudit === "pass");
  await clickTarget("inspectorTargets", "InspectorLoadDemo");
  let after = await waitFor("inspector demo", (s) => s.inspectorState === "demo" && Number(s.interactionRevision) > Number(before.interactionRevision));
  await screenshot("behavior-inspector-demo");
  before = after;
  await clickTarget("inspectorTargets", "InspectorReset");
  after = await waitFor("inspector reset", (s) => s.inspectorState === "empty" && Number(s.interactionRevision) > Number(before.interactionRevision));
  before = after;
  await clickTarget("inspectorTargets", "InspectorChooseFolder");
  after = await waitFor("inspector truthful folder limitation", (s) => s.inspectorState === "notice" && Number(s.interactionRevision) > Number(before.interactionRevision));
  results.inspector = { status: "pass", demo: true, reset: true, folderButtonIsNotFalse: true, folderImportParity: false };

  await navigate("/playground");
  before = await waitFor("playground default", (s) => s.playgroundMode === "DRAFT" && s.playgroundRan === "false");
  await clickTarget("playgroundTargets", "PlaygroundModeAUDIT");
  after = await waitFor("playground mode", (s) => s.playgroundMode === "AUDIT" && Number(s.interactionRevision) > Number(before.interactionRevision));

  const editor = await visibleEditor();
  await click(editor.x + editor.w / 2, editor.y + Math.min(editor.h / 2, 28));
  const sample = "This deterministic playground input contains enough characters for a prepared trace";
  await typeText(sample);
  after = await waitFor("playground text", (s) => Number(s.playgroundChars) >= 40, 15000);
  before = after;
  await clickTarget("playgroundTargets", "PlaygroundRun");
  after = await waitFor("playground run", (s) => s.playgroundRan === "true" && Number(s.interactionRevision) > Number(before.interactionRevision));
  await screenshot("behavior-playground-run");
  before = after;
  await clickTarget("playgroundTargets", "PlaygroundClear");
  after = await waitFor("playground clear", (s) => Number(s.playgroundChars) === 0 && s.playgroundRan === "false" && Number(s.interactionRevision) > Number(before.interactionRevision));
  results.playground = { status: "pass", mode: "AUDIT", typedCharacters: sample.length, ran: true, cleared: true };

  const fatal = diagnostics.filter((line) => /memory access out of bounds|RuntimeError|SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i.test(line));
  if (fatal.length) throw new Error(`fatal runtime diagnostics: ${fatal.join("\n")}`);
  results.status = "pass";
  results.diagnostics = diagnostics.filter((line) => /error|warning|exception/i.test(line)).slice(-80);
  fs.writeFileSync(output, JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
} catch (error) {
  results.error = error?.stack || String(error);
  results.diagnostics = diagnostics.slice(-120);
  fs.writeFileSync(output, JSON.stringify(results, null, 2));
  console.error(results.error);
  process.exitCode = 1;
} finally {
  cleanup();
}

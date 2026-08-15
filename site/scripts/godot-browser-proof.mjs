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
const url = arg("url");
const output = arg("output");
const width = Number(arg("width", "1440"));
const height = Number(arg("height", "900"));
const timeoutMs = Number(arg("timeout-ms", "90000"));
const expectLayout = arg("expect-layout");
const verifyHistory = arg("verify-history") === "true";

if (!chrome || !url || !output) {
  console.error("usage: CHROME=/path/to/chrome node godot-browser-proof.mjs --url URL --output screenshot.png [--width 1440 --height 900 --timeout-ms 90000 --expect-layout desktop|compact|phone --verify-history true]");
  process.exit(2);
}

const port = 19000 + (process.pid % 1000);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-godot-chrome-"));
const diagnostics = [];
let browser;
let socket;
let nextId = 1;
const pending = new Map();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function cleanup() {
  try { socket?.close(); } catch {}
  try { browser?.kill("SIGTERM"); } catch {}
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
}

process.on("SIGINT", () => { cleanup(); process.exit(130); });
process.on("SIGTERM", () => { cleanup(); process.exit(143); });

async function fetchTargets() {
  const response = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!response.ok) throw new Error(`DevTools target listing failed: ${response.status}`);
  return response.json();
}

async function connectDevTools() {
  const deadline = Date.now() + 15000;
  let target;
  while (Date.now() < deadline) {
    try {
      const targets = await fetchTargets();
      target = targets.find((item) => item.type === "page" && item.webSocketDebuggerUrl);
      if (target) break;
    } catch {}
    await sleep(150);
  }
  if (!target) throw new Error("Chrome DevTools page target did not appear");

  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("DevTools WebSocket open timeout")), 10000);
    socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("DevTools WebSocket failed")); }, { once: true });
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(`${message.error.message}: ${JSON.stringify(message.error.data ?? {})}`));
      else resolve(message.result ?? {});
      return;
    }
    if (message.method === "Runtime.exceptionThrown") {
      const detail = message.params?.exceptionDetails;
      diagnostics.push(`exception: ${detail?.text ?? "unknown"} ${detail?.exception?.description ?? ""}`.trim());
    } else if (message.method === "Runtime.consoleAPICalled") {
      const values = (message.params?.args ?? []).map((entry) => entry.value ?? entry.description ?? entry.type);
      diagnostics.push(`console.${message.params?.type ?? "log"}: ${values.join(" ")}`);
    } else if (message.method === "Log.entryAdded") {
      diagnostics.push(`log.${message.params?.entry?.level ?? "info"}: ${message.params?.entry?.text ?? ""}`);
    }
  });
}

function command(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`DevTools command timeout: ${method}`));
    }, 15000);
    pending.set(id, {
      resolve: (value) => { clearTimeout(timer); resolve(value); },
      reject: (error) => { clearTimeout(timer); reject(error); },
    });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  return command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
}

async function runtimeState() {
  const response = await evaluate(`JSON.stringify({runtime:document.documentElement.dataset.novelforgeRuntime||null,engine:document.documentElement.dataset.novelforgeEngine||null,layout:document.documentElement.dataset.novelforgeLayout||null,history:document.documentElement.dataset.novelforgeHistory||null,route:document.documentElement.dataset.novelforgeRoute||null,a11y:document.documentElement.dataset.novelforgeA11y||null,target:document.documentElement.dataset.novelforgeTarget||null,motion:document.documentElement.dataset.novelforgeMotion||null,locale:document.documentElement.dataset.novelforgeLocale||null,localeApplied:document.documentElement.dataset.novelforgeLocaleApplied||null,docsRoot:document.documentElement.dataset.novelforgeDocsRoot||null,localeSetter:typeof window.__novelforgeSetLocale==='function',status:document.getElementById('nf-status')?.textContent||null,loader:document.getElementById('nf-loader')?.className||null,path:location.pathname,proofToken:window.__novelforgeHistoryProof||null,innerWidth:window.innerWidth,innerHeight:window.innerHeight,dpr:window.devicePixelRatio,canvasWidth:document.getElementById('canvas')?.width||0,canvasHeight:document.getElementById('canvas')?.height||0})`);
  const value = response?.result?.value;
  return value ? JSON.parse(value) : null;
}

async function waitForState(predicate, description, deadlineMs = 8000) {
  const deadline = Date.now() + deadlineMs;
  let state = null;
  while (Date.now() < deadline) {
    state = await runtimeState();
    if (predicate(state)) return state;
    await sleep(100);
  }
  throw new Error(`${description}: ${JSON.stringify(state)}`);
}

try {
  browser = spawn(chrome, [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`,
    url,
  ], { stdio: ["ignore", "ignore", "pipe"] });

  browser.stderr.setEncoding("utf8");
  browser.stderr.on("data", (chunk) => {
    for (const line of chunk.split(/\r?\n/)) {
      if (line.trim()) diagnostics.push(`chrome: ${line.trim()}`);
    }
  });

  await connectDevTools();
  await command("Runtime.enable");
  await command("Page.enable");
  await command("Log.enable");

  const deadline = Date.now() + timeoutMs;
  let state = null;
  while (Date.now() < deadline) {
    state = await runtimeState();
    if (state?.runtime === "ready") break;
    if (state?.runtime === "error" || state?.engine === "error") {
      throw new Error(`Godot Web entered an error state: ${JSON.stringify(state)}`);
    }
    await sleep(500);
  }

  if (state?.runtime !== "ready") {
    throw new Error(`Godot Web did not become scene-ready within ${timeoutMs}ms: ${JSON.stringify(state)}`);
  }
  if (expectLayout && state?.layout !== expectLayout) {
    throw new Error(`Godot Web responsive layout mismatch: expected ${expectLayout}, got ${state?.layout ?? "unset"}; ${JSON.stringify(state)}`);
  }
  if (state?.a11y !== "ready" || state?.target !== "44") {
    throw new Error(`Godot Web accessibility contract is not ready: ${JSON.stringify(state)}`);
  }
  if (!state?.localeSetter || !["en-US", "zh-CN"].includes(state?.locale) || Number(state?.localeApplied ?? 0) < 10) {
    throw new Error(`Godot Web locale bridge is not ready: ${JSON.stringify(state)}`);
  }

  await evaluate("window.__novelforgeSetLocale('zh-CN')");
  state = await waitForState(
    (candidate) => candidate?.locale === "zh-CN" && candidate?.docsRoot === "/docs/" && Number(candidate?.localeApplied ?? 0) >= 10,
    "Godot Web did not apply the zh-CN Product locale",
  );
  await evaluate("window.__novelforgeSetLocale('en-US')");
  state = await waitForState(
    (candidate) => candidate?.locale === "en-US" && candidate?.docsRoot === "/docs/en/" && Number(candidate?.localeApplied ?? 0) >= 10,
    "Godot Web did not restore the en-US Product locale",
  );
  const localeProof = true;

  let historyProof = false;
  if (verifyHistory) {
    if (state?.history !== "live") {
      throw new Error(`Godot Web history bridge is not live: ${JSON.stringify(state)}`);
    }
    const originalPath = state.path || "/";
    const alternatePath = originalPath === "/studio" ? "/architecture" : "/studio";
    await evaluate(`window.__novelforgeHistoryProof='alive'; history.pushState({}, '', ${JSON.stringify(alternatePath)}); window.dispatchEvent(new PopStateEvent('popstate'));`);
    state = await waitForState(
      (candidate) => candidate?.path === alternatePath && candidate?.route === alternatePath && candidate?.proofToken === "alive" && candidate?.locale === "en-US",
      "Godot Web did not route the live scene after a history event",
    );
    await evaluate("history.back()");
    state = await waitForState(
      (candidate) => candidate?.path === originalPath && candidate?.route === originalPath && candidate?.proofToken === "alive" && candidate?.locale === "en-US",
      "Godot Web browser back did not restore the live scene without a reload",
    );
    historyProof = true;
  }

  const capture = await command("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, Buffer.from(capture.data, "base64"));

  const proof = {
    schema: "novelforge_godot_browser_proof_v4",
    status: "pass",
    url,
    requested_viewport: `${width}x${height}`,
    browser_viewport: `${state.innerWidth}x${state.innerHeight}`,
    runtime: state.runtime,
    engine: state.engine,
    layout: state.layout,
    a11y: state.a11y,
    target_px: Number(state.target),
    motion: state.motion,
    locale: state.locale,
    locale_proof: localeProof,
    docs_root: state.docsRoot,
    history: state.history,
    history_proof: historyProof,
    path: state.path,
    canvas: `${state.canvasWidth}x${state.canvasHeight}`,
    screenshot_bytes: fs.statSync(output).size,
  };
  console.log(JSON.stringify(proof));
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  const useful = diagnostics.filter((line) => !line.includes("dbus/") && !line.includes("org.freedesktop") && !line.includes("Registration response error"));
  if (useful.length) {
    console.error("--- browser diagnostics ---");
    for (const line of useful.slice(-80)) console.error(line);
  }
  process.exitCode = 1;
} finally {
  cleanup();
}

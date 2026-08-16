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
const expectLayout = arg("expect-layout");
const expectMarker = arg("expect-marker");
const wheelY = Number(arg("wheel-y", "0"));
const timeoutMs = Number(arg("timeout-ms", "90000"));

if (!chrome || !url || !output) {
  console.error("usage: CHROME=/path/to/chrome node godot-shadow-browser-shot.mjs --url URL --output shot.png --width 1440 --height 900 [--wheel-y 1200] [--expect-marker novelforgeVisualCompletion=ready]");
  process.exit(2);
}

const port = 20000 + (process.pid % 1000);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-godot-shadow-chrome-"));
const pending = new Map();
const diagnostics = [];
let browser;
let socket;
let nextId = 1;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function cleanup() {
  try { socket?.close(); } catch {}
  try { browser?.kill("SIGTERM"); } catch {}
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
}

async function targetList() {
  const response = await fetch(`http://127.0.0.1:${port}/json/list`);
  if (!response.ok) throw new Error(`DevTools target listing failed: ${response.status}`);
  return response.json();
}

async function connectDevTools() {
  const deadline = Date.now() + 15000;
  let target;
  while (Date.now() < deadline) {
    try {
      const targets = await targetList();
      target = targets.find((item) => item.type === "page" && item.webSocketDebuggerUrl);
      if (target) break;
    } catch {}
    await sleep(120);
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
      const pendingCommand = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) pendingCommand.reject(new Error(`${message.error.message}: ${JSON.stringify(message.error.data ?? {})}`));
      else pendingCommand.resolve(message.result ?? {});
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
  return response?.result?.value;
}

async function state() {
  const raw = await evaluate(`JSON.stringify({
    shadow: document.documentElement.dataset.novelforgeGodotShadow || null,
    runtime: document.documentElement.dataset.novelforgeRuntime || null,
    layout: document.documentElement.dataset.novelforgeLayout || null,
    loaderHidden: document.getElementById('nf-loader')?.getAttribute('data-hidden') || null,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    canvasWidth: document.getElementById('canvas')?.width || 0,
    canvasHeight: document.getElementById('canvas')?.height || 0,
    path: location.pathname,
    href: location.href,
    dataset: {...document.documentElement.dataset}
  })`);
  return raw ? JSON.parse(raw) : null;
}

function assertMarkers(current) {
  if (!expectMarker) return;
  for (const contract of expectMarker.split(",").map((v) => v.trim()).filter(Boolean)) {
    const [key, expected] = contract.split("=", 2);
    const actual = current?.dataset?.[key] ?? null;
    if (actual !== expected) throw new Error(`Godot browser marker mismatch: ${key} expected ${expected}, got ${actual}; ${JSON.stringify(current?.dataset ?? {})}`);
  }
}

async function scrollGodot(delta) {
  if (!delta) return;
  const sign = Math.sign(delta);
  let remaining = Math.abs(delta);
  const x = Math.round(width * 0.5);
  const y = Math.round(height * 0.55);
  await command("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  while (remaining > 0) {
    const step = Math.min(420, remaining);
    await command("Input.dispatchMouseEvent", {
      type: "mouseWheel",
      x,
      y,
      deltaX: 0,
      deltaY: step * sign,
    });
    remaining -= step;
    await sleep(90);
  }
  await sleep(500);
}

try {
  browser = spawn(chrome, [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-background-networking",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  browser.stderr.setEncoding("utf8");
  browser.stderr.on("data", (chunk) => {
    for (const line of chunk.split(/\r?\n/)) if (line.trim()) diagnostics.push(`chrome: ${line.trim()}`);
  });

  await connectDevTools();
  await command("Runtime.enable");
  await command("Page.enable");
  await command("Log.enable");
  await command("Input.setIgnoreInputEvents", { ignore: false });
  await command("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
    screenWidth: width,
    screenHeight: height,
  });
  await command("Page.navigate", { url });

  const deadline = Date.now() + timeoutMs;
  let current = null;
  while (Date.now() < deadline) {
    current = await state();
    if (current?.shadow === "ready" && current?.runtime === "ready" && current?.loaderHidden === "true") break;
    if (current?.shadow === "error" || current?.runtime === "error") {
      throw new Error(`Godot shadow entered error state: ${JSON.stringify(current)}`);
    }
    await sleep(250);
  }

  if (current?.shadow !== "ready" || current?.runtime !== "ready") {
    throw new Error(`Godot shadow did not become scene-ready within ${timeoutMs}ms: ${JSON.stringify(current)}`);
  }
  if (expectLayout && current.layout !== expectLayout) {
    throw new Error(`Godot shadow layout mismatch: expected ${expectLayout}, got ${current.layout}; ${JSON.stringify(current)}`);
  }
  if (current.innerWidth !== width || current.innerHeight !== height) {
    throw new Error(`Godot shadow viewport mismatch: expected ${width}x${height}, got ${current.innerWidth}x${current.innerHeight}`);
  }
  assertMarkers(current);

  await scrollGodot(wheelY);
  current = await state();
  assertMarkers(current);

  // Let the loader/scroll visual state settle before capture.
  await sleep(400);
  const capture = await command("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, Buffer.from(capture.data, "base64"));

  console.log(JSON.stringify({
    schema: "novelforge_godot_shadow_browser_shot_v2",
    status: "pass",
    ready: true,
    layout: current.layout,
    viewport: `${current.innerWidth}x${current.innerHeight}`,
    canvas: `${current.canvasWidth}x${current.canvasHeight}`,
    wheel_y: wheelY,
    markers: expectMarker || null,
    screenshot_bytes: fs.statSync(output).size,
    output,
  }));
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  const useful = diagnostics.filter((line) => !line.includes("dbus/") && !line.includes("org.freedesktop"));
  if (useful.length) {
    console.error("--- browser diagnostics ---");
    for (const line of useful.slice(-100)) console.error(line);
  }
  process.exitCode = 1;
} finally {
  cleanup();
}

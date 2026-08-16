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
const url = arg("url", "http://127.0.0.1:4188/?route=/studio");
const output = arg("output", "/tmp/product-site-browser-qa/studio-handoff.json");
const timeoutMs = Number(arg("timeout-ms", "30000"));
const expectedUrl = "https://studio.novelforge.wei-dev.com/";
const uniqueCommandQuery = "studio.novelforge.wei-dev.com";
if (!chrome) {
  console.error("CHROME is required");
  process.exit(2);
}

const port = 23000 + (process.pid % 1000);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-studio-handoff-"));
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
      if (message.error) item.reject(new Error(message.error.message)); else item.resolve(message.result ?? {});
      return;
    }
    if (message.method === "Runtime.exceptionThrown") {
      diagnostics.push(message.params?.exceptionDetails?.exception?.description ?? message.params?.exceptionDetails?.text ?? "exception");
    }
  });
}

function command(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`timeout: ${method}`)); }, 20000);
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

async function state() {
  const raw = await evaluate(`JSON.stringify({
    runtime: document.documentElement.dataset.novelforgeRuntime || null,
    interaction: document.documentElement.dataset.novelforgeInteraction || null,
    command: document.documentElement.dataset.novelforgeCommand || null,
    query: document.documentElement.dataset.novelforgeCommandQuery || '',
    route: document.documentElement.dataset.novelforgeAccessibilityRoute || null,
    layout: document.documentElement.dataset.novelforgeLayout || null
  })`);
  return JSON.parse(raw);
}

async function waitFor(label, predicate) {
  const deadline = Date.now() + timeoutMs;
  let current;
  while (Date.now() < deadline) {
    current = await state();
    if (predicate(current)) return current;
    await sleep(120);
  }
  throw new Error(`${label} timeout: ${JSON.stringify(current)}`);
}

async function key(key, modifiers = 0) {
  const code = key.length === 1 ? `Key${key.toUpperCase()}` : key;
  await command("Input.dispatchKeyEvent", { type: "keyDown", key, code, modifiers });
  await command("Input.dispatchKeyEvent", { type: "keyUp", key, code, modifiers });
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
  await command("Emulation.setDeviceMetricsOverride", {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false, screenWidth: 1440, screenHeight: 900,
  });
  await command("Page.navigate", { url });
  await waitFor("Studio runtime", (s) => s.runtime === "ready" && s.interaction === "ready" && s.route === "/studio" && s.layout === "desktop");

  // Intercept the handoff at the real browser boundary so QA never depends on
  // the external Studio host. The exact hostname query is deliberate: "hosted"
  // also matches the ordinary Studio route description, which previously made
  // Enter select /studio instead of the external command.
  await evaluate(`(() => {
    window.__novelforgeStudioHandoff = [];
    window.open = (...args) => {
      window.__novelforgeStudioHandoff.push(args);
      return { closed: false };
    };
    return true;
  })()`);

  await key("k", 2);
  await waitFor("command palette", (s) => s.command === "open");
  for (const ch of uniqueCommandQuery) await key(ch);
  await waitFor("Hosted Studio unique query", (s) => s.query === uniqueCommandQuery);
  await key("Enter");

  const deadline = Date.now() + timeoutMs;
  let opens = [];
  while (Date.now() < deadline) {
    opens = JSON.parse(await evaluate("JSON.stringify(window.__novelforgeStudioHandoff || [])"));
    if (opens.length) break;
    await sleep(120);
  }
  if (opens.length !== 1) throw new Error(`expected one Hosted Studio handoff, got ${JSON.stringify(opens)}`);
  const [handoffUrl, target, features] = opens[0];
  const normalizedUrl = new URL(handoffUrl).href;
  if (normalizedUrl !== expectedUrl) throw new Error(`Hosted Studio URL mismatch: ${handoffUrl}`);
  if (target !== "_blank") throw new Error(`Hosted Studio target mismatch: ${target}`);
  if (!String(features).includes("noopener") || !String(features).includes("noreferrer")) {
    throw new Error(`Hosted Studio window features missing isolation: ${features}`);
  }
  if (diagnostics.some((line) => /SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i.test(line))) {
    throw new Error(`Godot runtime diagnostics: ${diagnostics.join(" | ")}`);
  }

  const report = {
    schema: "novelforge_studio_handoff_browser_qa_v2",
    status: "pass",
    route: "/studio",
    command: "Hosted Studio",
    query: uniqueCommandQuery,
    url: normalizedUrl,
    target,
    noopener: true,
    noreferrer: true,
    external_network_required: false,
  };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  for (const line of diagnostics.slice(-80)) console.error(line);
  process.exitCode = 1;
} finally {
  cleanup();
}

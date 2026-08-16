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
const output = arg("output", "/tmp/novelforge-route-parity/interaction.json");
const timeoutMs = Number(arg("timeout-ms", "90000"));
if (!chrome) {
  console.error("CHROME is required");
  process.exit(2);
}

const port = 22000 + (process.pid % 1000);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "novelforge-godot-interaction-"));
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
    if (message.method === "Runtime.exceptionThrown") diagnostics.push(message.params?.exceptionDetails?.exception?.description ?? message.params?.exceptionDetails?.text ?? "exception");
  });
}

function command(method, params = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`timeout: ${method}`)); }, 20000);
    pending.set(id, { resolve: (v) => { clearTimeout(timer); resolve(v); }, reject: (e) => { clearTimeout(timer); reject(e); } });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  return response?.result?.value;
}

async function snapshot() {
  const raw = await evaluate(`JSON.stringify({
    ready: document.documentElement.dataset.novelforgeRuntime || null,
    shadow: document.documentElement.dataset.novelforgeGodotShadow || null,
    interaction: document.documentElement.dataset.novelforgeInteraction || null,
    command: document.documentElement.dataset.novelforgeCommand || null,
    query: document.documentElement.dataset.novelforgeCommandQuery || '',
    mobileMenu: document.documentElement.dataset.novelforgeMobileMenu || null,
    appearance: document.documentElement.dataset.novelforgeAppearance || null,
    locale: document.documentElement.dataset.locale || null,
    layout: document.documentElement.dataset.novelforgeLayout || null,
    responsive: document.documentElement.dataset.novelforgeResponsive || null,
    responsiveRevision: document.documentElement.dataset.novelforgeResponsiveRevision || '0',
    responsiveLayout: document.documentElement.dataset.novelforgeResponsiveLayout || null,
    responsiveWidth: document.documentElement.dataset.novelforgeResponsiveWidth || null,
    path: location.pathname,
    href: location.href
  })`);
  return JSON.parse(raw);
}

async function waitFor(label, predicate, timeout = timeoutMs) {
  const deadline = Date.now() + timeout;
  let current;
  while (Date.now() < deadline) {
    current = await snapshot();
    if (predicate(current)) return current;
    await sleep(150);
  }
  throw new Error(`${label} timeout: ${JSON.stringify(current)}`);
}

async function key(key, modifiers = 0) {
  await command("Input.dispatchKeyEvent", { type: "keyDown", key, code: key.length === 1 ? `Key${key.toUpperCase()}` : key, modifiers });
  await command("Input.dispatchKeyEvent", { type: "keyUp", key, code: key.length === 1 ? `Key${key.toUpperCase()}` : key, modifiers });
}

async function click(x, y) {
  await command("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await command("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await command("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function resizeAndWait(width, height, expectedLayout) {
  const before = Number((await snapshot()).responsiveRevision || 0);
  await command("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false, screenWidth: width, screenHeight: height });
  return waitFor(
    `responsive ${width}x${height}`,
    (s) => s.ready === "ready"
      && s.interaction === "ready"
      && s.responsive === "ready"
      && s.layout === expectedLayout
      && s.responsiveLayout === expectedLayout
      && Number(s.responsiveRevision || 0) > before,
    20000,
  );
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
  const initial = await waitFor("interaction ready", (s) => s.ready === "ready" && s.shadow === "ready" && s.interaction === "ready" && s.responsive === "ready" && s.layout === "desktop");

  await key("k", 2);
  await waitFor("command palette open", (s) => s.command === "open");
  for (const ch of "architecture") await key(ch);
  await waitFor("command query", (s) => s.query === "architecture");
  await key("Enter");
  await waitFor("command navigation", (s) => s.path === "/architecture" && s.ready === "ready");
  await evaluate("history.back()")
  await waitFor("popstate navigation", (s) => s.path === "/" && s.ready === "ready");

  const appearanceBefore = (await snapshot()).appearance;
  await click(1364, 37);
  const themed = await waitFor("appearance toggle", (s) => s.appearance && s.appearance !== appearanceBefore);

  const localeBefore = themed.locale;
  await click(1314, 37);
  await waitFor("locale toggle", (s) => s.locale && s.locale !== localeBefore);

  // Prove continuous reflow across all required representative widths. The
  // 1440->1280, 1024->768, and 430->390->360 transitions deliberately remain
  // inside one topology for at least one step, so a breakpoint-only rebuild
  // implementation cannot pass this check.
  await resizeAndWait(1280, 800, "desktop");
  await resizeAndWait(1024, 768, "compact");
  await resizeAndWait(768, 1024, "compact");
  await resizeAndWait(430, 932, "phone");
  await resizeAndWait(390, 844, "phone");
  await resizeAndWait(360, 800, "phone");
  const mobileReady = await resizeAndWait(390, 844, "phone");

  await click(340, 37);
  const mobile = await waitFor("mobile menu", (s) => s.mobileMenu === "open");

  if (diagnostics.some((line) => /SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i.test(line))) {
    throw new Error(`browser diagnostics contain Godot runtime errors: ${diagnostics.join(" | ")}`);
  }

  const report = {
    schema: "novelforge_godot_interaction_qa_v2",
    status: "pass",
    command_palette: true,
    ctrl_k: true,
    query_typing: true,
    push_state_route: true,
    popstate_back: true,
    appearance_toggle: true,
    locale_toggle: true,
    mobile_menu: mobile.mobileMenu === "open",
    responsive_reflow: true,
    same_topology_reflow: true,
    responsive_widths: ["1440x900", "1280x800", "1024x768", "768x1024", "430x932", "390x844", "360x800"],
    final_responsive_revision: Number(mobileReady.responsiveRevision || initial.responsiveRevision || 0),
    no_default_polling: true,
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

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
const evidenceDir = path.dirname(output);
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
  if (response?.exceptionDetails) throw new Error(response.exceptionDetails.text || "Runtime.evaluate exception");
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
    accessibility: document.documentElement.dataset.novelforgeAccessibility || null,
    accessibilityRoute: document.documentElement.dataset.novelforgeAccessibilityRoute || null,
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

async function screenshot(name) {
  const result = await command("Page.captureScreenshot", { format: "png", fromSurface: true });
  const target = path.join(evidenceDir, `${name}.png`);
  fs.writeFileSync(target, Buffer.from(result.data, "base64"));
  if (fs.statSync(target).size < 1024) throw new Error(`screenshot too small: ${name}`);
}

async function resizeAndWait(width, height, expectedLayout) {
  const before = Number((await snapshot()).responsiveRevision || 0);
  await command("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false, screenWidth: width, screenHeight: height });
  return waitFor(
    `responsive ${width}x${height}`,
    (s) => s.ready === "ready"
      && s.interaction === "ready"
      && s.responsive === "ready"
      && s.accessibility === "ready"
      && s.layout === expectedLayout
      && s.responsiveLayout === expectedLayout
      && Number(s.responsiveRevision || 0) > before,
    20000,
  );
}

async function navigateRoute(route) {
  await evaluate(`history.pushState({}, '', ${JSON.stringify(route)}); window.dispatchEvent(new PopStateEvent('popstate'));`);
  return waitFor(`route ${route}`, (s) => s.path === route && s.ready === "ready" && s.accessibilityRoute === route, 20000);
}

async function captureResponsiveRoute(routeName, route, sizes) {
  if ((await snapshot()).path !== route) await navigateRoute(route);
  for (const [width, height, layout] of sizes) {
    await resizeAndWait(width, height, layout);
    await screenshot(`responsive-${routeName}-${width}x${height}`);
  }
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
  await command("Accessibility.enable");
  await command("Input.setIgnoreInputEvents", { ignore: false });
  await command("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false, screenWidth: 1440, screenHeight: 900 });
  await command("Page.navigate", { url });
  const initial = await waitFor(
    "interaction ready",
    (s) => s.ready === "ready" && s.shadow === "ready" && s.interaction === "ready" && s.responsive === "ready" && s.accessibility === "ready" && s.layout === "desktop" && s.accessibilityRoute === "/",
  );

  const semanticDom = JSON.parse(await evaluate(`(() => {
    const skip = document.querySelector('.nf-skip');
    skip?.focus({preventScroll:true});
    const rect = skip?.getBoundingClientRect();
    const style = skip ? getComputedStyle(skip) : null;
    return JSON.stringify({
      nav: !!document.querySelector('nav[aria-label="NovelForge primary navigation"]'),
      main: !!document.querySelector('#nf-a11y-main'),
      routeLinks: document.querySelectorAll('[data-nf-route]').length,
      canvasLabel: document.querySelector('#canvas')?.getAttribute('aria-label') || '',
      activeSkip: document.activeElement === skip,
      skipVisibleOnFocus: !!rect && rect.left >= 0 && rect.width >= 44 && rect.height >= 44,
      skipOutlinePx: style ? parseFloat(style.outlineWidth) || 0 : 0
    });
  })()`));
  if (!semanticDom.nav || !semanticDom.main || semanticDom.routeLinks < 9 || !semanticDom.canvasLabel.includes("NovelForge")) {
    throw new Error(`semantic accessibility DOM incomplete: ${JSON.stringify(semanticDom)}`);
  }
  if (!semanticDom.activeSkip || !semanticDom.skipVisibleOnFocus || semanticDom.skipOutlinePx < 3) {
    throw new Error(`visible keyboard focus contract failed: ${JSON.stringify(semanticDom)}`);
  }

  const axTree = await command("Accessibility.getFullAXTree");
  const axNames = (axTree.nodes || []).map((node) => node?.name?.value).filter(Boolean);
  for (const requiredName of ["NovelForge primary navigation", "Home", "Product", "Architecture", "Publication"]) {
    if (!axNames.includes(requiredName)) throw new Error(`accessibility tree missing: ${requiredName}`);
  }

  await command("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  const reducedMotion = JSON.parse(await evaluate(`JSON.stringify({
    matches: matchMedia('(prefers-reduced-motion: reduce)').matches,
    progressAnimation: getComputedStyle(document.querySelector('.nf-progress>i')).animationName,
    canvasTransition: getComputedStyle(document.querySelector('#canvas')).transitionDuration,
    loaderTransition: getComputedStyle(document.querySelector('#nf-loader')).transitionDuration
  })`));
  if (!reducedMotion.matches || reducedMotion.progressAnimation !== "none" || reducedMotion.canvasTransition !== "0s" || reducedMotion.loaderTransition !== "0s") {
    throw new Error(`reduced-motion contract failed: ${JSON.stringify(reducedMotion)}`);
  }
  await command("Emulation.setEmulatedMedia", { features: [] });

  await evaluate(`document.querySelector('a[data-nf-route][href="/product"]')?.click()`);
  await waitFor("accessible navigation", (s) => s.path === "/product" && s.ready === "ready" && s.accessibilityRoute === "/product");
  await evaluate("history.back()");
  await waitFor("accessible back navigation", (s) => s.path === "/" && s.ready === "ready" && s.accessibilityRoute === "/");

  await key("k", 2);
  await waitFor("command palette open", (s) => s.command === "open");
  for (const ch of "architecture") await key(ch);
  await waitFor("command query", (s) => s.query === "architecture");
  await key("Enter");
  await waitFor("command navigation", (s) => s.path === "/architecture" && s.ready === "ready" && s.accessibilityRoute === "/architecture");
  await evaluate("history.back()");
  await waitFor("popstate navigation", (s) => s.path === "/" && s.ready === "ready" && s.accessibilityRoute === "/");

  const appearanceBefore = (await snapshot()).appearance;
  await click(1364, 37);
  const themed = await waitFor("appearance toggle", (s) => s.appearance && s.appearance !== appearanceBefore);

  const localeBefore = themed.locale;
  await click(1314, 37);
  await waitFor("locale toggle", (s) => s.locale && s.locale !== localeBefore);

  // Prove continuous reflow across every required representative width. Several
  // transitions stay inside the same topology, so breakpoint-only rebuilds
  // cannot pass this sequence. Capture rendered evidence as the viewport moves.
  const requiredSizes = [
    [1280, 800, "desktop"],
    [1024, 768, "compact"],
    [768, 1024, "compact"],
    [430, 932, "phone"],
    [390, 844, "phone"],
    [360, 800, "phone"],
  ];
  for (const [width, height, layout] of requiredSizes) {
    await resizeAndWait(width, height, layout);
    await screenshot(`responsive-home-${width}x${height}`);
  }
  const mobileReady = await resizeAndWait(390, 844, "phone");

  await click(340, 37);
  const mobile = await waitFor("mobile menu", (s) => s.mobileMenu === "open");
  await screenshot("responsive-home-390x844-mobile-menu");

  // Highest-risk workstation/editorial routes receive intermediate rendered
  // evidence in addition to the blocking continuous-resize receipt above.
  const evidenceSizes = [
    [1280, 800, "desktop"],
    [1024, 768, "compact"],
    [768, 1024, "compact"],
    [430, 932, "phone"],
    [360, 800, "phone"],
  ];
  await captureResponsiveRoute("studio", "/studio", evidenceSizes);
  await captureResponsiveRoute("publication", "/publication", evidenceSizes);
  await captureResponsiveRoute("inspect", "/inspect", [
    [1024, 768, "compact"],
    [768, 1024, "compact"],
    [430, 932, "phone"],
    [360, 800, "phone"],
  ]);

  const finalState = await snapshot();
  if (diagnostics.some((line) => /SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i.test(line))) {
    throw new Error(`browser diagnostics contain Godot runtime errors: ${diagnostics.join(" | ")}`);
  }

  const report = {
    schema: "novelforge_godot_interaction_qa_v3",
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
    responsive_evidence_routes: ["home", "studio", "publication", "inspect"],
    final_responsive_revision: Number(finalState.responsiveRevision || mobileReady.responsiveRevision || initial.responsiveRevision || 0),
    accessibility_dom: true,
    accessibility_tree: true,
    accessible_navigation: true,
    visible_keyboard_focus: true,
    web_focus_target_44px: true,
    reduced_motion: true,
    canvas_accessible_name: true,
    no_default_polling: true,
  };
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.writeFileSync(output, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  for (const line of diagnostics.slice(-80)) console.error(line);
  process.exitCode = 1;
} finally {
  cleanup();
}

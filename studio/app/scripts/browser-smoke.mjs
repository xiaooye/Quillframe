import fs from "node:fs";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { chromium } from "playwright-core";

const root = process.cwd();
const host = "127.0.0.1";
const port = 4173;
const origin = `http://${host}:${port}`;
const evidenceDir = process.env.QF_BROWSER_EVIDENCE_DIR || "/tmp/quillframe-browser-evidence";
const candidates = [
  process.env.CHROME_BIN,
  chromium.executablePath(),
  "google-chrome",
  "google-chrome-stable",
  "chromium",
  "chromium-browser",
].filter(Boolean);

function executable(candidate) {
  if (path.isAbsolute(candidate) && fs.existsSync(candidate)) return candidate;
  const result = spawnSync("which", [candidate], { encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : "";
}

const chrome = candidates.map(executable).find(Boolean);
if (!chrome) {
  if (process.env.CI) {
    console.error("browser_smoke=FAIL: no Chrome/Chromium executable on CI runner");
    process.exit(1);
  }
  console.log("browser_smoke=SKIP: no Chrome/Chromium executable found locally");
  process.exit(0);
}

fs.mkdirSync(evidenceDir, { recursive: true });
const preview = spawn(
  "corepack",
  ["pnpm", "exec", "vite", "preview", "--host", host, "--port", String(port), "--strictPort"],
  { cwd: root, stdio: ["ignore", "pipe", "pipe"], env: process.env },
);
let previewLog = "";
preview.stdout.on("data", (chunk) => { previewLog += String(chunk); });
preview.stderr.on("data", (chunk) => { previewLog += String(chunk); });

const cleanup = () => {
  if (!preview.killed) preview.kill("SIGTERM");
};
process.on("exit", cleanup);
process.on("SIGINT", () => { cleanup(); process.exit(130); });
process.on("SIGTERM", () => { cleanup(); process.exit(143); });

async function waitForPreview() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (preview.exitCode !== null) throw new Error(`vite preview exited early (${preview.exitCode})\n${previewLog}`);
    try {
      const response = await fetch(origin, { redirect: "manual" });
      if (response.ok) return;
    } catch {
      // Startup race.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`vite preview did not become ready\n${previewLog}`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function assertRoute(page, route, marker) {
  await page.goto(`${origin}${route}`, { waitUntil: "networkidle" });
  const bodyText = await page.locator("body").innerText();
  assert(bodyText.includes(marker), `Studio route ${route} did not render ${marker}`);
  assert(!bodyText.includes("Studio crashed") && !bodyText.includes("Unexpected bridge result schema"), `Studio route ${route} rendered a fatal error`);
  assert(await page.locator("main#main-content").count() === 1, `Studio route ${route} must expose one main landmark`);
  return bodyText;
}

let browser;
try {
  await waitForPreview();
  browser = await chromium.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await assertRoute(page, "/", "DESK");
  const manuscript = await assertRoute(page, "/manuscript", "MANUSCRIPT");
  assert(manuscript.includes("Core unbound") || manuscript.includes("Core 未绑定"), "Unbound Manuscript route must render truthful Core state");
  await assertRoute(page, "/review", "REVIEW");
  await assertRoute(page, "/context", "CONTEXT INSPECTOR");
  await assertRoute(page, "/settings?section=models", "Endpoint + Access Token");
  assert(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), "Reduced-motion preference was not applied");

  await page.goto(origin, { waitUntil: "networkidle" });
  const advanced = page.locator(".qf-inspector-disclosure");
  assert(await advanced.getAttribute("aria-expanded") === "false", "Advanced navigation must be collapsed by default");
  await advanced.click();
  assert(await advanced.getAttribute("aria-expanded") === "true", "Advanced navigation disclosure did not open");
  assert(await page.locator('[data-nav-tier="advanced"]').isVisible(), "Advanced navigation did not become visible");

  const accessibilityIssues = await page.evaluate(() => {
    const issues = [];
    for (const image of document.querySelectorAll('img')) {
      if (!image.hasAttribute('alt')) issues.push('Image without alt attribute');
    }
    for (const button of document.querySelectorAll('button')) {
      if (!(button instanceof HTMLElement) || button.offsetParent === null) continue;
      const name = button.getAttribute('aria-label') || button.getAttribute('title') || button.textContent?.trim();
      if (!name) issues.push('Visible button without accessible name');
    }
    return issues;
  });
  assert(accessibilityIssues.length === 0, `Studio accessibility smoke failed: ${accessibilityIssues.join('; ')}`);
  await page.screenshot({ path: path.join(evidenceDir, "studio-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await assertRoute(page, "/manuscript", "MANUSCRIPT");
  assert(await page.locator(".qf-writer-bottom-nav").isVisible(), "Phone Manuscript route did not expose mobile Writer navigation");
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "Studio overflows the phone viewport");
  await page.screenshot({ path: path.join(evidenceDir, "studio-phone.png"), fullPage: true });

  const darkContext = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: "dark" });
  const darkPage = await darkContext.newPage();
  await assertRoute(darkPage, "/manuscript", "MANUSCRIPT");
  assert(await darkPage.locator("html").evaluate((node) => node.classList.contains("dark")), "Dark preference did not activate documentElement.dark");
  assert(await darkPage.getByRole("button", { name: /Toggle theme|切换主题/ }).count() === 1, "Dark Studio must retain an accessible theme toggle");
  await darkPage.screenshot({ path: path.join(evidenceDir, "studio-dark.png"), fullPage: true });
  await darkContext.close();

  assert(pageErrors.length === 0, `Studio emitted browser errors: ${pageErrors.join('; ')}`);
  console.log("browser_smoke=PASS");
  console.log("browser_routes=desk,manuscript,review,context,ai-models,advanced,manuscript-phone,manuscript-dark");
  console.log(`browser_evidence=${evidenceDir}`);
} catch (error) {
  console.error(`browser_smoke=FAIL: ${error instanceof Error ? error.stack || error.message : String(error)}`);
  process.exitCode = 1;
} finally {
  await browser?.close();
  cleanup();
}

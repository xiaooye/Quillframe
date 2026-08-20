import fs from "node:fs";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { chromium } from "playwright-core";

const root = process.cwd();
const host = "127.0.0.1";
const port = 4174;
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

let browser;
try {
  await waitForPreview();
  browser = await chromium.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const pageErrors = [];
  const writeRequests = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (!['GET', 'HEAD'].includes(request.method())) writeRequests.push(`${request.method()} ${request.url()}`);
  });

  await page.goto(origin, { waitUntil: "networkidle" });
  assert(await page.locator('[data-home-section]').count() === 6, "Homepage must render exactly six product sections");
  assert(await page.locator('#quick-demo').count() === 1, "Homepage Quick Demo is missing");
  assert(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), "Reduced-motion preference was not applied");

  const accessibilityIssues = await page.evaluate(() => {
    const issues = [];
    if (document.querySelectorAll('main').length !== 1) issues.push('Homepage must expose exactly one main landmark');
    for (const image of document.querySelectorAll('img')) {
      if (!image.hasAttribute('alt')) issues.push('Image without alt attribute');
    }
    for (const button of document.querySelectorAll('button')) {
      const name = button.getAttribute('aria-label') || button.getAttribute('title') || button.textContent?.trim();
      if (!name) issues.push('Button without accessible name');
    }
    return issues;
  });
  assert(accessibilityIssues.length === 0, `Homepage accessibility smoke failed: ${accessibilityIssues.join('; ')}`);

  await page.screenshot({ path: path.join(evidenceDir, 'home-desktop.png'), fullPage: true });
  await page.locator('.quick-demo-run').click();
  await page.locator('.quick-demo-result').waitFor({ state: 'visible', timeout: 45000 });
  const receiptText = await page.locator('.quick-demo-result').innerText();
  assert(receiptText.includes('PASS'), 'Quick Demo deterministic Core did not pass');
  assert(receiptText.includes('FIXTURE'), 'Quick Demo did not truth-label recorded semantic evidence');
  assert(receiptText.includes('SAFE'), 'Quick Demo truth boundary did not render');
  assert(receiptText.includes('model=false · uploads=0 · canon=false'), 'Quick Demo receipt crossed its no-model/no-upload/no-Canon boundary');
  assert(writeRequests.length === 0, `Quick Demo emitted network writes: ${writeRequests.join(', ')}`);
  assert(pageErrors.length === 0, `Homepage emitted browser errors: ${pageErrors.join('; ')}`);
  await page.screenshot({ path: path.join(evidenceDir, 'home-demo-complete.png'), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(origin, { waitUntil: 'networkidle' });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'Homepage overflows the phone viewport');
  const demoButtonBox = await page.locator('.quick-demo-run').boundingBox();
  assert(Boolean(demoButtonBox && demoButtonBox.height >= 44), 'Quick Demo phone touch target is smaller than 44px');
  await page.screenshot({ path: path.join(evidenceDir, 'home-phone.png'), fullPage: true });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`${origin}/docs/`, { waitUntil: 'networkidle' });
  assert((await page.title()).includes('Quillframe'), 'Built Docs route did not render Quillframe identity');
  assert(await page.locator('main').count() === 1, 'Built Docs route must expose one main landmark');
  await page.screenshot({ path: path.join(evidenceDir, 'docs-desktop.png'), fullPage: true });

  console.log('browser_smoke=PASS');
  console.log('browser_routes=home,quick-demo,home-phone,docs');
  console.log(`browser_evidence=${evidenceDir}`);
} catch (error) {
  console.error(`browser_smoke=FAIL: ${error instanceof Error ? error.stack || error.message : String(error)}`);
  process.exitCode = 1;
} finally {
  await browser?.close();
  cleanup();
}

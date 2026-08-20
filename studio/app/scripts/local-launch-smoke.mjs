import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";
import { chromium } from "playwright-core";

const repositoryRoot = fileURLToPath(new URL("../../..", import.meta.url));
const evidenceDir = process.env.QF_BROWSER_EVIDENCE_DIR || "/tmp/quillframe-browser-evidence";
const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), "quillframe-launch-browser-"));
const projectRoot = path.join(temporaryRoot, "novel");
const statePath = path.join(temporaryRoot, "launch-state.json");
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
  fs.rmSync(temporaryRoot, { recursive: true, force: true });
  if (process.env.CI) {
    console.error("local_launch_smoke=FAIL: no Chrome/Chromium executable on CI runner");
    process.exit(1);
  }
  console.log("local_launch_smoke=SKIP: no Chrome/Chromium executable found locally");
  process.exit(0);
}

fs.mkdirSync(evidenceDir, { recursive: true });
const launched = spawn(
  process.env.PYTHON || "python",
  [
    "-u", "-m", "quillframe.cli", "launch", projectRoot, "--new",
    "--profile", "local", "--id", "browser-e2e", "--title", "Browser E2E Novel",
    "--language", "en", "--port", "0", "--no-browser", "--json",
  ],
  {
    cwd: repositoryRoot,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, QUILLFRAME_LAUNCH_STATE: statePath },
  },
);
let stderr = "";
launched.stderr.on("data", (chunk) => { stderr += String(chunk); });

function waitForReceipt() {
  return new Promise((resolve, reject) => {
    let buffer = "";
    const timer = setTimeout(() => reject(new Error(`launch receipt timed out\n${stderr}`)), 15000);
    launched.stdout.on("data", (chunk) => {
      buffer += String(chunk);
      for (const line of buffer.split("\n")) {
        if (!line.trim()) continue;
        try {
          const value = JSON.parse(line);
          if (value.schema === "quillframe_launch_receipt_v1") {
            clearTimeout(timer);
            resolve(value);
            return;
          }
        } catch {
          // Wait for a complete JSON line.
        }
      }
    });
    launched.once("exit", (code) => {
      clearTimeout(timer);
      reject(new Error(`quillframe launch exited before serving (${code})\n${stderr}`));
    });
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

let browser;
try {
  const receipt = await waitForReceipt();
  assert(receipt.status === "ready" && receipt.profile === "local", "Local launch did not become ready");
  assert(receipt.storage_boundary === "project_local_sqlite", "Local launch escaped project-local persistence");
  assert(receipt.cloud_upload_started === false, "Local launch attempted a cloud upload");
  const serialized = JSON.stringify(receipt).toLowerCase();
  assert(!serialized.includes("token") && !serialized.includes("secret"), "Launch receipt exposed a transport secret");

  browser = await chromium.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto(receipt.url, { waitUntil: "networkidle" });
  const bodyText = await page.locator("body").innerText();
  assert(bodyText.includes("Core bound") || bodyText.includes("Core 已绑定"), "Launched Studio did not bind its loopback Core");
  await page.goto(new URL("/start", receipt.url).href, { waitUntil: "networkidle" });
  assert((await page.locator("body").innerText()).includes("Browser E2E Novel"), "Launched Studio did not read the new Project from Core");
  assert(pageErrors.length === 0, `Launched Studio emitted browser errors: ${pageErrors.join('; ')}`);
  await page.screenshot({ path: path.join(evidenceDir, "local-launch-bound.png"), fullPage: true });

  console.log("local_launch_smoke=PASS");
  console.log("local_launch_profile=local");
  console.log("local_launch_core_bound=true");
  console.log("local_launch_cloud_upload_started=false");
} catch (error) {
  console.error(`local_launch_smoke=FAIL: ${error instanceof Error ? error.stack || error.message : String(error)}`);
  process.exitCode = 1;
} finally {
  await browser?.close();
  if (launched.exitCode === null) launched.kill("SIGTERM");
  fs.rmSync(temporaryRoot, { recursive: true, force: true });
}

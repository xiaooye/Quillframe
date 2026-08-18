import { spawn, spawnSync } from "node:child_process";

const host = "127.0.0.1";
const port = 4173;
const origin = `http://${host}:${port}`;
const candidates = [process.env.CHROME_BIN, "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"].filter(Boolean);

function executable(name) {
  const result = spawnSync("which", [name], { encoding: "utf8" });
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

const preview = spawn("pnpm", ["exec", "vite", "preview", "--host", host, "--port", String(port), "--strictPort"], {
  stdio: ["ignore", "pipe", "pipe"],
  env: process.env,
});
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
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (preview.exitCode !== null) throw new Error(`vite preview exited early (${preview.exitCode})\n${previewLog}`);
    try {
      const response = await fetch(origin, { redirect: "manual" });
      if (response.ok) return;
    } catch {
      // Startup race; retry below.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`vite preview did not become ready\n${previewLog}`);
}

function dumpDom(path, windowSize = "1280,900") {
  const result = spawnSync(chrome, [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    `--window-size=${windowSize}`,
    "--virtual-time-budget=1500",
    "--dump-dom",
    `${origin}${path}`,
  ], { encoding: "utf8", timeout: 25000, maxBuffer: 12 * 1024 * 1024 });
  if (result.status !== 0) throw new Error(`Chrome failed for ${path}: ${result.stderr || result.error || result.status}`);
  return result.stdout;
}

function assertRendered(path, markers, windowSize) {
  const dom = dumpDom(path, windowSize);
  const acceptable = Array.isArray(markers) ? markers : [markers];
  if (!acceptable.some((marker) => dom.includes(marker))) {
    throw new Error(`browser route ${path} did not render any marker: ${acceptable.join(" | ")}`);
  }
  if (dom.includes("Studio crashed") || dom.includes("Unexpected bridge result schema")) {
    throw new Error(`browser route ${path} rendered a fatal Studio/Bridge error`);
  }
  return dom;
}

try {
  await waitForPreview();
  assertRendered("/", "DESK");
  const manuscriptDesktop = assertRendered("/manuscript", "MANUSCRIPT");
  if (!manuscriptDesktop.includes("Core unbound") && !manuscriptDesktop.includes("Core 未绑定")) {
    throw new Error("unbound Manuscript route must render truthful Core-unbound state");
  }
  assertRendered("/review", "REVIEW");
  assertRendered("/context", "CONTEXT INSPECTOR");
  assertRendered("/settings?section=models", "Endpoint + Access Token");
  const manuscriptPhone = assertRendered("/manuscript", "MANUSCRIPT", "390,844");
  if (!manuscriptPhone.includes("qf-writer-bottom-nav")) throw new Error("phone Manuscript route did not render mobile Writer navigation");
  console.log("browser_smoke=PASS");
  console.log("browser_routes=desk,manuscript,review,context,ai-models,manuscript-phone");
} catch (error) {
  console.error(`browser_smoke=FAIL: ${error instanceof Error ? error.stack || error.message : String(error)}`);
  process.exitCode = 1;
} finally {
  cleanup();
}

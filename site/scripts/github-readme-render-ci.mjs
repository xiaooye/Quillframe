import fs from "node:fs";
import { chromium } from "playwright-core";

const targetBranch = "system-improve/quillframe-repo-polish";
if (process.env.GITHUB_EVENT_NAME !== "pull_request" || process.env.GITHUB_HEAD_REF !== targetBranch) {
  console.log("github-readme-render-ci: skipped outside repository-polish PR");
  process.exit(0);
}

const repo = process.env.GITHUB_REPOSITORY;
const eventPath = process.env.GITHUB_EVENT_PATH;
if (!repo || !eventPath) throw new Error("missing GitHub Actions repository/event context");
const event = JSON.parse(fs.readFileSync(eventPath, "utf8"));
const headSha = event?.pull_request?.head?.sha;
if (!headSha) throw new Error("cannot resolve pull_request.head.sha");

const executablePath = [
  process.env.CHROME_BIN,
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium-browser",
  "/usr/bin/chromium",
].find((candidate) => candidate && fs.existsSync(candidate));
if (!executablePath) throw new Error("GitHub runner Chrome/Chromium executable not found");

const url = `https://github.com/${repo}/tree/${headSha}`;
const cases = [
  { id: "desktop-light", width: 1440, height: 1000, scheme: "light" },
  { id: "desktop-dark", width: 1440, height: 1000, scheme: "dark" },
  { id: "narrow-light", width: 390, height: 844, scheme: "light" },
  { id: "narrow-dark", width: 390, height: 844, scheme: "dark" },
];

function luminance(css) {
  const match = css.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (!match) return null;
  return (Number(match[1]) * 0.2126 + Number(match[2]) * 0.7152 + Number(match[3]) * 0.0722) / 255;
}

function emitScreenshot(id, buffer) {
  const encoded = buffer.toString("base64");
  const chunkSize = 3500;
  const chunks = Math.ceil(encoded.length / chunkSize);
  console.log(`QF_README_SCREENSHOT_BEGIN ${id} image/jpeg chunks=${chunks}`);
  for (let index = 0; index < chunks; index += 1) {
    console.log(`QF_README_SCREENSHOT ${id} ${index + 1}/${chunks} ${encoded.slice(index * chunkSize, (index + 1) * chunkSize)}`);
  }
  console.log(`QF_README_SCREENSHOT_END ${id}`);
}

const browser = await chromium.launch({ headless: true, executablePath, args: ["--no-sandbox"] });
const report = {
  schema: "quillframe_github_readme_render_qa_v1",
  repository: repo,
  head_sha: headSha,
  url,
  captured_at: new Date().toISOString(),
  cases: [],
};
let failed = false;

try {
  for (const item of cases) {
    const context = await browser.newContext({
      viewport: { width: item.width, height: item.height },
      colorScheme: item.scheme,
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
    if (!response || !response.ok()) throw new Error(`${item.id}: GitHub returned ${response ? response.status() : "no response"}`);

    await page.locator("article.markdown-body").first().waitFor({ state: "visible", timeout: 30_000 });
    // GitHub can replace the README node once after the initial document load.
    // Scroll through a fresh DOM query instead of retaining an element handle.
    await page.waitForTimeout(1500);
    await page.evaluate(() => document.querySelector("article.markdown-body")?.scrollIntoView({ block: "start" }));
    await page.waitForTimeout(400);

    const readme = page.locator("article.markdown-body").first();
    await readme.waitFor({ state: "visible", timeout: 10_000 });
    const metrics = await readme.evaluate((el) => {
      const images = [...el.querySelectorAll("img")];
      const bounds = el.getBoundingClientRect();
      const text = (el.textContent || "").trim();
      const bodyStyle = getComputedStyle(document.body);
      const rootStyle = getComputedStyle(document.documentElement);
      return {
        article_width: Math.round(bounds.width),
        article_scroll_width: Math.round(el.scrollWidth),
        viewport_width: window.innerWidth,
        viewport_scroll_width: document.documentElement.scrollWidth,
        broken_images: images.filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src),
        oversized_images: images.filter((img) => img.getBoundingClientRect().width > bounds.width + 1).map((img) => ({ src: img.currentSrc || img.src, width: Math.round(img.getBoundingClientRect().width) })),
        headings: el.querySelectorAll("h1,h2,h3").length,
        links: el.querySelectorAll("a").length,
        text_chars: text.length,
        has_product_name: text.includes("Quillframe"),
        has_quick_start: text.includes("Quick Start"),
        has_license: text.includes("License"),
        body_background: bodyStyle.backgroundColor,
        root_background: rootStyle.backgroundColor,
        color_mode: document.documentElement.getAttribute("data-color-mode"),
        light_theme: document.documentElement.getAttribute("data-light-theme"),
        dark_theme: document.documentElement.getAttribute("data-dark-theme"),
      };
    });

    metrics.article_overflow = metrics.article_scroll_width > metrics.article_width + 1;
    metrics.page_overflow = metrics.viewport_scroll_width > metrics.viewport_width + 1;
    metrics.requested_color_scheme = item.scheme;
    metrics.background_luminance = luminance(metrics.body_background) ?? luminance(metrics.root_background);
    metrics.complete_readme = Boolean(metrics.has_product_name && metrics.has_quick_start && metrics.has_license && metrics.headings >= 10 && metrics.text_chars >= 5000);

    if (metrics.broken_images.length || metrics.oversized_images.length || metrics.article_overflow || !metrics.complete_readme) failed = true;

    const screenshot = await page.screenshot({ type: "jpeg", quality: 38, fullPage: false, animations: "disabled" });
    emitScreenshot(item.id, screenshot);
    report.cases.push({ id: item.id, ...metrics });
    await context.close();
  }

  const light = report.cases.find((item) => item.id === "desktop-light");
  const dark = report.cases.find((item) => item.id === "desktop-dark");
  report.theme_distinction = Boolean(light && dark && light.background_luminance != null && dark.background_luminance != null && Math.abs(light.background_luminance - dark.background_luminance) >= 0.2);
  if (!report.theme_distinction) failed = true;

  console.log(`QF_README_RENDER_REPORT ${JSON.stringify(report)}`);
  console.log(`github-readme-render-ci: ${failed ? "FAIL" : "PASS"}`);
  if (failed) process.exitCode = 1;
} finally {
  await browser.close();
}

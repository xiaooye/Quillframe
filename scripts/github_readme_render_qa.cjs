#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const repo = process.env.README_REPO;
const sha = process.env.README_SHA;
const root = process.env.README_QA_DIR;
if (!repo || !sha || !root) {
  throw new Error("README_REPO, README_SHA and README_QA_DIR are required");
}

const out = path.join(root, "evidence");
fs.mkdirSync(out, { recursive: true });
const url = `https://github.com/${repo}/tree/${sha}`;

const cases = [
  { id: "desktop-light", width: 1440, height: 1100, scheme: "light" },
  { id: "desktop-dark", width: 1440, height: 1100, scheme: "dark" },
  { id: "narrow-light", width: 390, height: 844, scheme: "light" },
  { id: "narrow-dark", width: 390, height: 844, scheme: "dark" },
];

function luminance(css) {
  const match = css.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (!match) return null;
  return (Number(match[1]) * 0.2126 + Number(match[2]) * 0.7152 + Number(match[3]) * 0.0722) / 255;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const report = {
    schema: "quillframe_github_readme_render_qa_v1",
    repository: repo,
    sha,
    url,
    captured_at: new Date().toISOString(),
    cases: [],
  };

  let failed = false;
  for (const item of cases) {
    const context = await browser.newContext({
      viewport: { width: item.width, height: item.height },
      colorScheme: item.scheme,
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    if (!response || !response.ok()) {
      throw new Error(`${item.id}: GitHub returned ${response ? response.status() : "no response"}`);
    }

    const readme = page.locator("article.markdown-body").first();
    await readme.waitFor({ state: "visible", timeout: 30000 });
    await page.waitForTimeout(1200);

    const metrics = await readme.evaluate((el) => {
      const images = [...el.querySelectorAll("img")];
      const bounds = el.getBoundingClientRect();
      const bodyStyle = getComputedStyle(document.body);
      const rootStyle = getComputedStyle(document.documentElement);
      return {
        article_width: Math.round(bounds.width),
        article_scroll_width: Math.round(el.scrollWidth),
        viewport_width: window.innerWidth,
        viewport_scroll_width: document.documentElement.scrollWidth,
        broken_images: images.filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src),
        oversized_images: images
          .filter((img) => img.getBoundingClientRect().width > bounds.width + 1)
          .map((img) => ({ src: img.currentSrc || img.src, width: Math.round(img.getBoundingClientRect().width) })),
        headings: el.querySelectorAll("h1,h2,h3").length,
        links: el.querySelectorAll("a").length,
        text_chars: (el.textContent || "").trim().length,
        body_background: bodyStyle.backgroundColor,
        root_background: rootStyle.backgroundColor,
        html_color_mode: document.documentElement.getAttribute("data-color-mode"),
        html_light_theme: document.documentElement.getAttribute("data-light-theme"),
        html_dark_theme: document.documentElement.getAttribute("data-dark-theme"),
      };
    });

    metrics.article_overflow = metrics.article_scroll_width > metrics.article_width + 1;
    metrics.page_overflow = metrics.viewport_scroll_width > metrics.viewport_width + 1;
    metrics.requested_color_scheme = item.scheme;
    metrics.background_luminance = luminance(metrics.body_background) ?? luminance(metrics.root_background);

    if (metrics.broken_images.length || metrics.oversized_images.length || metrics.article_overflow) {
      failed = true;
    }

    const screenshot = path.join(out, `${item.id}.png`);
    await readme.screenshot({ path: screenshot, animations: "disabled" });
    report.cases.push({ id: item.id, screenshot: path.basename(screenshot), ...metrics });
    await context.close();
  }

  const light = report.cases.find((item) => item.id === "desktop-light");
  const dark = report.cases.find((item) => item.id === "desktop-dark");
  report.theme_distinction = Boolean(
    light && dark && light.background_luminance != null && dark.background_luminance != null &&
      Math.abs(light.background_luminance - dark.background_luminance) >= 0.2
  );
  if (!report.theme_distinction) failed = true;

  fs.writeFileSync(path.join(out, "report.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
  if (failed) process.exitCode = 1;
})().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});

#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const outputRoot = path.join(siteRoot, "dist", "docs");
const manifest = JSON.parse(fs.readFileSync(path.resolve(siteRoot, "../docs/documentation_manifest.json"), "utf8"));

const required = [
  path.join(outputRoot, "index.html"),
  path.join(outputRoot, "why-novelforge", "index.html"),
  path.join(outputRoot, "en", "index.html"),
  path.join(outputRoot, "en", "why-novelforge", "index.html"),
];

const missing = required.filter((file) => !fs.existsSync(file));
if (missing.length > 0) {
  for (const file of missing) console.error(`verify-starlight-build: missing ${path.relative(siteRoot, file)}`);
  process.exit(1);
}

function countHtml(directory) {
  let count = 0;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) count += countHtml(absolute);
    else if (entry.isFile() && entry.name.endsWith(".html")) count += 1;
  }
  return count;
}

const htmlPages = countHtml(outputRoot);
const expectedMinimum = manifest.documents.length * 2;
if (htmlPages < expectedMinimum) {
  console.error(`verify-starlight-build: expected at least ${expectedMinimum} HTML pages, found ${htmlPages}`);
  process.exit(1);
}

const sample = fs.readFileSync(path.join(outputRoot, "why-novelforge", "index.html"), "utf8");
if (!sample.includes("NovelForge") || !sample.includes("starlight")) {
  console.error("verify-starlight-build: why-novelforge is not recognizable as a Starlight document");
  process.exit(1);
}

for (const [label, file] of [
  ["zh-CN", path.join(outputRoot, "index.html")],
  ["English", path.join(outputRoot, "en", "index.html")],
]) {
  const landing = fs.readFileSync(file, "utf8");
  if (!landing.includes("data-nf-docs-home")) {
    console.error(`verify-starlight-build: ${label} docs root is not the curated landing page`);
    process.exit(1);
  }
}

console.log(JSON.stringify({
  schema: "novelforge_starlight_build_verification_v1",
  status: "pass",
  output: "site/dist/docs",
  html_pages: htmlPages,
  expected_localized_pages: expectedMinimum,
  curated_landing_pages: 2,
}, null, 2));

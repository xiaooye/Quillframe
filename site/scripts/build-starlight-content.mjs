#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const repoRoot = path.resolve(siteRoot, "..");
const docsRoot = path.join(siteRoot, "docs-site");
const contentRoot = path.join(docsRoot, "src", "content", "docs");
const publicAssetRoot = path.join(docsRoot, "public", "repo-assets");
const manifestPath = path.join(repoRoot, "docs", "documentation_manifest.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

const sourceToTarget = new Map();
for (const doc of manifest.documents) {
  sourceToTarget.set(doc.english.replaceAll("\\", "/"), { id: doc.id, locale: "en-US" });
  sourceToTarget.set(doc.chinese.replaceAll("\\", "/"), { id: doc.id, locale: "zh-CN" });
}

function stripFrontmatter(source) {
  const normalized = source.replace(/\r\n/g, "\n");
  if (!normalized.startsWith("---\n")) return normalized;
  const end = normalized.indexOf("\n---\n", 4);
  return end === -1 ? normalized : normalized.slice(end + 5);
}

function plainInline(value) {
  return value
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function extractTitle(source, fallback) {
  const match = source.match(/^#\s+(.+?)\s*$/m);
  return plainInline(match?.[1] ?? fallback);
}

function stripFirstH1(source) {
  return source.replace(/^\s*#\s+.+?\s*\n+/, "");
}

function extractDescription(source, fallback) {
  const withoutFences = source.replace(/```[\s\S]*?```/g, "");
  const blocks = withoutFences.split(/\n\s*\n/);
  for (const block of blocks) {
    const text = block.trim();
    if (!text || /^#{1,6}\s/.test(text) || /^[-*+]\s/.test(text) || /^\d+\.\s/.test(text) || /^>/.test(text) || /^\|/.test(text)) continue;
    const plain = plainInline(text.replace(/\n/g, " "));
    if (plain.length >= 24) return plain.slice(0, 220);
  }
  return fallback;
}

function pageHref(id, locale) {
  if (id === "docs-home") return locale === "en-US" ? "/docs/en/" : "/docs/";
  const suffix = `/${encodeURIComponent(id)}`;
  return locale === "en-US" ? `/docs/en${suffix}` : `/docs${suffix}`;
}

function splitHref(href) {
  const hashIndex = href.indexOf("#");
  const hash = hashIndex >= 0 ? href.slice(hashIndex) : "";
  const withoutHash = hashIndex >= 0 ? href.slice(0, hashIndex) : href;
  const queryIndex = withoutHash.indexOf("?");
  const query = queryIndex >= 0 ? withoutHash.slice(queryIndex) : "";
  const pathname = queryIndex >= 0 ? withoutHash.slice(0, queryIndex) : withoutHash;
  return { pathname, query, hash };
}

function resolveSourcePath(sourceDir, pathname) {
  try {
    return path.posix.normalize(path.posix.join(sourceDir, decodeURIComponent(pathname)));
  } catch {
    return path.posix.normalize(path.posix.join(sourceDir, pathname));
  }
}

function copyRelativeAsset(href, sourceDir) {
  if (/^(?:https?:|data:|#|\/)/i.test(href)) return null;
  const { pathname, query, hash } = splitHref(href);
  const resolved = resolveSourcePath(sourceDir, pathname);
  const absolute = path.join(repoRoot, ...resolved.split("/"));

  if (!fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) return null;

  const destination = path.join(publicAssetRoot, ...resolved.split("/"));
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(absolute, destination);
  const publicHref = `/docs/repo-assets/${resolved.split("/").map(encodeURIComponent).join("/")}`;
  return `${publicHref}${query}${hash}`;
}

function rewriteDocHref(href, sourceDir) {
  if (/^(?:https?:|mailto:|tel:|#|\/)/i.test(href)) return null;
  const { pathname, query, hash } = splitHref(href);
  if (!/\.md$/i.test(pathname)) return null;

  const resolved = resolveSourcePath(sourceDir, pathname);
  const target = sourceToTarget.get(resolved);
  if (!target) return null;
  return `${pageHref(target.id, target.locale)}${query}${hash}`;
}

function rewriteHtmlAttributes(source, sourceDir) {
  const withImages = source.replace(/<img\b[^>]*>/gi, (tag) => tag.replace(
    /\bsrc\s*=\s*(["'])([^"']+)\1/i,
    (attribute, quote, href) => {
      const rewritten = copyRelativeAsset(href, sourceDir);
      return rewritten ? `src=${quote}${rewritten}${quote}` : attribute;
    },
  ));

  return withImages.replace(/<a\b[^>]*>/gi, (tag) => tag.replace(
    /\bhref\s*=\s*(["'])([^"']+)\1/i,
    (attribute, quote, href) => {
      const rewritten = rewriteDocHref(href, sourceDir);
      return rewritten ? `href=${quote}${rewritten}${quote}` : attribute;
    },
  ));
}

function rewriteLinks(source, sourcePath) {
  const sourceDir = path.posix.dirname(sourcePath.replaceAll("\\", "/"));

  const rewrittenImages = source.replace(
    /!\[([^\]]*)\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g,
    (full, alt, href) => {
      const rewritten = copyRelativeAsset(href, sourceDir);
      return rewritten ? `![${alt}](${rewritten})` : full;
    },
  );

  const rewrittenLinks = rewrittenImages.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g, (full, label, href) => {
    const rewritten = rewriteDocHref(href, sourceDir);
    return rewritten ? `[${label}](${rewritten})` : full;
  });

  return rewriteHtmlAttributes(rewrittenLinks, sourceDir);
}

function destinationFor(id, locale) {
  return locale === "zh-CN"
    ? path.join(contentRoot, `${id}.md`)
    : path.join(contentRoot, "en", `${id}.md`);
}

function renderDocument(doc, sourcePath, locale) {
  const absolute = path.join(repoRoot, ...sourcePath.split("/"));
  if (!fs.existsSync(absolute)) {
    throw new Error(`documentation source missing: ${sourcePath}`);
  }

  let body = stripFrontmatter(fs.readFileSync(absolute, "utf8"));
  const title = extractTitle(body, doc.id);
  body = stripFirstH1(body);
  body = rewriteLinks(body, sourcePath).trim();
  const description = extractDescription(body, locale === "zh-CN" ? "Quillframe 文档。" : "Quillframe documentation.");
  const editUrl = `https://github.com/xiaooye/cn_webnovel_agent/blob/main/${sourcePath}`;

  return `---
title: ${JSON.stringify(title)}
description: ${JSON.stringify(description)}
editUrl: ${JSON.stringify(editUrl)}
---

${body}
`;
}

fs.rmSync(contentRoot, { recursive: true, force: true });
fs.rmSync(publicAssetRoot, { recursive: true, force: true });
fs.mkdirSync(contentRoot, { recursive: true });
fs.mkdirSync(publicAssetRoot, { recursive: true });

let generated = 0;
for (const doc of manifest.documents) {
  if (doc.id === "docs-home") continue;

  for (const [locale, sourcePath] of [["zh-CN", doc.chinese], ["en-US", doc.english]]) {
    const destination = destinationFor(doc.id, locale);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, renderDocument(doc, sourcePath, locale), "utf8");
    generated += 1;
  }
}

const landingPages = 2;
const expectedStagedDocuments = (manifest.documents.length - 1) * 2;
if (generated !== expectedStagedDocuments) {
  throw new Error(`Starlight staging mismatch: generated ${generated}, expected ${expectedStagedDocuments}`);
}

console.log(JSON.stringify({
  schema: "quillframe_starlight_content_v1",
  status: "pass",
  documents: manifest.documents.length,
  staged_markdown_pages: generated,
  custom_landing_pages: landingPages,
  localized_pages: generated + landingPages,
  root_locale: "zh-CN",
  secondary_locale: "en-US",
}, null, 2));
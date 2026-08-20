#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { marked } from "marked";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const repoRoot = path.resolve(siteRoot, "..");
const sitePackage = JSON.parse(fs.readFileSync(path.join(siteRoot, "package.json"), "utf8"));
const markedVersion = sitePackage.dependencies?.marked ?? sitePackage.devDependencies?.marked;
if (typeof markedVersion !== "string" || !markedVersion) throw new Error("site/package.json must exact-pin marked");
const manifestPath = path.join(repoRoot, "docs", "documentation_manifest.json");
const outputRoot = path.join(siteRoot, "public", "generated");
const docsOutputRoot = path.join(outputRoot, "docs");
const browserRuntimeRoot = path.join(outputRoot, "runtime");

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
if (manifest.schema !== "quillframe_documentation_manifest_v1") {
  throw new Error(`Unsupported documentation manifest schema: ${manifest.schema}`);
}

const pathToDocId = new Map();
for (const doc of manifest.documents) {
  if (doc.english) pathToDocId.set(path.posix.normalize(doc.english), doc.id);
  if (doc.chinese) pathToDocId.set(path.posix.normalize(doc.chinese), doc.id);
}

const stripHtml = (value = "") => value
  .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
  .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "")
  .replace(/<[^>]+>/g, " ")
  .replace(/\s+/g, " ")
  .trim();

const safeHref = (href = "", sourcePath = "") => {
  const value = String(href).trim();
  if (!value || /^(?:javascript|data|vbscript):/i.test(value)) return null;
  if (/^(?:https?:|mailto:|#)/i.test(value)) return value;

  const [pathname, hash = ""] = value.split("#", 2);
  const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(sourcePath), pathname));
  const docId = pathToDocId.get(resolved);
  if (docId) return `/docs/${encodeURIComponent(docId)}${hash ? `#${encodeURIComponent(hash)}` : ""}`;
  return value;
};

const inlineText = (nodes = []) => nodes.map((node) => {
  if (!node) return "";
  if (node.type === "text" || node.type === "code") return node.text ?? "";
  if (node.type === "br") return "\n";
  if (node.type === "image") return node.alt ?? "";
  if (Array.isArray(node.children)) return inlineText(node.children);
  return "";
}).join("");

function convertInline(tokens = [], sourcePath = "") {
  const result = [];
  for (const token of tokens ?? []) {
    if (!token) continue;
    switch (token.type) {
      case "text":
      case "escape":
        result.push({ type: "text", text: token.text ?? stripHtml(token.raw ?? "") });
        break;
      case "codespan":
        result.push({ type: "code", text: token.text ?? "" });
        break;
      case "strong":
      case "em":
      case "del":
        result.push({ type: token.type, children: convertInline(token.tokens ?? [], sourcePath) });
        break;
      case "link": {
        const href = safeHref(token.href, sourcePath);
        const children = convertInline(token.tokens ?? [], sourcePath);
        result.push(href ? { type: "link", href, title: token.title ?? null, children } : { type: "text", text: inlineText(children) });
        break;
      }
      case "image": {
        const href = safeHref(token.href, sourcePath);
        result.push({ type: "image", href, alt: token.text ?? "", title: token.title ?? null });
        break;
      }
      case "br":
        result.push({ type: "br" });
        break;
      case "html":
        result.push({ type: "text", text: stripHtml(token.raw ?? token.text ?? "") });
        break;
      default:
        if (Array.isArray(token.tokens)) {
          result.push(...convertInline(token.tokens, sourcePath));
        } else if (token.text || token.raw) {
          result.push({ type: "text", text: stripHtml(token.text ?? token.raw ?? "") });
        }
        break;
    }
  }
  return result.filter((node) => node.type !== "text" || node.text.length > 0);
}

const slugBase = (value = "") => {
  const normalized = value
    .normalize("NFKC")
    .toLocaleLowerCase()
    .replace(/[^\p{Letter}\p{Number}\s-]/gu, " ")
    .trim()
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "section";
};

function createSlugger() {
  const seen = new Map();
  return (text) => {
    const base = slugBase(text);
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    return count === 0 ? base : `${base}-${count + 1}`;
  };
}

function convertBlocks(tokens = [], sourcePath = "", slugger = createSlugger(), toc = []) {
  const blocks = [];

  for (const token of tokens ?? []) {
    if (!token) continue;
    switch (token.type) {
      case "space":
      case "def":
        break;
      case "heading": {
        const inlines = convertInline(token.tokens ?? [], sourcePath);
        const text = inlineText(inlines) || token.text || "";
        const id = slugger(text);
        const level = Number(token.depth ?? 2);
        blocks.push({ type: "heading", level, id, inlines });
        if (level >= 1 && level <= 4) toc.push({ level, id, text });
        break;
      }
      case "paragraph":
        blocks.push({ type: "paragraph", inlines: convertInline(token.tokens ?? [], sourcePath) });
        break;
      case "text": {
        const inlines = convertInline(token.tokens ?? [{ type: "text", text: token.text ?? token.raw ?? "" }], sourcePath);
        if (inlineText(inlines).trim()) blocks.push({ type: "paragraph", inlines });
        break;
      }
      case "code":
        blocks.push({ type: "code", lang: token.lang ?? "", text: token.text ?? "" });
        break;
      case "blockquote":
        blocks.push({ type: "blockquote", blocks: convertBlocks(token.tokens ?? [], sourcePath, slugger, toc) });
        break;
      case "list":
        blocks.push({
          type: "list",
          ordered: Boolean(token.ordered),
          start: token.start ?? null,
          items: (token.items ?? []).map((item) => convertBlocks(item.tokens ?? [], sourcePath, slugger, toc)),
        });
        break;
      case "table": {
        const convertCell = (cell) => convertInline(cell?.tokens ?? [{ type: "text", text: cell?.text ?? "" }], sourcePath);
        blocks.push({
          type: "table",
          align: token.align ?? [],
          header: (token.header ?? []).map(convertCell),
          rows: (token.rows ?? []).map((row) => row.map(convertCell)),
        });
        break;
      }
      case "hr":
        blocks.push({ type: "hr" });
        break;
      case "html": {
        const text = stripHtml(token.raw ?? token.text ?? "");
        if (text) blocks.push({ type: "paragraph", inlines: [{ type: "text", text }] });
        break;
      }
      default:
        if (Array.isArray(token.tokens)) {
          blocks.push(...convertBlocks(token.tokens, sourcePath, slugger, toc));
        } else if (token.text || token.raw) {
          const text = stripHtml(token.text ?? token.raw ?? "");
          if (text) blocks.push({ type: "paragraph", inlines: [{ type: "text", text }] });
        }
        break;
    }
  }
  return blocks;
}

function flattenBlocks(blocks = []) {
  const parts = [];
  const walk = (block) => {
    if (!block) return;
    if (block.inlines) parts.push(inlineText(block.inlines));
    if (block.type === "code") parts.push(block.text ?? "");
    if (Array.isArray(block.blocks)) block.blocks.forEach(walk);
    if (Array.isArray(block.items)) block.items.flat().forEach(walk);
    if (block.type === "table") {
      block.header?.forEach((cell) => parts.push(inlineText(cell)));
      block.rows?.flat().forEach((cell) => parts.push(inlineText(cell)));
    }
  };
  blocks.forEach(walk);
  return parts.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

const compactExcerpt = (text, max = 260) => {
  const value = text.replace(/\s+/g, " ").trim();
  return value.length <= max ? value : `${value.slice(0, max - 1).trimEnd()}…`;
};

fs.rmSync(outputRoot, { recursive: true, force: true });
fs.mkdirSync(docsOutputRoot, { recursive: true });

const browserCoreSources = [
  "production_runtime/workflow.py",
  "production_runtime/types.py",
];
const browserCoreHashes = {};
for (const relative of browserCoreSources) {
  const source = path.join(repoRoot, relative);
  const destination = path.join(browserRuntimeRoot, relative);
  if (!fs.existsSync(source)) throw new Error(`Browser Core source is missing: ${relative}`);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(source, destination);
  browserCoreHashes[relative] = crypto.createHash("sha256").update(fs.readFileSync(source)).digest("hex");
}

const quickDemoFixture = path.join(repoRoot, "demo", "fixtures", "ch001_quick_demo.json");
if (!fs.existsSync(quickDemoFixture)) throw new Error("CH001 quick-demo fixture is missing");
fs.copyFileSync(quickDemoFixture, path.join(browserRuntimeRoot, "ch001_quick_demo.json"));
fs.writeFileSync(path.join(browserRuntimeRoot, "manifest.json"), `${JSON.stringify({
  schema: "quillframe_browser_core_manifest_v1",
  chapter_scope: "CH001",
  files: browserCoreHashes,
  demo_fixture: "ch001_quick_demo.json",
  authority: false,
}, null, 2)}\n`, "utf8");

const pyodideEntry = fileURLToPath(import.meta.resolve("pyodide"));
const pyodideSourceRoot = path.dirname(pyodideEntry);
const pyodideOutputRoot = path.join(siteRoot, "public", "pyodide");
const pyodideAssets = [
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "pyodide-lock.json",
  "python_stdlib.zip",
];
fs.rmSync(pyodideOutputRoot, { recursive: true, force: true });
fs.mkdirSync(pyodideOutputRoot, { recursive: true });
for (const asset of pyodideAssets) {
  const source = path.join(pyodideSourceRoot, asset);
  if (!fs.existsSync(source)) throw new Error(`Pyodide local runtime asset is missing: ${asset}`);
  fs.copyFileSync(source, path.join(pyodideOutputRoot, asset));
}

const indexDocuments = [];
let compiledCount = 0;

for (const doc of manifest.documents) {
  for (const [locale, sourcePath] of [["en-US", doc.english], ["zh-CN", doc.chinese]]) {
    if (!sourcePath) continue;
    const absolute = path.join(repoRoot, sourcePath);
    if (!fs.existsSync(absolute)) throw new Error(`Manifest source is missing: ${sourcePath}`);

    const markdown = fs.readFileSync(absolute, "utf8");
    const tokens = marked.lexer(markdown, { gfm: true });
    const toc = [];
    const blocks = convertBlocks(tokens, sourcePath, createSlugger(), toc);
    const plainText = flattenBlocks(blocks);
    const title = toc.find((item) => item.level === 1)?.text ?? doc.purpose ?? doc.id;
    const fingerprint = crypto.createHash("sha256").update(markdown, "utf8").digest("hex");

    const payload = {
      schema: "quillframe_product_document_v1",
      authority: false,
      generatedFrom: "docs/documentation_manifest.json",
      id: doc.id,
      locale,
      tier: doc.tier,
      status: doc.status,
      title,
      purpose: doc.purpose ?? "",
      audience: doc.audience ?? "",
      sourcePath,
      sourceFingerprint: fingerprint,
      freshnessOwner: doc.freshness_owner ?? "",
      authoritySources: doc.authority_sources ?? [],
      toc,
      blocks,
    };

    const localeDir = path.join(docsOutputRoot, locale);
    fs.mkdirSync(localeDir, { recursive: true });
    fs.writeFileSync(path.join(localeDir, `${doc.id}.json`), `${JSON.stringify(payload)}\n`, "utf8");

    indexDocuments.push({
      id: doc.id,
      locale,
      tier: doc.tier,
      status: doc.status,
      title,
      purpose: doc.purpose ?? "",
      audience: doc.audience ?? "",
      sourcePath,
      sourceFingerprint: fingerprint,
      freshnessOwner: doc.freshness_owner ?? "",
      excerpt: compactExcerpt(plainText),
      headings: toc.map((item) => item.text),
      searchText: plainText.slice(0, 50000),
    });
    compiledCount += 1;
  }
}

const indexPayload = {
  schema: "quillframe_product_document_index_v1",
  authority: false,
  frameworkVersion: manifest.framework_version,
  manifestSchema: manifest.schema,
  documentCount: compiledCount,
  documents: indexDocuments,
};

fs.writeFileSync(path.join(outputRoot, "docs-index.json"), `${JSON.stringify(indexPayload)}\n`, "utf8");
fs.writeFileSync(path.join(outputRoot, "build-meta.json"), `${JSON.stringify({
  schema: "quillframe_product_content_build_v1",
  authority: false,
  manifest: path.relative(repoRoot, manifestPath).replaceAll(path.sep, "/"),
  documents: compiledCount,
  locales: ["en-US", "zh-CN"],
  parser: `marked@${markedVersion}`,
  browserCore: "production_runtime/workflow.py + production_runtime/types.py",
}, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  schema: "quillframe_product_content_build_v1",
  status: "pass",
  documents: compiledCount,
  output: path.relative(repoRoot, outputRoot).replaceAll(path.sep, "/"),
}, null, 2));

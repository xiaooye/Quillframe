#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

function arg(name, fallback) {
  const flag = `--${name}`;
  const index = process.argv.indexOf(flag);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const distRoot = path.resolve(siteRoot, "dist");
const host = arg("host", "127.0.0.1");
const port = Number(arg("port", "4173"));

const mime = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".wasm", "application/wasm"],
  [".pck", "application/octet-stream"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".svg", "image/svg+xml"],
  [".ico", "image/x-icon"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
  [".txt", "text/plain; charset=utf-8"],
]);

function safeCandidate(pathname) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }
  const relative = decoded.replace(/^\/+/, "");
  const candidate = path.resolve(distRoot, relative);
  if (candidate !== distRoot && !candidate.startsWith(`${distRoot}${path.sep}`)) return null;
  return candidate;
}

function resolveFile(pathname) {
  const candidate = safeCandidate(pathname);
  if (!candidate) return null;
  if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
    const index = path.join(candidate, "index.html");
    if (fs.existsSync(index) && fs.statSync(index).isFile()) return index;
  }
  return null;
}

function sendFile(request, response, file) {
  const stat = fs.statSync(file);
  response.statusCode = 200;
  response.setHeader("Content-Type", mime.get(path.extname(file).toLowerCase()) ?? "application/octet-stream");
  response.setHeader("Content-Length", stat.size);
  response.setHeader("Cache-Control", "no-store");
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  fs.createReadStream(file).pipe(response);
}

const server = http.createServer((request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" });
    response.end("Method Not Allowed");
    return;
  }

  const url = new URL(request.url ?? "/", `http://${request.headers.host ?? `${host}:${port}`}`);
  const pathname = url.pathname;

  if (pathname === "/docs" || pathname === "/docs/en") {
    response.writeHead(301, { Location: `${pathname}/` });
    response.end();
    return;
  }

  const file = resolveFile(pathname);
  if (file) {
    sendFile(request, response, file);
    return;
  }

  // Docs are a separate semantic application. A missing docs path must never
  // silently become the Product canvas.
  if (/^\/docs(?:\/|$)/.test(pathname)) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Documentation page not found");
    return;
  }

  // Product routes are browser-addressable views inside one Godot runtime.
  // Mirror Cloudflare Pages' product-route fallback during local browser QA.
  const productHost = path.join(distRoot, "index.html");
  if (fs.existsSync(productHost)) {
    sendFile(request, response, productHost);
    return;
  }

  response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
  response.end("Godot product runtime has not been exported yet");
});

server.listen(port, host, () => {
  console.log(`NovelForge dist server listening on http://${host}:${port}`);
});

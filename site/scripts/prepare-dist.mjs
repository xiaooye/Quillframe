#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const distRoot = path.join(siteRoot, "dist");
const publicRoot = path.join(siteRoot, "public");

fs.rmSync(distRoot, { recursive: true, force: true });
fs.mkdirSync(distRoot, { recursive: true });

if (fs.existsSync(publicRoot)) {
  for (const entry of fs.readdirSync(publicRoot, { withFileTypes: true })) {
    const source = path.join(publicRoot, entry.name);
    const target = path.join(distRoot, entry.name);
    fs.cpSync(source, target, { recursive: true });
  }
}

console.log(JSON.stringify({
  schema: "novelforge_product_dist_prepare_v1",
  status: "pass",
  product_runtime: "godot_export_pending",
  docs_runtime: "astro_starlight",
  copied_public_root: fs.existsSync(publicRoot),
}));

#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const repoRoot = path.resolve(siteRoot, "..");
const integrationPath = path.join(repoRoot, "assets", "brand", "weiui.integration.json");
const integration = JSON.parse(fs.readFileSync(integrationPath, "utf8"));

if (integration.schema !== "novelforge_weiui_integration_v2") {
  throw new Error(`Unsupported WeiUI integration schema: ${integration.schema}`);
}

const delivery = integration.consumption?.css_delivery;
if (!delivery || delivery.mode !== "config_generated_checked_in") {
  throw new Error("Product Entry requires config-generated checked-in WeiUI CSS");
}

const sourceFiles = {
  "weiui.tokens.generated.css": delivery.generated_tokens,
  "weiui.generated.css": delivery.generated_css,
};

const outDir = path.join(siteRoot, "src", "generated");
fs.mkdirSync(outDir, { recursive: true });

for (const [outputName, repoRelative] of Object.entries(sourceFiles)) {
  const source = path.join(repoRoot, repoRelative);
  if (!fs.existsSync(source)) throw new Error(`WeiUI generated foundation is missing: ${repoRelative}`);
  fs.copyFileSync(source, path.join(outDir, outputName));
}

fs.writeFileSync(path.join(outDir, "weiui.foundation.json"), `${JSON.stringify({
  schema: "novelforge_product_weiui_foundation_v1",
  authority: false,
  integration: integration.schema,
  sourceRepository: integration.source.repository,
  sourceCommit: integration.source.commit,
  generatedTokens: delivery.generated_tokens,
  generatedCss: delivery.generated_css,
  importOrder: [
    "weiui.tokens.generated.css",
    "weiui.generated.css",
    "assets/brand/story-loom.weiui.css",
  ],
}, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  schema: "novelforge_product_weiui_foundation_v1",
  status: "pass",
  sourceCommit: integration.source.commit,
  generated: Object.keys(sourceFiles),
}, null, 2));

#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../..");
const read = (relative) => fs.readFileSync(path.join(repoRoot, relative), "utf8");

const retiredPaths = [
  "site/src/KnowledgeExperience.tsx",
  "site/src/DocumentRenderer.tsx",
  "site/src/knowledgePresentation.ts",
  "site/src/styles/knowledge-experience.css",
  "site/src/styles/knowledge-portal.css",
  "site/src/styles/editorial-composition.css",
  "site/src/styles/home-identity.css",
  "site/src/styles/kawaii-surfaces.css",
  "site/scripts/knowledge-experience-quality.mjs",
  "studio/app/src/styles/projection-inspector.css",
  "studio/app/src/styles/projection-workbenches.css",
];

const activeSources = [
  "site/src/main.tsx",
  "site/src/ProductApp.tsx",
  "site/src/ProductResilience.tsx",
  "site/src/styles/index.css",
  "site/scripts/quality.mjs",
  "site/scripts/docs-platform-quality.mjs",
  "site/scripts/atelier-quality.mjs",
  "site/scripts/css-architecture-quality.mjs",
  "site/scripts/surface-audit-quality.mjs",
  "site/scripts/tool-workbench-quality.mjs",
  "studio/app/src/main.tsx",
  "studio/app/src/AppShell.tsx",
  "studio/app/src/StudioResilience.tsx",
  "studio/app/src/styles/index.css",
];

const failures = [];
for (const relative of retiredPaths) {
  if (fs.existsSync(path.join(repoRoot, relative))) failures.push(`retired path still exists: ${relative}`);
}

for (const relative of activeSources) {
  const source = read(relative);
  for (const retired of retiredPaths) {
    const basename = path.basename(retired);
    if (source.includes(basename) || source.includes(retired)) {
      failures.push(`active source retains retired marker ${basename}: ${relative}`);
    }
  }
}

if (failures.length) {
  for (const failure of failures) console.error(`dead-surface-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_dead_surface_quality_v1",
    status: "pass",
    retired_paths: retiredPaths.length,
    active_sources: activeSources.length,
    authority: false,
  }, null, 2));
}

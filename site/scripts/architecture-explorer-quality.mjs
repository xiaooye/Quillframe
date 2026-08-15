#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const main = read("src/main.tsx");
const explorer = read("src/ArchitectureExplorerEntry.tsx");
const css = read("src/styles/architecture-explorer.css");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

for (const node of ["project", "manager", "context", "worker", "gate", "settlement", "publication"]) {
  check(explorer.includes(`id: "${node}"`), `architecture explorer missing ${node} node`);
}

for (const contract of [
  "novelforge_project_adapter_resolution_v1",
  "novelforge_host_capabilities_v1",
  "novelforge_context_inspector_v2",
  "novelforge_run_receipt_v1",
  "novelforge_production_readiness_v1",
  "novelforge_publication_ir_v1",
]) {
  check(explorer.includes(contract), `architecture explorer missing public contract ${contract}`);
}

check(explorer.includes("authority=false"), "architecture preview must state its non-authoritative boundary");
check(explorer.includes("This is not a real Core execution") && explorer.includes("不调用模型"), "architecture simulation must be explicitly identified as a deterministic preview");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(explorer), "architecture explorer must not add idle timers or frame loops");
check(main.includes('path === "/architecture"') && main.includes("ArchitectureExplorerEntry"), "main entry must route /architecture to the standalone explorer");
for (const route of ["/inspect", "/playground", "/architecture"]) {
  check(main.includes(`"${route}"`), `SPA handoff must cover standalone browser-native product surface ${route}`);
}
check(main.includes('import "./styles/architecture-explorer.css"'), "architecture explorer styles must be loaded by the product entry");
check(css.includes(".architecture-flow") && css.includes(".architecture-detail-grid") && css.includes(".architecture-trace-list"), "architecture explorer must retain flow, inspector, and trace surfaces");
check(css.includes("@media (max-width: 760px)"), "architecture explorer must retain a mobile responsive contract");

if (failures.length) {
  for (const failure of failures) console.error(`architecture-explorer-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_architecture_explorer_quality_v1",
    status: "pass",
    nodes: 7,
    deterministic_preview: true,
    model_execution: false,
    authority: false,
    public_contract_grounded: true,
    responsive: true,
    composable_handoff_gate: true,
  }, null, 2));
}

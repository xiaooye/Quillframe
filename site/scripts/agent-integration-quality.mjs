#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const app = read("src/ProductApp.tsx");
const main = read("src/main.tsx");
const index = read("src/styles/index.css");
const style = `${read("src/styles/agent-integration.css")}\n${read("src/styles/agent-host-profiles.css")}\n${read("src/styles/unified-product-app.css")}`;
const contract = JSON.parse(read("../studio/host_bridge_contract.json"));
const skill = read("../agent-skills/quillframe/SKILL.md");
const supported = contract.operations ?? {};
const deferred = contract.deferred_operations ?? {};
const operationEntries = Object.entries(supported);
const queryOperations = operationEntries.filter(([, metadata]) => metadata?.kind === "query");
const nonQueryOperations = operationEntries.filter(([, metadata]) => metadata?.kind !== "query");

check(contract.schema === "quillframe_host_bridge_contract_v11", "host bridge contract schema changed");
check(contract.version === "11", "host bridge contract version changed");
check(contract.authority === false, "host bridge must remain authority=false");
check(contract.direct_core_store_access === false, "host bridge must not expose direct Core store access");
check(skill.includes("read-only") && skill.includes("authority: false"), "portable skill must retain read-only authority boundary");
check(skill.includes("quillframe_host_bridge_description_v11") && skill.includes("quillframe_host_bridge_request_v11"), "portable skill must be hard-cut to Host Bridge v11");
check(skill.includes("query-only") && skill.includes("fails closed"), "portable skill must document query-only fail-closed behavior");
check(skill.includes("database.doctor") && skill.includes("side-effect-free"), "portable skill must document side-effect-free doctor");
check(queryOperations.length > 0, "Host Bridge must expose at least one query operation");
check(nonQueryOperations.length > 0, "Host Bridge metadata must retain non-query kinds for client validation");
for (const [operation, metadata] of operationEntries) {
  check(typeof metadata?.kind === "string", `operation kind missing: ${operation}`);
  check(Array.isArray(metadata?.required_args), `operation required_args missing: ${operation}`);
  if (metadata?.kind !== "query") check(!metadata?.allowed_surfaces?.includes("agent_package"), `non-query operation must not allow agent_package: ${operation}`);
}
check(supported["bridge.describe"]?.kind === "query", "bridge.describe must remain query kind");
check(supported["database.doctor"]?.kind === "query", "database.doctor must remain query kind");
check(supported["candidate.visible.get"]?.allowed_surfaces?.includes("agent_package"), "candidate.visible.get must declare agent_package when exposed");
check(!Object.keys(deferred).some((operation) => operation in supported), "deferred operation must not also be advertised");

check(app.includes('<Route path="/agents" component={AgentsPage}'), "shared ProductApp must expose /agents");
check(app.includes("ProductSurfaceHero") && app.includes("AGENT SKILL · HOST BRIDGE V11"), "Agent Integration must use the shared surface hero with exact v11 marker");
check(!app.includes("AGENT SKILL · HOST BRIDGE V1</span>"), "Agent Integration must not retain the retired v1 marker");
check(app.includes("agent-skills/quillframe/SKILL.md"), "Agent Integration must expose the portable Agent Skill entry");
check(app.includes("bridge.describe"), "Agent Integration must expose capability discovery");
check(app.includes("authority=false") || app.includes("authority: false"), "Agent Integration must visibly preserve authority=false");
check(app.includes("Never read private runtime stores directly"), "Agent Integration host instruction must forbid direct private runtime access");
for (const host of ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"]) {
  check(app.includes(host), `host recipe missing ${host}`);
}
check(main.includes('import ProductApp from "./ProductApp"') && !main.includes("AgentIntegrationEntry"), "main must use the shared ProductApp instead of a standalone Agent shell");
check(main.includes('import "./styles/index.css"'), "main must load the single Product stylesheet entrypoint");
check(index.includes('@import "./agent-integration.css"') && index.includes('@import "./agent-host-profiles.css"'), "agent integration styles must remain loaded through the Product CSS entrypoint");
check(index.indexOf('agent-host-profiles.css') < index.indexOf('readability.css'), "agent route styling must precede cross-cutting readability hardening");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(app), "ProductApp must not poll or run decorative frame loops");
for (const marker of [".agent-host-workbench", ".agent-host-detail", ".agent-host-instruction", ".unified-agent-hosts", "@media (max-width: 520px)"]) {
  check(style.includes(marker), `Agent integration styling marker missing: ${marker}`);
}

if (failures.length) {
  for (const failure of failures) console.error(`agent-integration-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_agent_integration_quality_v7",
    status: "pass",
    route: "/agents",
    shell: "shared_product_app",
    css_entrypoint: "index.css",
    portable_skill: true,
    host_bridge_v11: true,
    host_profiles: 5,
    supported_operations: Object.keys(supported).length,
    query_operations: queryOperations.length,
    non_query_operations: nonQueryOperations.length,
    agent_package_runtime_control: false,
    write_authority: false,
    direct_core_store_access: false,
    unsupported_fails_closed: true,
  }, null, 2));
}

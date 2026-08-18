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
const supported = contract.operations?.supported ?? {};
const deferred = contract.operations?.deferred ?? {};
const runtimeObservability = [
  "runtime.sessions.list",
  "runtime.session.get",
  "runtime.events.list",
  "runtime.handoff.inspect",
  "run.receipt.get",
  "runtime.command.receipt.get",
];
const runtimeSafetyQueries = ["session.resume.preflight", "session.terminate.preflight"];
const localAppCommands = ["session.resume", "session.terminate"];
const deferredCommands = ["command.invoke", "project.mutate", "publication.build"];

check(contract.schema === "quillframe_studio_host_bridge_contract_v1", "host bridge contract schema changed");
check(contract.authority === false, "host bridge must remain authority=false");
check(contract.agent_skill?.path === "agent-skills/quillframe/SKILL.md", "portable Agent Skill path changed");
check(contract.agent_skill?.runtime_mutation_allowed === false, "portable Agent Skill must remain runtime-mutation=false");
check(skill.includes("read-only") && skill.includes("authority: false"), "portable skill must retain read-only authority boundary");
check(skill.includes("Runtime observability is not runtime control"), "portable skill must distinguish runtime observability from control");
check(skill.includes("session.resume.preflight") && skill.includes("READY") && skill.includes("BLOCKED"), "portable skill must explain deterministic resume eligibility");
check(skill.includes("not portable Agent Skills capabilities") && skill.includes("local_app"), "portable skill must preserve local-app-only runtime command boundary");

for (const operation of ["bridge.describe", "framework.doctor", "project.inspect", "capabilities.inspect", "context.inspect", "semantic.catalog", "publication.preview", ...runtimeObservability, ...runtimeSafetyQueries]) {
  check(Boolean(supported[operation]), `expected supported bridge query missing from contract: ${operation}`);
  check(supported[operation]?.kind === "query", `supported read operation must remain query kind: ${operation}`);
  check(!deferred[operation], `public read/safety query must not remain deferred: ${operation}`);
}

for (const operation of localAppCommands) {
  const entry = supported[operation];
  check(Boolean(entry), `expected typed local-app runtime command missing from contract: ${operation}`);
  check(entry?.kind === "command", `typed local-app runtime operation must remain command kind: ${operation}`);
  check(Array.isArray(entry?.allowed_surfaces) && entry.allowed_surfaces.includes("local_app"), `runtime command must remain local_app scoped: ${operation}`);
  check(entry?.model_execution === false, `runtime command must not gain model execution: ${operation}`);
  check(entry?.project_write === false && entry?.canon_write === false && entry?.framework_write === false, `runtime command must not gain Project/Canon/Framework write authority: ${operation}`);
  check(!deferred[operation], `typed local-app runtime command must not also remain deferred: ${operation}`);
}

for (const operation of deferredCommands) {
  check(Boolean(deferred[operation]), `expected deferred generic/persistent command missing from contract: ${operation}`);
  check(!supported[operation], `deferred command must not be exposed as supported: ${operation}`);
}

check(app.includes('<Route path="/agents" component={AgentsPage}'), "shared ProductApp must expose /agents");
check(app.includes("ProductSurfaceHero") && app.includes("AGENT SKILL · HOST BRIDGE V1"), "Agent Integration must use the shared surface hero");
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
    host_bridge_v1: true,
    host_profiles: 5,
    supported_operations: Object.keys(supported).length,
    runtime_observability_operations: runtimeObservability.length,
    runtime_safety_queries: runtimeSafetyQueries.length,
    local_app_runtime_commands: localAppCommands.length,
    agent_package_runtime_control: false,
    write_authority: false,
    direct_core_store_access: false,
    unsupported_fails_closed: true,
  }, null, 2));
}

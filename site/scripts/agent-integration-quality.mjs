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
const skill = read("../agent-skills/novelforge/SKILL.md");
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
const guardedRuntimeCommands = ["session.resume", "session.terminate"];
const deferredMutations = ["command.invoke", "project.mutate", "publication.build"];
const baselineQueries = [
  "bridge.describe",
  "framework.doctor",
  "project.inspect",
  "capabilities.inspect",
  "context.inspect",
  "semantic.catalog",
  "publication.preview",
  ...runtimeObservability,
  ...runtimeSafetyQueries,
];

check(contract.schema === "novelforge_studio_host_bridge_contract_v1", "host bridge contract schema changed");
check(contract.authority === false, "host bridge must remain authority=false");
check(contract.canon_authority === false && contract.framework_write_authority === false && contract.settlement_authority === false, "delivery bridge must not gain story/framework authority");
check(contract.agent_skill?.path === "agent-skills/novelforge/SKILL.md", "portable Agent Skill path changed");
check(contract.agent_skill?.runtime_mutation_allowed === false, "portable Agent Skill must remain runtime-mutation false");
check(skill.includes("read-only") && skill.includes("authority: false"), "portable skill must retain read-only authority boundary");
check(skill.includes("Runtime observability is not runtime control"), "portable skill must distinguish runtime observability from control");
check(skill.includes("session.resume.preflight") && skill.includes("READY") && skill.includes("BLOCKED"), "portable skill must explain deterministic resume eligibility without exposing resume control");
check(skill.includes("local_app") && skill.includes("agent_package"), "portable skill must distinguish local-app command capability from agent-package capability");
check(skill.includes("kind: command") && skill.includes("invoke **query operations only**"), "portable skill must explicitly reject command invocation from the agent package");

for (const operation of baselineQueries) {
  check(Boolean(supported[operation]), `expected supported bridge query missing from contract: ${operation}`);
  check(supported[operation]?.kind === "query", `supported read must remain kind=query: ${operation}`);
  check(!deferred[operation], `public runtime/read query must not remain deferred: ${operation}`);
}

for (const operation of guardedRuntimeCommands) {
  const spec = supported[operation];
  check(Boolean(spec), `expected guarded runtime command missing from contract: ${operation}`);
  check(spec?.kind === "command", `guarded runtime command must remain kind=command: ${operation}`);
  check(Array.isArray(spec?.allowed_surfaces) && spec.allowed_surfaces.length === 1 && spec.allowed_surfaces[0] === "local_app", `guarded runtime command must remain local_app-only: ${operation}`);
  check(Array.isArray(spec?.required_args) && spec.required_args.includes("user_authorized"), `guarded runtime command must require explicit user authorization: ${operation}`);
  check(typeof spec?.mutation_scope === "string" && spec.mutation_scope.startsWith("runtime_"), `guarded command mutation scope must remain runtime-only: ${operation}`);
  check(spec?.model_execution === false, `guarded runtime command must not execute a model: ${operation}`);
  check(spec?.project_write === false && spec?.canon_write === false && spec?.framework_write === false && spec?.settlement === false, `guarded runtime command must not gain Project/Canon/Framework/Settlement authority: ${operation}`);
  check(!deferred[operation], `implemented guarded runtime command must not also be deferred: ${operation}`);
}

for (const operation of deferredMutations) {
  check(Boolean(deferred[operation]), `expected deferred mutation missing from contract: ${operation}`);
  check(!supported[operation], `generic/persistent mutation must not be exposed as supported: ${operation}`);
}
check(skill.includes("resume, terminate, replay, fork"), "portable skill must preserve the explicit runtime-control boundary");
check(skill.includes("forging a `local_app` surface identity"), "portable skill must forbid surface-identity escalation");

check(app.includes('<Route path="/agents" component={AgentsPage}'), "shared ProductApp must expose /agents");
check(app.includes("ProductSurfaceHero") && app.includes("AGENT SKILL · HOST BRIDGE V1"), "Agent Integration must use the shared surface hero");
check(app.includes("agent-skills/novelforge/SKILL.md"), "Agent Integration must expose the portable Agent Skill entry");
check(app.includes("bridge.describe"), "Agent Integration must expose capability discovery");
check(app.includes("authority=false") || app.includes("authority: false"), "Agent Integration must visibly preserve authority=false");
check(app.includes("Never read private runtime stores directly"), "Agent Integration host instruction must forbid direct private runtime access");
for (const host of ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"]) {
  check(app.includes(host), `host recipe missing ${host}`);
}
check(main.includes('import ProductApp from "./ProductApp"') && !main.includes("AgentIntegrationEntry"), "migration fallback must retain the shared Solid ProductApp source");
check(main.includes('import "./styles/index.css"'), "migration fallback must load the single Product stylesheet entrypoint");
check(index.includes('@import "./agent-integration.css"') && index.includes('@import "./agent-host-profiles.css"'), "agent integration styles must remain loaded through the fallback Product CSS entrypoint");
check(index.indexOf('agent-host-profiles.css') < index.indexOf('readability.css'), "agent route styling must precede cross-cutting readability hardening");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(app), "fallback ProductApp must not poll or run decorative frame loops");
for (const marker of [".agent-host-workbench", ".agent-host-detail", ".agent-host-instruction", ".unified-agent-hosts", "@media (max-width: 520px)"]) {
  check(style.includes(marker), `Agent integration styling marker missing: ${marker}`);
}

if (failures.length) {
  for (const failure of failures) console.error(`agent-integration-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_agent_integration_quality_v7",
    status: "pass",
    route: "/agents",
    product_runtime: "godot_first_with_solid_migration_fallback",
    portable_skill: true,
    host_bridge_v1: true,
    host_profiles: 5,
    supported_operations: Object.keys(supported).length,
    runtime_observability_operations: runtimeObservability.length,
    runtime_safety_queries: runtimeSafetyQueries.length,
    guarded_runtime_commands: guardedRuntimeCommands.length,
    guarded_command_surface: "local_app_only",
    agent_package_runtime_control: false,
    write_authority: false,
    direct_core_store_access: false,
    unsupported_fails_closed: true,
  }, null, 2));
}

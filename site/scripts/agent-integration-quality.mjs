#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const fail = (message) => {
  console.error(`agent-integration-quality: FAIL: ${message}`);
  process.exitCode = 1;
};
const check = (condition, message) => {
  if (!condition) fail(message);
};

const entry = read("src/AgentIntegrationEntry.tsx");
const style = read("src/styles/agent-integration.css");
const hostStyle = read("src/styles/agent-host-profiles.css");
const main = read("src/main.tsx");
const contract = JSON.parse(read("../studio/host_bridge_contract.json"));
const skill = read("../agent-skills/novelforge/SKILL.md");

check(contract.schema === "novelforge_studio_host_bridge_contract_v1", "host bridge contract schema changed");
check(contract.authority === false, "host bridge must remain authority=false");
check(contract.agent_skill?.path === "agent-skills/novelforge/SKILL.md", "portable Agent Skill path changed");
check(skill.includes("read-only") && skill.includes("authority: false"), "portable skill must retain read-only authority boundary");

for (const operation of Object.keys(contract.operations.supported)) {
  check(entry.includes(operation), `Agent integration surface missing supported operation ${operation}`);
}
for (const operation of ["run.receipt.get", "session.resume", "command.invoke", "project.mutate"]) {
  check(contract.operations.deferred[operation], `expected deferred bridge operation missing from contract: ${operation}`);
  check(entry.includes(operation), `Agent integration surface must expose deferred state for ${operation}`);
}

check(entry.includes("novelforge_studio_host_bridge_request_v1"), "request envelope schema must be visible");
check(entry.includes("surface: \"agent_package\""), "request builder must identify the agent_package surface");
check(entry.includes("authority: false"), "request builder must hard-code authority=false");
check(entry.includes("novelforge_bridge.py self-test"), "self-test onboarding command is missing");
check(entry.includes("novelforge_bridge.py describe"), "describe onboarding command is missing");
check(entry.includes("capability ≠ authority"), "authority messaging is missing");

for (const host of ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"]) {
  check(entry.includes(host), `host recipe missing ${host}`);
}
check(entry.includes("provider_specific_adapter: not_bundled"), "host recipes must not imply provider-specific adapters already ship");
check(entry.includes("generic_read_only"), "host recipes must identify the generic read-only bridge mode");
check(entry.includes("Never read .novelforge/runtime.db"), "copyable host instruction must forbid direct runtime DB access");
check(entry.includes("If an operation is unsupported, stop"), "copyable host instruction must fail closed on unsupported operations");

check(main.includes('import AgentIntegrationEntry from "./AgentIntegrationEntry"'), "main entry must import AgentIntegrationEntry");
check(main.includes('"/agents"'), "main handoff set must include /agents");
check(main.includes('path === "/agents"'), "main router must mount AgentIntegrationEntry at /agents");
check(main.includes('import "./styles/agent-integration.css"'), "main entry must load agent integration styling");
check(main.includes('import "./styles/agent-host-profiles.css"'), "main entry must load agent host profile styling");

for (const marker of [
  ".agent-integration-hero",
  ".agent-path-grid",
  ".agent-onboarding-grid",
  ".agent-operation-tabs",
  ".agent-contract-grid",
  "@media (max-width: 760px)",
]) {
  check(style.includes(marker), `Agent integration styling marker missing: ${marker}`);
}
for (const marker of [
  ".agent-host-workbench",
  ".agent-host-tabs",
  ".agent-host-detail",
  ".agent-host-instruction",
  "@media (max-width: 520px)",
]) {
  check(hostStyle.includes(marker), `Agent host profile styling marker missing: ${marker}`);
}

check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(entry), "Agent integration surface must not poll or run decorative frame loops");

if (!process.exitCode) {
  console.log(JSON.stringify({
    schema: "novelforge_agent_integration_quality_v2",
    status: "pass",
    portable_skill: true,
    host_bridge_v1: true,
    host_profiles: 5,
    provider_specific_adapters_claimed: false,
    supported_operations: Object.keys(contract.operations.supported).length,
    write_authority: false,
    direct_core_store_access: false,
    unsupported_fails_closed: true,
    route: "/agents",
  }, null, 2));
}

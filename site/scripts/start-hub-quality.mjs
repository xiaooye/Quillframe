#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const main = read("src/main.tsx");
const app = read("src/ProductApp.tsx");
const docsActions = read("docs-site/src/components/QuillframeActions.astro");
const docsLanding = read("docs-site/src/components/DocsLanding.astro");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(!main.includes('import StartHubEntry from "./StartHubEntry"'), "retired /start surface must not be mounted as a standalone product page");
check(!main.includes('import "./styles/start-hub.css"') && !main.includes('import "./styles/start-hub-kawaii.css"'), "retired start-specific styling must not ship in the product bundle");
check(main.includes('import ProductApp from "./ProductApp"') && main.includes("<ProductApp />"), "main must mount the shared ProductApp");
check(!app.includes('<Route path="/start"') && !main.includes('"/start"'), "retired /start must have no route, redirect, or direct-route allowlist entry");
check(!main.includes("standaloneProductPaths"), "retired /start handling must not reintroduce standalone page handoffs");

check(!docsActions.includes('href="/start"'), "documentation chrome must not expose a redundant standalone start page");
check(!docsLanding.includes('link: "/start"'), "documentation hero must not route through the retired start page");
check(!docsLanding.includes('["开始中心"') && !docsLanding.includes('["Start hub"'), "documentation runtime list must not advertise the retired start page");
check(docsLanding.includes('"/inspect"'), "Project Inspector must remain directly discoverable from documentation");
check(docsLanding.includes('"/playground"'), "Local Playground must remain directly discoverable from documentation");
check(docsLanding.includes('"/agents"'), "Agent Integration must remain directly discoverable from documentation");

if (failures.length) {
  for (const failure of failures) console.error(`start-hub-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "quillframe_start_flow_consolidation_quality_v3", status: "pass", standalone_start_page: false, start_redirect: false, product_home_is_primary_entry: true, shared_router: true, project_inspector_discoverable: true, local_playground_discoverable: true, agent_integration_discoverable: true }, null, 2));
}

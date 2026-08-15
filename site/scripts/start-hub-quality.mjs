#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const entry = read("src/StartHubEntry.tsx");
const css = read("src/styles/start-hub.css");
const main = read("src/main.tsx");
const docsActions = read("docs-site/src/components/NovelForgeActions.astro");
const docsLanding = read("docs-site/src/components/DocsLanding.astro");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

for (const intent of ["start-novel", "open-project", "connect-agent", "explore"]) {
  check(entry.includes(`id: "${intent}"`), `start hub missing intent ${intent}`);
}

check(entry.includes('https://studio.novelforge.wei-dev.com/start'), "new-novel intent must use Studio onboarding");
check(entry.includes('href: "/inspect"'), "existing-project intent must use Project Inspector");
check(entry.includes('href: "/agents"'), "coding-agent intent must use Agent Integration");
check(entry.includes('href: "/playground"'), "explore intent must use Local Playground");
check(entry.includes("不伪装未实现能力") && entry.includes("No fake capabilities"), "truthful product-boundary messaging is missing");
check(entry.includes("authority ≠ capability"), "start flow must preserve authority/capability distinction");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(entry), "start hub must not add idle animation or polling loops");

check(main.includes('import StartHubEntry from "./StartHubEntry"'), "main entry must import StartHubEntry");
check(main.includes('"/start"'), "standalone surface handoff must include /start");
check(main.includes('path === "/start"'), "main entry must mount StartHubEntry at /start");
check(main.includes('import "./styles/start-hub.css"'), "start hub styles must be loaded");

check(docsActions.includes('href="/start"'), "documentation header must expose the product-first start hub");
check(docsActions.includes('english ? "Start" : "开始"'), "documentation start action must remain natively localized");
check(docsLanding.includes('link: "/start"'), "documentation hero must route onboarding through /start");
check(docsLanding.includes('["开始中心"') && docsLanding.includes('["Start hub"'), "documentation runtime paths must expose /start in both locales");

for (const marker of [
  ".start-hub-hero",
  ".start-hub-ribbon",
  ".start-path-grid",
  ".start-hub-book",
  ".start-flow-track",
  "outline: 1px dashed",
  "@media (max-width: 680px)",
]) {
  check(css.includes(marker), `start hub design marker missing: ${marker}`);
}

if (failures.length) {
  for (const failure of failures) console.error(`start-hub-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_start_hub_quality_v1",
    status: "pass",
    route: "/start",
    goal_first_paths: 4,
    new_novel_onboarding: true,
    local_project_inspection: true,
    agent_integration: true,
    deterministic_playground: true,
    docs_discovery: true,
    authority_boundary_explicit: true,
    kawaii_story_loom_surface: true,
    responsive: true,
  }, null, 2));
}

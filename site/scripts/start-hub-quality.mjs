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
const kawaiiCss = read("src/styles/start-hub-kawaii.css");
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
check(entry.includes("authority ≠ capability"), "start surface must preserve authority/capability distinction");
check(!/setInterval\s*\(|requestAnimationFrame\s*\(/.test(entry), "start hub must not add idle animation or polling loops");

check(main.includes('import StartHubEntry from "./StartHubEntry"'), "main entry must import StartHubEntry");
check(main.includes('"/start"'), "standalone surface handoff must include /start");
check(main.includes('path === "/start"'), "main entry must mount StartHubEntry at /start");
check(main.includes('import "./styles/start-hub.css"'), "start hub styles must be loaded");
check(main.includes('import "./styles/start-hub-kawaii.css"'), "start hub kawaii palette layer must be loaded");

check(docsActions.includes('href="/start"'), "documentation header must expose the product-first start hub");
check(docsActions.includes('english ? "Start" : "开始"'), "documentation start action must remain natively localized");
check(docsLanding.includes('link: "/start"'), "documentation hero must route onboarding through /start");
check(docsLanding.includes('["开始中心"') && docsLanding.includes('["Start hub"'), "documentation runtime paths must expose /start in both locales");

for (const marker of [
  ".start-hub-hero",
  ".start-path-grid",
  ".start-path-card",
  ".start-hub-boundary",
  "grid-template-columns: repeat(2, minmax(0, 1fr))",
  "@media (max-width: 760px)",
]) {
  check(css.includes(marker), `start hub clean-layout marker missing: ${marker}`);
}

for (const removedMarker of [
  "start-hub-ribbon",
  "start-hub-book",
  "start-hub-cloud",
  "start-flow-track",
  "start-hub-footer-callout",
]) {
  check(!entry.includes(removedMarker), `start hub should not restore decorative block ${removedMarker}`);
}

for (const marker of [
  "--kawaii-pink-strong",
  ".start-hub-entry .studio-cta",
  ".start-hub-entry .start-path-card:nth-child(4)",
  "var(--kawaii-cream)",
]) {
  check(kawaiiCss.includes(marker), `start hub restrained kawaii marker missing: ${marker}`);
}

check(!kawaiiCss.includes("background-size: 32px 32px"), "start hub must not restore dense decorative grid texture");
check(!kawaiiCss.includes("var(--kawaii-shadow)"), "start hub must not restore heavy framed-surface shadow treatment");

if (failures.length) {
  for (const failure of failures) console.error(`start-hub-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_start_hub_quality_v2",
    status: "pass",
    route: "/start",
    goal_first_paths: 4,
    new_novel_onboarding: true,
    local_project_inspection: true,
    agent_integration: true,
    deterministic_playground: true,
    docs_discovery: true,
    authority_boundary_explicit: true,
    home_like_visual_density: true,
    decorative_preview_removed: true,
    restrained_kawaii_palette: true,
    responsive: true,
  }, null, 2));
}

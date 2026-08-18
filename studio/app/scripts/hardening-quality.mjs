#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const main = read("src/main.tsx");
const resilience = read("src/StudioResilience.tsx");
const index = read("src/styles/index.css");
const hardening = read("src/styles/hardening.css");

for (const marker of ["Suspense", "StudioShellRoot", "StudioFailureBoundary", "StudioSkipLink", "StudioRouteLoading", "StudioNotFound"]) check(main.includes(marker), `Studio runtime missing ${marker}`);
check(main.includes('path="*404"'), "Studio must expose a catch-all 404 route");
check(main.includes("configureOfflineShell().catch(() => undefined)"), "offline-shell configuration must not create an unhandled rejection");
check(resilience.includes("ErrorBoundary"), "Studio must have an ErrorBoundary");
check(resilience.includes('href="#main-content"'), "Studio must expose a skip link to main content");
check(resilience.includes('role="alert"'), "Studio render failure must use alert semantics");
check(resilience.includes('role="status"') && resilience.includes('aria-live="polite"'), "lazy route loading must expose polite status semantics");
check(index.trim().endsWith('@import "./hardening.css";'), "hardening.css must be Studio's final CSS layer");
for (const marker of [":focus-visible", "prefers-reduced-motion:reduce", "forced-colors:active", "pointer:coarse", "overflow-wrap:anywhere"]) check(hardening.includes(marker), `Studio hardening CSS missing ${marker}`);
check(!hardening.includes("!important"), "Studio hardening must not use !important");
const runtimeSource = `${main}\n${resilience}`;
for (const forbidden of ["localStorage.", "sessionStorage.", "setInterval(", "authority: true", "authority:true"]) check(!runtimeSource.includes(forbidden), `Studio resilience introduced forbidden runtime pattern ${forbidden}`);

if (failures.length) {
  for (const failure of failures) console.error(`studio-hardening-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ schema: "quillframe_studio_hardening_v1", status: "pass", suspense: true, error_boundary: true, route_404: true, skip_link: true, offline_shell_rejection_handled: true, focus_visible: true, reduced_motion: true, forced_colors: true }, null, 2));
}

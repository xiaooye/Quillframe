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

const index = read("src/styles/index.css");
const parity = read("src/styles/uiux-parity.css");
const shell = read("src/AppShell.tsx");
const tokens = read("src/styles/vendor/weiui.tokens.generated.css");

check(index.includes('@import "./uiux-parity.css";'), "Studio must load the UIUX parity layer");
check(index.indexOf('@import "./uiux-parity.css";') < index.indexOf('@import "./hardening.css";'), "UIUX parity must load before final hardening");
check(parity.includes("--qf-studio-canvas: var(--wui-color-background)"), "Writer canvas must use the same WeiUI background token as the Product Site");
check(parity.includes(".nf-app-shell") && parity.includes(".nf-main-column"), "Writer shell and main column must share the neutral canvas contract");
check(!parity.includes("var(--qf-product-canvas)"), "UIUX parity must not reintroduce the yellow Quillframe canvas token");
check(tokens.includes("--wui-color-background: oklch(1 0 0)"), "light WeiUI canvas must remain neutral");
check(tokens.includes("--wui-color-background: oklch(0.145 0.010 240)"), "dark WeiUI canvas must remain theme-aware");

check(shell.includes('<StudioIcon name={entry.icon} />'), "Writer navigation must render StudioIcon for every nav entry");
for (const icon of ["home", "workspace", "project", "semantic", "check", "search", "agents"]) {
  check(shell.includes(`icon: "${icon}"`), `Writer navigation missing mapped icon: ${icon}`);
}
check(parity.includes("display: inline-grid") && parity.includes("place-items: center") && parity.includes("stroke: currentColor"), "Sidebar icon slot must explicitly render visible SVG strokes");
check(parity.includes(".nf-sidebar-foot") && parity.includes("display: none"), "Writer Mode sidebar must hide runtime authority jargon");

if (failures.length) {
  for (const failure of failures) console.error(`uiux-parity-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_studio_uiux_parity_v1",
    status: "pass",
    product_site_canvas_parity: true,
    writer_sidebar_icons: true,
    writer_runtime_jargon_hidden: true,
    dark_mode_token_parity: true
  }, null, 2));
}

#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const script = path.join(here, "godot-interaction-qa.mjs");
const args = process.argv.slice(2);
const outputIndex = args.indexOf("--output");
const output = outputIndex >= 0 && outputIndex + 1 < args.length ? args[outputIndex + 1] : "";
const fatalPattern = /memory access out of bounds|RuntimeError|SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i;
const bootstrapRacePattern = /Error: Uncaught[\s\S]*at evaluate[\s\S]*at async snapshot/i;

function run() {
  return spawnSync(process.execPath, [script, ...args], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 });
}

function emit(result) {
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
}

let result = run();
if (result.status === 0) {
  emit(result);
  process.exit(0);
}

const first = `${result.stdout || ""}\n${result.stderr || ""}`;
const evidenceExists = output ? fs.existsSync(output) && fs.statSync(output).size > 0 : false;
const retryable = !evidenceExists && bootstrapRacePattern.test(first) && !fatalPattern.test(first);
if (!retryable) {
  emit(result);
  process.exit(result.status ?? 1);
}

process.stderr.write("godot-interaction-qa-runner: transient pre-document snapshot race; restarting one fresh browser session\n");
Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 350);
result = run();
emit(result);
process.exit(result.status ?? 1);

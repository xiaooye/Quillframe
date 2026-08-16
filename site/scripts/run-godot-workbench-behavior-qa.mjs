#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const script = path.join(here, "godot-workbench-behavior-qa.mjs");
const args = process.argv.slice(2);
const outputIndex = args.indexOf("--output");
const output = outputIndex >= 0 && outputIndex + 1 < args.length ? args[outputIndex + 1] : "";
const fatalPattern = /memory access out of bounds|RuntimeError|SCRIPT ERROR|Parse Error|Invalid call|Invalid access/i;
const bootstrapRacePattern = /Error: Uncaught[\s\S]*at evaluate[\s\S]*at async snapshot/i;

function run() {
  return spawnSync(process.execPath, [script, ...args], {
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function emit(result) {
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
}

function readEvidence() {
  if (!output || !fs.existsSync(output) || fs.statSync(output).size === 0) return null;
  try {
    return JSON.parse(fs.readFileSync(output, "utf8"));
  } catch {
    return null;
  }
}

let result = run();
if (result.status === 0) {
  emit(result);
  process.exit(0);
}

const evidence = readEvidence();
const first = `${result.stdout || ""}\n${result.stderr || ""}\n${evidence?.error || ""}\n${(evidence?.diagnostics || []).join("\n")}`;
const noBehaviorStarted = evidence
  && evidence.status === "fail"
  && Object.keys(evidence.inspector || {}).length === 0
  && Object.keys(evidence.playground || {}).length === 0;
const retryable = noBehaviorStarted && bootstrapRacePattern.test(first) && !fatalPattern.test(first);
if (!retryable) {
  emit(result);
  process.exit(result.status ?? 1);
}

process.stderr.write("godot-workbench-behavior-runner: transient pre-document snapshot race; restarting one fresh browser session\n");
if (output) {
  try { fs.rmSync(output, { force: true }); } catch {}
}
Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 350);
result = run();
emit(result);
process.exit(result.status ?? 1);

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

test("Cloudflare deploy resolves the pinned package-local Wrangler CLI", () => {
  const packageRoot = fileURLToPath(new URL("../", import.meta.url));
  const binary = path.join(packageRoot, "node_modules", ".bin", process.platform === "win32" ? "wrangler.cmd" : "wrangler");
  const run = spawnSync(binary, ["--version"], { encoding: "utf8" });

  assert.equal(run.status, 0, run.error?.message ?? run.stderr);
  assert.match(run.stdout, /4\.124\.0/);
});

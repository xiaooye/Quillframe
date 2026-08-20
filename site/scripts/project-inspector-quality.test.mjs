import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import test from "node:test";

const run = promisify(execFile);
const siteRoot = path.resolve(new URL("..", import.meta.url).pathname);
const qualityScript = path.join(siteRoot, "scripts/project-inspector-quality.mjs");

test("Project Inspector quality gate binds parser checks to the contract owner", async () => {
  const source = fs.readFileSync(qualityScript, "utf8");
  assert.match(source, /src\/project-inspector-contract\.ts/);
  assert.match(source, /inspectorContract\.includes\("file\.text\(\)"\)/);
  assert.match(source, /inspectorContract\.includes\('type InspectionStatus/);

  const temp = await fs.promises.mkdtemp(path.join(os.tmpdir(), "qf-project-inspector-quality-"));
  await fs.promises.cp(path.join(siteRoot, "src"), path.join(temp, "src"), { recursive: true });
  await fs.promises.cp(path.join(siteRoot, "scripts"), path.join(temp, "scripts"), { recursive: true });
  const contractPath = path.join(temp, "src/project-inspector-contract.ts");
  const contract = await fs.promises.readFile(contractPath, "utf8");
  await fs.promises.writeFile(contractPath, contract.replace("file.text()", "file.text_removed()"));

  await assert.rejects(
    run(process.execPath, [path.join(temp, "scripts/project-inspector-quality.mjs")], { cwd: temp }),
    (error) => error.code === 1 && `${error.stdout}\n${error.stderr}`.includes("browser File API"),
  );
});

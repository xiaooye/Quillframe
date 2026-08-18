import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const app = read("src/ProductApp.tsx");
const workbench = read("src/PublicationWorkbench.tsx");
const worker = read("src/publicationCompiler.worker.ts");
const compiler = read("../publication/compiler.py");

const failures = [];
const requireText = (condition, message) => { if (!condition) failures.push(message); };

requireText(app.includes('import PublicationWorkbench from "./PublicationWorkbench"'), "ProductApp must route Publication through PublicationWorkbench");
requireText(!app.includes("夜幕降临，城市的灯光"), "hard-coded publication fixture prose must be removed from ProductApp");
requireText(workbench.includes("quillframe_agent_result_v1"), "playground must recognize the public agent result schema");
requireText(workbench.includes("source_authority_verified"), "playground must expose source authority boundary");
requireText(workbench.includes("brandMark"), "preview branding must use the repository Quillframe mark");
requireText(workbench.includes("downloadArtifact"), "playground must expose real artifact download behavior");
requireText(worker.includes('../../publication/compiler.py?raw'), "worker must execute the repository compiler source, not a copied exporter");
requireText(worker.includes('qf_compile_publication'), "worker must expose a bounded publication compile bridge");
requireText(worker.includes('source_authority_verified": False'), "worker result must never grant uploaded source authority");
requireText(worker.includes('canon_authority": False'), "worker result must never grant Canon authority");
requireText(compiler.includes('PROFILES = {"clean_text", "web_reflow", "print_book", "epub3"}'), "compiler profile contract changed unexpectedly");
requireText(compiler.includes("accepted manuscript fingerprint mismatch"), "compiler accepted-text fingerprint guard is missing");

if (failures.length) {
  console.error("publication playground quality: FAIL");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("publication playground quality: PASS");

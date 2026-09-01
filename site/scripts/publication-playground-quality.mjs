import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const app = read("src/ProductApp.tsx");
const workbench = read("src/PublicationWorkbench.tsx");

const failures = [];
const requireText = (condition, message) => { if (!condition) failures.push(message); };

requireText(app.includes('import PublicationWorkbench from "./PublicationWorkbench"'), "ProductApp must route Publication through PublicationWorkbench");
requireText(!app.includes("夜幕降临，城市的灯光"), "hard-coded publication fixture prose must be removed from ProductApp");
requireText(workbench.includes("native/quillframe-core"), "publication owner must be the native Rust Core");
requireText(workbench.includes("Studio required"), "website must direct consequential publication to Studio");
requireText(workbench.includes("accepts no manuscript") && workbench.includes("creates no file"), "website must state that it does not compile or persist manuscripts");
requireText(!workbench.includes("new Worker") && !workbench.includes("downloadArtifact"), "website must not retain a browser publication runtime");

if (failures.length) {
  console.error("publication playground quality: FAIL");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("publication playground quality: PASS");

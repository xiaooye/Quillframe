import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

const appShell = read("src/AppShell.tsx");
const main = read("src/main.tsx");
const manuscript = read("src/routes/Manuscript.tsx");
const review = read("src/routes/Review.tsx");
const context = read("src/routes/Context.tsx");
const settings = read("src/routes/Settings.tsx");
const publication = read("src/routes/Publication.tsx");
const css = read("src/styles/authoring-product.css");
const bridge = read("src/bridge.ts");

for (const [file, source] of [
  ["AppShell.tsx", appShell], ["Manuscript.tsx", manuscript], ["Review.tsx", review],
  ["Context.tsx", context], ["Settings.tsx", settings], ["Publication.tsx", publication],
]) {
  assert(!/\bfetch\s*\(/.test(source), `${file} must use BridgeClient/invokeBridge instead of fetch`);
  assert(!/indexedDB|openDatabase|better-sqlite|sqlite3/i.test(source), `${file} must not open a browser/database persistence backend`);
  assert(!/cloudflare[_-]?binding|env\.CF_|wrangler/i.test(source), `${file} must not consume Cloudflare bindings`);
}

assert(/class BridgeClient/.test(bridge), "BridgeClient must exist");
assert(/class LocalHttpTransport/.test(bridge), "LocalHttpTransport must exist while local_app is a Core surface");
assert(/class HostedHttpTransport/.test(bridge), "HostedHttpTransport must exist");
assert(/class TauriTransport/.test(bridge), "TauriTransport must exist");
assert(!/VITE_.*TOKEN|ACCESS_TOKEN|API_KEY/.test(bridge), "Bridge transport must not read secret Vite environment variables");

for (const route of ["/manuscript", "/plan", "/story", "/review", "/research", "/learning", "/publication"]) {
  assert(main.includes(`path=\"${route}\"`), `Writer Mode route missing: ${route}`);
}
for (const label of ["Manuscript", "Plan", "Story", "Review", "Research & Corpus", "Learning", "Publish"]) {
  assert(appShell.includes(label), `Writer Mode navigation missing: ${label}`);
}
assert(appShell.includes("author.run.start"), "AI Dock must start a real Core author Run");
assert(appShell.includes("RunProgress") && appShell.includes("run.events.list"), "AI Dock must separate typed progress from missing runtime-event evidence");

assert(manuscript.includes("document.revision.save"), "Manuscript autosave must call document.revision.save");
assert(manuscript.includes("expected_parent_revision_id"), "Manuscript autosave must use optimistic before-state/CAS");
assert(manuscript.includes('authority_class: "proposal"'), "Manuscript autosave must create proposal authority only");
assert(!/localStorage\.setItem\([^\n]*(content|manuscript|canon)/i.test(manuscript), "Manuscript content/Canon must never be stored in localStorage");

assert(review.includes("Accepted ✓") && review.includes("Not Settled"), "Review must visibly separate Accepted from Settled");
assert(review.includes("candidate.accept"), "Accept must use the typed Core authority operation");
assert(review.includes("settlement.preflight"), "Settlement must remain gated on Core preflight");
assert(!review.includes('invokeBridge<SettlementResult>("settlement.apply"'), "Studio must not call settlement.apply without a Core preflight in this contract");

assert(context.includes("ACTUALLY LOADED INTO THIS STAGE"), "Context Inspector must label actually loaded Context");
assert(context.includes("MODEL CONSIDERED RELEVANT"), "Context Inspector must distinguish considered Context");
assert(context.includes("AuthorityLabel"), "Context authority must be textual, not color-only");
assert(context.includes("private_chain_of_thought_exposed"), "Context Inspector must retain the private-CoT boundary");

assert(settings.includes("Endpoint + Access Token"), "AI & Models must preserve the Endpoint + Access Token mental model");
assert(settings.includes('operations().includes("model.connect")'), "Model connection must stay disabled without the Core operation");
assert(settings.includes('setToken("")'), "Access Token field must be cleared after a connection attempt");
assert(!/Provider dashboard|provider type/i.test(settings), "Ordinary Settings must not introduce a Provider dashboard/type chooser");

assert(publication.includes("acceptance_id"), "Publish must consume a Core acceptance_id");
assert(!publication.includes("accepted manuscript text") && !publication.includes("inlineFixture"), "Publish must not let browser input impersonate Accepted text");

assert(css.includes("min-block-size: 44px"), "Writer Mode must enforce 44px touch targets");
assert(css.includes("@media (max-width: 1080px)"), "Tablet responsive behavior must be explicit");
assert(css.includes("@media (max-width: 760px)"), "Phone focus-first behavior must be explicit");
assert(css.includes(".qf-manuscript-editor { order: 1;"), "Phone layout must put the manuscript editor first");
assert(css.includes("prefers-reduced-motion"), "Writer Mode must honor reduced motion");

if (failures.length) {
  console.error("authoring_boundary_quality=FAIL");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("authoring_boundary_quality=PASS");

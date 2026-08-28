import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

const appShell = read("src/AppShell.tsx");
const main = read("src/main.tsx");
const start = read("src/routes/Start.tsx");
const manuscript = read("src/routes/Manuscript.tsx");
const manuscriptBuffer = read("src/authoring/manuscriptBuffer.ts");
const plan = read("src/routes/Plan.tsx");
const story = read("src/routes/Story.tsx");
const learning = read("src/routes/Learning.tsx");
const review = read("src/routes/Review.tsx");
const context = read("src/routes/Context.tsx");
const settings = read("src/routes/Settings.tsx");
const publication = read("src/routes/Publication.tsx");
const css = read("src/styles/authoring-product.css");
const bridge = read("src/bridge.ts");

for (const [file, source] of [
  ["AppShell.tsx", appShell], ["Start.tsx", start], ["Manuscript.tsx", manuscript], ["Review.tsx", review],
  ["Context.tsx", context], ["Settings.tsx", settings], ["Publication.tsx", publication],
  ["Plan.tsx", plan], ["Story.tsx", story], ["Learning.tsx", learning],
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
for (const label of ["Start", "Write", "Review", "Publish", "Plan", "Story", "Research"]) {
  assert(appShell.includes(`en: "${label}"`), `Writer Mode navigation missing: ${label}`);
}
assert(appShell.includes('data-nav-tier="primary"'), "Writer Mode must expose the Start / Write / Review / Publish primary flow");
assert(appShell.includes('data-nav-tier="support"'), "Writer Mode must expose Plan / Story / Research as support navigation");
assert(appShell.includes('data-nav-tier="advanced"'), "Writer Mode must retain advanced diagnostics behind an explicit tier");
assert(appShell.includes('createSignal(false)') && appShell.includes('aria-expanded={inspectorOpen()}'), "Advanced navigation must be collapsed by default and explicitly disclosed");
assert(!/en:\s*"(?:Control|Inspector)"/.test(appShell), "Retired Control / Inspector product navigation must not return");
assert(start.includes('"project.list"'), "Project picker must consume canonical project.list");
assert(appShell.includes("author.run.start"), "AI Dock must register a real Core author Run");
assert(appShell.includes("author.run.execute"), "AI Dock must expose explicit DRAFT/REVISE production execution");
assert(appShell.includes("author.run.status") && !appShell.includes("run.events.list"), "AI Dock progress must use author.run.status rather than a fabricated event API");
assert(appShell.includes('authority: "current_request"'), "Studio may bind the explicit current request as rule_material but must not impersonate Framework/Project authority");
assert(!appShell.includes('authority: "framework"'), "Studio must not forge Framework rule authority");

for (const operation of ["document.list", "document.open", "document.revisions.list", "document.revision.save"]) {
  assert(manuscript.includes(`\"${operation}\"`), `Manuscript must consume ${operation}`);
}
assert(manuscriptBuffer.includes("expected_parent_revision_id"), "Manuscript autosave must use optimistic before-state/CAS");
assert(manuscript.includes("editor.flushAndRefresh") && manuscript.includes("!editor.current()?.dirty"), "Navigation must recheck the editor after asynchronous metadata refresh");
assert(manuscript.includes('authority_class: "proposal"'), "Manuscript autosave must create proposal authority only");
assert(!/localStorage\.setItem\([^\n]*(content|manuscript|canon)/i.test(manuscript), "Manuscript content/Canon must never be stored in localStorage");
assert(plan.includes('"plan.inspect"') && plan.includes('"plan.save"') && plan.includes("expected_version"), "Plans must use Core reads and version-bound writes");
assert(story.includes('"story.inspect"') && story.includes("AuthorityLabel"), "Story facts must use typed Core data with authority labels");
assert(learning.includes('"learning.feedback.observe"') && learning.includes('"learning.preference.review"') && learning.includes("user_authorized: true"), "Learning must separate observation, model review and explicit author authority");

assert(review.includes("Accepted ✓") && review.includes("Settlement unconfirmed")
  && review.includes('settled={settlement()?.status === "settled" ? "true" : "unknown"}'), "Review must separate confirmed settlement from unknown receipt state");
for (const operation of ["candidate.review.get", "candidate.accept", "candidate.reject", "candidate.revision.request", "settlement.preflight", "settlement.apply"]) {
  assert(review.includes(`\"${operation}\"`), `Review must consume ${operation}`);
}
assert(review.indexOf('"settlement.preflight"') < review.indexOf('"settlement.apply"'), "Settlement preflight call must precede settlement.apply in the explicit settle flow");
assert(review.includes("parseReviewSettlementPreflight(preflight.data, detail, accepted, target)")
  && review.includes("expected_before_fingerprint: verifiedPreflight.expected_before_fingerprint"), "Settlement apply must use the exact validated Core preflight before fingerprint");
assert(review.includes("auto-start REVISE") || review.includes("auto-start REVISE") || review.includes("does not auto-start REVISE"), "Request Revision UX must state that REVISE is not auto-started");

assert(context.includes("ACTUALLY LOADED INTO THIS STAGE"), "Context Inspector must label actually loaded Context");
assert(context.includes("MODEL CONSIDERED RELEVANT"), "Context Inspector must distinguish considered Context");
assert(context.includes("AuthorityLabel"), "Context authority must be textual, not color-only");
assert(context.includes("private_chain_of_thought_exposed"), "Context Inspector must retain the private-CoT boundary");

assert(settings.includes("Endpoint + Access Token"), "AI & Models must preserve the Endpoint + Access Token mental model");
assert(settings.includes('operations().includes("model.service.add")'), "Model connection must use model.service.add");
assert(settings.includes('operations().includes("model.service.list")'), "Model list must use model.service.list");
assert(!settings.includes('"model.connect"') && !settings.includes('"model.services.list"'), "Conceptual pre-v8 model operation names must not survive");
assert(settings.includes('setToken("")'), "Access Token field must be cleared after a connection attempt");
assert(!/<select[^>]+(?:name|id)=["'][^"']*provider/i.test(settings), "Ordinary Settings must not introduce a Provider type chooser");
assert(!/Provider Dashboard/.test(settings), "Ordinary Settings must not introduce a Provider dashboard");

assert(publication.includes("acceptance_id"), "Publish must consume a Core acceptance_id");
assert(!publication.includes("accepted manuscript text") && !publication.includes("inlineFixture"), "Publish must not let browser input impersonate Accepted text");
assert(publication.includes('"publication.artifact.get"') && publication.includes("parsePublicationArtifact"), "Downloads must verify actual Core artifact bytes");
assert(publication.includes('"publication.collection.build"') && publication.includes("current_acceptance_id"), "Ordered collections must use current Core acceptance heads");

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

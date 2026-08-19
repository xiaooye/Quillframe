import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (relative) => fs.readFileSync(new URL(`../${relative}`, import.meta.url), "utf8");
const start = read("src/routes/Start.tsx");
const manuscript = read("src/routes/Manuscript.tsx");
const review = read("src/routes/Review.tsx");
const context = read("src/routes/Context.tsx");
const appShell = read("src/AppShell.tsx");
const settings = read("src/routes/Settings.tsx");
const styles = read("src/styles/authoring-product.css");

test("Start and Binder consume canonical Core registries", () => {
  assert.match(start, /project\.list/);
  assert.match(manuscript, /document\.list/);
  assert.match(manuscript, /document\.open/);
  assert.match(manuscript, /document\.revisions\.list/);
});

test("Manuscript exposes autosave status, proposal authority, conflict alert and accessible editor", () => {
  assert.match(manuscript, /aria-live="polite"/);
  assert.match(manuscript, /aria-label=\{zh\(\) \? "正文" : "Manuscript text"\}/);
  assert.match(manuscript, /authority_class: "proposal"/);
  assert.match(manuscript, /revision conflict/);
  assert.match(manuscript, /role="alert"/);
});

test("Review consumes exact evidence and keeps lifecycle operations separate", () => {
  assert.match(review, /candidate\.review\.get/);
  assert.match(review, /candidate\.visible\.get/);
  assert.match(review, /released\(\)\.content/);
  assert.doesNotMatch(review, /detail\(\)\.diff\?\.diff/);
  assert.match(review, /candidate\.accept/);
  assert.match(review, /candidate\.reject/);
  assert.match(review, /candidate\.revision\.request/);
  assert.match(review, /Accepted ✓/);
  assert.match(review, /Not Settled/);
  assert.match(review, /settlement\.preflight/);
  assert.match(review, /settlement\.apply/);
  assert.match(review, /expected_before_fingerprint: preflight\.data\.expected_before_fingerprint/);
});

test("Context Inspector exposes loaded versus considered semantics and textual authority", () => {
  assert.match(context, /ACTUALLY LOADED INTO THIS STAGE/);
  assert.match(context, /MODEL CONSIDERED RELEVANT/);
  assert.match(context, /<AuthorityLabel value=\{item\.authority\}/);
  assert.match(context, /private_chain_of_thought_exposed/);
});

test("AI Dock has keyboard access, explicit production execution and no self-advancing progress timer", () => {
  assert.match(appShell, /event\.key\.toLowerCase\(\) === "i"/);
  assert.match(appShell, /aria-controls="qf-ai-dock"/);
  assert.match(appShell, /author\.run\.start/);
  assert.match(appShell, /author\.run\.execute/);
  assert.match(appShell, /author\.run\.status/);
  assert.match(appShell, /current_request/);
  assert.doesNotMatch(appShell, /setInterval|setTimeout\([^)]*RunProgress/);
});

test("AI & Models remains endpoint-plus-token and token is never persisted by Settings", () => {
  assert.match(settings, /Endpoint \+ Access Token/);
  assert.match(settings, /model\.service\.add/);
  assert.match(settings, /model\.service\.list/);
  assert.match(settings, /type="password"/);
  assert.doesNotMatch(settings, /(?:localStorage|sessionStorage)\.(?:setItem|getItem|removeItem|clear)\s*\(/);
  assert.doesNotMatch(settings, /indexedDB\.(?:open|deleteDatabase)\s*\(/);
});

test("responsive authoring CSS encodes touch and focus-first constraints", () => {
  assert.match(styles, /min-block-size: 44px/);
  assert.match(styles, /@media \(max-width: 1080px\)/);
  assert.match(styles, /@media \(max-width: 760px\)/);
  assert.match(styles, /\.qf-manuscript-editor \{ order: 1;/);
  assert.match(styles, /prefers-reduced-motion/);
});

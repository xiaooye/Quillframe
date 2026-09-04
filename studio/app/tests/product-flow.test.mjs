import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const shell = fs.readFileSync(new URL("../src/AppShell.tsx", import.meta.url), "utf8");
const routes = fs.readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
const agents = fs.readFileSync(new URL("../src/routes/Agents.tsx", import.meta.url), "utf8");
const publication = fs.readFileSync(new URL("../src/routes/Publication.tsx", import.meta.url), "utf8");

test("Studio presents one author journey before support and advanced tools", () => {
  assert.match(shell, /const primaryNavigation: NavEntry\[\]/);
  assert.match(shell, /path: "\/start", en: "Start"/);
  assert.match(shell, /path: "\/manuscript", en: "Write"/);
  assert.match(shell, /path: "\/review", en: "Review"/);
  assert.match(shell, /path: "\/publication", en: "Publish"/);
  assert.match(shell, /const supportNavigation: NavEntry\[\]/);
  assert.match(shell, /path: "\/plan", en: "Plan"/);
  assert.match(shell, /path: "\/story", en: "Story"/);
  assert.match(shell, /path: "\/research", en: "Research"/);
  assert.match(shell, /const advancedNavigation: NavEntry\[\]/);
  assert.match(shell, /data-nav-tier="primary"/);
  assert.match(shell, /data-nav-tier="support"/);
  assert.match(shell, /data-nav-tier="advanced"/);
});

test("every Studio author run binds the selected Core chapter, document and profile", () => {
  assert.match(shell, /chapter_id: chapter\.chapter_id/);
  assert.match(shell, /target_ref: chapter\.document_id/);
  assert.doesNotMatch(shell, /chapter_id: "CH001"/);
  assert.match(shell, /selected_preference_ids: selectedPreferenceIds/);
  assert.match(shell, /author_profile: authorProfile\(\)/);
  assert.match(shell, /const selectedModel = studio\.selectedModel\(\)/);
  assert.match(shell, /model_id: selectedModel\.modelId/);
  assert.match(shell, /model\.model_id === selectedModel\.modelId/);
  assert.match(shell, /createSignal<"guided" \| "expert">\("guided"\)/);
  assert.match(shell, /author\.run\.events/);
  assert.match(shell, /author\.run\.resume/);
  assert.match(shell, /author\.run\.cancel/);
});

test("current UI surfaces name Bridge v11 only", () => {
  assert.doesNotMatch(`${shell}\n${agents}`, /Host Bridge v(?:1|9|10)\b/);
  assert.match(agents, /Host Bridge v11/);
  assert.match(routes, /path="\/start"/);
});

test("Studio keeps the command palette and AI Dock as one modal surface", () => {
  assert.match(shell, /const openPalette[\s\S]*?if \(aiOpen\(\)\) setAiOpen\(false\);[\s\S]*?paletteA11y\.open/);
  assert.match(shell, /const toggleAiDock = \(\) => \{[\s\S]*?if \(paletteOpen\(\)\) \{[\s\S]*?closePalette\(\);[\s\S]*?return;[\s\S]*?\}[\s\S]*?setAiOpen/);
  assert.match(shell, /key\.toLowerCase\(\) === "i"\)[\s\S]*?event\.preventDefault\(\);[\s\S]*?toggleAiDock\(\);/);
  assert.match(shell, /onClick=\{toggleAiDock\}/);
});

test("publication renders manuscript content as text and offers only Core export formats", () => {
  assert.match(publication, /<pre[^>]*>\{result\(\)\.content\}<\/pre>/);
  assert.doesNotMatch(publication, /<iframe|srcdoc=|innerHTML=|preview\?\.content/);
  assert.deepEqual([...publication.matchAll(/<option value="([^"]+)"/g)].map((match) => match[1]), ["md", "txt"]);
  assert.match(publication, /result\(\)\.source_acceptance_id/);
});

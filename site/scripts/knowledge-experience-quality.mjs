#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");
const readJson = (relative) => JSON.parse(read(relative));

const knowledgeExperience = read("src/KnowledgeExperience.tsx");
const knowledgePresentation = read("src/knowledgePresentation.ts");
const documentRenderer = read("src/DocumentRenderer.tsx");
const knowledgeCss = read("src/styles/knowledge-experience.css");
const zhCopy = read("src/content.zh-CN.ts");
const docsIndex = readJson("public/generated/docs-index.json");

const failures = [];
const requireCheck = (condition, message) => {
  if (!condition) failures.push(message);
};

// The replacement Knowledge Portal is mounted beside the legacy Router rather
// than as one of its Route descendants. Nothing rendered by that portal may
// depend on router-context primitives such as <A> or useNavigate/useParams.
for (const [name, source] of [["KnowledgeExperience", knowledgeExperience], ["DocumentRenderer", documentRenderer]]) {
  requireCheck(
    !source.includes('from "@solidjs/router"') && !/<A\b/.test(source) && !/\buse(?:Navigate|Location|Params)\b/.test(source),
    `${name} must remain independent of @solidjs/router context`,
  );
}

// Knowledge links are owned by the replacement portal. pushState already emits
// novelforge:locationchange in main.tsx; a synthetic popstate also wakes the
// legacy @solidjs/router route and previously made document navigation brittle.
requireCheck(
  !knowledgeExperience.includes("new PopStateEvent") && !knowledgeExperience.includes("dispatchEvent(new PopStateEvent"),
  "Knowledge Experience must not synthesize popstate during portal navigation",
);
requireCheck(
  knowledgeExperience.includes('window.history.pushState({}, "", href)') && knowledgeExperience.includes("window.scrollTo(0, 0)"),
  "Knowledge Experience must keep its lightweight pushState navigation path",
);

// Manifest purpose strings are repository-facing and currently English-only.
// Chinese product cards and document headers must derive their visible intro
// from the locale-specific compiled Markdown instead.
requireCheck(
  knowledgePresentation.includes('locale === "zh-CN"') && knowledgePresentation.includes("doc.excerpt || doc.purpose"),
  "zh-CN knowledge summaries must prefer locale-specific excerpts over manifest purpose",
);
requireCheck(
  documentRenderer.includes("localizedDocumentSummary") && !documentRenderer.includes("<p>{props.document.purpose}</p>"),
  "zh-CN document headers must not render manifest purpose directly",
);

// The long-form Knowledge reader deliberately opts out of the generic
// product-document content-visibility placeholder. Reserving 120px for every
// off-screen Markdown block made short guides appear as enormous empty slabs.
requireCheck(
  knowledgeCss.includes("content-visibility: visible") && knowledgeCss.includes("contain-intrinsic-size: none"),
  "Knowledge document reader must disable generic per-block intrinsic placeholders",
);
requireCheck(
  knowledgeCss.includes("--nf-doc-reading: 800px") && knowledgeCss.includes("font-size: 17px"),
  "Knowledge document reader must preserve the professional reading-width and prose-size contract",
);
requireCheck(
  knowledgeCss.includes("border-inline-end") && knowledgeCss.includes("border-inline-start") && knowledgeCss.includes("knowledge-document-toc"),
  "Knowledge document navigation must retain restrained separated side rails",
);

requireCheck(zhCopy.includes('docs: "知识库"'), "zh-CN primary navigation should call the product surface 知识库");
requireCheck(zhCopy.includes('changelog: "版本"'), "zh-CN primary navigation should use the concise native label 版本");

const chineseDocs = docsIndex.documents.filter((doc) => doc.locale === "zh-CN");
requireCheck(chineseDocs.length > 0, "generated knowledge index must contain zh-CN documents");
for (const doc of chineseDocs) {
  const generated = path.join(siteRoot, "public", "generated", "docs", "zh-CN", `${doc.id}.json`);
  requireCheck(fs.existsSync(generated), `generated zh-CN document missing: ${doc.id}`);
}

if (failures.length > 0) {
  for (const failure of failures) console.error(`knowledge-experience-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "novelforge_knowledge_experience_quality_v1",
    status: "pass",
    zh_documents: chineseDocs.length,
    native_chinese_presentation: true,
    synthetic_popstate: false,
    router_context_dependency: false,
    professional_reading_surface: true,
    intrinsic_placeholder_reservation: false,
  }, null, 2));
}

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

const here = path.dirname(fileURLToPath(import.meta.url));
const manifest = JSON.parse(fs.readFileSync(path.resolve(here, "../../docs/documentation_manifest.json"), "utf8"));
const ids = new Set(manifest.documents.map((doc) => doc.id));

const groups = [
  {
    label: "开始",
    translations: { en: "Start" },
    ids: ["why-quillframe", "architecture", "studio-overview"],
  },
  {
    label: "写作",
    translations: { en: "Write" },
    ids: ["production-pipeline", "context-memory", "story-system", "character-system", "canon-state"],
  },
  {
    label: "审阅",
    translations: { en: "Review" },
    ids: ["quality-assurance", "reader-engagement", "quality-evolution", "candidate-lineage", "evals-overview"],
  },
  {
    label: "发布",
    translations: { en: "Publish" },
    ids: ["release-bundle", "product-site-overview"],
  },
  {
    label: "连接与运维",
    translations: { en: "Connect & operate" },
    ids: ["model-runtime", "agent-runtime", "integrations", "project-contract", "studio-product-architecture"],
  },
  {
    label: "高级架构",
    translations: { en: "Advanced architecture" },
    ids: ["architecture-atlas", "adaptive-learning", "corpus-overview", "changelog"],
  },
];

const claimed = new Set(["docs-home"]);
for (const group of groups) {
  group.ids = group.ids.filter((id) => ids.has(id));
  for (const id of group.ids) claimed.add(id);
}

const referenceIds = manifest.documents
  .map((doc) => doc.id)
  .filter((id) => !claimed.has(id));

const sidebar = [
  ...groups.map((group, index) => ({
    label: group.label,
    translations: group.translations,
    items: group.ids,
    collapsed: index > 0,
  })),
  {
    label: "完整参考",
    translations: { en: "Full reference" },
    items: referenceIds,
    collapsed: true,
  },
];

export default defineConfig({
  site: "https://quillframe.wei-dev.com",
  base: "/docs",
  integrations: [
    starlight({
      title: "Quillframe",
      description: "Quillframe documentation for long-form fiction production, project integration, runtime contracts, quality, and publication.",
      logo: {
        src: "./src/assets/quillframe-mark.svg",
        alt: "Quillframe",
      },
      locales: {
        root: {
          label: "简体中文",
          lang: "zh-CN",
        },
        en: {
          label: "English",
          lang: "en",
        },
      },
      defaultLocale: "root",
      sidebar,
      tableOfContents: {
        minHeadingLevel: 2,
        maxHeadingLevel: 3,
      },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/xiaooye/Quillframe",
        },
      ],
      components: {
        SiteTitle: "./src/components/QuillframeSiteTitle.astro",
        PageTitle: "./src/components/QuillframePageTitle.astro",
        SocialIcons: "./src/components/QuillframeActions.astro",
      },
      customCss: [
        "./src/styles/custom.css",
        "./src/styles/article-polish.css",
        "./src/styles/navigation-polish.css",
        "./src/styles/docs-home-clean.css",
        "./src/styles/surface-audit.css",
        "./src/styles/story-loom-docs.css",
        "./src/styles/readability-audit.css",
        "./src/styles/product-header-parity.css",
      ],
      credits: false,
    }),
  ],
  outDir: "../dist/docs",
});

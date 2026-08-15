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
    label: "入门",
    translations: { en: "Getting started" },
    ids: ["why-novelforge", "architecture", "production-pipeline"],
  },
  {
    label: "创作与质量",
    translations: { en: "Writing & quality" },
    ids: ["context-memory", "quality-assurance", "quality-evolution", "adaptive-learning", "story-system", "character-system", "canon-state"],
  },
  {
    label: "Studio 与接入",
    translations: { en: "Studio & integration" },
    ids: ["studio-overview", "studio-product-architecture", "integrations", "project-sdk", "project-adapters"],
  },
  {
    label: "架构与发布",
    translations: { en: "Architecture & release" },
    ids: ["architecture-atlas", "release-bundle", "development-change-inventory"],
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
  site: "https://novelforge.wei-dev.com",
  base: "/docs",
  integrations: [
    starlight({
      title: "NovelForge",
      description: "NovelForge documentation for long-form fiction production, project integration, runtime contracts, quality, and publication.",
      logo: {
        src: "./src/assets/novelforge-mark.svg",
        alt: "NovelForge",
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
          href: "https://github.com/xiaooye/cn_webnovel_agent",
        },
      ],
      components: {
        SiteTitle: "./src/components/NovelForgeSiteTitle.astro",
        PageTitle: "./src/components/NovelForgePageTitle.astro",
        SocialIcons: "./src/components/NovelForgeActions.astro",
      },
      customCss: [
        "./src/styles/custom.css",
        "./src/styles/article-polish.css",
        "./src/styles/navigation-polish.css",
        "./src/styles/docs-home-clean.css",
        "./src/styles/surface-audit.css",
        "./src/styles/story-loom-docs.css",
        "./src/styles/readability-audit.css",
      ],
      credits: false,
    }),
  ],
  outDir: "../dist/docs",
});
import type { DocIndexEntry, KnowledgeLocale } from "./knowledge";

export type KnowledgeJourney =
  | "start"
  | "workflow"
  | "story"
  | "quality"
  | "studio"
  | "publication"
  | "reference";

export type KnowledgeJourneyDefinition = {
  key: KnowledgeJourney;
  icon: string;
  label: Record<KnowledgeLocale, string>;
  description: Record<KnowledgeLocale, string>;
};

export const knowledgeJourneys: KnowledgeJourneyDefinition[] = [
  {
    key: "start",
    icon: "✦",
    label: { "zh-CN": "先从这里开始", "en-US": "Start here" },
    description: {
      "zh-CN": "第一次来？先看 NovelForge 是什么、适合谁，以及从哪里开始。",
      "en-US": "Understand NovelForge, the problems it solves, and the recommended reading path.",
    },
  },
  {
    key: "workflow",
    icon: "✍",
    label: { "zh-CN": "创作与工作流", "en-US": "Writing & workflow" },
    description: {
      "zh-CN": "从规划、写作、审查到接受与结算，看看一章是怎么完整走完的。",
      "en-US": "Follow planning, scenes, generation, review, acceptance, and settlement end to end.",
    },
  },
  {
    key: "story",
    icon: "🧵",
    label: { "zh-CN": "上下文、角色与正典", "en-US": "Context, character & canon" },
    description: {
      "zh-CN": "系统记住什么、角色此刻知道什么，以及长期事实怎样不打架。",
      "en-US": "Learn what the system remembers, what characters may know, and how story truth stays coherent.",
    },
  },
  {
    key: "quality",
    icon: "♡",
    label: { "zh-CN": "审查与质量", "en-US": "Review & quality" },
    description: {
      "zh-CN": "从读者体验、连续性到语义审查，看看一份候选稿为什么能过、为什么会被打回。",
      "en-US": "See how reader engagement, continuity, surface, and semantic review determine readiness.",
    },
  },
  {
    key: "studio",
    icon: "⌘",
    label: { "zh-CN": "Studio 与运行方式", "en-US": "Studio & hosts" },
    description: {
      "zh-CN": "本地网页、云端 Studio、Agent Skill 都怎样接入同一套 Core，以及各自能做什么。",
      "en-US": "Understand Local Web, Hosted Studio, Agent Skill, and their boundaries around Core.",
    },
  },
  {
    key: "publication",
    icon: "📖",
    label: { "zh-CN": "出版与派生格式", "en-US": "Publication & formats" },
    description: {
      "zh-CN": "从已接受正文生成网页、纯文本、印刷版和 EPUB，同时不改变正文权威。",
      "en-US": "Derive web, text, print, and EPUB outputs from accepted text without moving manuscript authority.",
    },
  },
  {
    key: "reference",
    icon: "⌁",
    label: { "zh-CN": "架构与参考", "en-US": "Architecture & reference" },
    description: {
      "zh-CN": "想查精确契约、架构关系、运行时细节或开发记录时，从这里找。",
      "en-US": "Go deeper into contracts, architecture maps, runtime details, and development inventories.",
    },
  },
];

const includesAny = (value: string, terms: string[]) => terms.some((term) => value.includes(term));

export function knowledgeJourneyFor(doc: DocIndexEntry): KnowledgeJourney {
  const haystack = `${doc.id} ${doc.title} ${doc.purpose} ${doc.sourcePath} ${doc.headings.join(" ")}`.toLocaleLowerCase();

  if (includesAny(haystack, [
    "studio", "host bridge", "host-bridge", "hosted", "local web", "tauri", "agent skill", "mcp", "runtime routing",
    "宿主", "工作台", "本地 web", "托管",
  ])) return "studio";

  if (includesAny(haystack, [
    "publication", "epub", "typesetting", "print_book", "print book", "web_reflow", "clean_text", "出版", "排版", "印刷",
  ])) return "publication";

  if (includesAny(haystack, [
    "quality", "reader", "continuity", "surface", "gate", "review", "candidate", "regression", "semantic", "qa", "质量", "读者", "连续性", "审查", "候选稿",
  ])) return "quality";

  if (includesAny(haystack, [
    "context", "canon", "character", "knowledge", "relationship", "story mechanics", "story simulation", "context packet", "正典", "上下文", "角色", "关系", "故事机制",
  ])) return "story";

  if (includesAny(haystack, [
    "production pipeline", "workflow", "draft", "revise", "scene", "settlement", "acceptance", "plan", "生产流水线", "工作流", "草稿", "修订", "场景", "结算", "接受",
  ])) return "workflow";

  if (doc.tier === "A" && includesAny(haystack, [
    "readme", "why novelforge", "documentation", "introduction", "start", "overview", "why-novelforge", "文档中心", "为什么", "架构总览",
  ])) return "start";

  return "reference";
}

export function knowledgeJourneyDefinition(key: KnowledgeJourney) {
  return knowledgeJourneys.find((journey) => journey.key === key) ?? knowledgeJourneys[0];
}

export function humanDocKind(doc: DocIndexEntry, locale: KnowledgeLocale): string {
  const labels = locale === "zh-CN"
    ? { A: "核心指南", B: "深入指南", C: "参考资料" }
    : { A: "Core guide", B: "Deep dive", C: "Reference" };
  return labels[doc.tier as "A" | "B" | "C"] ?? (locale === "zh-CN" ? "文档" : "Guide");
}

function compactSummary(value: string, title: string): string {
  let raw = value.replace(/&nbsp;|\s+/g, " ").trim();
  if (title && raw.startsWith(title)) raw = raw.slice(title.length).trim();
  return raw.length > 190 ? `${raw.slice(0, 187).trimEnd()}…` : raw;
}

export function readableDocSummary(doc: DocIndexEntry, locale: KnowledgeLocale): string {
  // The manifest purpose is intentionally repository-facing and currently English-only.
  // Chinese cards therefore lead with the locale-specific compiled document excerpt so
  // product UI never leaks English maintenance copy into a zh-CN reading surface.
  const localizedSource = locale === "zh-CN"
    ? (doc.excerpt || doc.purpose || "")
    : (doc.purpose || doc.excerpt || "");
  const summary = compactSummary(localizedSource, doc.title);
  if (summary) return summary;
  return locale === "zh-CN" ? "打开这篇文档继续阅读。" : "Open this guide to continue reading.";
}

export function recommendedStartDocs(docs: DocIndexEntry[]): DocIndexEntry[] {
  const score = (doc: DocIndexEntry) => {
    const haystack = `${doc.id} ${doc.title} ${doc.sourcePath}`.toLocaleLowerCase();
    let value = 0;
    if (doc.tier === "A") value += 20;
    if (includesAny(haystack, ["why-novelforge", "why novelforge", "为什么是 novelforge"])) value += 90;
    if (includesAny(haystack, ["readme.zh-cn", "readme.en", "documentation", "文档中心"])) value += 70;
    if (includesAny(haystack, ["architecture-atlas", "架构图谱"])) value += 60;
    if (includesAny(haystack, ["production-pipeline", "生产流水线"])) value += 50;
    return value;
  };

  return [...docs].sort((a, b) => score(b) - score(a) || a.title.localeCompare(b.title)).slice(0, 4);
}

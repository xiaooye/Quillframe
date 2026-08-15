export type KnowledgeLocale = "en-US" | "zh-CN";

export type DocIndexEntry = {
  id: string;
  locale: KnowledgeLocale;
  tier: "A" | "B" | "C" | string;
  status: string;
  title: string;
  purpose: string;
  audience: string;
  sourcePath: string;
  sourceFingerprint: string;
  freshnessOwner: string;
  excerpt: string;
  headings: string[];
  searchText: string;
};

export type DocIndex = {
  schema: "novelforge_product_document_index_v1";
  authority: false;
  frameworkVersion: string;
  manifestSchema: string;
  documentCount: number;
  documents: DocIndexEntry[];
};

export type InlineNode =
  | { type: "text"; text: string }
  | { type: "code"; text: string }
  | { type: "strong"; children: InlineNode[] }
  | { type: "em"; children: InlineNode[] }
  | { type: "del"; children: InlineNode[] }
  | { type: "link"; href: string; title?: string | null; children: InlineNode[] }
  | { type: "image"; href?: string | null; alt: string; title?: string | null }
  | { type: "br" };

export type DocumentBlock =
  | { type: "heading"; level: number; id: string; inlines: InlineNode[] }
  | { type: "paragraph"; inlines: InlineNode[] }
  | { type: "code"; lang: string; text: string }
  | { type: "blockquote"; blocks: DocumentBlock[] }
  | { type: "list"; ordered: boolean; start?: number | null; items: DocumentBlock[][] }
  | { type: "table"; align?: Array<string | null>; header: InlineNode[][]; rows: InlineNode[][][] }
  | { type: "hr" };

export type ProductDocument = {
  schema: "novelforge_product_document_v1";
  authority: false;
  generatedFrom: string;
  id: string;
  locale: KnowledgeLocale;
  tier: string;
  status: string;
  title: string;
  purpose: string;
  audience: string;
  sourcePath: string;
  sourceFingerprint: string;
  freshnessOwner: string;
  authoritySources: string[];
  toc: Array<{ level: number; id: string; text: string }>;
  blocks: DocumentBlock[];
};

let indexPromise: Promise<DocIndex> | undefined;

export function loadKnowledgeIndex(): Promise<DocIndex> {
  indexPromise ??= fetch("/generated/docs-index.json", { cache: "force-cache" }).then(async (response) => {
    if (!response.ok) throw new Error(`Knowledge index failed: ${response.status}`);
    const payload = await response.json() as DocIndex;
    if (payload.schema !== "novelforge_product_document_index_v1" || payload.authority !== false) {
      throw new Error("Knowledge index contract mismatch");
    }
    return payload;
  });
  return indexPromise;
}

export async function loadProductDocument(locale: KnowledgeLocale, id: string | undefined): Promise<ProductDocument> {
  if (!id) throw new Error("Document id is required");
  const response = await fetch(`/generated/docs/${locale}/${encodeURIComponent(id)}.json`, { cache: "force-cache" });
  if (!response.ok) throw new Error(`Document failed: ${response.status}`);
  const payload = await response.json() as ProductDocument;
  if (payload.schema !== "novelforge_product_document_v1" || payload.authority !== false) {
    throw new Error("Document contract mismatch");
  }
  return payload;
}

const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase().trim();

export function searchKnowledge(index: DocIndex | undefined, locale: KnowledgeLocale, query: string, limit = 10): DocIndexEntry[] {
  if (!index) return [];
  const q = normalize(query);
  const local = index.documents.filter((doc) => doc.locale === locale);
  if (!q) return local.slice(0, limit);

  const terms = Array.from(new Set([q, ...q.split(/\s+/).filter((term) => term.length > 1)]));
  const score = (doc: DocIndexEntry) => {
    const title = normalize(doc.title);
    const purpose = normalize(doc.purpose);
    const excerpt = normalize(doc.excerpt);
    const headings = normalize(doc.headings.join(" "));
    const body = normalize(doc.searchText);
    let total = 0;
    for (const term of terms) {
      if (title.includes(term)) total += 14;
      if (headings.includes(term)) total += 7;
      if (purpose.includes(term)) total += 5;
      if (excerpt.includes(term)) total += 3;
      if (body.includes(term)) total += 1;
    }
    if (title.startsWith(q)) total += 8;
    return total;
  };

  return local
    .map((doc) => ({ doc, score: score(doc) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.doc.title.localeCompare(b.doc.title, locale))
    .slice(0, limit)
    .map((item) => item.doc);
}

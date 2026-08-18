export type Locale = "en-US" | "zh-CN";

export type Card = {
  eyebrow?: string;
  title: string;
  body: string;
  meta?: string;
};

export type RouteCopy = {
  eyebrow: string;
  title: string;
  lede: string;
  cards: Card[];
  note?: string;
};

export const githubRoot = "https://github.com/xiaooye/Quillframe";

export function sourceUrl(path: string): string {
  return `${githubRoot}/blob/main/${path}`;
}

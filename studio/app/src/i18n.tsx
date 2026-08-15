import { createContext, createResource, createSignal, ParentComponent, useContext } from "solid-js";
import type { MessageKey, Messages } from "./locales/types";

export type Locale = "en-US" | "zh-CN";

const loaders: Record<Locale, () => Promise<{ default: Messages }>> = {
  "en-US": () => import("./locales/en-US"),
  "zh-CN": () => import("./locales/zh-CN"),
};

function initialLocale(): Locale {
  const requested = new URLSearchParams(window.location.search).get("lang");
  if (requested === "en-US" || requested === "zh-CN") return requested;
  const language = navigator.language.toLowerCase();
  return language.startsWith("zh") ? "zh-CN" : "en-US";
}

interface I18nValue {
  locale: () => Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}

const I18nContext = createContext<I18nValue>();

export const I18nProvider: ParentComponent = (props) => {
  const [locale, setLocaleSignal] = createSignal<Locale>(initialLocale());
  const [messages] = createResource(locale, async (next) => (await loaders[next]()).default);

  const setLocale = (next: Locale) => {
    setLocaleSignal(next);
    document.documentElement.lang = next;
  };

  document.documentElement.lang = locale();

  const value: I18nValue = {
    locale,
    setLocale,
    t: (key) => messages()?.[key] ?? key,
  };

  return <I18nContext.Provider value={value}>{props.children}</I18nContext.Provider>;
};

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("I18nProvider is missing");
  return value;
}

import { create } from "zustand";
import { LANGS, type Lang, translations } from "./translations";

export { LANGS } from "./translations";
export type { Lang } from "./translations";

function dirFor(lang: Lang): "ltr" | "rtl" {
  return LANGS.find((l) => l.code === lang)?.dir ?? "ltr";
}

/** Apply text direction + lang attribute to <html> so RTL works app-wide. */
function applyDocument(lang: Lang): void {
  const root = document.documentElement;
  root.dir = dirFor(lang);
  root.lang = lang;
}

// localStorage can throw (Safari private mode) or be unavailable (SSR/tests) —
// degrade gracefully to the default language rather than crashing on import.
function initialLang(): Lang {
  try {
    const stored = localStorage.getItem("lang");
    return stored === "he" || stored === "en" ? stored : "en";
  } catch {
    return "en";
  }
}

function persistLang(lang: Lang): void {
  try {
    localStorage.setItem("lang", lang);
  } catch {
    /* ignore — preference just won't persist */
  }
}

interface I18nState {
  lang: Lang;
  setLang: (lang: Lang) => void;
}

export const useI18n = create<I18nState>((set) => ({
  lang: initialLang(),
  setLang: (lang) => {
    persistLang(lang);
    applyDocument(lang);
    set({ lang });
  },
}));

// Apply direction on first load.
applyDocument(useI18n.getState().lang);

export function translate(
  lang: Lang,
  key: string,
  params?: Record<string, string | number>,
): string {
  let s = translations[lang]?.[key] ?? translations.en[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      s = s.replaceAll(`{${k}}`, String(v));
    }
  }
  return s;
}

/** Hook: returns a `t` bound to the current language and re-renders on change. */
export function useTranslation() {
  const lang = useI18n((s) => s.lang);
  const setLang = useI18n((s) => s.setLang);
  const t = (key: string, params?: Record<string, string | number>) =>
    translate(lang, key, params);
  return { t, lang, dir: dirFor(lang), setLang };
}

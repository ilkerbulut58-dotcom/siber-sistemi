import type { Locale } from "./types";

let activeLocale: Locale = "tr";

export function getActiveLocale(): Locale {
  return activeLocale;
}

export function setActiveLocale(locale: Locale): void {
  activeLocale = locale;
}

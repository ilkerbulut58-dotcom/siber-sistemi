import { de } from "./de";
import { getActiveLocale } from "./locale-store";
import { tr } from "./tr";
import type { Dictionary, Locale } from "./types";

export type { Dictionary, Locale };
export { LOCALES, LOCALE_STORAGE_KEY } from "./types";
export { tr, de };

export const dictionaries: Record<Locale, Dictionary> = { tr, de };

export function resolveLocale(locale?: string | null): Locale {
  if (locale === "de" || locale === "tr") return locale;
  const active = getActiveLocale();
  if (active === "de" || active === "tr") return active;
  return "tr";
}

function dictionaryFor(locale?: string | null): Dictionary {
  return dictionaries[resolveLocale(locale)];
}

function getNestedValue(obj: unknown, path: string): string | undefined {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null || typeof current !== "object") return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current : undefined;
}

export function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? `{${key}}`));
}

export function translate(
  locale: Locale,
  key: string,
  params?: Record<string, string | number>
): string {
  const dict = dictionaries[locale];
  const value = getNestedValue(dict, key);
  if (value) return interpolate(value, params);
  return key;
}

export function translateError(locale: Locale, code: string, fallback?: string): string {
  const translated = dictionaryFor(locale).errors[code];
  if (translated) {
    if (
      code === "REQUEST_FAILED" &&
      fallback &&
      fallback !== "Request failed" &&
      fallback !== translated
    ) {
      return fallback;
    }
    return translated;
  }
  return fallback ?? code;
}

export function scanProfileLabel(locale: Locale, name: string, fallback?: string): string {
  return dictionaries[locale].scanProfile[name]?.label ?? fallback ?? name;
}

export function scanProfileDescription(locale: Locale, name: string, fallback?: string): string {
  return dictionaries[locale].scanProfile[name]?.description ?? fallback ?? "";
}

export function severityLabel(locale: Locale, severity: string): string {
  return dictionaries[locale].severity[severity] ?? severity;
}

export function scanStatusLabel(locale: Locale, status: string): string {
  return dictionaries[locale].scanStatus[status] ?? status;
}

export function scanRiskSummary(locale: Locale, counts: Record<string, number>): string {
  const dict = dictionaries[locale].scanRisk;
  if ((counts.critical ?? 0) > 0 || (counts.high ?? 0) > 0) return dict.critical;
  if ((counts.medium ?? 0) > 0) return dict.medium;
  if ((counts.low ?? 0) + (counts.info ?? 0) > 0) return dict.low;
  return dict.none;
}

export function onboardingStepLabel(locale: Locale, stepId: string): string {
  const labels = dictionaries[locale].onboarding as Record<string, string>;
  return labels[stepId] ?? stepId;
}

export function findingStatusLabel(locale: Locale, status: string): string {
  return dictionaries[locale].findingStatus[status] ?? status;
}

export function findingWorkflowLabel(locale: Locale, status: string): string {
  return dictionaries[locale].findingWorkflow[status] ?? status;
}

export function verificationFailureLabel(locale: Locale, code: string | null | undefined): string {
  if (!code) return "";
  return translateError(locale, code, code);
}

export function conceptTooltip(locale: Locale, key: string): string {
  const tips = dictionaries[locale].conceptTooltips as Record<string, string> | undefined;
  return tips?.[key] ?? "";
}

export function verificationStatusLabel(locale: Locale, status: string): string {
  return dictionaries[locale].verificationStatus[status] ?? status;
}

export function historyEventLabel(locale: Locale, event: string): string {
  return dictionaries[locale].historyEvent[event] ?? event;
}

export function securityLevelLabel(locale: Locale, level: string): string {
  return dictionaries[locale].securityLevel[level] ?? level;
}

export function sourceToolLabel(locale: Locale | string | undefined, tool: string | null | undefined): string {
  if (!tool) return "—";
  return dictionaryFor(locale).sourceTool[tool] ?? tool;
}

export function assetTypeLabel(locale: Locale, type: string): string {
  return dictionaries[locale].assetType[type] ?? type;
}

export function confidenceLabel(locale: Locale, confidence: string | null | undefined): string {
  if (!confidence) return "—";
  return dictionaries[locale].confidence[confidence] ?? confidence;
}

export function aiConfidenceLabel(locale: Locale, label: string | null | undefined): string {
  if (!label) return "—";
  return dictionaries[locale].aiConfidence[label] ?? label;
}

export function parseApiError(err: unknown): { code: string; message: string } {
  if (err instanceof ApiError) return { code: err.code, message: err.message };
  if (err instanceof Error) return { code: "REQUEST_FAILED", message: err.message };
  return { code: "REQUEST_FAILED", message: "Request failed" };
}

export class ApiError extends Error {
  retryAfterSeconds?: number;

  constructor(
    public code: string,
    message: string,
    retryAfterSeconds?: number
  ) {
    super(message);
    this.name = "ApiError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export function formatApiError(locale: Locale, err: unknown): string {
  const parsed = parseApiError(err);
  return translateError(locale, parsed.code, parsed.message);
}

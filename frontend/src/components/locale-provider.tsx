"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  findingStatusLabel as findingStatusLabelFn,
  findingWorkflowLabel as findingWorkflowLabelFn,
  formatApiError,
  historyEventLabel as historyEventLabelFn,
  interpolate,
  onboardingStepLabel,
  scanProfileDescription,
  scanProfileLabel,
  scanRiskSummary,
  scanStatusLabel,
  severityLabel,
  translate,
  translateError,
  verificationStatusLabel as verificationStatusLabelFn,
  confidenceLabel as confidenceLabelFn,
  aiConfidenceLabel as aiConfidenceLabelFn,
  type Locale,
} from "@/lib/i18n";
import { setActiveLocale } from "@/lib/i18n/locale-store";
import { LOCALE_STORAGE_KEY } from "@/lib/i18n/types";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  translateError: (code: string, fallback?: string) => string;
  formatApiError: (err: unknown) => string;
  scanProfileLabel: (name: string, fallback?: string) => string;
  scanProfileDescription: (name: string, fallback?: string) => string;
  severityLabel: (severity: string) => string;
  scanStatusLabel: (status: string) => string;
  scanRiskSummary: (counts: Record<string, number>) => string;
  onboardingStepLabel: (stepId: string) => string;
  findingStatusLabel: (status: string) => string;
  findingWorkflowLabel: (status: string) => string;
  verificationStatusLabel: (status: string) => string;
  historyEventLabel: (event: string) => string;
  confidenceLabel: (confidence: string | null | undefined) => string;
  aiConfidenceLabel: (label: string | null | undefined) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readStoredLocale(): Locale {
  if (typeof window === "undefined") return "tr";
  return localStorage.getItem(LOCALE_STORAGE_KEY) === "de" ? "de" : "tr";
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("tr");

  useEffect(() => {
    const stored = readStoredLocale();
    setActiveLocale(stored);
    setLocaleState(stored);
    document.documentElement.lang = stored;
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setActiveLocale(next);
    localStorage.setItem(LOCALE_STORAGE_KEY, next);
    document.documentElement.lang = next;
    setLocaleState(next);
  }, []);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale,
      t: (key, params) => translate(locale, key, params),
      translateError: (code, fallback) => translateError(locale, code, fallback),
      formatApiError: (err) => formatApiError(locale, err),
      scanProfileLabel: (name, fallback) => scanProfileLabel(locale, name, fallback),
      scanProfileDescription: (name, fallback) =>
        scanProfileDescription(locale, name, fallback),
      severityLabel: (s) => severityLabel(locale, s),
      scanStatusLabel: (s) => scanStatusLabel(locale, s),
      scanRiskSummary: (counts) => scanRiskSummary(locale, counts),
      onboardingStepLabel: (stepId) => onboardingStepLabel(locale, stepId),
      findingStatusLabel: (s) => findingStatusLabelFn(locale, s),
      findingWorkflowLabel: (s) => findingWorkflowLabelFn(locale, s),
      verificationStatusLabel: (s) => verificationStatusLabelFn(locale, s),
      historyEventLabel: (e) => historyEventLabelFn(locale, e),
      confidenceLabel: (c) => confidenceLabelFn(locale, c),
      aiConfidenceLabel: (l) => aiConfidenceLabelFn(locale, l),
    }),
    [locale, setLocale]
  );

  return (
    <LocaleContext.Provider value={value}>
      <div key={locale}>{children}</div>
    </LocaleContext.Provider>
  );
}

export function useTranslation() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useTranslation must be used within LocaleProvider");
  return ctx;
}

export { interpolate };

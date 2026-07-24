/** Locale-aware label helpers — always read active locale from store. */
import {
  aiConfidenceLabel as aiConfidenceLabelFn,
  confidenceLabel as confidenceLabelFn,
  findingStatusLabel as findingStatusLabelFn,
  findingWorkflowLabel as findingWorkflowLabelFn,
  historyEventLabel as historyEventLabelFn,
  scanProfileDescription as scanProfileDescriptionFn,
  scanProfileLabel as scanProfileLabelFn,
  scanRiskSummary as scanRiskSummaryFn,
  scanStatusLabel as scanStatusLabelFn,
  severityLabel as severityLabelFn,
  verificationStatusLabel as verificationStatusLabelFn,
} from "@/lib/i18n";
import { getActiveLocale } from "@/lib/i18n/locale-store";

export function scanProfileLabel(name: string, fallback?: string): string {
  return scanProfileLabelFn(getActiveLocale(), name, fallback);
}

export function scanProfileDescription(name: string, fallback?: string): string {
  return scanProfileDescriptionFn(getActiveLocale(), name, fallback);
}

export function severityLabel(severity: string): string {
  return severityLabelFn(getActiveLocale(), severity);
}

export function confidenceLabel(confidence: string | null | undefined): string {
  return confidenceLabelFn(getActiveLocale(), confidence);
}

export function aiConfidenceLabel(label: string | null | undefined): string {
  return aiConfidenceLabelFn(getActiveLocale(), label);
}

export function scanRiskSummary(counts: Record<string, number>): string {
  return scanRiskSummaryFn(getActiveLocale(), counts);
}

export function scanStatusLabel(status: string): string {
  return scanStatusLabelFn(getActiveLocale(), status);
}

export function findingStatusLabel(status: string): string {
  return findingStatusLabelFn(getActiveLocale(), status);
}

export function findingWorkflowLabel(status: string): string {
  return findingWorkflowLabelFn(getActiveLocale(), status);
}

export function verificationStatusLabel(status: string): string {
  return verificationStatusLabelFn(getActiveLocale(), status);
}

export function historyEventLabel(event: string): string {
  return historyEventLabelFn(getActiveLocale(), event);
}

/** @deprecated Use scanStatusLabel() — kept for gradual migration */
export const SCAN_STATUS_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => scanStatusLabel(prop),
});

/** @deprecated Use findingWorkflowLabel() */
export const FINDING_WORKFLOW_STATUS_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => findingWorkflowLabel(prop),
});

/** @deprecated Use verificationStatusLabel() */
export const VERIFICATION_STATUS_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => verificationStatusLabel(prop),
});

/** @deprecated Use historyEventLabel() */
export const HISTORY_EVENT_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => historyEventLabel(prop),
});

/** @deprecated Use severityLabel() */
export const SEVERITY_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => severityLabel(prop),
});

export const STATUS_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => findingStatusLabel(prop),
});
export const CONFIDENCE_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => confidenceLabel(prop) || prop,
});

export const AI_CONFIDENCE_TR = new Proxy({} as Record<string, string>, {
  get: (_target, prop: string) => aiConfidenceLabel(prop) || prop,
});

export const SCAN_PROFILE_TR = new Proxy({} as Record<string, { label: string; description: string }>, {
  get: (_target, prop: string) => ({
    label: scanProfileLabel(prop),
    description: scanProfileDescription(prop),
  }),
});

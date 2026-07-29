import type { Finding } from "@/lib/api-types";

export type FindingFilterState = {
  severity: string;
  confidence: string;
  status: string;
  source: string;
  review: string;
  lifecycle: string;
  query: string;
};

export const DEFAULT_FINDING_FILTERS: FindingFilterState = {
  severity: "all",
  confidence: "all",
  status: "all",
  source: "all",
  review: "all",
  lifecycle: "all",
  query: "",
};

function matchesReview(f: Finding, review: string): boolean {
  if (review === "all") return true;
  if (review === "confirmed") return f.verification_status === "verified";
  if (review === "needs_review") {
    return f.verification_status === "unverified" || f.verification_status === "inconclusive";
  }
  if (review === "informational") return f.severity === "info";
  return true;
}

function matchesLifecycle(f: Finding, lifecycle: string): boolean {
  if (lifecycle === "all") return true;
  if (lifecycle === "fixed") return f.status === "resolved";
  if (lifecycle === "reopened") return false;
  if (lifecycle === "new") return f.status === "open";
  return true;
}

export function filterFindings(findings: Finding[], filters: FindingFilterState): Finding[] {
  const q = filters.query.trim().toLowerCase();
  return findings.filter((f) => {
    if (filters.severity !== "all" && f.severity !== filters.severity) return false;
    if (filters.confidence !== "all" && (f.confidence ?? "") !== filters.confidence) return false;
    if (filters.status !== "all" && f.status !== filters.status) return false;
    if (filters.source !== "all") {
      const tools = f.source_tools?.length ? f.source_tools : [f.source_tool];
      if (!tools.includes(filters.source)) return false;
    }
    if (!matchesReview(f, filters.review)) return false;
    if (!matchesLifecycle(f, filters.lifecycle)) return false;
    if (q) {
      const hay = [
        f.title,
        f.description,
        f.affected_url,
        f.source_tool,
        ...(f.source_tools ?? []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

export function uniqueSources(findings: Finding[]): string[] {
  const set = new Set<string>();
  for (const f of findings) {
    if (f.source_tool) set.add(f.source_tool);
    for (const t of f.source_tools ?? []) set.add(t);
  }
  return [...set].sort();
}

import type { Finding, ScanJob } from "@/lib/api-client";

export type SecurityLevel = "critical" | "weak" | "medium" | "good" | "strong";

export interface SecurityScoreResult {
  score: number;
  level: SecurityLevel;
  label: string;
}

export interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface TrendPoint {
  scanId: string;
  label: string;
  score: number;
  date: string;
}

export interface HeaderStatusItem {
  key: string;
  label: string;
  shortLabel: string;
  status: "present" | "missing" | "recommended";
}

const LEVEL_LABELS: Record<SecurityLevel, string> = {
  critical: "Kritik",
  weak: "Zayıf",
  medium: "Orta",
  good: "İyi",
  strong: "Güçlü",
};

const SEVERITY_WEIGHT: Record<string, number> = {
  critical: 28,
  high: 18,
  medium: 10,
  low: 4,
  info: 1,
};

const HEADER_DEFS: Omit<HeaderStatusItem, "status">[] = [
  { key: "content-security-policy", label: "Content-Security-Policy", shortLabel: "CSP" },
  { key: "strict-transport-security", label: "Strict-Transport-Security", shortLabel: "HSTS" },
  { key: "x-frame-options", label: "X-Frame-Options", shortLabel: "X-Frame" },
  { key: "x-content-type-options", label: "X-Content-Type-Options", shortLabel: "X-Content" },
  { key: "referrer-policy", label: "Referrer-Policy", shortLabel: "Referrer" },
  { key: "permissions-policy", label: "Permissions-Policy", shortLabel: "Permissions" },
];

export function countBySeverity(findings: Finding[]): SeverityCounts {
  const counts: SeverityCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  for (const f of findings) {
    const key = f.severity as keyof SeverityCounts;
    if (key in counts) counts[key] += 1;
  }
  return counts;
}

export function computeSecurityScore(findings: Finding[]): SecurityScoreResult {
  if (findings.length === 0) {
    return { score: 95, level: "strong", label: LEVEL_LABELS.strong };
  }

  const withRisk = findings.filter((f) => f.risk_score != null);
  let score: number;

  if (withRisk.length > 0) {
    const avgRisk =
      withRisk.reduce((sum, f) => sum + (f.risk_score ?? 0), 0) / withRisk.length;
    const maxRisk = Math.max(...withRisk.map((f) => f.risk_score ?? 0));
    score = Math.round(Math.max(0, Math.min(100, 100 - avgRisk * 0.72 - maxRisk * 0.08)));
  } else {
    let penalty = 0;
    for (const f of findings) {
      penalty += SEVERITY_WEIGHT[f.severity] ?? 6;
    }
    score = Math.round(Math.max(0, Math.min(100, 100 - penalty)));
  }

  const level = scoreToLevel(score);
  return { score, level, label: LEVEL_LABELS[level] };
}

export function scoreToLevel(score: number): SecurityLevel {
  if (score < 40) return "critical";
  if (score < 60) return "weak";
  if (score < 80) return "medium";
  if (score < 90) return "good";
  return "strong";
}

export function scoreColor(score: number): string {
  if (score < 40) return "#ef4444";
  if (score < 60) return "#f97316";
  if (score < 80) return "#eab308";
  return "#22c55e";
}

export function countSourceTools(findings: Finding[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const f of findings) {
    const tools = f.source_tools?.length ? f.source_tools : [f.source_tool];
    for (const tool of tools) {
      const label = formatSourceTool(tool);
      counts[label] = (counts[label] ?? 0) + 1;
    }
  }
  return counts;
}

export function formatSourceTool(tool: string): string {
  const map: Record<string, string> = {
    passive_http: "HTTP Kontrolleri",
    tls_check: "TLS/SSL",
    zap: "ZAP",
    nuclei: "Nuclei",
    deep_scan: "Derin Tarama",
    code_scan: "Kod Taraması",
    correlated: "Korelasyon",
  };
  return map[tool] ?? tool;
}

export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url.replace(/^https?:\/\//, "").split("/")[0];
  }
}

export function formatScanDuration(scan: ScanJob): string | null {
  if (!scan.started_at || !scan.completed_at) return null;
  const ms = new Date(scan.completed_at).getTime() - new Date(scan.started_at).getTime();
  if (ms < 1000) return `${ms} ms`;
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec} sn`;
  return `${Math.floor(sec / 60)} dk ${sec % 60} sn`;
}

export function getTopFindings(findings: Finding[], limit = 8): Finding[] {
  return [...findings]
    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .slice(0, limit);
}

export function getHeaderStatuses(findings: Finding[]): HeaderStatusItem[] {
  const missingKeys = new Set<string>();
  for (const f of findings) {
    const key = f.correlation_key ?? f.source_rule_id ?? "";
    if (key.startsWith("missing-header-")) {
      missingKeys.add(key.replace("missing-header-", ""));
    }
  }

  return HEADER_DEFS.map((h) => ({
    ...h,
    status: missingKeys.has(h.key)
      ? "missing"
      : findings.some(
            (f) =>
              f.correlation_key?.includes(h.key) ||
              f.title.toLowerCase().includes(h.shortLabel.toLowerCase())
          )
        ? "recommended"
        : "present",
  }));
}

export function buildPrioritySummary(findings: Finding[]): string[] {
  const missing = getHeaderStatuses(findings)
    .filter((h) => h.status === "missing")
    .map((h) => h.shortLabel);
  if (missing.length > 0) {
    return missing.slice(0, 4);
  }
  return getTopFindings(findings, 3).map((f) => f.title.split("—")[0].trim());
}

export function buildStatusSummaryText(
  score: SecurityScoreResult,
  counts: SeverityCounts,
  priorities: string[]
): string {
  const levelText =
    score.level === "strong" || score.level === "good"
      ? "Site genel olarak iyi bir güvenlik seviyesinde."
      : score.level === "medium"
        ? "Site genel olarak orta risk seviyesinde."
        : "Site genel olarak yüksek risk taşıyor — acil inceleme önerilir.";

  if (priorities.length === 0 && counts.critical + counts.high === 0) {
    return `${levelText} Kritik bulgu tespit edilmedi.`;
  }

  return `${levelText} Öncelikli düzeltme alanları: ${priorities.join(", ")}.`;
}

export function buildAiOverview(findings: Finding[], score: SecurityScoreResult): {
  summary: string;
  priorities: string[];
  firstSteps: string[];
} {
  const top = getTopFindings(findings, 5);
  const priorities = buildPrioritySummary(findings);

  const summary =
    findings.length === 0
      ? "Tarama sonucunda önemli bir güvenlik açığı tespit edilmedi. Periyodik izleme ile durumu koruyabilirsiniz."
      : `Güvenlik skoru ${score.score}/100 (${score.label}). ${top.length} öncelikli bulgu tespit edildi. ${
          score.level === "critical" || score.level === "weak"
            ? "Eksik güvenlik başlıkları ve yapılandırma sorunları acil ele alınmalı."
            : "Bulguların çoğu yapılandırma iyileştirmesi ile giderilebilir."
        }`;

  const firstSteps = top.slice(0, 3).map((f, i) => {
    const step = f.remediation_steps?.[0] ?? f.remediation ?? f.title;
    return `${i + 1}. ${step}`;
  });

  return { summary, priorities, firstSteps };
}

export function estimateScoreFromFindingsCount(count: number): number {
  return Math.max(15, Math.min(95, 100 - count * 5));
}

export async function buildTrendPoints(
  scans: ScanJob[],
  currentScanId: string,
  currentFindings: Finding[],
  fetchFindings: (scanId: string) => Promise<Finding[]>
): Promise<TrendPoint[]> {
  const target = scans.find((s) => s.id === currentScanId)?.target_url;
  if (!target) return [];

  const related = scans
    .filter((s) => s.target_url === target && s.status === "completed")
    .sort((a, b) => new Date(a.completed_at ?? 0).getTime() - new Date(b.completed_at ?? 0).getTime())
    .slice(-7);

  const points: TrendPoint[] = [];
  for (const s of related) {
    const f =
      s.id === currentScanId ? currentFindings : await fetchFindings(s.id);
    const { score } = computeSecurityScore(f);
    points.push({
      scanId: s.id,
      score,
      label: s.completed_at
        ? new Date(s.completed_at).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "short",
          })
        : "—",
      date: s.completed_at ?? s.created_at,
    });
  }
  return points;
}

export function computeScoreDelta(trend: TrendPoint[], currentScanId: string): number | null {
  if (trend.length < 2) return null;
  const idx = trend.findIndex((p) => p.scanId === currentScanId);
  if (idx <= 0) return null;
  return trend[idx].score - trend[idx - 1].score;
}

export function uniqueTechnologies(findings: Finding[]): number {
  const tools = new Set<string>();
  for (const f of findings) {
    for (const t of f.source_tools ?? [f.source_tool]) tools.add(t);
  }
  return tools.size;
}

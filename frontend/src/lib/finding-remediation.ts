import type { Finding } from "@/lib/api-types";
import { dictionaries } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n/types";
import { REMEDIATION_CONTENT } from "@/lib/remediation-content";

export type RemediationTabId =
  | "general"
  | "nginx"
  | "apache"
  | "plesk"
  | "cpanel"
  | "cloudflare"
  | "iis"
  | "framework"
  | "android"
  | "ios";

export interface RemediationTab {
  id: RemediationTabId;
  label: string;
  steps: string[];
  code?: string;
}

function mentions(text: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  return keywords.some((k) => lower.includes(k));
}

function filterSteps(steps: string[], keywords: string[]): string[] {
  return steps.filter((s) => mentions(s, keywords));
}

function pathsForPlatform(paths: string[], keywords: string[]): string[] {
  return paths.filter((p) => mentions(p, keywords));
}

function toApacheHeaderSnippet(nginxSnippet: string): string | undefined {
  const match = nginxSnippet.match(/add_header\s+([\w-]+)\s+"([^"]*)"\s*(always)?/);
  if (!match) return undefined;
  const always = match[3] ? " always" : "";
  return `Header set ${match[1]} "${match[2]}"${always}`;
}

function isSecurityHeaderFinding(finding: Finding, snippet: string, combined: string): boolean {
  return (
    Boolean(finding.correlation_key?.startsWith("missing-header")) ||
    snippet.includes("add_header") ||
    mentions(combined, ["header", "hsts", "csp", "x-frame", "nosniff"])
  );
}

function tabLabel(locale: Locale, id: RemediationTabId): string {
  const map: Record<RemediationTabId, keyof typeof dictionaries.tr.remediation> = {
    general: "tabGeneral",
    nginx: "tabNginx",
    apache: "tabApache",
    plesk: "tabPlesk",
    cpanel: "tabCpanel",
    cloudflare: "tabCloudflare",
    iis: "tabIis",
    framework: "tabFramework",
    android: "tabAndroid",
    ios: "tabIos",
  };
  return dictionaries[locale].remediation[map[id]];
}

export function buildRemediationTabs(finding: Finding, locale: Locale = "tr"): RemediationTab[] {
  const r = dictionaries[locale].remediation;
  const content = REMEDIATION_CONTENT[locale];
  const locationPrefix = r.locationPrefix;

  const steps = finding.remediation_steps ?? [];
  const paths = finding.config_file_paths ?? [];
  const snippet = finding.config_snippet ?? "";
  const combined = [finding.remediation ?? "", ...steps, ...paths, snippet].join("\n");
  const isHeaderFix = isSecurityHeaderFinding(finding, snippet, combined);

  const tabs: RemediationTab[] = [];

  const genericSteps = steps.filter(
    (s) => !mentions(s, ["plesk", "domains → sitenizi", "domains →"])
  );
  tabs.push({
    id: "general",
    label: tabLabel(locale, "general"),
    steps:
      genericSteps.length > 0
        ? genericSteps
        : finding.remediation
          ? [finding.remediation]
          : [r.fallbackReview],
  });

  if (finding.asset_type === "mobile") {
    tabs.push({
      id: "android",
      label: tabLabel(locale, "android"),
      steps: content.androidSteps,
    });
    tabs.push({
      id: "ios",
      label: tabLabel(locale, "ios"),
      steps: content.iosSteps,
    });
    return tabs;
  }

  if (isHeaderFix || mentions(combined, ["nginx", "add_header", "server_tokens"])) {
    const nginxPaths = pathsForPlatform(paths, ["[nginx", "nginx", "sites-available"]);
    tabs.push({
      id: "nginx",
      label: tabLabel(locale, "nginx"),
      steps: [
        ...content.nginxSteps,
        ...nginxPaths.map((p) => `${locationPrefix}: ${p.replace(/^\[[^\]]+\]\s*/, "")}`),
      ],
      code: snippet.includes("add_header") || snippet.includes("server_tokens") ? snippet : undefined,
    });
  }

  if (isHeaderFix || mentions(combined, ["apache", ".htaccess", "mod_"])) {
    const apachePaths = pathsForPlatform(paths, ["[apache", "apache", ".htaccess"]);
    tabs.push({
      id: "apache",
      label: tabLabel(locale, "apache"),
      steps: [
        ...content.apacheSteps,
        ...apachePaths.map((p) => `${locationPrefix}: ${p.replace(/^\[[^\]]+\]\s*/, "")}`),
      ],
      code: toApacheHeaderSnippet(snippet),
    });
  }

  if (pathsForPlatform(paths, ["plesk"]).length > 0 || filterSteps(steps, ["plesk"]).length > 0) {
    tabs.push({
      id: "plesk",
      label: tabLabel(locale, "plesk"),
      steps: [
        ...content.pleskSteps,
        ...pathsForPlatform(paths, ["plesk"]).map(
          (p) => `${locationPrefix}: ${p.replace(/^\[[^\]]+\]\s*/, "")}`
        ),
      ],
      code: snippet.includes("add_header") ? snippet : undefined,
    });
  }

  if (pathsForPlatform(paths, ["cpanel", "whm"]).length > 0 || mentions(combined, ["cpanel", "whm"])) {
    tabs.push({
      id: "cpanel",
      label: tabLabel(locale, "cpanel"),
      steps: [
        ...content.cpanelSteps,
        ...pathsForPlatform(paths, ["cpanel", "whm"]).map(
          (p) => `${locationPrefix}: ${p.replace(/^\[[^\]]+\]\s*/, "")}`
        ),
      ],
    });
  }

  if (
    pathsForPlatform(paths, ["cloudflare"]).length > 0 ||
    mentions(combined, ["cloudflare", "cf-"])
  ) {
    tabs.push({
      id: "cloudflare",
      label: tabLabel(locale, "cloudflare"),
      steps: [
        ...content.cloudflareSteps,
        ...pathsForPlatform(paths, ["cloudflare"]).map(
          (p) => `${locationPrefix}: ${p.replace(/^\[[^\]]+\]\s*/, "")}`
        ),
      ],
    });
  }

  if (pathsForPlatform(paths, ["iis", "web.config"]).length > 0 || mentions(combined, ["iis", "asp.net"])) {
    tabs.push({
      id: "iis",
      label: tabLabel(locale, "iis"),
      steps: [
        ...content.iisSteps,
        ...pathsForPlatform(paths, ["iis"]).map(
          (p) => `${locationPrefix}: ${p.replace(/^\[[^\]]+\]\s*/, "")}`
        ),
      ],
    });
  }

  if (
    mentions(combined, ["wordpress", "next.js", "nextjs", "react", "framework", "uygulama", "php:", "node:", "anwendung"])
  ) {
    tabs.push({
      id: "framework",
      label: tabLabel(locale, "framework"),
      steps: filterSteps(steps, ["wordpress", "next", "framework", "uygulama", "script", "php", "node", "anwendung"]).length
        ? filterSteps(steps, ["wordpress", "next", "framework", "uygulama", "script", "php", "node", "anwendung"])
        : [finding.remediation ?? r.frameworkFallback],
    });
  }

  return tabs;
}

export function getFindingCategory(finding: Finding, locale: Locale = "tr"): string {
  const r = dictionaries[locale].remediation;
  if (finding.correlation_key?.startsWith("missing-header")) return r.categoryHeader;
  if (finding.correlation_key?.startsWith("exposed-")) return r.categoryExposure;
  if (finding.correlation_key?.startsWith("cert-") || finding.correlation_key === "no-https") {
    return r.categoryTls;
  }
  if (finding.source_tool === "zap") return r.categoryZap;
  if (finding.source_tool === "nuclei") return r.categoryNuclei;
  return r.categoryGeneral;
}

export function getBusinessImpact(finding: Finding, locale: Locale = "tr"): string {
  return (
    finding.risk_explanation ??
    finding.description ??
    dictionaries[locale].remediation.impactFallback
  );
}

export function getWhatItMeans(finding: Finding): string {
  return finding.description ?? finding.ai_summary ?? finding.title;
}

export function getFixPriority(finding: Finding, locale: Locale = "tr"): string {
  const r = dictionaries[locale].remediation;
  const score = finding.risk_score ?? 0;
  if (finding.severity === "critical" || score >= 80) return r.priorityUrgent;
  if (finding.severity === "high" || score >= 60) return r.priorityHigh;
  if (finding.severity === "medium" || score >= 35) return r.priorityMedium;
  return r.priorityLow;
}

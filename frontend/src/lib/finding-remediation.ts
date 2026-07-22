import type { Finding } from "@/lib/api-types";

export type RemediationTabId =
  | "plesk"
  | "nginx"
  | "apache"
  | "cloudflare"
  | "framework"
  | "general";

export interface RemediationTab {
  id: RemediationTabId;
  label: string;
  steps: string[];
  code?: string;
}

const TAB_LABELS: Record<RemediationTabId, string> = {
  plesk: "Plesk",
  nginx: "Nginx",
  apache: "Apache",
  cloudflare: "Cloudflare",
  framework: "Framework / Uygulama",
  general: "Genel",
};

function mentions(text: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  return keywords.some((k) => lower.includes(k));
}

function filterSteps(steps: string[], keywords: string[]): string[] {
  return steps.filter((s) => mentions(s, keywords));
}

export function buildRemediationTabs(finding: Finding): RemediationTab[] {
  const steps = finding.remediation_steps ?? [];
  const paths = finding.config_file_paths ?? [];
  const snippet = finding.config_snippet ?? "";
  const combined = [finding.remediation ?? "", ...steps, ...paths, snippet].join("\n");

  const tabs: RemediationTab[] = [];

  const pleskSteps = filterSteps(steps, ["plesk", "domains", "panel"]);
  const pleskPaths = paths.filter((p) => mentions(p, ["plesk", "domains"]));
  if (pleskSteps.length > 0 || pleskPaths.length > 0 || mentions(combined, ["plesk"])) {
    tabs.push({
      id: "plesk",
      label: TAB_LABELS.plesk,
      steps: [...pleskSteps, ...pleskPaths.map((p) => `Konum: ${p}`)],
      code: mentions(snippet, ["nginx", "add_header"]) ? undefined : snippet || undefined,
    });
  }

  if (
    mentions(snippet, ["add_header", "nginx", "server {", "location"]) ||
    filterSteps(steps, ["nginx"]).length > 0 ||
    paths.some((p) => mentions(p, ["nginx", "vhost_nginx"]))
  ) {
    tabs.push({
      id: "nginx",
      label: TAB_LABELS.nginx,
      steps:
        filterSteps(steps, ["nginx"]).length > 0
          ? filterSteps(steps, ["nginx"])
          : ["Additional nginx directives bölümüne aşağıdaki yapılandırmayı ekleyin."],
      code: snippet || undefined,
    });
  }

  if (mentions(combined, ["apache", ".htaccess", "mod_"])) {
    tabs.push({
      id: "apache",
      label: TAB_LABELS.apache,
      steps: filterSteps(steps, ["apache", ".htaccess"]).length
        ? filterSteps(steps, ["apache", ".htaccess"])
        : [".htaccess veya Apache virtual host yapılandırmasını güncelleyin."],
      code: mentions(snippet, ["Header set", "RewriteEngine"]) ? snippet : undefined,
    });
  }

  if (mentions(combined, ["cloudflare", "cf-"])) {
    tabs.push({
      id: "cloudflare",
      label: TAB_LABELS.cloudflare,
      steps: [
        "Cloudflare Dashboard → siteniz → Rules / Transform Rules veya Page Rules.",
        "Gerekli güvenlik başlıklarını ekleyin veya WAF ayarlarını gözden geçirin.",
      ],
    });
  }

  if (
    mentions(combined, ["wordpress", "next.js", "nextjs", "react", "framework", "uygulama"])
  ) {
    tabs.push({
      id: "framework",
      label: TAB_LABELS.framework,
      steps: filterSteps(steps, ["wordpress", "next", "framework", "uygulama", "script"]).length
        ? filterSteps(steps, ["wordpress", "next", "framework", "uygulama", "script"])
        : [
            finding.remediation ??
              "Uygulama katmanında ilgili güvenlik ayarını güncelleyin.",
          ],
    });
  }

  if (tabs.length === 0) {
    tabs.push({
      id: "general",
      label: TAB_LABELS.general,
      steps: steps.length
        ? steps
        : finding.remediation
          ? [finding.remediation]
          : ["Yapılandırmayı gözden geçirin ve test ortamında doğrulayın."],
      code: snippet || undefined,
    });
  }

  return tabs;
}

export function getFindingCategory(finding: Finding): string {
  if (finding.correlation_key?.startsWith("missing-header")) return "Güvenlik başlığı";
  if (finding.correlation_key?.startsWith("exposed-")) return "Hassas dosya / ifşa";
  if (finding.correlation_key?.startsWith("cert-") || finding.correlation_key === "no-https") {
    return "TLS / HTTPS";
  }
  if (finding.source_tool === "zap") return "ZAP pasif analiz";
  if (finding.source_tool === "nuclei") return "Nuclei şablonu";
  return "Genel güvenlik";
}

export function getBusinessImpact(finding: Finding): string {
  return (
    finding.risk_explanation ??
    finding.description ??
    "Bu bulgu güvenlik duruşunuzu etkileyebilir; detaylar teknik kanıt bölümünde."
  );
}

export function getWhatItMeans(finding: Finding): string {
  return finding.description ?? finding.ai_summary ?? finding.title;
}

export function getFixPriority(finding: Finding): string {
  const score = finding.risk_score ?? 0;
  if (finding.severity === "critical" || score >= 80) return "Acil — öncelikli";
  if (finding.severity === "high" || score >= 60) return "Yüksek — bu hafta";
  if (finding.severity === "medium" || score >= 35) return "Orta — planlı";
  return "Düşük — iyileştirme";
}

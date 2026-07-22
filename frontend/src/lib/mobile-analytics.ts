import type { Finding } from "@/lib/api-types";

export type MobileFindingCategory =
  | "all"
  | "permissions"
  | "exported"
  | "secrets"
  | "network"
  | "manifest";

export const MOBILE_CATEGORY_LABELS: Record<MobileFindingCategory, string> = {
  all: "Tümü",
  permissions: "İzinler",
  exported: "Dışa Aktarılan Bileşenler",
  secrets: "Gizli Anahtarlar",
  network: "Ağ Güvenliği",
  manifest: "Manifest / Yapılandırma",
};

const NETWORK_RULES = new Set([
  "mobile-cleartext-traffic",
  "mobile-cleartext-network-config",
  "mobile-user-trust-anchors",
]);

const MANIFEST_RULES = new Set([
  "mobile-debuggable",
  "mobile-allow-backup",
]);

export function getMobileFindingCategory(finding: Finding): MobileFindingCategory {
  const ruleId = finding.source_rule_id ?? "";
  if (ruleId.startsWith("mobile-permission-")) return "permissions";
  if (ruleId === "mobile-exported-component") return "exported";
  if (ruleId.startsWith("mobile-secret-")) return "secrets";
  if (NETWORK_RULES.has(ruleId)) return "network";
  if (MANIFEST_RULES.has(ruleId)) return "manifest";
  return "manifest";
}

export function filterMobileFindings(
  findings: Finding[],
  category: MobileFindingCategory
): Finding[] {
  if (category === "all") return findings;
  return findings.filter((f) => getMobileFindingCategory(f) === category);
}

export function countMobileByCategory(
  findings: Finding[]
): Record<MobileFindingCategory, number> {
  const counts: Record<MobileFindingCategory, number> = {
    all: findings.length,
    permissions: 0,
    exported: 0,
    secrets: 0,
    network: 0,
    manifest: 0,
  };
  for (const finding of findings) {
    counts[getMobileFindingCategory(finding)] += 1;
  }
  return counts;
}

"use client";

import type { ScanJob } from "@/lib/api-client";
import { extractDomain, formatScanDuration, uniqueTechnologies } from "@/lib/scan-analytics";
import type { Finding } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  scan: ScanJob;
  findings: Finding[];
}

export function ScanScopeCard({ scan, findings }: Props) {
  const domain = extractDomain(scan.target_url);
  const urls = new Set(findings.map((f) => f.affected_url).filter(Boolean));

  const rows = [
    { label: "Domain", value: domain },
    { label: "Taranan URL", value: String(urls.size || 1) },
    { label: "Bulgu sayısı", value: String(scan.findings_count) },
    { label: "Teknoloji / kaynak", value: String(uniqueTechnologies(findings)) },
    { label: "Profil", value: scan.scan_profile },
    { label: "Süre", value: formatScanDuration(scan) ?? "—" },
  ];

  return (
    <Card className="border-border/60 bg-card/80 shadow-[0_0_24px_-8px_rgba(99,102,241,0.15)]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Tarama Kapsamı</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="space-y-2 text-sm">
          {rows.map((r) => (
            <div key={r.label} className="flex justify-between gap-2 border-b border-border/40 pb-2 last:border-0">
              <dt className="text-muted-foreground">{r.label}</dt>
              <dd className="truncate text-right font-medium">{r.value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

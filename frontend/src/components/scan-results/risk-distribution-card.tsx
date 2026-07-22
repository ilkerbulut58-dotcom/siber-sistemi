"use client";

import { severityLabel } from "@/lib/i18n-tr";
import type { SeverityCounts } from "@/lib/scan-analytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
  info: "#64748b",
};

const ORDER = ["critical", "high", "medium", "low", "info"] as const;

export function RiskDistributionCard({ counts }: { counts: SeverityCounts }) {
  const total = ORDER.reduce((s, k) => s + counts[k], 0);
  let offset = 0;
  const segments = ORDER.filter((k) => counts[k] > 0).map((k) => {
    const pct = counts[k] / total;
    const seg = { key: k, pct, offset, color: COLORS[k], count: counts[k] };
    offset += pct;
    return seg;
  });

  const r = 40;
  const c = 2 * Math.PI * r;

  return (
    <Card className="border-border/60 bg-card/80 shadow-[0_0_24px_-8px_rgba(99,102,241,0.15)]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Risk Dağılımı</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-4">
        <svg width="100" height="100" viewBox="0 0 100 100" className="shrink-0">
          <circle cx="50" cy="50" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="14" />
          {segments.map((s) => (
            <circle
              key={s.key}
              cx="50"
              cy="50"
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth="14"
              strokeDasharray={`${c * s.pct} ${c}`}
              strokeDashoffset={-c * s.offset}
              transform="rotate(-90 50 50)"
            />
          ))}
          <text x="50" y="52" textAnchor="middle" className="fill-foreground text-lg font-bold">
            {total}
          </text>
        </svg>
        <ul className="flex-1 space-y-1.5 text-xs">
          {ORDER.map((k) =>
            counts[k] > 0 ? (
              <li key={k} className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: COLORS[k] }} />
                  {severityLabel(k)}
                </span>
                <span className="font-semibold tabular-nums">{counts[k]}</span>
              </li>
            ) : null
          )}
          {total === 0 && (
            <li className="text-muted-foreground">Bulgu yok</li>
          )}
        </ul>
      </CardContent>
    </Card>
  );
}

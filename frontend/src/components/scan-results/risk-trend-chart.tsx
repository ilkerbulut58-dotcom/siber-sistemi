"use client";

import type { TrendPoint } from "@/lib/scan-analytics";
import { scoreColor } from "@/lib/scan-analytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function RiskTrendChart({
  points,
  currentScanId,
}: {
  points: TrendPoint[];
  currentScanId: string;
}) {
  const w = 320;
  const h = 140;
  const pad = { t: 16, r: 12, b: 28, l: 32 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  if (points.length < 2) {
    return (
      <Card className="border-border/60 bg-card/80">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Risk Trendi (Son Taramalar)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Trend için en az 2 tamamlanmış tarama gerekir.
          </p>
        </CardContent>
      </Card>
    );
  }

  const scores = points.map((p) => p.score);
  const minS = Math.max(0, Math.min(...scores) - 10);
  const maxS = Math.min(100, Math.max(...scores) + 10);
  const range = maxS - minS || 1;

  const coords = points.map((p, i) => ({
    x: pad.l + (i / (points.length - 1)) * innerW,
    y: pad.t + innerH - ((p.score - minS) / range) * innerH,
    ...p,
  }));

  const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ");

  return (
    <Card className="border-border/60 bg-card/80 shadow-[0_0_24px_-8px_rgba(99,102,241,0.15)]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Risk Trendi (Son {points.length} Tarama)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-full">
          {[0, 0.5, 1].map((t) => {
            const y = pad.t + innerH * (1 - t);
            const val = Math.round(minS + range * t);
            return (
              <g key={t}>
                <line
                  x1={pad.l}
                  y1={y}
                  x2={w - pad.r}
                  y2={y}
                  stroke="hsl(var(--border))"
                  strokeDasharray="4 4"
                />
                <text x={4} y={y + 4} className="fill-muted-foreground text-[9px]">
                  {val}
                </text>
              </g>
            );
          })}
          <path d={linePath} fill="none" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" />
          {coords.map((c) => (
            <g key={c.scanId}>
              <circle
                cx={c.x}
                cy={c.y}
                r={c.scanId === currentScanId ? 5 : 3.5}
                fill={scoreColor(c.score)}
                stroke={c.scanId === currentScanId ? "#fff" : "none"}
                strokeWidth={1.5}
              />
              <text
                x={c.x}
                y={h - 6}
                textAnchor="middle"
                className="fill-muted-foreground text-[8px]"
              >
                {c.label}
              </text>
            </g>
          ))}
        </svg>
      </CardContent>
    </Card>
  );
}

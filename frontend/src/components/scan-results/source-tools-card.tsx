"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SourceToolsCard({ sources }: { sources: Record<string, number> }) {
  const entries = Object.entries(sources).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <Card className="border-border/60 bg-card/80 shadow-[0_0_24px_-8px_rgba(99,102,241,0.15)]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Bulgu Kaynakları</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Kaynak verisi yok</p>
        ) : (
          entries.map(([name, count]) => (
            <div key={name}>
              <div className="mb-1 flex justify-between text-xs">
                <span>{name}</span>
                <span className="font-semibold tabular-nums">{count}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

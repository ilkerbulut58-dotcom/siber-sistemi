"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function StatusSummaryCard({ text }: { text: string }) {
  return (
    <Card className="border-border/60 bg-card/80 shadow-[0_0_24px_-8px_rgba(99,102,241,0.15)]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Genel Durum</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-foreground/90">{text}</p>
      </CardContent>
    </Card>
  );
}

"use client";

import { CheckCircle2, AlertCircle, HelpCircle } from "lucide-react";
import type { HeaderStatusItem } from "@/lib/scan-analytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const STATUS_UI = {
  present: {
    icon: CheckCircle2,
    label: "Var",
    className: "border-green-500/30 bg-green-500/5 text-green-400",
  },
  missing: {
    icon: AlertCircle,
    label: "Eksik",
    className: "border-red-500/30 bg-red-500/5 text-red-400",
  },
  recommended: {
    icon: HelpCircle,
    label: "Öneriliyor",
    className: "border-yellow-500/30 bg-yellow-500/5 text-yellow-400",
  },
};

export function SecurityHeadersStatusGrid({ headers }: { headers: HeaderStatusItem[] }) {
  return (
    <Card className="border-border/60 bg-card/80" id="section-headers">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Güvenlik Başlıkları Durumu</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {headers.map((h) => {
            const ui = STATUS_UI[h.status];
            const Icon = ui.icon;
            return (
              <div
                key={h.key}
                className={cn(
                  "flex flex-col gap-2 rounded-lg border p-3 transition-colors hover:brightness-110",
                  ui.className
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold">{h.shortLabel}</span>
                  <Icon className="h-4 w-4 shrink-0 opacity-80" />
                </div>
                <p className="text-[10px] leading-tight opacity-70">{h.label}</p>
                <span className="text-xs font-semibold">{ui.label}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

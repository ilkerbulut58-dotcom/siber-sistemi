"use client";

import { Download, RefreshCw } from "lucide-react";
import type { ScanJob } from "@/lib/api-client";
import { SCAN_STATUS_TR, scanProfileLabel } from "@/lib/i18n-tr";
import { extractDomain, formatScanDuration } from "@/lib/scan-analytics";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  scan: ScanJob;
  onRescan?: () => void;
  onDownload?: () => void;
  isRunning?: boolean;
}

export function ScanSummaryHeader({ scan, onRescan, onDownload, isRunning }: Props) {
  const duration = formatScanDuration(scan);
  const completedAt = scan.completed_at
    ? new Date(scan.completed_at).toLocaleString("tr-TR")
    : null;

  return (
    <div className="rounded-xl border border-border/60 bg-gradient-to-br from-card via-card/95 to-indigo-950/20 p-6 shadow-[0_0_40px_-12px_rgba(99,102,241,0.25)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
            Tarama Özeti
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight md:text-3xl">
            {extractDomain(scan.target_url)}
          </h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">{scan.target_url}</p>
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm">
            <Meta label="Profil" value={scanProfileLabel(scan.scan_profile)} />
            <Meta
              label="Durum"
              value={SCAN_STATUS_TR[scan.status] ?? scan.status ?? "Bilinmiyor"}
              highlight={
                scan.status === "completed"
                  ? "text-green-400"
                  : scan.status === "failed"
                    ? "text-red-400"
                    : "text-amber-400"
              }
            />
            {completedAt && <Meta label="Tarih" value={completedAt} />}
            {duration && <Meta label="Süre" value={duration} />}
            <Meta label="Bulgu" value={String(scan.findings_count)} />
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {onRescan && (
            <Button type="button" variant="outline" size="sm" onClick={onRescan} disabled={isRunning}>
              <RefreshCw className={cn("mr-2 h-4 w-4", isRunning && "animate-spin")} />
              Yeniden Tara
            </Button>
          )}
          {onDownload && scan.status === "completed" && (
            <Button type="button" size="sm" onClick={onDownload}>
              <Download className="mr-2 h-4 w-4" />
              Rapor İndir
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function Meta({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: string;
}) {
  return (
    <span className="text-muted-foreground">
      {label}:{" "}
      <span className={cn("font-medium text-foreground", highlight)}>{value}</span>
    </span>
  );
}

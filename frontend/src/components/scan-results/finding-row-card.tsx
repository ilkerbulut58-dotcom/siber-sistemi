"use client";

import { ChevronRight } from "lucide-react";
import type { Finding } from "@/lib/api-client";
import { formatSourceTool } from "@/lib/scan-analytics";
import { useTranslation } from "@/components/locale-provider";
import { Button } from "@/components/ui/button";
import { MiniRiskRing, SeverityBadge } from "@/components/scan-results/severity-badge";
import { cn } from "@/lib/utils";

interface Props {
  finding: Finding;
  onDetail?: () => void;
  onRowClick?: () => void;
  compact?: boolean;
}

export function FindingRowCard({ finding, onDetail, onRowClick, compact }: Props) {
  const { t, locale, confidenceLabel, findingWorkflowLabel } = useTranslation();
  const sources =
    finding.source_tools?.map((tool) => formatSourceTool(tool, locale)).join(", ") ??
    formatSourceTool(finding.source_tool, locale);

  const endpoint = finding.affected_url
    ? finding.affected_url.length > 64
      ? `${finding.affected_url.slice(0, 61)}…`
      : finding.affected_url
    : null;

  return (
    <article
      role={onRowClick ? "button" : undefined}
      tabIndex={onRowClick ? 0 : undefined}
      onClick={onRowClick}
      onKeyDown={(e) => {
        if (onRowClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onRowClick();
        }
      }}
      className={cn(
        "group rounded-xl border border-border/60 bg-card/60 p-4 transition-all hover:border-indigo-500/30 hover:bg-card/80",
        compact && "p-3",
        onRowClick && "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
      )}
    >
      <div className="flex gap-3">
        <MiniRiskRing score={finding.risk_score} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            {finding.confidence && (
              <span className="text-xs text-muted-foreground">
                {t("findingDrawer.confidence")}: {confidenceLabel(finding.confidence)}
              </span>
            )}
            <span className="text-xs text-muted-foreground">{findingWorkflowLabel(finding.status)}</span>
            {finding.cvss_score != null && (
              <span className="text-xs text-muted-foreground">CVSS {finding.cvss_score}</span>
            )}
            <span className="text-xs text-muted-foreground">{sources}</span>
          </div>
          <h3 className="mt-2 font-semibold leading-snug">{finding.title ?? "—"}</h3>
          {endpoint && (
            <p className="mt-1 truncate text-xs text-muted-foreground" title={finding.affected_url ?? undefined}>
              {endpoint}
            </p>
          )}
          <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
            {finding.risk_explanation ?? finding.description ?? finding.ai_summary}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {onDetail && (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  onDetail();
                }}
              >
                {t("findingFilters.detail")}
                <ChevronRight className="ml-1 h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

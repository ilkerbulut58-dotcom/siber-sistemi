"use client";

import { useMemo, useState } from "react";
import type { Finding } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { FindingRowCard } from "@/components/scan-results/finding-row-card";
import { useTranslation } from "@/components/locale-provider";
import {
  DEFAULT_FINDING_FILTERS,
  filterFindings,
  uniqueSources,
  type FindingFilterState,
} from "@/lib/finding-filters";

interface Props {
  findings: Finding[];
  onOpenDetail: (id: string) => void;
}

export function AllFindingsPanel({ findings, onOpenDetail }: Props) {
  const { t, findingWorkflowLabel } = useTranslation();
  const [filters, setFilters] = useState<FindingFilterState>(DEFAULT_FINDING_FILTERS);

  const sources = useMemo(() => uniqueSources(findings), [findings]);
  const filtered = useMemo(() => filterFindings(findings, filters), [findings, filters]);

  function setField<K extends keyof FindingFilterState>(key: K, value: FindingFilterState[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <Card className="border-border/60 bg-card/80" id="section-all-findings">
      <CardHeader>
        <CardTitle>{t("analytics.allFindingsTitle")}</CardTitle>
        <CardDescription>
          {t("analytics.allFindingsDesc", { count: filtered.length })}
          {filtered.length !== findings.length &&
            ` (${t("findingFilters.filteredFrom", { total: findings.length })})`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder={t("findingFilters.searchPlaceholder")}
            value={filters.query}
            onChange={(e) => setField("query", e.target.value)}
            aria-label={t("findingFilters.searchPlaceholder")}
          />
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={filters.severity}
            onChange={(e) => setField("severity", e.target.value)}
            aria-label={t("findingFilters.severity")}
          >
            <option value="all">{t("findingFilters.allSeverities")}</option>
            {["critical", "high", "medium", "low", "info"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={filters.confidence}
            onChange={(e) => setField("confidence", e.target.value)}
            aria-label={t("findingFilters.confidence")}
          >
            <option value="all">{t("findingFilters.allConfidence")}</option>
            {["high", "medium", "low"].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={filters.status}
            onChange={(e) => setField("status", e.target.value)}
            aria-label={t("findingFilters.status")}
          >
            <option value="all">{t("findingFilters.allStatuses")}</option>
            {["open", "inconclusive", "accepted_risk", "false_positive", "resolved"].map((s) => (
              <option key={s} value={s}>
                {findingWorkflowLabel(s)}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={filters.source}
            onChange={(e) => setField("source", e.target.value)}
            aria-label={t("findingFilters.scanner")}
          >
            <option value="all">{t("findingFilters.allScanners")}</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={filters.review}
            onChange={(e) => setField("review", e.target.value)}
            aria-label={t("findingFilters.review")}
          >
            <option value="all">{t("findingFilters.allReview")}</option>
            <option value="confirmed">{t("findingFilters.confirmed")}</option>
            <option value="needs_review">{t("findingFilters.needsReview")}</option>
            <option value="informational">{t("findingFilters.informational")}</option>
          </select>
        </div>

        {filters.query || filters.severity !== "all" || filters.confidence !== "all" ? (
          <Button type="button" size="sm" variant="outline" onClick={() => setFilters(DEFAULT_FINDING_FILTERS)}>
            {t("findingFilters.clearFilters")}
          </Button>
        ) : null}

        {filtered.length === 0 ? (
          <p className="text-muted-foreground">{t("analytics.findingsNotFound")}</p>
        ) : (
          <div className="space-y-3">
            {filtered.map((finding) => (
              <FindingRowCard
                key={finding.id}
                finding={finding}
                onDetail={() => onOpenDetail(finding.id)}
                onRowClick={() => onOpenDetail(finding.id)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

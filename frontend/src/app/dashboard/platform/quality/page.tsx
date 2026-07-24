"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { BarChart3, Clock3, ShieldAlert, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type BenchmarkRun, type QualitySummary } from "@/lib/api-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const percentage = (value: number) => `${Math.round(value * 1000) / 10}%`;

export default function PlatformQualityPage() {
  const { user, getAccessToken } = useAuth();
  const { t, formatApiError } = useTranslation();
  const [summary, setSummary] = useState<QualitySummary | null>(null);
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const token = getAccessToken();
      const [quality, history] = await Promise.all([
        apiFetch<QualitySummary>("/api/v1/platform/quality/summary", { token }),
        apiFetch<BenchmarkRun[]>("/api/v1/platform/quality/runs", { token }),
      ]);
      setSummary(quality);
      setRuns(history);
    } catch (cause) {
      setError(formatApiError(cause));
    }
  }, [formatApiError, getAccessToken]);

  useEffect(() => {
    if (user?.is_platform_admin) void load();
  }, [load, user?.is_platform_admin]);

  if (!user?.is_platform_admin) {
    return (
      <main className="container mx-auto px-4 py-12 text-muted-foreground">
        {t("platform.qualityOnlyAdmin")}
      </main>
    );
  }

  const cards: Array<[string, string, LucideIcon]> = summary
    ? [
        [t("quality.precision"), percentage(summary.precision), Target],
        [t("quality.recall"), percentage(summary.recall), BarChart3],
        [t("quality.f1"), percentage(summary.f1_score), ShieldAlert],
        [t("quality.avgDuration"), `${Math.round(summary.average_duration_seconds)} s`, Clock3],
      ]
    : [];

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-7xl px-4 py-8">
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
          ← {t("quality.back")}
        </Link>
        <h1 className="mt-2 text-3xl font-bold">{t("quality.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("quality.desc")}</p>
        {error && <p className="mt-6 text-destructive">{error}</p>}
        {!summary && !error && <p className="mt-8 text-muted-foreground">{t("quality.loading")}</p>}
        {summary?.scanner_health.status === "no_runs" && (
          <Card className="mt-6 border-border/60 bg-card/80">
            <CardContent className="py-8 text-muted-foreground">{t("quality.noRuns")}</CardContent>
          </Card>
        )}
        {summary && (
          <>
            <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {cards.map(([label, value, Icon]) => (
                <Card key={String(label)} className="border-border/60 bg-card/80">
                  <CardHeader className="pb-2">
                    <CardDescription>{label}</CardDescription>
                    <CardTitle className="flex items-center justify-between text-3xl">
                      {value}
                      <Icon className="h-5 w-5 text-muted-foreground" />
                    </CardTitle>
                  </CardHeader>
                </Card>
              ))}
            </section>
            <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card className="border-border/60 bg-card/80">
                <CardHeader className="pb-2">
                  <CardDescription>{t("quality.tpFnFp")}</CardDescription>
                  <CardTitle className="text-2xl">
                    {summary.true_positive_count} / {summary.false_negative_count} /{" "}
                    {summary.false_positive_count}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card className="border-border/60 bg-card/80">
                <CardHeader className="pb-2">
                  <CardDescription>{t("quality.duplicateScanner")}</CardDescription>
                  <CardTitle className="text-2xl">
                    {summary.duplicate_count} / {summary.scanner_error_count}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card className="border-border/60 bg-card/80">
                <CardHeader className="pb-2">
                  <CardDescription>{t("quality.expectedFindings")}</CardDescription>
                  <CardTitle className="text-2xl">{summary.expected_count}</CardTitle>
                </CardHeader>
              </Card>
              <Card className="border-border/60 bg-card/80">
                <CardHeader className="pb-2">
                  <CardDescription>{t("quality.baselineDelta")}</CardDescription>
                  <CardTitle className="text-2xl">
                    {summary.baseline_delta?.recall_delta != null
                      ? `${Math.round(Number(summary.baseline_delta.recall_delta) * 1000) / 10}%`
                      : "—"}
                  </CardTitle>
                </CardHeader>
              </Card>
            </section>
          </>
        )}
        {summary && (
          <section className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card className="border-border/60 bg-card/80">
              <CardHeader>
                <CardTitle>{t("quality.targetBreakdown")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.entries(summary.by_target_type).length === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("quality.noBenchmark")}</p>
                ) : (
                  Object.entries(summary.by_target_type).map(([type, item]) => (
                    <div
                      key={type}
                      className="flex justify-between border-b border-border/50 pb-2 text-sm"
                    >
                      <span className="font-medium">
                        {type.toUpperCase()} · {item.runs} {t("quality.runs")}
                      </span>
                      <span>
                        R {percentage(item.recall)} · P {percentage(item.precision)} · F1{" "}
                        {percentage(item.f1_score)}
                      </span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/80">
              <CardHeader>
                <CardTitle>{t("quality.lastRun")}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {summary.last_run ? (
                  <>
                    <p className="font-medium">
                      {summary.last_run.fixture_set} · {summary.last_run.status}
                    </p>
                    <p className="mt-1 text-muted-foreground">
                      {summary.last_run.git_commit ?? t("quality.noCommit")} ·{" "}
                      {summary.last_run.duration_seconds ?? "—"} s
                    </p>
                    <p className="mt-3 text-muted-foreground">
                      {t("quality.falsePositiveRate")}: {percentage(summary.false_positive_rate)} ·{" "}
                      {t("quality.falseNegativeRate")}: {percentage(summary.false_negative_rate)} ·{" "}
                      {t("quality.failedRuns")}: {summary.scanner_health.failed_runs ?? 0}
                    </p>
                  </>
                ) : (
                  <p className="text-muted-foreground">{t("quality.awaitingResult")}</p>
                )}
              </CardContent>
            </Card>
          </section>
        )}
        <Card className="mt-6 border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle>{t("quality.history")}</CardTitle>
            <CardDescription>{t("quality.historyDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            {runs.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("quality.noHistory")}</p>
            ) : (
              <div className="space-y-2">
                {runs.map((run) => (
                  <div
                    key={run.id}
                    className="flex flex-wrap justify-between gap-2 border-b border-border/50 py-2 text-sm"
                  >
                    <span>
                      {run.fixture_set} · {run.scan_profile ?? "mobile"}
                    </span>
                    <span
                      className={run.status === "failed" ? "text-destructive" : "text-muted-foreground"}
                    >
                      {run.status}
                    </span>
                    <span>{run.duration_seconds ?? "—"} s</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}

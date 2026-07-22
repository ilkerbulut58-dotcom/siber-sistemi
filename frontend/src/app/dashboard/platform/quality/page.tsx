"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { BarChart3, Clock3, ShieldAlert, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, type BenchmarkRun, type QualitySummary } from "@/lib/api-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const percentage = (value: number) => `${Math.round(value * 1000) / 10}%`;

export default function PlatformQualityPage() {
  const { user, getAccessToken } = useAuth();
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
      setError(cause instanceof Error ? cause.message : "Kalite verisi yüklenemedi.");
    }
  }, [getAccessToken]);

  useEffect(() => {
    if (user?.is_platform_admin) void load();
  }, [load, user?.is_platform_admin]);

  if (!user?.is_platform_admin) {
    return <main className="container mx-auto px-4 py-12 text-muted-foreground">Bu alan yalnız platform yöneticilerine açıktır.</main>;
  }

  const cards: Array<[string, string, LucideIcon]> = summary ? [
    ["Precision", percentage(summary.precision), Target],
    ["Recall", percentage(summary.recall), BarChart3],
    ["F1 Score", percentage(summary.f1_score), ShieldAlert],
    ["Ort. süre", `${Math.round(summary.average_duration_seconds)} sn`, Clock3],
  ] : [];

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-7xl px-4 py-8">
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">← Panel</Link>
        <h1 className="mt-2 text-3xl font-bold">Detection Quality Lab</h1>
        <p className="mt-1 text-muted-foreground">Yalnız kapalı benchmark fixture’larından üretilen platform kalite ölçümleri.</p>
        {error && <p className="mt-6 text-destructive">{error}</p>}
        {!summary && !error && <p className="mt-8 text-muted-foreground">Kalite verileri yükleniyor…</p>}
        {summary?.scanner_health.status === "no_runs" && (
          <Card className="mt-6 border-border/60 bg-card/80"><CardContent className="py-8 text-muted-foreground">Henüz benchmark çalışması yok. CI veya yerel benchmark runner ilk sonucu oluşturduğunda ölçümler burada görünür.</CardContent></Card>
        )}
        {summary && (
          <>
          <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {cards.map(([label, value, Icon]) => (
              <Card key={String(label)} className="border-border/60 bg-card/80">
                <CardHeader className="pb-2"><CardDescription>{label}</CardDescription><CardTitle className="flex items-center justify-between text-3xl">{value}<Icon className="h-5 w-5 text-muted-foreground" /></CardTitle></CardHeader>
              </Card>
            ))}
          </section>
          <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="border-border/60 bg-card/80"><CardHeader className="pb-2"><CardDescription>TP / FN / FP</CardDescription><CardTitle className="text-2xl">{summary.true_positive_count} / {summary.false_negative_count} / {summary.false_positive_count}</CardTitle></CardHeader></Card>
            <Card className="border-border/60 bg-card/80"><CardHeader className="pb-2"><CardDescription>Duplicate / Scanner error</CardDescription><CardTitle className="text-2xl">{summary.duplicate_count} / {summary.scanner_error_count}</CardTitle></CardHeader></Card>
            <Card className="border-border/60 bg-card/80"><CardHeader className="pb-2"><CardDescription>Expected findings</CardDescription><CardTitle className="text-2xl">{summary.expected_count}</CardTitle></CardHeader></Card>
            <Card className="border-border/60 bg-card/80"><CardHeader className="pb-2"><CardDescription>Baseline delta (recall)</CardDescription><CardTitle className="text-2xl">{summary.baseline_delta?.recall_delta != null ? `${Math.round(Number(summary.baseline_delta.recall_delta) * 1000) / 10}%` : "—"}</CardTitle></CardHeader></Card>
          </section>
          </>
        )}
        {summary && (
          <section className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card className="border-border/60 bg-card/80"><CardHeader><CardTitle>Hedef türü kırılımı</CardTitle></CardHeader><CardContent className="space-y-3">
              {Object.entries(summary.by_target_type).length === 0 ? <p className="text-sm text-muted-foreground">Tamamlanmış benchmark sonucu yok.</p> : Object.entries(summary.by_target_type).map(([type, item]) => <div key={type} className="flex justify-between border-b border-border/50 pb-2 text-sm"><span className="font-medium">{type.toUpperCase()} · {item.runs} run</span><span>R {percentage(item.recall)} · P {percentage(item.precision)} · F1 {percentage(item.f1_score)}</span></div>)}
            </CardContent></Card>
            <Card className="border-border/60 bg-card/80"><CardHeader><CardTitle>Son çalışma</CardTitle></CardHeader><CardContent className="text-sm">
              {summary.last_run ? <><p className="font-medium">{summary.last_run.fixture_set} · {summary.last_run.status}</p><p className="mt-1 text-muted-foreground">{summary.last_run.git_commit ?? "commit bilgisi yok"} · {summary.last_run.duration_seconds ?? "—"} sn</p><p className="mt-3 text-muted-foreground">Yanlış alarm: {percentage(summary.false_positive_rate)} · Kaçırılan: {percentage(summary.false_negative_rate)} · Başarısız scanner run: {summary.scanner_health.failed_runs ?? 0}</p></> : <p className="text-muted-foreground">Sonuç bekleniyor.</p>}
            </CardContent></Card>
          </section>
        )}
        <Card className="mt-6 border-border/60 bg-card/80"><CardHeader><CardTitle>Benchmark geçmişi</CardTitle><CardDescription>Report-only ilk koşular baseline oluşturmaya yöneliktir.</CardDescription></CardHeader><CardContent>
          {runs.length === 0 ? <p className="text-sm text-muted-foreground">Geçmiş çalışma yok.</p> : <div className="space-y-2">{runs.map((run) => <div key={run.id} className="flex flex-wrap justify-between gap-2 border-b border-border/50 py-2 text-sm"><span>{run.fixture_set} · {run.scan_profile ?? "mobile"}</span><span className={run.status === "failed" ? "text-destructive" : "text-muted-foreground"}>{run.status}</span><span>{run.duration_seconds ?? "—"} sn</span></div>)}</div>}
        </CardContent></Card>
      </main>
    </>
  );
}

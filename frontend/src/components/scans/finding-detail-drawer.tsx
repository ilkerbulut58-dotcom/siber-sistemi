"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Check,
  Copy,
  ExternalLink,
  History,
  Loader2,
  RefreshCw,
  Shield,
  Sparkles,
} from "lucide-react";
import type { Finding, FindingHistoryEntry } from "@/lib/api-client";
import { apiFetch } from "@/lib/api-client";
import { formatMaskedEvidence, maskText } from "@/lib/evidence-masker";
import type { RiskBreakdown } from "@/lib/api-client";
import {
  buildRemediationTabs,
  getBusinessImpact,
  getFindingCategory,
  getFixPriority,
  getWhatItMeans,
  type RemediationTab,
} from "@/lib/finding-remediation";
import {
  aiConfidenceLabel,
  confidenceLabel,
  FINDING_WORKFLOW_STATUS_TR,
  HISTORY_EVENT_TR,
  VERIFICATION_STATUS_TR,
} from "@/lib/i18n-tr";
import { formatSourceTool } from "@/lib/scan-analytics";
import { SeverityBadge, MiniRiskRing } from "@/components/scan-results/severity-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const WORKFLOW_STATUSES = [
  "open",
  "inconclusive",
  "accepted_risk",
  "false_positive",
  "resolved",
] as const;

function useIsMobile(breakpoint = 640): boolean {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const update = () => setMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, [breakpoint]);
  return mobile;
}

function CopyCodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="relative rounded-lg border border-border/60 bg-black/40">
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="absolute right-2 top-2 h-8 gap-1 text-xs"
        onClick={copy}
        aria-label="Kodu kopyala"
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" /> Kopyalandı
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" /> Kopyala
          </>
        )}
      </Button>
      <pre className="overflow-x-auto p-4 pt-10 text-xs leading-relaxed text-emerald-100/90">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3 border-b border-border/40 pb-6">
      <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

function RiskBreakdownVisual({ breakdown, riskScore }: { breakdown: RiskBreakdown | null; riskScore: number | null }) {
  if (!breakdown) {
    return (
      <p className="text-sm text-muted-foreground">
        Risk dağılımı henüz hesaplanmadı.
        {riskScore != null && ` Toplam puan: ${Math.round(riskScore)}.`}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 rounded-lg border border-border/50 bg-muted/20 p-4">
        <MiniRiskRing score={breakdown.total} />
        <div>
          <p className="text-2xl font-bold">{Math.round(breakdown.total)}</p>
          <p className="text-xs text-muted-foreground">Toplam risk puanı (1–100)</p>
        </div>
      </div>
      <div className="space-y-2">
        {breakdown.items.map((item) => (
          <div key={item.key} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium">{item.label}</span>
              <span className="text-muted-foreground">{item.value}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted/50">
              <div
                className="h-full rounded-full bg-indigo-500/80 transition-all"
                style={{ width: `${Math.min(100, item.weight * 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function RemediationTabsSection({ tabs }: { tabs: RemediationTab[] }) {
  const [active, setActive] = useState(tabs[0]?.id ?? "general");

  useEffect(() => {
    if (tabs.length && !tabs.find((t) => t.id === active)) {
      setActive(tabs[0].id);
    }
  }, [tabs, active]);

  const current = tabs.find((t) => t.id === active) ?? tabs[0];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1 rounded-lg border border-border/50 bg-muted/20 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active === tab.id}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              active === tab.id
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {current && (
        <div role="tabpanel" className="space-y-3">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
            {current.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {current.code && <CopyCodeBlock code={current.code} />}
        </div>
      )}
      <p className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200/90">
        Değişiklikleri önce test/staging ortamında uygulayın; production&apos;a almadan
        önce doğrulayın.
      </p>
    </div>
  );
}

function HistoryTimeline({
  history,
  loading,
}: {
  history: FindingHistoryEntry[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }
  if (history.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Henüz geçmiş kaydı bulunmuyor.</p>
    );
  }

  return (
    <ol className="relative space-y-4 border-l border-border/60 pl-4">
      {history.map((entry) => (
        <li key={entry.id} className="relative">
          <span className="absolute -left-[1.3rem] top-1 h-2.5 w-2.5 rounded-full bg-indigo-500 ring-4 ring-background" />
          <p className="text-sm font-medium">
            {HISTORY_EVENT_TR[entry.event_type] ?? entry.event_type}
          </p>
          <p className="text-xs text-muted-foreground">
            {new Date(entry.created_at).toLocaleString("tr-TR")}
          </p>
          {entry.details && entry.event_type === "status_change" && (
            <p className="mt-1 text-xs text-muted-foreground">
              {String(entry.details.from ?? "—")} → {String(entry.details.to ?? "—")}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}

export interface FindingDetailDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  finding: Finding | null;
  orgId: string;
  getAccessToken: () => string | null;
  onFindingUpdated: (finding: Finding) => void;
  onToast: (message: string, variant: "success" | "error") => void;
  onRetestNavigate: (scanId: string) => void;
  scanCompleted?: boolean;
  onFindingNotFound?: () => void;
  enableRetest?: boolean;
  canManageFinding?: boolean;
  mobileApp?: {
    application_name: string | null;
    package_name: string | null;
    version_name: string | null;
    version_code: string | null;
  };
}

export function FindingDetailDrawer({
  open,
  onOpenChange,
  finding,
  orgId,
  getAccessToken,
  onFindingUpdated,
  onToast,
  onRetestNavigate,
  scanCompleted = true,
  onFindingNotFound,
  enableRetest = true,
  canManageFinding = true,
  mobileApp,
}: FindingDetailDrawerProps) {
  const isMobile = useIsMobile();
  const [history, setHistory] = useState<FindingHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [retestLoading, setRetestLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [localFinding, setLocalFinding] = useState<Finding | null>(finding);

  useEffect(() => {
    setLocalFinding(finding);
  }, [finding]);

  const refreshFinding = useCallback(async () => {
    if (!localFinding || !open) return;
    if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
    try {
      const data = await apiFetch<Finding>(
        `/api/v1/organizations/${orgId}/findings/${localFinding.id}`,
        { token: getAccessToken() }
      );
      setLocalFinding(data);
      onFindingUpdated(data);
      setAiLoading(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (/not found|forbidden|403|404/i.test(msg)) {
        onFindingNotFound?.();
      }
    }
  }, [localFinding, open, orgId, getAccessToken, onFindingUpdated, onFindingNotFound]);

  const loadHistory = useCallback(async () => {
    if (!localFinding) return;
    setHistoryLoading(true);
    try {
      const data = await apiFetch<FindingHistoryEntry[]>(
        `/api/v1/organizations/${orgId}/findings/${localFinding.id}/history`,
        { token: getAccessToken() }
      );
      setHistory(data);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [localFinding, orgId, getAccessToken]);

  useEffect(() => {
    if (open && localFinding) {
      void loadHistory();
    }
  }, [open, localFinding?.id, loadHistory]);

  useEffect(() => {
    if (!open || !localFinding || !scanCompleted) {
      setAiLoading(false);
      return;
    }
    setAiLoading(!localFinding.ai_summary);
    let ticks = 0;
    const maxTicks = 8;
    const timer = setInterval(() => {
      if (document.visibilityState === "hidden") return;
      ticks += 1;
      void refreshFinding();
      if (ticks >= maxTicks) setAiLoading(false);
    }, 5000);
    return () => {
      clearInterval(timer);
      setAiLoading(false);
    };
  }, [open, localFinding?.id, scanCompleted, refreshFinding]);

  async function handleStatusChange(status: string) {
    if (!canManageFinding || !localFinding || statusUpdating) return;
    setStatusUpdating(true);
    try {
      const updated = await apiFetch<Finding>(
        `/api/v1/organizations/${orgId}/findings/${localFinding.id}`,
        {
          method: "PATCH",
          token: getAccessToken(),
          body: JSON.stringify({ status }),
        }
      );
      setLocalFinding(updated);
      onFindingUpdated(updated);
      onToast("Bulgu durumu güncellendi.", "success");
      await loadHistory();
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Durum güncellenemedi", "error");
    } finally {
      setStatusUpdating(false);
    }
  }

  async function handleRetest() {
    if (!canManageFinding || !localFinding || retestLoading) return;
    setRetestLoading(true);
    try {
      const newScan = await apiFetch<{ id: string }>(
        `/api/v1/organizations/${orgId}/findings/${localFinding.id}/retest`,
        { method: "POST", token: getAccessToken() }
      );
      onToast("Yeniden tarama başlatıldı.", "success");
      onRetestNavigate(newScan.id);
    } catch (err) {
      onToast(err instanceof Error ? err.message : "Yeniden tarama başarısız", "error");
    } finally {
      setRetestLoading(false);
    }
  }

  const f = localFinding;
  const evidenceRows = useMemo(
    () => (f ? formatMaskedEvidence(f.evidence) : []),
    [f]
  );
  const remediationTabs = useMemo(
    () => (f ? buildRemediationTabs(f) : []),
    [f]
  );
  const sources = f?.source_tools?.length
    ? f.source_tools.map(formatSourceTool)
    : f
      ? [formatSourceTool(f.source_tool)]
      : [];

  const showAiSkeleton = aiLoading && !f?.ai_summary;
  const showAiFallback = !f?.ai_summary && !aiLoading;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side={isMobile ? "bottom" : "right"}
        className={cn(
          "flex flex-col p-0",
          isMobile && "h-[100dvh] max-h-[100dvh] rounded-none"
        )}
        aria-describedby={f ? "finding-drawer-desc" : undefined}
      >
        {!f ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <header className="sticky top-0 z-10 shrink-0 border-b border-border/60 bg-background/95 px-6 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
              <SheetHeader className="space-y-3 text-left">
                <div className="flex flex-wrap items-start gap-2 pr-8">
                  <SeverityBadge severity={f.severity} />
                  {f.risk_score != null && (
                    <Badge variant="outline" aria-label={`Risk puanı ${Math.round(f.risk_score)}`}>
                      Risk {Math.round(f.risk_score)}
                    </Badge>
                  )}
                  {f.confidence && (
                    <Badge variant="muted">Güven: {confidenceLabel(f.confidence)}</Badge>
                  )}
                  {f.verification_status && (
                    <Badge variant="secondary">
                      {VERIFICATION_STATUS_TR[f.verification_status] ?? f.verification_status}
                    </Badge>
                  )}
                  <Badge variant="outline">
                    {FINDING_WORKFLOW_STATUS_TR[f.status] ?? f.status}
                  </Badge>
                </div>
                <SheetTitle className="text-xl leading-snug">{f.title}</SheetTitle>
                <SheetDescription id="finding-drawer-desc" className="sr-only">
                  Bulgu detay paneli — {f.title}
                </SheetDescription>
              </SheetHeader>
            </header>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <div className="space-y-6">
                <Section title="Hızlı özet" icon={<Shield className="h-4 w-4" />}>
                  <div className="grid gap-3 text-sm">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        Bu ne anlama geliyor?
                      </p>
                      <p>{getWhatItMeans(f)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">İş etkisi</p>
                      <p className="text-muted-foreground">{getBusinessImpact(f)}</p>
                    </div>
                    {f.affected_url && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground">
                          Etkilenen URL
                        </p>
                        <a
                          href={f.affected_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 break-all text-indigo-300 hover:underline"
                        >
                          {maskText(f.affected_url)}
                          <ExternalLink className="h-3 w-3 shrink-0" />
                        </a>
                      </div>
                    )}
                    {f.asset_type === "mobile" && (
                      <div className="grid gap-2 rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 text-xs">
                        {mobileApp?.package_name && (
                          <p>
                            <span className="text-muted-foreground">Paket: </span>
                            {mobileApp.package_name}
                          </p>
                        )}
                        {(mobileApp?.version_name || mobileApp?.version_code) && (
                          <p>
                            <span className="text-muted-foreground">Sürüm: </span>
                            {mobileApp.version_name ?? "—"}
                            {mobileApp.version_code ? ` (${mobileApp.version_code})` : ""}
                          </p>
                        )}
                        {f.affected_component && (
                          <p>
                            <span className="text-muted-foreground">Bileşen / İzin: </span>
                            {f.affected_component}
                          </p>
                        )}
                        {f.masvs_category && (
                          <p>
                            <span className="text-muted-foreground">MASVS: </span>
                            {f.masvs_category}
                          </p>
                        )}
                        {f.platform && (
                          <p>
                            <span className="text-muted-foreground">Platform: </span>
                            {f.platform}
                          </p>
                        )}
                      </div>
                    )}
                    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                      <span>Kategori: {getFindingCategory(f)}</span>
                      <span>
                        İlk görülme:{" "}
                        {new Date(f.first_seen_at).toLocaleDateString("tr-TR")}
                      </span>
                      <span>
                        Son görülme:{" "}
                        {new Date(f.last_seen_at).toLocaleDateString("tr-TR")}
                      </span>
                    </div>
                  </div>
                </Section>

                <Section title="Risk açıklaması" icon={<AlertTriangle className="h-4 w-4" />}>
                  <RiskBreakdownVisual breakdown={f.risk_breakdown} riskScore={f.risk_score} />
                  {f.risk_model_version && (
                    <p className="text-xs text-muted-foreground">
                      Risk modeli: {f.risk_model_version}
                    </p>
                  )}
                </Section>

                <Section title="Kanıtlar">
                  <div className="space-y-2 text-sm">
                    {f.affected_url && (
                      <p>
                        <span className="text-muted-foreground">İstek URL: </span>
                        <code className="break-all text-xs">{maskText(f.affected_url)}</code>
                      </p>
                    )}
                    {evidenceRows.length === 0 ? (
                      <p className="text-muted-foreground">
                        Ek kanıt verisi bulunmuyor.
                      </p>
                    ) : (
                      <dl className="space-y-2 rounded-lg border border-border/50 bg-muted/10 p-3">
                        {evidenceRows.map((row) => (
                          <div key={row.label}>
                            <dt className="text-xs font-medium text-muted-foreground">
                              {row.label}
                            </dt>
                            <dd className="mt-0.5 break-all font-mono text-xs">{row.value}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        Tespit eden araçlar
                      </p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {sources.map((s) => (
                          <Badge key={s} variant="secondary">
                            {s}
                          </Badge>
                        ))}
                      </div>
                      {(f.source_tools?.length ?? 0) > 1 && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Korelasyon: {f.correlation_key ?? "—"} — birden fazla tarayıcı aynı
                          bulguyu doğruladı.
                        </p>
                      )}
                    </div>
                  </div>
                </Section>

                <Section title="AI Analizi" icon={<Sparkles className="h-4 w-4" />}>
                  {showAiSkeleton ? (
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                    </div>
                  ) : showAiFallback ? (
                    <p className="text-sm text-muted-foreground">
                      AI analizi henüz hazır değil. Kural tabanlı özet kısa süre içinde
                      görünecektir.
                    </p>
                  ) : (
                    <div className="space-y-3 rounded-lg border border-violet-500/20 bg-violet-500/5 p-4 text-sm">
                      <p>{f.ai_summary}</p>
                      {f.ai_remediation && (
                        <div>
                          <p className="mb-1 text-xs font-medium text-violet-300">
                            Önerilen düzeltme
                          </p>
                          <p className="whitespace-pre-wrap text-muted-foreground">
                            {f.ai_remediation}
                          </p>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-2 text-xs">
                        <Badge variant="outline">
                          Öncelik: {getFixPriority(f)}
                        </Badge>
                        {f.ai_confidence_label && (
                          <Badge variant="secondary">
                            {aiConfidenceLabel(f.ai_confidence_label)}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">
                    AI analizi destekleyicidir; otomatik doğrulama veya exploit yerine geçmez.
                  </p>
                </Section>

                <Section title="Nasıl düzeltilir?">
                  <RemediationTabsSection tabs={remediationTabs} />
                </Section>

                <Section title="Geçmiş" icon={<History className="h-4 w-4" />}>
                  <HistoryTimeline history={history} loading={historyLoading} />
                </Section>
              </div>
            </div>

            {canManageFinding && (
              <footer className="sticky bottom-0 shrink-0 border-t border-border/60 bg-background/95 px-6 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-1 items-center gap-2">
                  <label htmlFor="finding-status" className="sr-only">
                    Bulgu durumu
                  </label>
                  <select
                    id="finding-status"
                    className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm"
                    value={f.status}
                    disabled={statusUpdating}
                    onChange={(e) => void handleStatusChange(e.target.value)}
                  >
                    {WORKFLOW_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {FINDING_WORKFLOW_STATUS_TR[s]}
                      </option>
                    ))}
                  </select>
                </div>
                {enableRetest && f.asset_type !== "mobile" && (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={retestLoading}
                    onClick={() => void handleRetest()}
                    className="gap-2"
                  >
                    {retestLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                    Yeniden Doğrula
                  </Button>
                )}
              </div>
              </footer>
            )}
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

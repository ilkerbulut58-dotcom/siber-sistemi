"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import {
  apiFetch,
  type Finding,
  type ScanJob,
  type SiteProfile,
} from "@/lib/api-client";
import { ensureFreshAccessToken } from "@/lib/auth-tokens";
import { getApiBase } from "@/lib/api-base";
import {
  buildAiOverview,
  buildPrioritySummary,
  buildStatusSummaryText,
  buildTrendPoints,
  computeScoreDelta,
  computeSecurityScore,
  countBySeverity,
  countSourceTools,
  getHeaderStatuses,
  getTopFindings,
} from "@/lib/scan-analytics";
import { AISummaryCard } from "@/components/scan-results/ai-summary-card";
import { AllFindingsPanel } from "@/components/scan-results/all-findings-panel";
import { FindingHighlightsList } from "@/components/scan-results/finding-highlights-list";
import { RiskDistributionCard } from "@/components/scan-results/risk-distribution-card";
import { RiskTrendChart } from "@/components/scan-results/risk-trend-chart";
import { ScanDashboardSidebar, type ScanSection } from "@/components/scan-results/scan-dashboard-sidebar";
import { ScanScopeCard } from "@/components/scan-results/scan-scope-card";
import { ScanSummaryHeader } from "@/components/scan-results/scan-summary-header";
import { SecurityHeadersStatusGrid } from "@/components/scan-results/security-headers-status-grid";
import { SecurityScoreGauge } from "@/components/scan-results/security-score-gauge";
import { SourceToolsCard } from "@/components/scan-results/source-tools-card";
import { StatusSummaryCard } from "@/components/scan-results/status-summary-card";
import { SiteProfileCard } from "@/components/scan-results/site-profile-card";
import { FindingDetailDrawer } from "@/components/scans/finding-detail-drawer";
import { Button } from "@/components/ui/button";
import { sanitizeScanError } from "@/lib/scan-error-sanitizer";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/components/locale-provider";

type OrganizationMember = { user_id: string; role: string };

function ToastBanner({
  message,
  variant,
  onDismiss,
}: {
  message: string;
  variant: "success" | "error";
  onDismiss: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <div
      role="status"
      className={cn(
        "fixed bottom-6 right-6 z-[60] max-w-sm rounded-lg border px-4 py-3 text-sm shadow-lg",
        variant === "success"
          ? "border-green-500/40 bg-green-950/90 text-green-100"
          : "border-red-500/40 bg-red-950/90 text-red-100"
      )}
    >
      {message}
    </div>
  );
}

export default function ScanDetailPage() {
  const { t } = useTranslation();

  return (
    <Suspense
      fallback={
        <>
          <Navbar />
          <main className="container mx-auto px-4 py-12 text-sm text-muted-foreground">
            {t("scanResults.loadingScan")}
          </main>
        </>
      }
    >
      <ScanDetailPageContent />
    </Suspense>
  );
}

function ScanDetailPageContent() {
  const params = useParams<{ orgId: string; scanId: string }>();
  const { orgId, scanId } = params;
  const { getAccessToken, user } = useAuth();
  const { t, scanStatusLabel, locale, formatApiError } = useTranslation();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [scan, setScan] = useState<ScanJob | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [allScans, setAllScans] = useState<ScanJob[]>([]);
  const [trendPoints, setTrendPoints] = useState<Awaited<ReturnType<typeof buildTrendPoints>>>([]);
  const [activeSection, setActiveSection] = useState<ScanSection>("overview");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(
    null
  );
  const [showAiFull, setShowAiFull] = useState(false);
  const [canManageFindings, setCanManageFindings] = useState(false);
  const [siteProfile, setSiteProfile] = useState<SiteProfile | null>(null);

  const allFindingsRef = useRef<HTMLDivElement>(null);
  const isRunning = scan != null && !["completed", "failed", "cancelled"].includes(scan.status);

  const selectedFinding = useMemo(
    () => findings.find((f) => f.id === selectedFindingId) ?? null,
    [findings, selectedFindingId]
  );

  const severityCounts = useMemo(() => countBySeverity(findings), [findings]);
  const securityScore = useMemo(() => computeSecurityScore(findings, locale), [findings, locale]);
  const sourceCounts = useMemo(() => countSourceTools(findings), [findings]);
  const topFindings = useMemo(() => getTopFindings(findings, 8), [findings]);
  const headerStatuses = useMemo(() => getHeaderStatuses(findings), [findings]);
  const priorities = useMemo(() => buildPrioritySummary(findings), [findings]);
  const statusText = useMemo(
    () => buildStatusSummaryText(securityScore, severityCounts, priorities, locale),
    [securityScore, severityCounts, priorities, locale]
  );
  const aiOverview = useMemo(
    () => buildAiOverview(findings, securityScore, locale),
    [findings, securityScore, locale]
  );
  const scoreDelta = useMemo(
    () => computeScoreDelta(trendPoints, scanId),
    [trendPoints, scanId]
  );

  const sortedFindings = useMemo(
    () => [...findings].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0)),
    [findings]
  );

  const load = useCallback(async () => {
    try {
      const token = getAccessToken();
      const [scanData, findingData, scansData, members] = await Promise.all([
        apiFetch<ScanJob>(`/api/v1/organizations/${orgId}/scans/${scanId}`, { token }),
        apiFetch<Finding[]>(`/api/v1/organizations/${orgId}/findings?scan_id=${scanId}`, { token }),
        apiFetch<ScanJob[]>(`/api/v1/organizations/${orgId}/scans`, { token }),
        apiFetch<OrganizationMember[]>(`/api/v1/organizations/${orgId}/members`, { token }),
      ]);
      setScan(scanData);
      setFindings(findingData);
      setAllScans(scansData);
      const ownMembership = members.find((member) => member.user_id === user?.id);
      setCanManageFindings(Boolean(ownMembership && ownMembership.role !== "viewer"));

      const trend = await buildTrendPoints(scansData, scanId, findingData, (sid) =>
        apiFetch<Finding[]>(`/api/v1/organizations/${orgId}/findings?scan_id=${sid}`, { token }),
        locale
      );
      setTrendPoints(trend);

      if (scanData.status === "completed") {
        try {
          const profileData = await apiFetch<SiteProfile>(
            `/api/v1/organizations/${orgId}/scans/${scanId}/site-profile`,
            { token }
          );
          setSiteProfile(profileData);
        } catch {
          setSiteProfile(null);
        }
      } else {
        setSiteProfile(null);
      }

      setError(null);
    } catch (err) {
      const msg = formatApiError(err);
      if (!/token/i.test(msg)) setError(msg);
    }
  }, [formatApiError, getAccessToken, locale, orgId, scanId, user?.id]);

  useEffect(() => {
    load();
    if (!isRunning) return;
    const timer = setInterval(load, 4000);
    return () => clearInterval(timer);
  }, [load, isRunning]);

  const setFindingQueryParam = useCallback(
    (findingId: string | null, replace = true) => {
      const params = new URLSearchParams(searchParams.toString());
      if (findingId) params.set("finding", findingId);
      else params.delete("finding");
      const q = params.toString();
      const url = q ? `${pathname}?${q}` : pathname;
      if (replace) router.replace(url, { scroll: false });
      else router.push(url, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const clearFindingFromUrl = useCallback(() => {
    setSelectedFindingId(null);
    setDrawerOpen(false);
    setFindingQueryParam(null);
    setToast({ message: t("analytics.findingNotFound"), variant: "error" });
  }, [setFindingQueryParam, t]);

  const openFindingDrawer = useCallback(
    (findingId: string) => {
      setSelectedFindingId(findingId);
      setDrawerOpen(true);
      setFindingQueryParam(findingId);
    },
    [setFindingQueryParam]
  );

  const closeFindingDrawer = useCallback(
    (open: boolean) => {
      setDrawerOpen(open);
      if (!open) {
        setSelectedFindingId(null);
        setFindingQueryParam(null);
      }
    },
    [setFindingQueryParam]
  );

  useEffect(() => {
    const paramId = searchParams.get("finding");
    if (paramId && findings.some((f) => f.id === paramId)) {
      setSelectedFindingId(paramId);
      setDrawerOpen(true);
    } else if (paramId && scan) {
      clearFindingFromUrl();
    }
  }, [searchParams, findings, scan, clearFindingFromUrl]);

  function handleFindingUpdated(updated: Finding) {
    setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
  }

  function scrollToSection(section: ScanSection) {
    setActiveSection(section);
    const ids: Record<string, string> = {
      overview: "section-overview",
      findings: "section-findings",
      "all-findings": "section-all-findings",
      headers: "section-headers",
      "site-profile": "section-site-profile",
      reports: "section-reports",
    };
    document.getElementById(ids[section] ?? section)?.scrollIntoView({ behavior: "smooth" });
  }

  function handleRescan() {
    if (scan) window.location.href = `/dashboard/scan?url=${encodeURIComponent(scan.target_url)}`;
  }

  async function cancelScan() {
    if (!scan || !window.confirm(t("scanResults.cancelScanConfirm"))) return;
    try {
      await apiFetch(`/api/v1/organizations/${orgId}/scans/${scanId}/cancel`, {
        method: "POST",
        token: getAccessToken(),
      });
      setToast({ message: t("scanResults.cancelScanSuccess"), variant: "success" });
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function downloadReport(format: "html" | "pdf" | "json" = "pdf") {
    try {
      const token = await ensureFreshAccessToken();
      const response = await fetch(
        `${getApiBase()}/api/v1/organizations/${orgId}/scans/${scanId}/report?format=${format}&locale=${locale}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      if (!response.ok) throw new Error(t("scanResults.reportDownloadFailed"));
      const blob = await response.blob();
      const match = (response.headers.get("Content-Disposition") ?? "").match(/filename="([^"]+)"/);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = match?.[1] ?? `siber-report.${format}`;
      link.click();
      URL.revokeObjectURL(url);
      setToast({ message: t("scanResults.reportDownloaded"), variant: "success" });
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  return (
    <>
      <Navbar />
      <div className="mx-auto flex max-w-[1600px] gap-6 px-4 py-6 lg:px-6">
        <ScanDashboardSidebar
          orgId={orgId}
          projectId={scan?.project_id}
          active={activeSection}
          onNavigate={scrollToSection}
        />

        <main className="min-w-0 flex-1 space-y-6">
          <Link
            href="/dashboard/scan"
            className="inline-block text-sm text-muted-foreground hover:text-foreground"
          >
            ← {t("scanResults.newScan")}
          </Link>

          {!scan && !error && (
            <div className="rounded-lg border border-border/60 bg-card/50 px-4 py-8 text-center text-sm text-muted-foreground">
              {t("scanResults.loadingScan")}
            </div>
          )}

          {scan && (
            <ScanSummaryHeader
              scan={scan}
              isRunning={isRunning}
              onRescan={handleRescan}
              onDownload={() => downloadReport("pdf")}
            />
          )}

          {isRunning && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              <p>
                {t("scanResults.scanInProgress")} ({scanStatusLabel(scan?.status ?? "")}) —
                {t("scanResults.findingsAfterComplete")}
              </p>
              {scan?.status === "queued" && (
                <p className="mt-1 text-xs text-amber-200/80">{t("scanResults.queuedNote")}</p>
              )}
              {scan?.started_at && (
                <p className="mt-1 text-xs text-amber-200/80">
                  {t("scanResults.startedAt")}:{" "}
                  {new Date(scan.started_at).toLocaleTimeString(locale === "de" ? "de-DE" : "tr-TR")}
                  {" · "}
                  {t("analytics.safeProfileTiming")}
                </p>
              )}
              <Button type="button" size="sm" variant="outline" className="mt-3" onClick={() => void cancelScan()}>
                {t("scanResults.cancelScan")}
              </Button>
            </div>
          )}

          {scan?.status === "failed" && scan.error_log && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              <p className="font-medium">{t("scanResults.scanFailed")}</p>
              <p className="mt-1 text-xs">
                {t(sanitizeScanError(scan.error_log).detailKey as "scanResults.errorGeneric")}
              </p>
              <p className="mt-2 text-xs text-red-200/80">
                {t("scanResults.scanIdLabel")}: {scan.id}
              </p>
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div id="section-overview" className="grid gap-6 xl:grid-cols-[280px_1fr]">
            <div className="flex justify-center rounded-xl border border-border/60 bg-card/50 p-6">
              <SecurityScoreGauge result={securityScore} delta={scoreDelta} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <RiskDistributionCard counts={severityCounts} />
              <SourceToolsCard sources={sourceCounts} />
              {scan && <ScanScopeCard scan={scan} findings={findings} />}
              <StatusSummaryCard text={statusText} />
            </div>
          </div>

          <div id="section-site-profile">
            <SiteProfileCard profile={siteProfile} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <FindingHighlightsList
                findings={topFindings}
                onOpenDetail={openFindingDrawer}
                onViewAll={() => scrollToSection("all-findings")}
              />
            </div>
            <RiskTrendChart points={trendPoints} currentScanId={scanId} />
          </div>

          <AISummaryCard
            summary={aiOverview.summary}
            priorities={aiOverview.priorities}
            firstSteps={aiOverview.firstSteps}
            onExpand={() => setShowAiFull((v) => !v)}
          />

          {showAiFull && (
            <div className="space-y-3 rounded-xl border border-violet-500/20 bg-violet-500/5 p-4">
              {sortedFindings
                .filter((f) => f.ai_summary)
                .slice(0, 5)
                .map((f) => (
                  <div key={f.id} className="text-sm">
                    <p className="font-medium">{f.title}</p>
                    <p className="text-muted-foreground">{f.ai_summary}</p>
                  </div>
                ))}
            </div>
          )}

          <SecurityHeadersStatusGrid headers={headerStatuses} />

          <div ref={allFindingsRef}>
            <AllFindingsPanel
              findings={sortedFindings}
              onOpenDetail={openFindingDrawer}
            />
          </div>

          <div id="section-reports" className="rounded-xl border border-border/60 bg-card/50 p-6">
            <h2 className="mb-4 text-lg font-semibold">{t("scanResults.reports")}</h2>
            <p className="mb-3 text-sm text-muted-foreground">{t("scanResults.reportLocaleNote")}</p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => downloadReport("html")}>
                {t("scanResults.htmlReport")}
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => downloadReport("pdf")}>
                {t("scanResults.pdfReport")}
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => downloadReport("json")}>
                {t("scanResults.downloadJson")}
              </Button>
            </div>
          </div>
        </main>
      </div>

      <FindingDetailDrawer
        open={drawerOpen}
        onOpenChange={closeFindingDrawer}
        finding={selectedFinding}
        orgId={orgId}
        getAccessToken={getAccessToken}
        onFindingUpdated={handleFindingUpdated}
        onToast={(message, variant) => setToast({ message, variant })}
        onRetestNavigate={(newScanId) => {
          router.push(`/dashboard/${orgId}/scans/${newScanId}`);
        }}
        onFindingNotFound={clearFindingFromUrl}
        canManageFinding={canManageFindings}
        scanCompleted={scan?.status === "completed"}
      />

      {toast && (
        <ToastBanner
          message={toast.message}
          variant={toast.variant}
          onDismiss={() => setToast(null)}
        />
      )}
    </>
  );
}

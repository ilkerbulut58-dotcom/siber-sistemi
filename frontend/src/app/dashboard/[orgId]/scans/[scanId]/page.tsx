"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { cn } from "@/lib/utils";
import { SCAN_STATUS_TR } from "@/lib/i18n-tr";

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
  const params = useParams<{ orgId: string; scanId: string }>();
  const { orgId, scanId } = params;
  const { getAccessToken, user } = useAuth();
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
  const securityScore = useMemo(() => computeSecurityScore(findings), [findings]);
  const sourceCounts = useMemo(() => countSourceTools(findings), [findings]);
  const topFindings = useMemo(() => getTopFindings(findings, 8), [findings]);
  const headerStatuses = useMemo(() => getHeaderStatuses(findings), [findings]);
  const priorities = useMemo(() => buildPrioritySummary(findings), [findings]);
  const statusText = useMemo(
    () => buildStatusSummaryText(securityScore, severityCounts, priorities),
    [securityScore, severityCounts, priorities]
  );
  const aiOverview = useMemo(
    () => buildAiOverview(findings, securityScore),
    [findings, securityScore]
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
        apiFetch<Finding[]>(`/api/v1/organizations/${orgId}/findings?scan_id=${sid}`, { token })
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
      const msg = err instanceof Error ? err.message : "Veri yüklenemedi";
      if (!/token/i.test(msg)) setError(msg);
    }
  }, [getAccessToken, orgId, scanId, user?.id]);

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
    setToast({ message: "Bulgu bulunamadı veya erişim yok.", variant: "error" });
  }, [setFindingQueryParam]);

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

  async function downloadReport(format: "html" | "pdf" | "json" = "pdf") {
    try {
      const token = await ensureFreshAccessToken();
      const response = await fetch(
        `${getApiBase()}/api/v1/organizations/${orgId}/scans/${scanId}/report?format=${format}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      if (!response.ok) throw new Error("Rapor indirilemedi");
      const blob = await response.blob();
      const match = (response.headers.get("Content-Disposition") ?? "").match(/filename="([^"]+)"/);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = match?.[1] ?? `siber-rapor.${format}`;
      link.click();
      URL.revokeObjectURL(url);
      setToast({ message: "Rapor indirildi.", variant: "success" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rapor indirilemedi");
    }
  }

  function handleRescan() {
    if (scan) window.location.href = `/dashboard/scan?url=${encodeURIComponent(scan.target_url)}`;
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
            ← Yeni tarama
          </Link>

          {!scan && !error && (
            <div className="rounded-lg border border-border/60 bg-card/50 px-4 py-8 text-center text-sm text-muted-foreground">
              Tarama bilgileri yükleniyor…
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
                Tarama devam ediyor ({SCAN_STATUS_TR[scan?.status ?? ""] ?? scan?.status}) —
                bulgular tarama tamamlanınca görünür.
              </p>
              {scan?.status === "queued" && (
                <p className="mt-1 text-xs text-amber-200/80">
                  Kuyrukta bekliyorsa worker meşgul olabilir; birkaç dakika normaldir.
                </p>
              )}
              {scan?.started_at && (
                <p className="mt-1 text-xs text-amber-200/80">
                  Başlangıç: {new Date(scan.started_at).toLocaleTimeString("tr-TR")}
                  {" · "}
                  Güvenli profil genelde 2–3 dk, derin profil 4–5 dk sürer. 12 dk sonra otomatik
                  iptal edilir.
                </p>
              )}
            </div>
          )}

          {scan?.status === "failed" && scan.error_log && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              <p className="font-medium">Tarama tamamlanamadı</p>
              <p className="mt-1 text-xs">{scan.error_log}</p>
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
            <h2 className="mb-4 text-lg font-semibold">Raporlar</h2>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => downloadReport("html")}>
                HTML Rapor
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => downloadReport("pdf")}>
                PDF Rapor
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => downloadReport("json")}>
                JSON İndir
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

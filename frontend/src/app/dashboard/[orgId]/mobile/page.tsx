"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import {
  apiFetch,
  type Finding,
  type MobileApplication,
  type MobileUploadResult,
  type Project,
} from "@/lib/api-client";
import { FindingDetailDrawer } from "@/components/scans/finding-detail-drawer";
import { SecurityScoreGauge } from "@/components/scan-results/security-score-gauge";
import { RiskDistributionCard } from "@/components/scan-results/risk-distribution-card";
import { FindingRowCard } from "@/components/scan-results/finding-row-card";
import { countBySeverity, computeSecurityScore } from "@/lib/scan-analytics";
import {
  countMobileByCategory,
  filterMobileFindings,
  MOBILE_CATEGORY_LABELS,
  type MobileFindingCategory,
} from "@/lib/mobile-analytics";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type OrganizationMember = { user_id: string; role: string };

export default function MobileSecurityPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const { getAccessToken, user } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [apps, setApps] = useState<MobileApplication[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [projectId, setProjectId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [drawerFindingId, setDrawerFindingId] = useState<string | null>(null);
  const [canManageFindings, setCanManageFindings] = useState(false);
  const [category, setCategory] = useState<MobileFindingCategory>("all");

  const selectedApp = apps.find((a) => a.id === selectedAppId) ?? null;
  const severityCounts = useMemo(() => countBySeverity(findings), [findings]);
  const securityScore = useMemo(() => {
    if (selectedApp?.security_score != null) {
      const s = selectedApp.security_score;
      return {
        score: Math.round(s),
        level: s >= 80 ? "strong" : s >= 60 ? "good" : s >= 40 ? "medium" : "weak",
        label: s >= 80 ? "Güçlü" : s >= 60 ? "İyi" : s >= 40 ? "Orta" : "Zayıf",
      } as ReturnType<typeof computeSecurityScore>;
    }
    return computeSecurityScore(findings);
  }, [findings, selectedApp]);
  const categoryCounts = useMemo(() => countMobileByCategory(findings), [findings]);
  const filteredFindings = useMemo(
    () => filterMobileFindings(findings, category),
    [findings, category]
  );
  const drawerFinding = findings.find((f) => f.id === drawerFindingId) ?? null;

  const load = useCallback(async () => {
    const token = getAccessToken();
    const [projData, appData, members] = await Promise.all([
      apiFetch<Project[]>(`/api/v1/organizations/${orgId}/projects`, { token }),
      apiFetch<MobileApplication[]>(`/api/v1/organizations/${orgId}/mobile/applications`, {
        token,
      }),
      apiFetch<OrganizationMember[]>(`/api/v1/organizations/${orgId}/members`, { token }),
    ]);
    setProjects(projData);
    setApps(appData);
    const ownMembership = members.find((member) => member.user_id === user?.id);
    setCanManageFindings(
      Boolean(ownMembership && ownMembership.role !== "viewer")
    );
    if (!projectId && projData[0]) setProjectId(projData[0].id);
  }, [getAccessToken, orgId, projectId, user?.id]);

  const loadFindings = useCallback(
    async (appId: string) => {
      const token = getAccessToken();
      const data = await apiFetch<Finding[]>(
        `/api/v1/organizations/${orgId}/mobile/applications/${appId}/findings`,
        { token }
      );
      setFindings(data);
    },
    [getAccessToken, orgId]
  );

  useEffect(() => {
    void load().catch((e) => setError(e instanceof Error ? e.message : "Yüklenemedi"));
  }, [load]);

  useEffect(() => {
    if (!selectedAppId) return;
    void loadFindings(selectedAppId).catch(() => setFindings([]));
    if (selectedApp?.analysis_status === "running" || selectedApp?.analysis_status === "queued") {
      const t = setInterval(() => {
        void loadFindings(selectedAppId);
        void load();
      }, 5000);
      return () => clearInterval(t);
    }
  }, [selectedAppId, selectedApp?.analysis_status, loadFindings, load]);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file || !projectId || !authorized) return;
    setUploading(true);
    setError(null);
    try {
      const token = getAccessToken();
      const form = new FormData();
      form.append("project_id", projectId);
      form.append("environment", "staging");
      form.append("authorization_accepted", "true");
      form.append("file", file);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/organizations/${orgId}/mobile/applications`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        }
      );
      const body = await res.json();
      if (!res.ok || !body.success) throw new Error(body.error?.message || "Yükleme başarısız");
      const result = body.data as MobileUploadResult;
      setToast(result.duplicate ? "Bu APK daha önce yüklendi." : "APK yüklendi, analiz başlatıldı.");
      setSelectedAppId(result.id);
      await load();
      await loadFindings(result.id);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yükleme hatası");
    } finally {
      setUploading(false);
    }
  }

  async function downloadReport(format: "json" | "html" | "pdf" = "json") {
    if (!selectedAppId) return;
    const token = getAccessToken();
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/organizations/${orgId}/mobile/applications/${selectedAppId}/report?format=${format}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    );
    if (!res.ok) throw new Error("Rapor indirilemedi");
    const blob = await res.blob();
    const ext = format === "json" ? "json" : format;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `siber-mobile-rapor.${ext}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Mobil Uygulama Güvenliği</h1>
            <p className="text-sm text-muted-foreground">
              Statik APK analizi — dinamik saldırı veya kod çalıştırma yok
            </p>
          </div>
          <Link href={`/dashboard/${orgId}`} className="text-sm text-muted-foreground hover:text-foreground">
            ← Organizasyon
          </Link>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {toast && <p className="text-sm text-green-400">{toast}</p>}

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="border-border/60 bg-card/80 lg:col-span-1">
            <CardHeader>
              <CardTitle>Yeni APK Yükle</CardTitle>
              <CardDescription>Maks. 100 MB — yalnızca .apk</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleUpload}>
                <div>
                  <Label htmlFor="project">Proje</Label>
                  <select
                    id="project"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label htmlFor="apk">APK dosyası</Label>
                  <Input
                    id="apk"
                    type="file"
                    accept=".apk,application/vnd.android.package-archive"
                    className="mt-1"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <label className="flex items-start gap-2 text-xs text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={authorized}
                    onChange={(e) => setAuthorized(e.target.checked)}
                  />
                  Bu uygulamayı analiz etme yetkim olduğunu onaylıyorum.
                </label>
                <Button type="submit" disabled={uploading || !file || !authorized} className="w-full">
                  {uploading ? "Yükleniyor…" : "Analizi Başlat"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 lg:col-span-2">
            <CardHeader>
              <CardTitle>Mobil Uygulamalar</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {apps.length === 0 ? (
                <p className="text-sm text-muted-foreground">Henüz uygulama yüklenmedi.</p>
              ) : (
                apps.map((app) => (
                  <button
                    key={app.id}
                    type="button"
                    onClick={() => setSelectedAppId(app.id)}
                    className={`w-full rounded-lg border p-3 text-left text-sm transition-colors ${
                      selectedAppId === app.id
                        ? "border-indigo-500/50 bg-indigo-500/10"
                        : "border-border/60 hover:bg-muted/20"
                    }`}
                  >
                    <p className="font-medium">{app.application_name ?? app.original_filename}</p>
                    <p className="text-xs text-muted-foreground">
                      {app.package_name ?? "—"} · {app.analysis_status} · {app.findings_count} bulgu
                    </p>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {selectedApp && (
          <>
            <Card className="border-border/60 bg-card/80">
              <CardContent className="flex flex-wrap items-center gap-4 pt-6 text-sm">
                <div>
                  <p className="font-medium">
                    {selectedApp.application_name ?? selectedApp.original_filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Paket: {selectedApp.package_name ?? "—"} · Sürüm:{" "}
                    {selectedApp.version_name ?? "—"}
                    {selectedApp.version_code ? ` (${selectedApp.version_code})` : ""}
                  </p>
                </div>
                <div className="text-xs text-muted-foreground">
                  Durum: {selectedApp.analysis_status} · {selectedApp.findings_count} bulgu
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 md:grid-cols-[220px_1fr]">
              <div className="flex justify-center rounded-xl border border-border/60 bg-card/50 p-4">
                <SecurityScoreGauge result={securityScore} />
              </div>
              <RiskDistributionCard counts={severityCounts} />
            </div>

            {selectedApp.analysis_summary && (
              <Card className="border-border/60 bg-card/80">
                <CardHeader>
                  <CardTitle className="text-lg">Analiz Özeti</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  {Object.entries(selectedApp.analysis_summary).map(([k, v]) => (
                    <div key={k} className="rounded-md border border-border/40 bg-muted/10 p-2">
                      <p className="text-xs text-muted-foreground">{k}</p>
                      <p className="font-medium">{String(v)}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card className="border-border/60 bg-card/80">
              <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
                <CardTitle>Mobil Bulgular</CardTitle>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => downloadReport("json")}>
                    JSON
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => downloadReport("html")}>
                    HTML
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => downloadReport("pdf")}>
                    PDF
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {(Object.keys(MOBILE_CATEGORY_LABELS) as MobileFindingCategory[]).map((key) => {
                    const count = categoryCounts[key];
                    if (key !== "all" && count === 0) return null;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setCategory(key)}
                        className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                          category === key
                            ? "border-indigo-500/50 bg-indigo-500/15 text-foreground"
                            : "border-border/60 text-muted-foreground hover:bg-muted/20"
                        }`}
                      >
                        {MOBILE_CATEGORY_LABELS[key]} ({count})
                      </button>
                    );
                  })}
                </div>

                {filteredFindings.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {selectedApp.analysis_status === "completed"
                      ? category === "all"
                        ? "Bulgu tespit edilmedi."
                        : "Bu kategoride bulgu yok."
                      : "Analiz devam ediyor…"}
                  </p>
                ) : (
                  filteredFindings.map((f) => (
                    <FindingRowCard
                      key={f.id}
                      finding={f}
                      onDetail={() => setDrawerFindingId(f.id)}
                      onRowClick={() => setDrawerFindingId(f.id)}
                    />
                  ))
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>

      <FindingDetailDrawer
        open={drawerFindingId != null}
        onOpenChange={(open) => !open && setDrawerFindingId(null)}
        finding={drawerFinding}
        orgId={orgId}
        getAccessToken={getAccessToken}
        onFindingUpdated={(f) =>
          setFindings((prev) => prev.map((x) => (x.id === f.id ? f : x)))
        }
        onToast={(msg, variant) => {
          if (variant === "success") {
            setToast(msg);
            setError(null);
          } else {
            setError(msg);
          }
        }}
        onRetestNavigate={() => {}}
        enableRetest={false}
        canManageFinding={canManageFindings}
        scanCompleted={selectedApp?.analysis_status === "completed"}
        mobileApp={
          selectedApp
            ? {
                application_name: selectedApp.application_name,
                package_name: selectedApp.package_name,
                version_name: selectedApp.version_name,
                version_code: selectedApp.version_code,
              }
            : undefined
        }
      />
    </>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  Globe,
  Radar,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type AsmDiscoveryJob,
  type MobileUploadResult,
  type OnboardingStatus,
  type Organization,
  type Project,
  type QuickScanResult,
  type ScanProfile,
} from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type AssessmentResult = {
  label: string;
  status: "success" | "error" | "skipped";
  href?: string;
  message?: string;
};

export default function AssessmentPage() {
  const router = useRouter();
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError, scanProfileLabel } = useTranslation();
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [testMode, setTestMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AssessmentResult[]>([]);
  const [runWeb, setRunWeb] = useState(true);
  const [runAsm, setRunAsm] = useState(true);
  const [runMobile, setRunMobile] = useState(false);
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const token = getAccessToken();
      const health = await fetch(`${getApiBase()}/api/v1/health`).then((r) => r.json());
      setTestMode(Boolean(health?.data?.skip_domain_verification));

      const [profileData, orgData] = await Promise.all([
        apiFetch<ScanProfile[]>("/api/v1/scan-profiles", { token }),
        apiFetch<Organization[]>("/api/v1/organizations", { token }),
      ]);
      setProfiles(profileData);
      setOrgs(orgData);
      if (orgData[0] && !selectedOrgId) {
        setSelectedOrgId(orgData[0].id);
      }
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken, selectedOrgId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedOrgId) {
      setProjects([]);
      setSelectedProjectId("");
      setOnboarding(null);
      return;
    }
    void apiFetch<Project[]>(`/api/v1/organizations/${selectedOrgId}/projects`, {
      token: getAccessToken(),
    })
      .then((data) => {
        setProjects(data);
        setSelectedProjectId(data[0]?.id ?? "");
      })
      .catch(() => {
        setProjects([]);
        setSelectedProjectId("");
      });
    void apiFetch<OnboardingStatus>(`/api/v1/organizations/${selectedOrgId}/onboarding-status`, {
      token: getAccessToken(),
    })
      .then(setOnboarding)
      .catch(() => setOnboarding(null));
  }, [selectedOrgId, getAccessToken]);

  async function uploadApk(
    orgId: string,
    projectId: string,
    file: File
  ): Promise<MobileUploadResult> {
    const token = getAccessToken();
    const form = new FormData();
    form.append("project_id", projectId);
    form.append("environment", "staging");
    form.append("authorization_accepted", "true");
    form.append("file", file);
    const res = await fetch(
      `${getApiBase()}/api/v1/organizations/${orgId}/mobile/applications`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      }
    );
    const body = await res.json();
    if (!res.ok || !body.success) {
      throw new Error(body.error?.message || t("assessment.mobileUploadFailed"));
    }
    return body.data as MobileUploadResult;
  }

  async function runAssessment(
    e: FormEvent<HTMLFormElement>,
    mode: "full" | "web" | "asm" | "mobile"
  ) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResults([]);

    const form = new FormData(e.currentTarget);
    const targetUrl = String(form.get("target_url") || "");
    const scanProfile = String(form.get("scan_profile") || "safe");
    const authorized = form.get("authorization") === "on";
    const apkFile = (form.get("apk") as File | null)?.size
      ? (form.get("apk") as File)
      : null;

    const doWeb = mode === "full" ? runWeb : mode === "web";
    const doAsm = mode === "full" ? runAsm : mode === "asm";
    const doMobile = mode === "full" ? runMobile : mode === "mobile";

    const nextResults: AssessmentResult[] = [];

    try {
      if (!authorized && (doWeb || doAsm)) {
        throw new Error(t("assessment.authRequired"));
      }
      if (doMobile && !apkFile) {
        throw new Error(t("assessment.apkRequired"));
      }
      if (doMobile && !doWeb && (!selectedOrgId || !selectedProjectId)) {
        throw new Error(t("assessment.mobileOnlyNeedOrg"));
      }
      if ((doWeb || doAsm) && !targetUrl) {
        throw new Error(t("assessment.urlRequired"));
      }

      let orgId = selectedOrgId;
      let projectId = selectedProjectId;
      let domainId: string | null = null;
      let scanHref: string | undefined;
      let asmHref: string | undefined;
      let mobileHref: string | undefined;

      if (doWeb || doAsm) {
        const quick = await apiFetch<QuickScanResult>("/api/v1/quick-scan", {
          method: "POST",
          token: getAccessToken(),
          body: JSON.stringify({
            target_url: targetUrl,
            scan_profile: scanProfile,
            authorization_accepted: authorized,
          }),
        });
        orgId = quick.organization_id;
        projectId = quick.project_id;
        domainId = quick.domain_id;
        scanHref = `/dashboard/${orgId}/scans/${quick.scan.id}`;

        if (doWeb) {
          nextResults.push({
            label: t("assessment.webScan"),
            status: "success",
            href: scanHref,
            message: t("assessment.webScanStarted"),
          });
        } else {
          nextResults.push({
            label: t("assessment.webScan"),
            status: "skipped",
            message: t("assessment.webScanSkipped"),
          });
        }
      }

      if (doAsm && orgId && projectId && domainId) {
        const asm = await apiFetch<AsmDiscoveryJob>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/asm/discover`,
          {
            method: "POST",
            token: getAccessToken(),
            body: JSON.stringify({
              domain_id: domainId,
              target_url: targetUrl,
              authorization_accepted: authorized,
            }),
          }
        );
        asmHref = `/dashboard/${orgId}/projects/${projectId}/attack-surface`;
        nextResults.push({
          label: t("assessment.asmDiscoveryLabel"),
          status: "success",
          href: asmHref,
          message: t("assessment.asmJobStarted", { id: asm.id.slice(0, 8) }),
        });
      }

      if (doMobile && apkFile && orgId && projectId) {
        const mobile = await uploadApk(orgId, projectId, apkFile);
        mobileHref = `/dashboard/${orgId}/mobile`;
        nextResults.push({
          label: t("assessment.mobileAnalysisLabel"),
          status: "success",
          href: mobileHref,
          message: mobile.duplicate
            ? t("assessment.mobileDuplicate")
            : t("assessment.mobileUploaded"),
        });
      }

      setResults(nextResults);

      if (mode === "web" && scanHref) {
        router.push(scanHref);
        return;
      }
      if (mode === "asm" && asmHref) {
        router.push(asmHref);
        return;
      }
      if (mode === "mobile" && mobileHref) {
        router.push(mobileHref);
        return;
      }
      if (mode === "full" && scanHref) {
        router.push(scanHref);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  const quotaUnlimited = Boolean(user?.is_platform_admin);
  const todayCount = onboarding?.daily_scan_count ?? 0;
  const effectiveQuota = quotaUnlimited ? null : (onboarding?.daily_scan_quota ?? 5);
  const quotaExceeded =
    !quotaUnlimited && effectiveQuota !== null && todayCount >= effectiveQuota;
  const activeScanAllowed = onboarding?.pilot_active_scan_allowed !== false;
  const isRestrictedProfile = (name: string) =>
    !activeScanAllowed && (name === "deep" || name === "code");

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-3xl font-bold">{t("assessment.title")}</h1>
          <p className="mt-2 text-muted-foreground">{t("assessment.subtitle")}</p>
        </div>

        {testMode && (
          <p className="rounded-md border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm text-green-200">
            {t("project.testModeBanner")}
          </p>
        )}

        {error && <p className="text-destructive">{error}</p>}
        {effectiveQuota != null && (
          <p className={`text-sm ${quotaExceeded ? "text-orange-400" : "text-muted-foreground"}`}>
            {t("scanPage.quotaToday", { count: todayCount, quota: effectiveQuota })}
            {quotaExceeded && ` — ${t("scanPage.quotaExceededHint")}`}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: Globe, title: t("assessment.webScan"), desc: t("assessment.webScanDesc") },
            { icon: Radar, title: t("assessment.asm"), desc: t("dashboard.attackSurfaceDesc") },
            { icon: Smartphone, title: t("assessment.mobile"), desc: t("dashboard.quickMobileDesc") },
          ].map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="border-border/60 bg-card/80">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Icon className="h-4 w-4 text-primary" />
                  {title}
                </CardTitle>
                <CardDescription>{desc}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary" />
              {t("assessment.settingsTitle")}
            </CardTitle>
            <CardDescription>
              {t("assessment.fullScanNote")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              ref={formRef}
              onSubmit={(e) => runAssessment(e, "full")}
              className="space-y-5"
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="target_url">{t("assessment.targetUrlWebAsm")}</Label>
                  <Input
                    id="target_url"
                    name="target_url"
                    type="url"
                    placeholder={t("project.targetUrlPlaceholder")}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="scan_profile">{t("assessment.webProfile")}</Label>
                  {!activeScanAllowed && (
                    <p className="text-xs text-orange-400">{t("project.profileDisabled")}</p>
                  )}
                  <select
                    id="scan_profile"
                    name="scan_profile"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    defaultValue="safe"
                  >
                    {profiles.map((p) => (
                      <option key={p.id} value={p.name} disabled={isRestrictedProfile(p.name)}>
                        {scanProfileLabel(p.name, p.display_name)}
                      </option>
                    ))}
                    {profiles.length === 0 && (
                      <option value="safe">{t("assessment.safeProfileFallback")}</option>
                    )}
                  </select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="org">{t("assessment.orgMobileOnly")}</Label>
                  <select
                    id="org"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={selectedOrgId}
                    onChange={(e) => setSelectedOrgId(e.target.value)}
                  >
                    <option value="">{t("assessment.autoFromWeb")}</option>
                    {orgs.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="project">{t("assessment.projectMobileOnly")}</Label>
                  <select
                    id="project"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={selectedProjectId}
                    onChange={(e) => setSelectedProjectId(e.target.value)}
                    disabled={!selectedOrgId}
                  >
                    <option value="">{t("common.selectEllipsis")}</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="apk">{t("assessment.apkOptional")}</Label>
                <Input
                  id="apk"
                  name="apk"
                  type="file"
                  accept=".apk,application/vnd.android.package-archive"
                />
              </div>

              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={runWeb}
                    onChange={(e) => setRunWeb(e.target.checked)}
                  />
                  {t("assessment.webScan")}
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={runAsm}
                    onChange={(e) => setRunAsm(e.target.checked)}
                  />
                  {t("assessment.asm")}
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={runMobile}
                    onChange={(e) => setRunMobile(e.target.checked)}
                  />
                  {t("assessment.mobile")}
                </label>
              </div>

              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" name="authorization" className="mt-1" defaultChecked />
                <span>{t("project.authorization")}</span>
              </label>

              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={loading || (runWeb && quotaExceeded)}>
                  {loading
                    ? t("scanPage.starting")
                    : runWeb && quotaExceeded
                      ? t("scanPage.scanDisabledQuota")
                      : t("assessment.runFull")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading || quotaExceeded}
                  onClick={() => {
                    if (formRef.current) {
                      void runAssessment(
                        { preventDefault: () => {}, currentTarget: formRef.current } as FormEvent<HTMLFormElement>,
                        "web"
                      );
                    }
                  }}
                >
                  {t("assessment.runWeb")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={() => {
                    if (formRef.current) {
                      void runAssessment(
                        { preventDefault: () => {}, currentTarget: formRef.current } as FormEvent<HTMLFormElement>,
                        "asm"
                      );
                    }
                  }}
                >
                  {t("assessment.runAsm")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={() => {
                    if (formRef.current) {
                      void runAssessment(
                        { preventDefault: () => {}, currentTarget: formRef.current } as FormEvent<HTMLFormElement>,
                        "mobile"
                      );
                    }
                  }}
                >
                  {t("assessment.runMobile")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {results.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>{t("assessment.results")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {results.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium">{item.label}</p>
                    {item.message && (
                      <p className="text-xs text-muted-foreground">{item.message}</p>
                    )}
                  </div>
                  {item.href && (
                    <Link href={item.href} className="text-primary underline">
                      {t("common.open")}
                    </Link>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </main>
    </>
  );
}

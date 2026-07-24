"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type OnboardingStatus, type QuickScanResult, type ScanJob, type ScanProfile } from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function QuickScanPage() {
  const router = useRouter();
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError, scanProfileLabel, scanProfileDescription, scanStatusLabel } =
    useTranslation();
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [recentScans, setRecentScans] = useState<ScanJob[]>([]);
  const [testMode, setTestMode] = useState(true);
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const health = await fetch(`${getApiBase()}/api/v1/health`).then((r) => r.json());
      setTestMode(Boolean(health?.data?.skip_domain_verification));

      const profileData = await apiFetch<ScanProfile[]>("/api/v1/scan-profiles", {
        token: getAccessToken(),
      });
      setProfiles(profileData);

      const orgs = await apiFetch<{ id: string }[]>("/api/v1/organizations", {
        token: getAccessToken(),
      });
      if (orgs[0]) {
        const scans = await apiFetch<ScanJob[]>(`/api/v1/organizations/${orgs[0].id}/scans`, {
          token: getAccessToken(),
        });
        setRecentScans(scans.slice(0, 8));
        const onboardingData = await apiFetch<OnboardingStatus>(
          `/api/v1/organizations/${orgs[0].id}/onboarding-status`,
          { token: getAccessToken() }
        ).catch(() => null);
        setOnboarding(onboardingData);
      }
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 6000);
    return () => clearInterval(timer);
  }, [load]);

  const quotaUnlimited = Boolean(user?.is_platform_admin);
  const todayCount = onboarding?.daily_scan_count ?? 0;
  const effectiveQuota = quotaUnlimited ? null : (onboarding?.daily_scan_quota ?? 5);
  const quotaExceeded =
    !quotaUnlimited && effectiveQuota !== null && todayCount >= effectiveQuota;
  const activeScanAllowed = onboarding?.pilot_active_scan_allowed !== false;
  const isRestrictedProfile = (name: string) =>
    !activeScanAllowed && (name === "deep" || name === "code");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const form = new FormData(e.currentTarget);
    try {
      const result = await apiFetch<QuickScanResult>("/api/v1/quick-scan", {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          target_url: form.get("target_url"),
          scan_profile: form.get("scan_profile") || "safe",
          authorization_accepted: form.get("authorization") === "on",
        }),
      });
      router.push(`/dashboard/${result.organization_id}/scans/${result.scan.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-3xl px-4 py-8">
        <h1 className="mb-2 text-3xl font-bold">{t("scanPage.title")}</h1>
        <p className="mb-6 text-muted-foreground">{t("scanPage.subtitle")}</p>

        {testMode && (
          <p className="mb-4 rounded-md border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm text-green-200">
            {t("scanPage.testBanner")}
          </p>
        )}

        {error && <p className="mb-4 text-destructive">{error}</p>}
        {effectiveQuota != null && (
          <p className={`mb-4 text-sm ${quotaExceeded ? "text-orange-400" : "text-muted-foreground"}`}>
            {t("scanPage.quotaToday", { count: todayCount, quota: effectiveQuota })}
            {quotaExceeded && ` — ${t("scanPage.quotaExceededHint")}`}
          </p>
        )}

        <Card>
          <CardHeader>
            <CardTitle>{t("assessment.targetSite")}</CardTitle>
            <CardDescription>{t("assessment.targetSiteDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="target_url">{t("assessment.siteUrl")}</Label>
                <Input
                  id="target_url"
                  name="target_url"
                  type="url"
                  placeholder={t("project.targetUrlPlaceholder")}
                  required
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="scan_profile">{t("scanPage.scanProfile")}</Label>
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
                      {scanProfileLabel(p.name, p.display_name)} —{" "}
                      {scanProfileDescription(p.name, p.description ?? "")}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" name="authorization" className="mt-1" required defaultChecked />
                <span>{t("scanPage.authorization")}</span>
              </label>
              <Button type="submit" className="w-full" disabled={loading || quotaExceeded}>
                {loading ? t("scanPage.starting") : quotaExceeded ? t("scanPage.scanDisabledQuota") : t("scanPage.start")}
              </Button>
            </form>
          </CardContent>
        </Card>

        {recentScans.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>{t("scanPage.recentScans")}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {recentScans.map((scan) => (
                  <li key={scan.id}>
                    <Link
                      href={`/dashboard/${scan.organization_id}/scans/${scan.id}`}
                      className="block rounded-md border border-border px-4 py-3 hover:bg-muted/40"
                    >
                      <div className="font-medium">{scan.target_url}</div>
                      <div className="text-muted-foreground">
                        {scanStatusLabel(scan.status)} · {scan.findings_count}{" "}
                        {t("common.findings")}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link href="/dashboard" className="underline hover:text-foreground">
            ← {t("assessment.backToDashboard")}
          </Link>
        </p>
      </main>
    </>
  );
}

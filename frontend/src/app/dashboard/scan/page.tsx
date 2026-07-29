"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowRight, Globe, Shield, Zap } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type OnboardingStatus,
  type QuickScanResult,
  type ScanJob,
  type ScanProfile,
} from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type ProfileMode = "safe" | "deep";

export default function QuickScanPage() {
  const router = useRouter();
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError, scanStatusLabel } = useTranslation();
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [recentScans, setRecentScans] = useState<ScanJob[]>([]);
  const [testMode, setTestMode] = useState(false);
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [profileMode, setProfileMode] = useState<ProfileMode>("safe");
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
  const deepDisabled = !activeScanAllowed;

  const resolvedProfile =
    profileMode === "deep"
      ? profiles.find((p) => p.name === "deep")?.name ?? "deep"
      : profiles.find((p) => p.name === "safe")?.name ?? "safe";

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
          scan_profile: resolvedProfile,
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
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">{t("scanPage.title")}</h1>
          <p className="mt-2 text-muted-foreground">{t("scanPage.subtitle")}</p>
        </div>

        {testMode && (
          <p className="mb-4 rounded-lg border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm text-green-200">
            {t("scanPage.testBanner")}
          </p>
        )}

        {error && (
          <p className="mb-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        {effectiveQuota != null && (
          <p
            className={cn(
              "mb-4 text-sm",
              quotaExceeded ? "text-orange-400" : "text-muted-foreground"
            )}
          >
            {t("scanPage.quotaToday", { count: todayCount, quota: effectiveQuota })}
            {quotaExceeded && ` — ${t("scanPage.quotaExceededHint")}`}
          </p>
        )}

        <Card className="glass-card border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-primary" />
              {t("assessment.targetSite")}
            </CardTitle>
            <CardDescription>{t("assessment.targetSiteDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="target_url">{t("assessment.siteUrl")}</Label>
                <Input
                  id="target_url"
                  name="target_url"
                  type="url"
                  placeholder="https://example.com"
                  required
                  autoFocus
                  className="h-11 text-base"
                />
              </div>

              <div className="space-y-3">
                <Label>{t("scanPage.scanProfile")}</Label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => setProfileMode("safe")}
                    className={cn(
                      "rounded-lg border p-4 text-left transition-all",
                      profileMode === "safe"
                        ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                        : "border-border hover:border-primary/40"
                    )}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <Shield className="h-4 w-4 text-primary" />
                      <span className="font-medium">{t("scanPage.profileQuick")}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{t("scanPage.profileQuickDesc")}</p>
                  </button>
                  <button
                    type="button"
                    disabled={deepDisabled}
                    onClick={() => !deepDisabled && setProfileMode("deep")}
                    className={cn(
                      "rounded-lg border p-4 text-left transition-all",
                      deepDisabled && "cursor-not-allowed opacity-50",
                      profileMode === "deep" && !deepDisabled
                        ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                        : "border-border hover:border-primary/40"
                    )}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <Zap className="h-4 w-4 text-orange-400" />
                      <span className="font-medium">{t("scanPage.profileDeep")}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{t("scanPage.profileDeepDesc")}</p>
                  </button>
                </div>
                {deepDisabled && (
                  <p className="text-xs text-orange-400">{t("project.profileDisabled")}</p>
                )}
              </div>

              <label className="flex items-start gap-3 rounded-lg border border-border/60 bg-muted/10 p-4 text-sm">
                <input type="checkbox" name="authorization" className="mt-1" required defaultChecked />
                <span>{t("scanPage.authorization")}</span>
              </label>

              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={loading || quotaExceeded}
              >
                {loading ? t("scanPage.starting") : quotaExceeded ? t("scanPage.scanDisabledQuota") : t("scanPage.start")}
                {!loading && !quotaExceeded && <ArrowRight className="ml-2 h-4 w-4" />}
              </Button>
            </form>
          </CardContent>
        </Card>

        {recentScans.length > 0 && (
          <Card className="mt-6 border-border/60">
            <CardHeader>
              <CardTitle className="text-lg">{t("scanPage.recentScans")}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {recentScans.map((scan) => (
                  <li key={scan.id}>
                    <Link
                      href={`/dashboard/${scan.organization_id}/scans/${scan.id}`}
                      className="group flex items-center justify-between rounded-lg border border-border/60 px-4 py-3 transition-colors hover:border-primary/30 hover:bg-muted/20"
                    >
                      <div>
                        <div className="font-medium">{scan.target_url}</div>
                        <div className="text-xs text-muted-foreground">
                          {scanStatusLabel(scan.status)} · {scan.findings_count}{" "}
                          {t("common.findings")}
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
                    </Link>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </main>
    </>
  );
}

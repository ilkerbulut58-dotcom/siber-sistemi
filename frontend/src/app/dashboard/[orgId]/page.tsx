"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, Circle } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type OnboardingStatus,
  type Organization,
  type Project,
  type ScanJob,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

export default function OrgDashboardPage() {
  const params = useParams<{ orgId: string }>();
  const orgId = params.orgId;
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError, onboardingStepLabel } = useTranslation();
  const [org, setOrg] = useState<Organization | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [scans, setScans] = useState<ScanJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const token = getAccessToken();
      const [orgData, projectData, onboardingData, scanData] = await Promise.all([
        apiFetch<Organization>(`/api/v1/organizations/${orgId}`, { token }),
        apiFetch<Project[]>(`/api/v1/organizations/${orgId}/projects`, { token }),
        apiFetch<OnboardingStatus>(`/api/v1/organizations/${orgId}/onboarding-status`, {
          token,
        }).catch(() => null),
        apiFetch<ScanJob[]>(`/api/v1/organizations/${orgId}/scans`, { token }).catch(
          () => [] as ScanJob[]
        ),
      ]);
      setOrg(orgData);
      setProjects(projectData);
      setOnboarding(onboardingData);
      setScans(scanData);
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken, orgId]);

  useEffect(() => {
    load();
  }, [load]);

  const todayScanCount = useMemo(
    () => onboarding?.daily_scan_count ?? scans.filter((s) => isToday(s.created_at)).length,
    [onboarding?.daily_scan_count, scans]
  );

  const dailyQuota = onboarding?.daily_scan_quota;
  const quotaUnlimited = Boolean(user?.is_platform_admin);
  const effectiveQuota = quotaUnlimited ? null : (dailyQuota ?? 5);
  const quotaDisplay = quotaUnlimited ? t("org.quotaUnlimited") : String(effectiveQuota);
  const quotaExceeded =
    !quotaUnlimited && effectiveQuota !== null && todayScanCount >= effectiveQuota;

  async function createProject(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    setError(null);
    try {
      await apiFetch<Project>(`/api/v1/organizations/${orgId}/projects`, {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          name: form.get("name"),
          description: form.get("description") || null,
          environment: form.get("environment") || "production",
        }),
      });
      formEl.reset();
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  const stepHref = (stepId: string): string | null => {
    if (stepId === "email_verified") return "/dashboard/settings";
    if (stepId === "domain_added" && projects[0]) {
      return `/dashboard/${orgId}/projects/${projects[0].id}`;
    }
    if (stepId === "domain_verified" && projects[0]) {
      return `/dashboard/${orgId}/projects/${projects[0].id}`;
    }
    if (stepId === "authorization_accepted" && projects[0]) {
      return `/dashboard/${orgId}/projects/${projects[0].id}`;
    }
    return null;
  };

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
              ← {t("org.backToOrgs")}
            </Link>
            <h1 className="mt-2 text-3xl font-bold">{org?.name || t("org.projects")}</h1>
          </div>
          <Link
            href={`/dashboard/${orgId}/mobile`}
            className="rounded-md border border-indigo-500/40 bg-indigo-500/10 px-4 py-2 text-sm font-medium hover:bg-indigo-500/20"
          >
            {t("org.mobileSecurity")} →
          </Link>
        </div>
        {error && <p className="mb-4 text-destructive">{error}</p>}

        {user?.is_platform_admin && (
          <p className="mb-4 rounded-md border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
            {t("admin.modeHint")}
          </p>
        )}

        {onboarding?.is_pilot && onboarding.pilot_ends_at && (
          <p className="mb-4 rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
            {new Date(onboarding.pilot_ends_at) < new Date()
              ? t("org.pilotExpired")
              : t("org.pilotExpires", {
                  date: new Date(onboarding.pilot_ends_at).toLocaleDateString(),
                })}
          </p>
        )}

        <div className="mb-6 grid gap-4 md:grid-cols-2">
          {onboarding?.is_pilot && (
            <Card>
              <CardHeader>
                <CardTitle>{t("org.onboarding")}</CardTitle>
                <CardDescription>
                  {onboarding.ready_to_scan
                    ? t("org.onboardingReady")
                    : t("org.onboardingPending")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {onboarding.steps.map((step) => {
                    const href = !step.completed ? stepHref(step.step_id) : null;
                    return (
                    <li key={step.step_id} className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                      {step.completed ? (
                        <CheckCircle2 className="h-4 w-4 text-green-400" />
                      ) : (
                        <Circle className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className={step.completed ? "text-foreground" : "text-muted-foreground"}>
                        {onboardingStepLabel(step.step_id)}
                      </span>
                      </div>
                      {href && (
                        <Link href={href} className="text-xs text-indigo-300 hover:underline">
                          {t("org.completeStep")}
                        </Link>
                      )}
                    </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>{t("org.dailyQuota")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">
                {t("common.today")}: {todayScanCount} {t("common.of")} {quotaDisplay}{" "}
                {t("common.scans")}
              </p>
              {quotaExceeded && (
                <p className="mt-2 text-sm text-orange-400">{t("org.quotaExceeded")}</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("org.newProject")}</CardTitle>
              <CardDescription>{t("org.newProjectDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={createProject} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="name">{t("org.projectName")}</Label>
                  <Input id="name" name="name" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="environment">{t("org.environment")}</Label>
                  <select
                    id="environment"
                    name="environment"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    defaultValue="production"
                  >
                    <option value="production">{t("org.envProduction")}</option>
                    <option value="staging">{t("org.envStaging")}</option>
                    <option value="development">{t("org.envDevelopment")}</option>
                  </select>
                </div>
                <Button type="submit">{t("org.createProject")}</Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("org.projects")}</CardTitle>
            </CardHeader>
            <CardContent>
              {projects.length === 0 ? (
                <p className="text-muted-foreground">{t("org.noProjects")}</p>
              ) : (
                <ul className="space-y-2">
                  {projects.map((project) => (
                    <li key={project.id}>
                      <Link
                        href={`/dashboard/${orgId}/projects/${project.id}`}
                        className="block rounded-md border border-border px-4 py-3 hover:bg-muted/40"
                      >
                        <p className="font-medium">{project.name}</p>
                        <p className="text-xs text-muted-foreground">{project.environment}</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}

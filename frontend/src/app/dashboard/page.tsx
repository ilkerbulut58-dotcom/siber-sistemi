"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  ChevronRight,
  Globe,
  Radar,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { Navbar } from "@/components/navbar";
import { EmailVerificationBanner } from "@/components/email-verification-banner";
import { useAuth } from "@/components/auth-provider";
import { useTranslation, interpolate } from "@/components/locale-provider";
import {
  apiFetch,
  type Organization,
  type ScanJob,
  type SupportGrant,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function DashboardPage() {
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError, scanStatusLabel } = useTranslation();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [customerOrgs, setCustomerOrgs] = useState<Organization[]>([]);
  const [supportGrants, setSupportGrants] = useState<SupportGrant[]>([]);
  const [recentScans, setRecentScans] = useState<ScanJob[]>([]);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showWorkspaces, setShowWorkspaces] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const moreTools = [
    {
      href: "/dashboard/assessment",
      title: t("dashboard.quickFullAssessment"),
      description: t("dashboard.quickFullAssessmentDesc"),
      icon: ShieldCheck,
    },
    {
      href: "/dashboard/mobile",
      title: t("dashboard.quickMobile"),
      description: t("dashboard.quickMobileDesc"),
      icon: Smartphone,
    },
  ];

  const loadOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const data = await apiFetch<Organization[]>("/api/v1/organizations", { token });
      setOrgs(data);

      const scanLists = await Promise.all(
        data.slice(0, 3).map((org) =>
          apiFetch<ScanJob[]>(`/api/v1/organizations/${org.id}/scans`, { token }).catch(
            () => [] as ScanJob[]
          )
        )
      );
      setRecentScans(
        scanLists
          .flat()
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 6)
      );

      if (user?.is_platform_admin) {
        const [grants, customers] = await Promise.all([
          apiFetch<SupportGrant[]>("/api/v1/platform/support-grants", { token }),
          apiFetch<Organization[]>("/api/v1/platform/customer-organizations", { token }),
        ]);
        setSupportGrants(grants);
        setCustomerOrgs(customers);
      } else {
        setSupportGrants([]);
        setCustomerOrgs([]);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [formatApiError, getAccessToken, user?.is_platform_admin]);

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  async function createOrg(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const name = new FormData(formEl).get("name");
    setError(null);
    try {
      await apiFetch<Organization>("/api/v1/organizations", {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({ name }),
      });
      formEl.reset();
      await loadOrgs();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function createManagedWorkspace(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const name = new FormData(formEl).get("name");
    setError(null);
    try {
      await apiFetch<Organization>("/api/v1/platform/managed-workspaces", {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({ name }),
      });
      formEl.reset();
      await loadOrgs();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function createSupportGrant(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    setError(null);
    try {
      await apiFetch<SupportGrant>("/api/v1/platform/support-grants", {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          organization_id: form.get("organization_id"),
          granted_to_user_id: user?.id,
          reason: form.get("reason"),
          duration_hours: Number(form.get("duration_hours") || 24),
        }),
      });
      formEl.reset();
      await loadOrgs();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function revokeSupportGrant(grantId: string) {
    setError(null);
    try {
      await apiFetch<SupportGrant>(`/api/v1/platform/support-grants/${grantId}`, {
        method: "DELETE",
        token: getAccessToken(),
      });
      await loadOrgs();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  const welcomeText = user?.full_name
    ? interpolate(t("dashboard.welcomeName"), { name: user.full_name })
    : t("dashboard.welcome");

  return (
    <>
      <Navbar />
      <main className="container mx-auto space-y-8 px-4 py-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">{t("dashboard.title")}</h1>
          <p className="mt-1 text-muted-foreground">{welcomeText}</p>
        </div>

        {error && <p className="text-destructive">{error}</p>}

        <EmailVerificationBanner />

        <Card className="glass-card overflow-hidden border-primary/25 glow-primary">
          <CardContent className="flex flex-col gap-6 p-6 md:flex-row md:items-center md:justify-between md:p-8">
            <div className="max-w-xl">
              <h2 className="text-xl font-semibold md:text-2xl">{t("dashboard.heroTitle")}</h2>
              <p className="mt-2 text-muted-foreground">{t("dashboard.heroSubtitle")}</p>
            </div>
            <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
              <Link href="/dashboard/scan">
                <Button size="lg" className="w-full sm:w-auto">
                  <Globe className="mr-2 h-4 w-4" />
                  {t("dashboard.heroCta")}
                </Button>
              </Link>
              {recentScans.length > 0 && (
                <Link href="/dashboard/scan">
                  <Button size="lg" variant="outline" className="w-full border-white/15 sm:w-auto">
                    {t("dashboard.heroSecondary")}
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card className="border-border/60">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">{t("dashboard.recentScans")}</CardTitle>
              {recentScans.length > 0 && (
                <Link
                  href="/dashboard/scan"
                  className="flex items-center text-sm text-primary hover:underline"
                >
                  {t("dashboard.viewAllScans")}
                  <ChevronRight className="h-4 w-4" />
                </Link>
              )}
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-muted-foreground">{t("common.loading")}</p>
              ) : recentScans.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/80 py-12 text-center">
                  <Globe className="mx-auto mb-3 h-10 w-10 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">{t("dashboard.noScans")}</p>
                  <Link href="/dashboard/scan" className="mt-4 inline-block">
                    <Button size="sm">{t("dashboard.startFirstScan")}</Button>
                  </Link>
                </div>
              ) : (
                <ul className="space-y-2">
                  {recentScans.map((scan) => (
                    <li key={scan.id}>
                      <Link
                        href={`/dashboard/${scan.organization_id}/scans/${scan.id}`}
                        className="group flex items-center justify-between rounded-lg border border-border/60 px-4 py-3 transition-colors hover:border-primary/30 hover:bg-muted/20"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">{scan.target_url}</p>
                          <p className="text-xs text-muted-foreground">
                            {scanStatusLabel(scan.status)} · {scan.findings_count}{" "}
                            {t("common.findings")}
                          </p>
                        </div>
                        <ArrowRight className="ml-3 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            {orgs[0] && (
              <Card className="border-border/60">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Radar className="h-5 w-5 text-primary" />
                    {t("dashboard.attackSurface")}
                  </CardTitle>
                  <CardDescription>{t("dashboard.attackSurfaceDesc")}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href={`/dashboard/${orgs[0].id}`}>
                    <Button variant="outline" className="w-full">
                      {t("common.projects")} <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}

            <Card className="border-border/60">
              <CardHeader>
                <CardTitle className="text-lg">{t("dashboard.moreTools")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {moreTools.map(({ href, title, description, icon: Icon }) => (
                  <Link key={href} href={href}>
                    <div className="flex items-start gap-3 rounded-lg border border-border/60 p-3 transition-colors hover:border-primary/30 hover:bg-muted/20">
                      <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                      <div>
                        <p className="text-sm font-medium">{title}</p>
                        <p className="text-xs text-muted-foreground">{description}</p>
                      </div>
                    </div>
                  </Link>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>

        <Card className="border-border/60">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">{t("dashboard.organizations")}</CardTitle>
              <CardDescription className="sr-only">{t("dashboard.organizations")}</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setShowWorkspaces((v) => !v)}>
              {showWorkspaces ? t("common.hide") : t("common.show")}
            </Button>
          </CardHeader>
          {showWorkspaces && (
            <CardContent>
              <form onSubmit={createOrg} className="mb-4 flex gap-2">
                <Input
                  name="name"
                  required
                  placeholder={t("dashboard.newOrgPlaceholder")}
                  className="max-w-xs"
                />
                <Button type="submit" size="sm">
                  {t("common.add")}
                </Button>
              </form>
              {loading ? (
                <p className="text-muted-foreground">{t("common.loading")}</p>
              ) : orgs.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("dashboard.noOrgs")}</p>
              ) : (
                <ul className="space-y-2">
                  {orgs.map((org) => (
                    <li
                      key={org.id}
                      className="flex items-center justify-between rounded-lg border border-border/60 px-4 py-3"
                    >
                      <div>
                        <p className="font-medium">{org.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {org.is_managed_workspace ? t("dashboard.managedWorkspace") : org.slug}
                        </p>
                      </div>
                      <Link href={`/dashboard/${org.id}`}>
                        <Button variant="outline" size="sm">
                          {t("common.open")}
                        </Button>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          )}
        </Card>

        {user?.is_platform_admin && (
          <Card className="border-amber-500/20 bg-amber-500/5">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>{t("dashboard.platformAdmin")}</CardTitle>
                <CardDescription>{t("dashboard.platformAdminDesc")}</CardDescription>
              </div>
              <div className="flex gap-2">
                <Link href="/dashboard/platform/quality">
                  <Button variant="outline" size="sm">
                    {t("dashboard.qualityLab")}
                  </Button>
                </Link>
                <Link href="/dashboard/platform/pilot">
                  <Button variant="outline" size="sm">
                    {t("dashboard.pilotTenants")}
                  </Button>
                </Link>
                <Button variant="outline" size="sm" onClick={() => setShowAdmin((v) => !v)}>
                  {showAdmin ? t("common.hide") : t("common.show")}
                </Button>
              </div>
            </CardHeader>
            {showAdmin && (
              <CardContent className="grid gap-6 lg:grid-cols-2">
                <form
                  onSubmit={createManagedWorkspace}
                  className="space-y-3 rounded-md border border-border p-4"
                >
                  <p className="text-sm font-medium">{t("dashboard.managedWorkspaceForm")}</p>
                  <Input name="name" required placeholder={t("dashboard.managedWorkspacePlaceholder")} />
                  <Button type="submit" size="sm">
                    {t("common.create")}
                  </Button>
                </form>

                <form
                  onSubmit={createSupportGrant}
                  className="space-y-3 rounded-md border border-border p-4"
                >
                  <p className="text-sm font-medium">{t("dashboard.supportGrant")}</p>
                  <select
                    name="organization_id"
                    required
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">{t("dashboard.supportOrgPlaceholder")}</option>
                    {customerOrgs.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                  <Input name="reason" required minLength={10} placeholder={t("dashboard.supportReason")} />
                  <Input name="duration_hours" type="number" min={1} max={168} defaultValue={24} />
                  <Button type="submit" size="sm">
                    {t("dashboard.grantAccess")}
                  </Button>
                  {supportGrants.length > 0 && (
                    <ul className="space-y-1 pt-2 text-xs">
                      {supportGrants.map((grant) => (
                        <li key={grant.id} className="flex justify-between gap-2">
                          <span>{grant.organization_name}</span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => revokeSupportGrant(grant.id)}
                          >
                            {t("common.revoke")}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </form>
              </CardContent>
            )}
          </Card>
        )}
      </main>
    </>
  );
}

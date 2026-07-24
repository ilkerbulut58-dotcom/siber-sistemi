"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Globe, Radar, ShieldCheck, Smartphone } from "lucide-react";
import { Navbar } from "@/components/navbar";
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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const quickActions = [
    {
      href: "/dashboard/assessment",
      title: t("dashboard.quickFullAssessment"),
      description: t("dashboard.quickFullAssessmentDesc"),
      icon: ShieldCheck,
      primary: true,
    },
    {
      href: "/dashboard/scan",
      title: t("dashboard.quickWebScan"),
      description: t("dashboard.quickWebScanDesc"),
      icon: Globe,
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
          <h1 className="text-3xl font-bold">{t("dashboard.title")}</h1>
          <p className="mt-2 text-muted-foreground">{welcomeText}</p>
        </div>

        {error && <p className="text-destructive">{error}</p>}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {quickActions.map(({ href, title, description, icon: Icon, ...rest }) => (
            <Link key={href} href={href}>
              <Card
                className={`h-full transition-colors hover:border-primary/40 hover:bg-muted/20 ${
                  "primary" in rest && rest.primary
                    ? "border-primary/30 bg-primary/5"
                    : "border-border/60 bg-card/80"
                }`}
              >
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Icon className="h-5 w-5 text-primary" />
                    {title}
                  </CardTitle>
                  <CardDescription>{description}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </section>

        {orgs[0] && (
          <Card className="border-border/60 bg-card/80">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Radar className="h-5 w-5 text-primary" />
                  {t("dashboard.attackSurface")}
                </CardTitle>
                <CardDescription>{t("dashboard.attackSurfaceDesc")}</CardDescription>
              </div>
              <Link href={`/dashboard/${orgs[0].id}`}>
                <Button variant="outline" size="sm">
                  {t("common.projects")} →
                </Button>
              </Link>
            </CardHeader>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("dashboard.recentScans")}</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-muted-foreground">{t("common.loading")}</p>
              ) : recentScans.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {t("dashboard.noScans")}{" "}
                  <Link href="/dashboard/scan" className="underline">
                    {t("dashboard.startFirstScan")}
                  </Link>
                </p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {recentScans.map((scan) => (
                    <li key={scan.id}>
                      <Link
                        href={`/dashboard/${scan.organization_id}/scans/${scan.id}`}
                        className="block rounded-md border border-border px-3 py-2 hover:bg-muted/40"
                      >
                        <p className="truncate font-medium">{scan.target_url}</p>
                        <p className="text-xs text-muted-foreground">
                          {scanStatusLabel(scan.status)} · {scan.findings_count}{" "}
                          {t("common.findings")}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{t("dashboard.organizations")}</CardTitle>
              <form onSubmit={createOrg} className="flex gap-2">
                <Input
                  name="name"
                  required
                  placeholder={t("dashboard.newOrgPlaceholder")}
                  className="h-9 w-40"
                />
                <Button type="submit" size="sm">
                  {t("common.add")}
                </Button>
              </form>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-muted-foreground">{t("common.loading")}</p>
              ) : orgs.length === 0 ? (
                <p className="text-muted-foreground">{t("dashboard.noOrgs")}</p>
              ) : (
                <ul className="space-y-2">
                  {orgs.map((org) => (
                    <li
                      key={org.id}
                      className="flex items-center justify-between rounded-md border border-border px-3 py-2"
                    >
                      <div>
                        <p className="font-medium">{org.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {org.is_managed_workspace ? t("dashboard.managedWorkspace") : org.slug}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Link href={`/dashboard/${org.id}/mobile`}>
                          <Button variant="outline" size="sm">
                            {t("common.mobile")}
                          </Button>
                        </Link>
                        <Link href={`/dashboard/${org.id}`}>
                          <Button variant="outline" size="sm">
                            {t("common.open")}
                          </Button>
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

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

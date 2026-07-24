"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Smartphone } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type MobileApplication,
  type Organization,
  type Project,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";

export default function MobileHubPage() {
  const { getAccessToken } = useAuth();
  const { t, formatApiError } = useTranslation();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [apps, setApps] = useState<MobileApplication[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadOrgs = useCallback(async () => {
    try {
      const data = await apiFetch<Organization[]>("/api/v1/organizations", {
        token: getAccessToken(),
      });
      setOrgs(data);
      if (data[0] && !selectedOrgId) setSelectedOrgId(data[0].id);
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken, selectedOrgId]);

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) return;
    void Promise.all([
      apiFetch<Project[]>(`/api/v1/organizations/${selectedOrgId}/projects`, {
        token: getAccessToken(),
      }),
      apiFetch<MobileApplication[]>(`/api/v1/organizations/${selectedOrgId}/mobile/applications`, {
        token: getAccessToken(),
      }),
    ])
      .then(([projectData, appData]) => {
        setProjects(projectData);
        setApps(appData);
      })
      .catch(() => {
        setProjects([]);
        setApps([]);
      });
  }, [selectedOrgId, getAccessToken]);

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold">
            <Smartphone className="h-8 w-8 text-primary" />
            {t("mobile.title")}
          </h1>
          <p className="mt-2 text-muted-foreground">{t("mobile.subtitle")}</p>
        </div>

        {error && <p className="text-destructive">{error}</p>}

        <Card>
          <CardHeader>
            <CardTitle>{t("mobile.selectOrg")}</CardTitle>
            <CardDescription>{t("org.newProjectDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="mobile-org">{t("dashboard.organizations")}</Label>
              <select
                id="mobile-org"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={selectedOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value)}
              >
                {orgs.length === 0 && <option value="">{t("dashboard.noOrgs")}</option>}
                {orgs.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>

            {selectedOrgId && (
              <Link href={`/dashboard/${selectedOrgId}/mobile`}>
                <Button className="w-full sm:w-auto">{t("mobile.uploadApk")} →</Button>
              </Link>
            )}
          </CardContent>
        </Card>

        {selectedOrgId && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{t("org.projects")}</CardTitle>
              </CardHeader>
              <CardContent>
                {projects.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("org.noProjects")}</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {projects.map((p) => (
                      <li key={p.id} className="rounded-md border border-border px-3 py-2">
                        {p.name} · {p.environment}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>{t("dashboard.recentScans")}</CardTitle>
              </CardHeader>
              <CardContent>
                {apps.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("mobile.noApps")}</p>
                ) : (
                  <ul className="space-y-2">
                    {apps.slice(0, 6).map((app) => (
                      <li key={app.id}>
                        <Link
                          href={`/dashboard/${selectedOrgId}/mobile`}
                          className="block rounded-md border border-border px-3 py-2 text-sm hover:bg-muted/40"
                        >
                          <p className="font-medium">{app.application_name ?? app.original_filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {app.package_name ?? "—"} · {app.analysis_status} · {app.findings_count}{" "}
                            {t("common.findings")}
                          </p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        <p className="text-center text-sm text-muted-foreground">
          <Link href="/dashboard/assessment" className="underline">
            {t("assessment.title")}
          </Link>
        </p>
      </main>
    </>
  );
}

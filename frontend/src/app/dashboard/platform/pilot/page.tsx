"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type Domain, type PilotTenant } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type TenantDraft = {
  pilot_scan_quota: string;
  pilot_starts_at: string;
  pilot_ends_at: string;
  pilot_notes: string;
  pilot_active_scan_allowed: boolean;
  scans_disabled: boolean;
};

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function draftFromTenant(tenant: PilotTenant): TenantDraft {
  return {
    pilot_scan_quota: tenant.pilot_scan_quota != null ? String(tenant.pilot_scan_quota) : "",
    pilot_starts_at: toLocalInput(tenant.pilot_starts_at),
    pilot_ends_at: toLocalInput(tenant.pilot_ends_at),
    pilot_notes: tenant.pilot_notes ?? "",
    pilot_active_scan_allowed: tenant.pilot_active_scan_allowed,
    scans_disabled: tenant.scans_disabled,
  };
}

export default function PilotTenantsPage() {
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError } = useTranslation();
  const [tenants, setTenants] = useState<PilotTenant[]>([]);
  const [drafts, setDrafts] = useState<Record<string, TenantDraft>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [verifyOrgId, setVerifyOrgId] = useState("");
  const [verifyProjectId, setVerifyProjectId] = useState("");
  const [verifyDomainId, setVerifyDomainId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<PilotTenant[]>("/api/v1/platform/pilot-tenants", {
        token: getAccessToken(),
      });
      setTenants(data);
      setDrafts(Object.fromEntries(data.map((tenant) => [tenant.id, draftFromTenant(tenant)])));
      setError(null);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [formatApiError, getAccessToken]);

  useEffect(() => {
    void load();
  }, [load]);

  function updateDraft(tenantId: string, patch: Partial<TenantDraft>) {
    setDrafts((prev) => ({
      ...prev,
      [tenantId]: { ...prev[tenantId], ...patch },
    }));
  }

  async function saveTenant(tenant: PilotTenant) {
    const draft = drafts[tenant.id] ?? draftFromTenant(tenant);
    setSavingId(tenant.id);
    setError(null);
    setMessage(null);
    try {
      const body: Record<string, unknown> = {
        pilot_notes: draft.pilot_notes || null,
        scans_disabled: draft.scans_disabled,
        pilot_active_scan_allowed: draft.pilot_active_scan_allowed,
      };
      if (draft.pilot_scan_quota.trim()) {
        body.pilot_scan_quota = Number(draft.pilot_scan_quota);
      }
      if (draft.pilot_starts_at) {
        body.pilot_starts_at = new Date(draft.pilot_starts_at).toISOString();
      }
      if (draft.pilot_ends_at) {
        body.pilot_ends_at = new Date(draft.pilot_ends_at).toISOString();
      }
      await apiFetch<PilotTenant>(`/api/v1/platform/pilot-tenants/${tenant.id}`, {
        method: "PATCH",
        token: getAccessToken(),
        body: JSON.stringify(body),
      });
      setMessage(t("pilot.saved"));
      await load();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSavingId(null);
    }
  }

  async function verifyDomain(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const domain = await apiFetch<Domain>(
        `/api/v1/platform/pilot-tenants/${verifyOrgId}/projects/${verifyProjectId}/domains/${verifyDomainId}/verify`,
        { method: "POST", token: getAccessToken() }
      );
      setMessage(
        domain.is_verified ? t("pilot.verifyDomainSuccess") : t("project.verifySuccess")
      );
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  if (!user?.is_platform_admin) {
    return (
      <>
        <Navbar />
        <main className="container mx-auto px-4 py-12 text-muted-foreground">
          {t("platform.qualityOnlyAdmin")}
        </main>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto space-y-6 px-4 py-8">
        <div>
          <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
            ← {t("common.back")}
          </Link>
          <h1 className="mt-2 text-3xl font-bold">{t("pilot.title")}</h1>
          <p className="text-muted-foreground">{t("pilot.desc")}</p>
        </div>

        {error && <p className="text-destructive">{error}</p>}
        {message && <p className="text-green-400">{message}</p>}

        <Card>
          <CardHeader>
            <CardTitle>{t("pilot.title")}</CardTitle>
            <CardDescription>{t("pilot.desc")}</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-muted-foreground">{t("common.loading")}</p>
            ) : tenants.length === 0 ? (
              <p className="text-muted-foreground">{t("pilot.noTenants")}</p>
            ) : (
              <div className="space-y-6">
                {tenants.map((tenant) => {
                  const draft = drafts[tenant.id] ?? draftFromTenant(tenant);
                  return (
                    <div key={tenant.id} className="rounded-lg border border-border p-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-semibold">{tenant.name}</p>
                          <p className="text-xs text-muted-foreground">{tenant.slug}</p>
                        </div>
                        <span className="text-xs text-muted-foreground">{tenant.id}</span>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        <div className="space-y-1">
                          <Label>{t("pilot.quota")}</Label>
                          <Input
                            type="number"
                            min={1}
                            max={1000}
                            value={draft.pilot_scan_quota}
                            onChange={(e) =>
                              updateDraft(tenant.id, { pilot_scan_quota: e.target.value })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label>{t("pilot.startsAt")}</Label>
                          <Input
                            type="datetime-local"
                            value={draft.pilot_starts_at}
                            onChange={(e) =>
                              updateDraft(tenant.id, { pilot_starts_at: e.target.value })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label>{t("pilot.endsAt")}</Label>
                          <Input
                            type="datetime-local"
                            value={draft.pilot_ends_at}
                            onChange={(e) =>
                              updateDraft(tenant.id, { pilot_ends_at: e.target.value })
                            }
                          />
                        </div>
                        <div className="space-y-1 sm:col-span-2 lg:col-span-3">
                          <Label>{t("pilot.notes")}</Label>
                          <Input
                            value={draft.pilot_notes}
                            onChange={(e) =>
                              updateDraft(tenant.id, { pilot_notes: e.target.value })
                            }
                          />
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-4 text-sm">
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={draft.pilot_active_scan_allowed}
                            onChange={(e) =>
                              updateDraft(tenant.id, {
                                pilot_active_scan_allowed: e.target.checked,
                              })
                            }
                          />
                          {t("pilot.activeScan")}
                        </label>
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={draft.scans_disabled}
                            onChange={(e) =>
                              updateDraft(tenant.id, { scans_disabled: e.target.checked })
                            }
                          />
                          {t("pilot.scansDisabled")}
                        </label>
                      </div>
                      <div className="mt-3">
                        <Button
                          type="button"
                          size="sm"
                          disabled={savingId === tenant.id}
                          onClick={() => saveTenant(tenant)}
                        >
                          {savingId === tenant.id ? t("common.loading") : t("pilot.save")}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("pilot.verifyDomain")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={verifyDomain} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1">
                <Label htmlFor="verify-org">{t("pilot.orgId")}</Label>
                <Input
                  id="verify-org"
                  value={verifyOrgId}
                  onChange={(e) => setVerifyOrgId(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="verify-project">{t("pilot.projectId")}</Label>
                <Input
                  id="verify-project"
                  value={verifyProjectId}
                  onChange={(e) => setVerifyProjectId(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="verify-domain">{t("pilot.domainId")}</Label>
                <Input
                  id="verify-domain"
                  value={verifyDomainId}
                  onChange={(e) => setVerifyDomainId(e.target.value)}
                  required
                />
              </div>
              <div className="flex items-end">
                <Button type="submit" className="w-full sm:w-auto">
                  {t("pilot.verifyDomainBtn")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </>
  );
}

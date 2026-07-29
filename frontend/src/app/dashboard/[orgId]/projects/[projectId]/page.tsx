"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type Domain,
  type OnboardingStatus,
  type Project,
  type ScanJob,
  type ScanProfile,
  type VerificationInstructions,
} from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DomainVerificationPanel } from "@/components/domains/domain-verification-panel";
import type { DomainVerifyResult } from "@/lib/api-types";
import { verificationFailureLabel } from "@/lib/i18n";

export default function ProjectPage() {
  const params = useParams<{ orgId: string; projectId: string }>();
  const { orgId, projectId } = params;
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError, scanProfileLabel, scanProfileDescription, scanStatusLabel, locale } =
    useTranslation();

  const [project, setProject] = useState<Project | null>(null);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [scans, setScans] = useState<ScanJob[]>([]);
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [instructions, setInstructions] = useState<VerificationInstructions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testMode, setTestMode] = useState(false);
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [memberRole, setMemberRole] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const healthRes = await fetch(`${getApiBase()}/api/v1/health`);
      const healthBody = await healthRes.json();
      setTestMode(Boolean(healthBody?.data?.skip_domain_verification));

      const [projectData, domainData, scanData, profileData, onboardingData, members] =
        await Promise.all([
        apiFetch<Project>(`/api/v1/organizations/${orgId}/projects/${projectId}`, {
          token: getAccessToken(),
        }),
        apiFetch<Domain[]>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/domains`,
          { token: getAccessToken() }
        ),
        apiFetch<ScanJob[]>(`/api/v1/organizations/${orgId}/scans`, {
          token: getAccessToken(),
        }),
        apiFetch<ScanProfile[]>("/api/v1/scan-profiles", { token: getAccessToken() }),
        apiFetch<OnboardingStatus>(`/api/v1/organizations/${orgId}/onboarding-status`, {
          token: getAccessToken(),
        }).catch(() => null),
        apiFetch<{ user_id: string; role: string }[]>(
          `/api/v1/organizations/${orgId}/members`,
          { token: getAccessToken() }
        ).catch(() => []),
      ]);
      setProject(projectData);
      setDomains(domainData);
      setScans(scanData.filter((s) => s.project_id === projectId));
      setProfiles(profileData);
      setOnboarding(onboardingData ?? null);
      const own = members.find((m) => m.user_id === user?.id);
      setMemberRole(own?.role ?? null);
      setError(null);
    } catch (err) {
      const msg = formatApiError(err);
      if (!/token|INVALID_TOKEN/i.test(msg)) setError(msg);
    }
  }, [formatApiError, getAccessToken, orgId, projectId, user?.id]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [load]);

  async function addDomain(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage(null);
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    try {
      await apiFetch<Domain>(
        `/api/v1/organizations/${orgId}/projects/${projectId}/domains`,
        {
          method: "POST",
          token: getAccessToken(),
          body: JSON.stringify({
            hostname: form.get("hostname"),
            method: form.get("method") || "dns_txt",
          }),
        }
      );
      formEl.reset();
      setMessage(testMode ? t("project.domainAddedTest") : t("project.domainAdded"));
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function showInstructions(domainId: string) {
    try {
      const data = await apiFetch<VerificationInstructions>(
        `/api/v1/organizations/${orgId}/projects/${projectId}/domains/${domainId}/verification-instructions`,
        { token: getAccessToken() }
      );
      setInstructions(data);
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function verifyDomain(domainId: string) {
    try {
      const data = await apiFetch<DomainVerifyResult>(
        `/api/v1/organizations/${orgId}/projects/${projectId}/domains/${domainId}/verify`,
        { method: "POST", token: getAccessToken() }
      );
      if (data.verified) {
        setMessage(t("project.verifySuccess"));
      } else {
        const failureMsg = data.failure_code
          ? verificationFailureLabel(locale, data.failure_code)
          : t("project.verifyFailed");
        setError(failureMsg);
      }
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function startScan(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage(null);
    const form = new FormData(e.currentTarget);
    try {
      await apiFetch<ScanJob>(`/api/v1/organizations/${orgId}/scans`, {
        method: "POST",
        token: getAccessToken(),
        body: JSON.stringify({
          project_id: projectId,
          domain_id: form.get("domain_id"),
          scan_profile: form.get("scan_profile") || "safe",
          target_url: form.get("target_url"),
          authorization_accepted: form.get("authorization") === "on",
        }),
      });
      setMessage(t("project.scanQueued"));
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function toggleActiveScan(domainId: string, allow: boolean) {
    try {
      const path = allow ? "approve-active-scan" : "revoke-active-scan";
      await apiFetch(
        `/api/v1/organizations/${orgId}/projects/${projectId}/domains/${domainId}/${path}`,
        { method: "POST", token: getAccessToken() }
      );
      await load();
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  const isOrgAdmin = memberRole === "admin" || memberRole === "owner";
  const activeScanAllowed = onboarding?.pilot_active_scan_allowed !== false;
  const verifiedDomains = testMode ? domains : domains.filter((d) => d.is_verified);
  const isRestrictedProfile = (name: string) =>
    !activeScanAllowed && (name === "deep" || name === "code");

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Link href={`/dashboard/${orgId}`} className="text-sm text-muted-foreground hover:underline">
          ← {project?.name || t("common.back")}
        </Link>
        <h1 className="mt-2 mb-4 text-3xl font-bold">{project?.name}</h1>
        <div className="mb-6">
          <Link href={`/dashboard/${orgId}/projects/${projectId}/attack-surface`}>
            <Button type="button" variant="outline" size="sm">
              {t("project.attackSurface")}
            </Button>
          </Link>
        </div>

        {error && <p className="mb-4 text-destructive">{error}</p>}
        {message && <p className="mb-4 text-green-400">{message}</p>}
        {testMode && (
          <p className="mb-4 rounded-md border border-yellow-500/40 bg-yellow-500/10 px-4 py-2 text-sm text-yellow-200">
            {t("project.testModeBanner")}
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("project.addDomain")}</CardTitle>
              <CardDescription>
                {testMode ? t("project.addDomainDescTest") : t("project.addDomainDesc")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={addDomain} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="hostname">{t("project.hostname")}</Label>
                  <Input
                    id="hostname"
                    name="hostname"
                    placeholder={t("project.hostnamePlaceholder")}
                    required
                  />
                </div>
                {!testMode && (
                  <div className="space-y-2">
                    <Label htmlFor="method">{t("project.verificationMethod")}</Label>
                    <select
                      id="method"
                      name="method"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                      defaultValue="dns_txt"
                    >
                      <option value="dns_txt">{t("project.methodDns")}</option>
                      <option value="meta_tag">{t("project.methodMeta")}</option>
                      <option value="well_known_file">{t("project.methodFile")}</option>
                    </select>
                  </div>
                )}
                <Button type="submit">{t("project.addDomainBtn")}</Button>
              </form>

              <ul className="mt-6 space-y-3">
                {domains.map((domain) => (
                  <li key={domain.id} className="rounded-md border border-border p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">{domain.hostname}</span>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className={domain.is_verified ? "text-green-400" : "text-yellow-400"}>
                          {domain.is_verified ? t("project.verified") : t("project.pending")}
                        </span>
                        {domain.is_verified && (
                          <span
                            className={
                              domain.active_scan_allowed ? "text-green-400" : "text-orange-400"
                            }
                          >
                            {domain.active_scan_allowed
                              ? t("project.activeScanOn")
                              : t("project.activeScanOff")}
                          </span>
                        )}
                        {domain.is_verified && domain.admin_approved_at && (
                          <span className="text-muted-foreground">
                            {t("project.adminApprovedAt")}:{" "}
                            {new Date(domain.admin_approved_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    {!testMode && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => showInstructions(domain.id)}
                        >
                          {t("project.instructions")}
                        </Button>
                        <Button type="button" size="sm" onClick={() => verifyDomain(domain.id)}>
                          {t("project.verify")}
                        </Button>
                        {domain.is_verified && isOrgAdmin && (
                          <>
                            {!domain.active_scan_allowed ? (
                              <Button
                                type="button"
                                size="sm"
                                variant="secondary"
                                onClick={() => toggleActiveScan(domain.id, true)}
                              >
                                {t("project.approveActiveScan")}
                              </Button>
                            ) : (
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => toggleActiveScan(domain.id, false)}
                              >
                                {t("project.revokeActiveScan")}
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>

              {!testMode && instructions && <DomainVerificationPanel instructions={instructions} />}
              {!testMode && !isOrgAdmin && (
                <p className="mt-3 text-xs text-muted-foreground">{t("project.adminOnlyApproval")}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("project.startScan")}</CardTitle>
              <CardDescription>
                {testMode ? t("project.startScanDescTest") : t("project.startScanDesc")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={startScan} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="domain_id">{t("project.domain")}</Label>
                  <select
                    id="domain_id"
                    name="domain_id"
                    required
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    defaultValue={verifiedDomains[0]?.id || ""}
                  >
                    <option value="" disabled>
                      {verifiedDomains.length ? t("project.selectDomain") : t("project.addDomainFirst")}
                    </option>
                    {verifiedDomains.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.hostname}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="target_url">{t("project.targetUrl")}</Label>
                  <Input
                    id="target_url"
                    name="target_url"
                    type="url"
                    placeholder={t("project.targetUrlPlaceholder")}
                    required
                  />
                </div>
                {!activeScanAllowed && (
                  <p className="text-xs text-orange-400">{t("project.profileDisabled")}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="scan_profile">{t("project.scanProfile")}</Label>
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
                        {isRestrictedProfile(p.name) ? ` (${t("project.profileDisabled")})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" name="authorization" className="mt-1" required />
                  <span>{t("project.authorization")}</span>
                </label>
                <Button type="submit" disabled={verifiedDomains.length === 0}>
                  {t("project.startScanBtn")}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>{t("project.scans")}</CardTitle>
          </CardHeader>
          <CardContent>
            {scans.length === 0 ? (
              <p className="text-muted-foreground">{t("project.noScans")}</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {scans.map((scan) => (
                  <li key={scan.id}>
                    <Link
                      href={`/dashboard/${orgId}/scans/${scan.id}`}
                      className="block rounded-md border border-border px-4 py-3 hover:bg-muted/40"
                    >
                      <div className="font-medium">{scan.target_url}</div>
                      <div className="text-muted-foreground">
                        {scanProfileLabel(scan.scan_profile)} · {scanStatusLabel(scan.status)} ·{" "}
                        {scan.findings_count} {t("common.findings")}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}

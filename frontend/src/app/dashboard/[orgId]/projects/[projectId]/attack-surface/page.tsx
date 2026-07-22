"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import {
  apiFetch,
  type Asset,
  type AttackSurfaceSummary,
  type AsmDiscoveryJob,
  type Domain,
  type Project,
} from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";

const TYPE_LABELS: Record<string, string> = {
  domain: "Domain",
  subdomain: "Alt domain",
  ip: "IP",
  url: "URL",
  api: "API",
  mobile: "Mobil",
  service: "Servis",
  certificate: "Sertifika",
};

const STATUS_COLORS: Record<string, string> = {
  active: "text-green-400",
  inactive: "text-muted-foreground",
  unknown: "text-yellow-400",
};

function riskColor(score: number | null | undefined): string {
  if (score == null) return "text-muted-foreground";
  if (score >= 70) return "text-red-400";
  if (score >= 45) return "text-orange-400";
  if (score >= 25) return "text-yellow-400";
  return "text-green-400";
}

export default function AttackSurfacePage() {
  const params = useParams<{ orgId: string; projectId: string }>();
  const { orgId, projectId } = params;
  const { getAccessToken } = useAuth();

  const [project, setProject] = useState<Project | null>(null);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [summary, setSummary] = useState<AttackSurfaceSummary | null>(null);
  const [jobs, setJobs] = useState<AsmDiscoveryJob[]>([]);
  const [discoveryDomainId, setDiscoveryDomainId] = useState<string>("");
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testMode, setTestMode] = useState(false);

  const latestJob = jobs[0] ?? null;
  const activeJobForSelection = useMemo(() => {
    if (!discoveryDomainId) return null;
    return (
      jobs.find(
        (job) =>
          job.domain_id === discoveryDomainId &&
          (job.status === "running" || job.status === "queued")
      ) ?? null
    );
  }, [jobs, discoveryDomainId]);
  const isRunning = activeJobForSelection != null;

  const verifiedDomains = useMemo(
    () => (testMode ? domains : domains.filter((d) => d.is_verified)),
    [domains, testMode]
  );

  const load = useCallback(async () => {
    try {
      const healthRes = await fetch(`${getApiBase()}/api/v1/health`);
      const healthBody = await healthRes.json();
      setTestMode(Boolean(healthBody?.data?.skip_domain_verification));

      const [projectData, domainData, assetData, summaryData, jobData] = await Promise.all([
        apiFetch<Project>(`/api/v1/organizations/${orgId}/projects/${projectId}`, {
          token: getAccessToken(),
        }),
        apiFetch<Domain[]>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/domains`,
          { token: getAccessToken() }
        ),
        apiFetch<Asset[]>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/asm/assets${
            selectedDomain ? `?domain_id=${selectedDomain}` : ""
          }`,
          { token: getAccessToken() }
        ),
        apiFetch<AttackSurfaceSummary>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/asm/surface${
            selectedDomain ? `?domain_id=${selectedDomain}` : ""
          }`,
          { token: getAccessToken() }
        ),
        apiFetch<AsmDiscoveryJob[]>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/asm/jobs`,
          { token: getAccessToken() }
        ),
      ]);
      setProject(projectData);
      setDomains(domainData);
      setAssets(assetData);
      setSummary(summaryData);
      setJobs(jobData);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Veri yüklenemedi";
      if (!/token/i.test(msg)) {
        setError(msg);
      }
    }
  }, [getAccessToken, orgId, projectId, selectedDomain]);

  useEffect(() => {
    load();
    const timer = setInterval(load, isRunning ? 4000 : 15000);
    return () => clearInterval(timer);
  }, [load, isRunning]);

  async function startDiscovery(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    const form = new FormData(e.currentTarget);
    const domainId = String(form.get("domain_id") || "");
    const domain = domains.find((d) => d.id === domainId);
    if (!domain) return;

    try {
      await apiFetch<AsmDiscoveryJob>(
        `/api/v1/organizations/${orgId}/projects/${projectId}/asm/discover`,
        {
          method: "POST",
          token: getAccessToken(),
          body: JSON.stringify({
            domain_id: domainId,
            target_url: `https://${domain.hostname}`,
            authorization_accepted: true,
          }),
        }
      );
      setMessage("Saldırı yüzeyi analizi başlatıldı — pasif keşif çalışıyor.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analiz başlatılamadı");
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Link
          href={`/dashboard/${orgId}/projects/${projectId}`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Proje
        </Link>
        <h1 className="mt-2 mb-2 text-3xl font-bold">Saldırı Yüzeyi (ASM)</h1>
        {project && (
          <p className="mb-6 text-muted-foreground">
            {project.name} · Pasif varlık keşfi ve envanter
          </p>
        )}

        {error && <p className="mb-4 text-destructive">{error}</p>}
        {message && <p className="mb-4 text-green-400">{message}</p>}

        <div className="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Toplam varlık</CardDescription>
              <CardTitle className="text-3xl">{summary?.total_assets ?? 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Alt domain</CardDescription>
              <CardTitle className="text-3xl">{summary?.subdomains ?? 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Ortalama risk</CardDescription>
              <CardTitle className={`text-3xl ${riskColor(summary?.avg_risk_score)}`}>
                {summary?.avg_risk_score ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Max risk</CardDescription>
              <CardTitle className={`text-3xl ${riskColor(summary?.max_risk_score)}`}>
                {summary?.max_risk_score ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Yeni keşif başlat</CardTitle>
              <CardDescription>
                Yalnızca doğrulanmış domainlerde pasif analiz — brute-force veya saldırı yok.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={startDiscovery} className="space-y-4">
                <div>
                  <Label htmlFor="domain_id">Domain</Label>
                  <select
                    id="domain_id"
                    name="domain_id"
                    required
                    value={discoveryDomainId}
                    onChange={(e) => setDiscoveryDomainId(e.target.value)}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">Domain seçin…</option>
                    {verifiedDomains.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.hostname}
                      </option>
                    ))}
                  </select>
                </div>
                <Button
                  type="submit"
                  disabled={!discoveryDomainId || verifiedDomains.length === 0 || isRunning}
                >
                  {isRunning ? "Analiz devam ediyor…" : "Saldırı yüzeyini analiz et"}
                </Button>
              </form>
              {latestJob && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Son keşif: {latestJob.status}
                  {latestJob.target_url ? ` · ${latestJob.target_url}` : ""}
                  {" · "}
                  {latestJob.assets_count} varlık
                  {latestJob.status === "failed" && latestJob.error_log
                    ? ` · ${latestJob.error_log}`
                    : ""}
                </p>
              )}
              {isRunning && activeJobForSelection && (
                <p className="mt-1 text-xs text-yellow-400">
                  Seçili domain için pasif keşif çalışıyor…
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>DNS kayıtları</CardTitle>
              <CardDescription>Kök domain pasif DNS analizi</CardDescription>
            </CardHeader>
            <CardContent className="text-sm">
              {Object.keys(summary?.dns_records ?? {}).length === 0 ? (
                <p className="text-muted-foreground">Henüz DNS verisi yok.</p>
              ) : (
                <dl className="space-y-2">
                  {Object.entries(summary?.dns_records ?? {}).map(([rtype, values]) => (
                    <div key={rtype}>
                      <dt className="font-medium text-foreground">{rtype}</dt>
                      <dd className="font-mono text-xs text-muted-foreground">
                        {values.join(", ")}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Teknoloji tespiti</CardTitle>
            </CardHeader>
            <CardContent>
              {(summary?.technologies ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground">Henüz teknoloji tespit edilmedi.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {summary?.technologies.map((tech) => (
                    <span
                      key={`${tech.category}-${tech.name}`}
                      className="rounded bg-blue-500/15 px-2 py-1 text-xs text-blue-200"
                    >
                      {tech.name}
                      {tech.category ? ` · ${tech.category}` : ""}
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>CDN / WAF</CardTitle>
            </CardHeader>
            <CardContent>
              {(summary?.cdn_waf ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground">CDN/WAF tespit edilmedi.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {summary?.cdn_waf.map((entry) => (
                    <li key={entry.name}>
                      <span className="font-medium">{entry.name}</span>
                      <span className="text-muted-foreground"> ({entry.type})</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Varlık envanteri</CardTitle>
            <CardDescription>
              Domain, alt domain, IP ve servisler — Risk Engine ile skorlanmış
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <Label htmlFor="filter-domain">Domain filtresi</Label>
              <select
                id="filter-domain"
                className="mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value)}
              >
                <option value="">Tümü</option>
                {domains.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.hostname}
                  </option>
                ))}
              </select>
            </div>

            {assets.length === 0 ? (
              <p className="text-muted-foreground">
                Henüz varlık keşfedilmedi. Doğrulanmış bir domain için analiz başlatın.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="py-2 pr-4">Varlık</th>
                      <th className="py-2 pr-4">Tür</th>
                      <th className="py-2 pr-4">Durum</th>
                      <th className="py-2 pr-4">Risk</th>
                      <th className="py-2 pr-4">Teknoloji</th>
                      <th className="py-2">TLS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map((asset) => {
                      const meta = asset.metadata ?? {};
                      const techs = (meta.technologies as Array<{ name?: string }>) ?? [];
                      const tls = meta.tls as { days_until_expiry?: number; valid?: boolean } | undefined;
                      return (
                        <tr key={asset.id} className="border-b border-border/50">
                          <td className="py-3 pr-4">
                            <div className="font-medium">{asset.identifier}</div>
                            {asset.url && (
                              <div className="text-xs text-muted-foreground">{asset.url}</div>
                            )}
                          </td>
                          <td className="py-3 pr-4">{TYPE_LABELS[asset.asset_type] ?? asset.asset_type}</td>
                          <td className={`py-3 pr-4 ${STATUS_COLORS[asset.status] ?? ""}`}>
                            {asset.status}
                          </td>
                          <td className={`py-3 pr-4 font-medium ${riskColor(asset.risk_score)}`}>
                            {asset.risk_score ?? "—"}
                          </td>
                          <td className="py-3 pr-4 text-xs text-muted-foreground">
                            {techs.slice(0, 3).map((t) => t.name).filter(Boolean).join(", ") || "—"}
                          </td>
                          <td className="py-3 text-xs text-muted-foreground">
                            {tls?.valid === false
                              ? "Geçersiz"
                              : tls?.days_until_expiry != null
                                ? `${tls.days_until_expiry} gün`
                                : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}

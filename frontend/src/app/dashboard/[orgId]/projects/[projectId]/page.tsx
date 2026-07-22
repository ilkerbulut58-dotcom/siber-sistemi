"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import {
  apiFetch,
  type Domain,
  type Project,
  type ScanJob,
  type ScanProfile,
  type VerificationInstructions,
} from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ProjectPage() {
  const params = useParams<{ orgId: string; projectId: string }>();
  const { orgId, projectId } = params;
  const { getAccessToken } = useAuth();

  const [project, setProject] = useState<Project | null>(null);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [scans, setScans] = useState<ScanJob[]>([]);
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [instructions, setInstructions] = useState<VerificationInstructions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testMode, setTestMode] = useState(false);

  const load = useCallback(async () => {
    try {
      const healthRes = await fetch(`${getApiBase()}/api/v1/health`);
      const healthBody = await healthRes.json();
      setTestMode(Boolean(healthBody?.data?.skip_domain_verification));

      const [projectData, domainData, scanData, profileData] = await Promise.all([
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
      ]);
      setProject(projectData);
      setDomains(domainData);
      setScans(scanData.filter((s) => s.project_id === projectId));
      setProfiles(profileData);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Veri yüklenemedi";
      if (!/token/i.test(msg)) {
        setError(msg);
      }
    }
  }, [getAccessToken, orgId, projectId]);

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
      setMessage(
        testMode
          ? "Domain eklendi (test modu — otomatik doğrulandı)."
          : "Domain eklendi. Doğrulama talimatlarını alın."
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Domain eklenemedi");
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
      setError(err instanceof Error ? err.message : "Talimatlar alınamadı");
    }
  }

  async function verifyDomain(domainId: string) {
    try {
      const data = await apiFetch<{ message: string; verified: boolean }>(
        `/api/v1/organizations/${orgId}/projects/${projectId}/domains/${domainId}/verify`,
        { method: "POST", token: getAccessToken() }
      );
      setMessage(data.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Doğrulama başarısız");
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
      setMessage("Tarama kuyruğa alındı.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tarama başlatılamadı");
    }
  }

  const verifiedDomains = testMode ? domains : domains.filter((d) => d.is_verified);

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Link href={`/dashboard/${orgId}`} className="text-sm text-muted-foreground hover:underline">
          ← {project?.name || "Proje"}
        </Link>
        <h1 className="mt-2 mb-4 text-3xl font-bold">{project?.name}</h1>
        <div className="mb-6">
          <Link href={`/dashboard/${orgId}/projects/${projectId}/attack-surface`}>
            <Button type="button" variant="outline" size="sm">
              Saldırı Yüzeyi (ASM)
            </Button>
          </Link>
        </div>

        {error && <p className="mb-4 text-destructive">{error}</p>}
        {message && <p className="mb-4 text-green-400">{message}</p>}
        {testMode && (
          <p className="mb-4 rounded-md border border-yellow-500/40 bg-yellow-500/10 px-4 py-2 text-sm text-yellow-200">
            Test modu aktif: DNS doğrulama devre dışı. Domain ekleyince otomatik onaylanır, herhangi
            bir URL tarayabilirsiniz.
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Domain Ekle</CardTitle>
              <CardDescription>
                {testMode
                  ? "Test modu — DNS/meta doğrulama gerekmez"
                  : "Tarama öncesi domain sahipliği doğrulanmalı"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={addDomain} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="hostname">Domain / hostname</Label>
                  <Input id="hostname" name="hostname" placeholder="ornek.com" required />
                </div>
                {!testMode && (
                  <div className="space-y-2">
                    <Label htmlFor="method">Doğrulama yöntemi</Label>
                    <select
                      id="method"
                      name="method"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                      defaultValue="dns_txt"
                    >
                      <option value="dns_txt">DNS TXT</option>
                      <option value="meta_tag">HTML Meta Tag</option>
                      <option value="well_known_file">Well-Known Dosya</option>
                    </select>
                  </div>
                )}
                <Button type="submit">Domain Ekle</Button>
              </form>

              <ul className="mt-6 space-y-3">
                {domains.map((domain) => (
                  <li key={domain.id} className="rounded-md border border-border p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{domain.hostname}</span>
                      <span className={domain.is_verified ? "text-green-400" : "text-yellow-400"}>
                        {domain.is_verified ? "Doğrulandı" : "Bekliyor"}
                      </span>
                    </div>
                    {!testMode && (
                      <div className="mt-2 flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => showInstructions(domain.id)}
                        >
                          Talimatlar
                        </Button>
                        <Button type="button" size="sm" onClick={() => verifyDomain(domain.id)}>
                          Doğrula
                        </Button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>

              {!testMode && instructions && (
                <div className="mt-4 rounded-md bg-muted/30 p-4 text-sm">
                  <p className="mb-2 font-medium">{instructions.hostname} — {instructions.method}</p>
                  <ol className="list-decimal space-y-1 pl-5">
                    {instructions.instructions.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Güvenlik Taraması Başlat (Faz 4)</CardTitle>
              <CardDescription>
                {testMode ? "Test modu — herhangi bir hedef URL" : "Doğrulanmış domain için URL girin"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={startScan} className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="domain_id">Domain</Label>
                  <select
                    id="domain_id"
                    name="domain_id"
                    required
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    defaultValue={verifiedDomains[0]?.id || ""}
                  >
                    <option value="" disabled>
                      {verifiedDomains.length ? "Seçin" : "Önce domain ekleyin"}
                    </option>
                    {verifiedDomains.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.hostname}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="target_url">Hedef URL</Label>
                  <Input
                    id="target_url"
                    name="target_url"
                    type="url"
                    placeholder="https://ornek.com"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="scan_profile">Tarama profili</Label>
                  <select
                    id="scan_profile"
                    name="scan_profile"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    defaultValue="safe"
                  >
                    {profiles.map((p) => (
                      <option key={p.id} value={p.name}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" name="authorization" className="mt-1" required />
                  <span>
                    Bu hedefi tarama yetkisine sahip olduğumu ve yalnızca doğrulanmış domain
                    üzerinde test yapacağımı onaylıyorum.
                  </span>
                </label>
                <Button type="submit" disabled={verifiedDomains.length === 0}>
                  Taramayı Başlat
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Taramalar</CardTitle>
          </CardHeader>
          <CardContent>
            {scans.length === 0 ? (
              <p className="text-muted-foreground">Henüz tarama yok.</p>
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
                        {scan.scan_profile} · {scan.status} · {scan.findings_count} bulgu
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

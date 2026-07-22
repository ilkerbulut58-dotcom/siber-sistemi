"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, type QuickScanResult, type ScanJob, type ScanProfile } from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { scanProfileLabel, SCAN_STATUS_TR } from "@/lib/i18n-tr";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function QuickScanPage() {
  const router = useRouter();
  const { getAccessToken } = useAuth();
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [recentScans, setRecentScans] = useState<ScanJob[]>([]);
  const [testMode, setTestMode] = useState(true);
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
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Veri yüklenemedi");
    }
  }, [getAccessToken]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 6000);
    return () => clearInterval(timer);
  }, [load]);

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
      setError(err instanceof Error ? err.message : "Tarama başlatılamadı");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-3xl px-4 py-8">
        <h1 className="mb-2 text-3xl font-bold">Güvenlik Taraması</h1>
        <p className="mb-6 text-muted-foreground">
          Web sitenizin URL&apos;sini girin — domain ve proje ayarları otomatik yapılır.
        </p>

        {testMode && (
          <p className="mb-4 rounded-md border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm text-green-200">
            Hazır test modu: DNS doğrulama gerekmez. URL girip taramayı başlatabilirsiniz.
          </p>
        )}

        {error && <p className="mb-4 text-destructive">{error}</p>}

        <Card>
          <CardHeader>
            <CardTitle>Hedef site</CardTitle>
            <CardDescription>
              Örnek: https://siteniz.com veya https://localhost:3000
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="target_url">Site URL</Label>
                <Input
                  id="target_url"
                  name="target_url"
                  type="url"
                  placeholder="https://ornek.com"
                  required
                  autoFocus
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
                      {scanProfileLabel(p.name, p.display_name)}
                    </option>
                  ))}
                  {profiles.length === 0 && <option value="safe">Güvenli (Safe)</option>}
                </select>
              </div>
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" name="authorization" className="mt-1" required defaultChecked />
                <span>
                  Bu siteyi tarama yetkisine sahip olduğumu onaylıyorum.
                </span>
              </label>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Tarama başlatılıyor..." : "Taramayı Başlat"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {recentScans.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Son taramalar</CardTitle>
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
                        {SCAN_STATUS_TR[scan.status] ?? scan.status ?? "Bilinmiyor"} ·{" "}
                        {scan.findings_count} bulgu
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
            ← Güvenlik paneline dön
          </Link>
        </p>
      </main>
    </>
  );
}

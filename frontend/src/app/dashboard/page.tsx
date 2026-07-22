"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  Globe,
  Radar,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import {
  apiFetch,
  type Organization,
  type ScanJob,
  type SupportGrant,
} from "@/lib/api-client";
import { SCAN_STATUS_TR } from "@/lib/i18n-tr";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const QUICK_ACTIONS = [
  {
    href: "/dashboard/assessment",
    title: "Tam Değerlendirme",
    description: "Web + saldırı yüzeyi + mobil APK birlikte",
    icon: ShieldCheck,
    primary: true,
  },
  {
    href: "/dashboard/scan",
    title: "Web Tarama",
    description: "Tek URL ile hızlı güvenlik taraması",
    icon: Globe,
  },
  {
    href: "/dashboard/mobile",
    title: "Mobil APK",
    description: "Android statik analiz",
    icon: Smartphone,
  },
] as const satisfies ReadonlyArray<{
  href: string;
  title: string;
  description: string;
  icon: typeof ShieldCheck;
  primary?: boolean;
}>;

export default function DashboardPage() {
  const { getAccessToken, user } = useAuth();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [customerOrgs, setCustomerOrgs] = useState<Organization[]>([]);
  const [supportGrants, setSupportGrants] = useState<SupportGrant[]>([]);
  const [recentScans, setRecentScans] = useState<ScanJob[]>([]);
  const [showAdmin, setShowAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
      setError(err instanceof Error ? err.message : "Veri yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, [getAccessToken, user?.is_platform_admin]);

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
      setError(err instanceof Error ? err.message : "Organizasyon oluşturulamadı");
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
      setError(err instanceof Error ? err.message : "Yönetilen çalışma alanı oluşturulamadı");
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
      setError(err instanceof Error ? err.message : "Support erişimi oluşturulamadı");
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
      setError(err instanceof Error ? err.message : "Support erişimi iptal edilemedi");
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto space-y-8 px-4 py-8">
        <div>
          <h1 className="text-3xl font-bold">Güvenlik Paneli</h1>
          <p className="mt-2 text-muted-foreground">
            Hoş geldiniz{user?.full_name ? `, ${user.full_name}` : ""}. Testleri tek tek veya tam
            değerlendirme olarak başlatın.
          </p>
        </div>

        {error && <p className="text-destructive">{error}</p>}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {QUICK_ACTIONS.map(({ href, title, description, icon: Icon, ...rest }) => (
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
                  Saldırı Yüzeyi
                </CardTitle>
                <CardDescription>Proje bazında varlık keşfi</CardDescription>
              </div>
              <Link href={`/dashboard/${orgs[0].id}`}>
                <Button variant="outline" size="sm">
                  Projeler →
                </Button>
              </Link>
            </CardHeader>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Son Taramalar</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-muted-foreground">Yükleniyor…</p>
              ) : recentScans.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Henüz tarama yok.{" "}
                  <Link href="/dashboard/scan" className="underline">
                    İlk taramayı başlatın
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
                        <p className="font-medium truncate">{scan.target_url}</p>
                        <p className="text-xs text-muted-foreground">
                          {SCAN_STATUS_TR[scan.status] ?? scan.status} · {scan.findings_count} bulgu
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
              <CardTitle>Organizasyonlar</CardTitle>
              <form onSubmit={createOrg} className="flex gap-2">
                <Input name="name" required placeholder="Yeni org adı" className="h-9 w-40" />
                <Button type="submit" size="sm">
                  Ekle
                </Button>
              </form>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-muted-foreground">Yükleniyor…</p>
              ) : orgs.length === 0 ? (
                <p className="text-muted-foreground">Henüz organizasyon yok.</p>
              ) : (
                <ul className="space-y-2">
                  {orgs.map((org) => (
                    <li key={org.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                      <div>
                        <p className="font-medium">{org.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {org.is_managed_workspace ? "Yönetilen alan" : org.slug}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Link href={`/dashboard/${org.id}/mobile`}>
                          <Button variant="outline" size="sm">
                            Mobil
                          </Button>
                        </Link>
                        <Link href={`/dashboard/${org.id}`}>
                          <Button variant="outline" size="sm">
                            Aç
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
                <CardTitle>Platform Yönetimi</CardTitle>
                <CardDescription>Yönetilen alanlar ve müşteri support erişimi</CardDescription>
              </div>
              <div className="flex gap-2">
                <Link href="/dashboard/platform/quality">
                  <Button variant="outline" size="sm">Kalite Lab</Button>
                </Link>
                <Button variant="outline" size="sm" onClick={() => setShowAdmin((v) => !v)}>
                  {showAdmin ? "Gizle" : "Göster"}
                </Button>
              </div>
            </CardHeader>
            {showAdmin && (
              <CardContent className="grid gap-6 lg:grid-cols-2">
                <form onSubmit={createManagedWorkspace} className="space-y-3 rounded-md border border-border p-4">
                  <p className="font-medium text-sm">Yönetilen çalışma alanı</p>
                  <Input name="name" required placeholder="Örn: Müşteri denetimi" />
                  <Button type="submit" size="sm">
                    Oluştur
                  </Button>
                </form>

                <form onSubmit={createSupportGrant} className="space-y-3 rounded-md border border-border p-4">
                  <p className="font-medium text-sm">Müşteri support erişimi</p>
                  <select
                    name="organization_id"
                    required
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">Organizasyon…</option>
                    {customerOrgs.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                  <Input name="reason" required minLength={10} placeholder="Gerekçe" />
                  <Input name="duration_hours" type="number" min={1} max={168} defaultValue={24} />
                  <Button type="submit" size="sm">
                    Erişim ver
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
                            İptal
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

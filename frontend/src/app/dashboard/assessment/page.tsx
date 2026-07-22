"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
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
  type AsmDiscoveryJob,
  type MobileUploadResult,
  type Organization,
  type Project,
  type QuickScanResult,
  type ScanProfile,
} from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { scanProfileLabel } from "@/lib/i18n-tr";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type AssessmentResult = {
  label: string;
  status: "success" | "error" | "skipped";
  href?: string;
  message?: string;
};

export default function AssessmentPage() {
  const router = useRouter();
  const { getAccessToken } = useAuth();
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [testMode, setTestMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AssessmentResult[]>([]);
  const [runWeb, setRunWeb] = useState(true);
  const [runAsm, setRunAsm] = useState(true);
  const [runMobile, setRunMobile] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const token = getAccessToken();
      const health = await fetch(`${getApiBase()}/api/v1/health`).then((r) => r.json());
      setTestMode(Boolean(health?.data?.skip_domain_verification));

      const [profileData, orgData] = await Promise.all([
        apiFetch<ScanProfile[]>("/api/v1/scan-profiles", { token }),
        apiFetch<Organization[]>("/api/v1/organizations", { token }),
      ]);
      setProfiles(profileData);
      setOrgs(orgData);
      if (orgData[0] && !selectedOrgId) {
        setSelectedOrgId(orgData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Veri yüklenemedi");
    }
  }, [getAccessToken, selectedOrgId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedOrgId) {
      setProjects([]);
      setSelectedProjectId("");
      return;
    }
    void apiFetch<Project[]>(`/api/v1/organizations/${selectedOrgId}/projects`, {
      token: getAccessToken(),
    })
      .then((data) => {
        setProjects(data);
        setSelectedProjectId(data[0]?.id ?? "");
      })
      .catch(() => {
        setProjects([]);
        setSelectedProjectId("");
      });
  }, [selectedOrgId, getAccessToken]);

  async function uploadApk(
    orgId: string,
    projectId: string,
    file: File
  ): Promise<MobileUploadResult> {
    const token = getAccessToken();
    const form = new FormData();
    form.append("project_id", projectId);
    form.append("environment", "staging");
    form.append("authorization_accepted", "true");
    form.append("file", file);
    const res = await fetch(
      `${getApiBase()}/api/v1/organizations/${orgId}/mobile/applications`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      }
    );
    const body = await res.json();
    if (!res.ok || !body.success) {
      throw new Error(body.error?.message || "APK yüklenemedi");
    }
    return body.data as MobileUploadResult;
  }

  async function runAssessment(
    e: FormEvent<HTMLFormElement>,
    mode: "full" | "web" | "asm" | "mobile"
  ) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResults([]);

    const form = new FormData(e.currentTarget);
    const targetUrl = String(form.get("target_url") || "");
    const scanProfile = String(form.get("scan_profile") || "safe");
    const authorized = form.get("authorization") === "on";
    const apkFile = (form.get("apk") as File | null)?.size
      ? (form.get("apk") as File)
      : null;

    const doWeb = mode === "full" ? runWeb : mode === "web";
    const doAsm = mode === "full" ? runAsm : mode === "asm";
    const doMobile = mode === "full" ? runMobile : mode === "mobile";

    const nextResults: AssessmentResult[] = [];

    try {
      if (!authorized && (doWeb || doAsm)) {
        throw new Error("Web ve saldırı yüzeyi testleri için yetkilendirme onayı gerekli.");
      }
      if (doMobile && !apkFile) {
        throw new Error("Mobil analiz için APK dosyası seçin.");
      }
      if (doMobile && !doWeb && (!selectedOrgId || !selectedProjectId)) {
        throw new Error("Mobil-only tarama için organizasyon ve proje seçin.");
      }
      if ((doWeb || doAsm) && !targetUrl) {
        throw new Error("Web testleri için hedef URL girin.");
      }

      let orgId = selectedOrgId;
      let projectId = selectedProjectId;
      let domainId: string | null = null;
      let scanHref: string | undefined;
      let asmHref: string | undefined;
      let mobileHref: string | undefined;

      if (doWeb || doAsm) {
        const quick = await apiFetch<QuickScanResult>("/api/v1/quick-scan", {
          method: "POST",
          token: getAccessToken(),
          body: JSON.stringify({
            target_url: targetUrl,
            scan_profile: scanProfile,
            authorization_accepted: authorized,
          }),
        });
        orgId = quick.organization_id;
        projectId = quick.project_id;
        domainId = quick.domain_id;
        scanHref = `/dashboard/${orgId}/scans/${quick.scan.id}`;

        if (doWeb) {
          nextResults.push({
            label: "Web güvenlik taraması",
            status: "success",
            href: scanHref,
            message: "Tarama başlatıldı",
          });
        } else {
          nextResults.push({
            label: "Web güvenlik taraması",
            status: "skipped",
            message: "Tam taramada web adımı atlandı",
          });
        }
      }

      if (doAsm && orgId && projectId && domainId) {
        const asm = await apiFetch<AsmDiscoveryJob>(
          `/api/v1/organizations/${orgId}/projects/${projectId}/asm/discover`,
          {
            method: "POST",
            token: getAccessToken(),
            body: JSON.stringify({
              domain_id: domainId,
              target_url: targetUrl,
              authorization_accepted: authorized,
            }),
          }
        );
        asmHref = `/dashboard/${orgId}/projects/${projectId}/attack-surface`;
        nextResults.push({
          label: "Saldırı yüzeyi keşfi",
          status: "success",
          href: asmHref,
          message: `Keşif job #${asm.id.slice(0, 8)} başlatıldı`,
        });
      }

      if (doMobile && apkFile && orgId && projectId) {
        const mobile = await uploadApk(orgId, projectId, apkFile);
        mobileHref = `/dashboard/${orgId}/mobile`;
        nextResults.push({
          label: "Mobil APK analizi",
          status: "success",
          href: mobileHref,
          message: mobile.duplicate ? "Mevcut APK — analiz yenilendi" : "APK yüklendi, analiz başladı",
        });
      }

      setResults(nextResults);

      if (mode === "web" && scanHref) {
        router.push(scanHref);
        return;
      }
      if (mode === "asm" && asmHref) {
        router.push(asmHref);
        return;
      }
      if (mode === "mobile" && mobileHref) {
        router.push(mobileHref);
        return;
      }
      if (mode === "full" && scanHref) {
        router.push(scanHref);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Değerlendirme başlatılamadı");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-3xl font-bold">Güvenlik Değerlendirmesi</h1>
          <p className="mt-2 text-muted-foreground">
            Web, saldırı yüzeyi ve mobil testleri tek tek veya tam değerlendirme olarak başlatın.
          </p>
        </div>

        {testMode && (
          <p className="rounded-md border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm text-green-200">
            Test modu aktif — DNS doğrulama gerekmez.
          </p>
        )}

        {error && <p className="text-destructive">{error}</p>}

        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: Globe, title: "Web", desc: "HTTP, header, Nuclei" },
            { icon: Radar, title: "Saldırı Yüzeyi", desc: "Alt domain ve varlık keşfi" },
            { icon: Smartphone, title: "Mobil APK", desc: "Statik manifest analizi" },
          ].map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="border-border/60 bg-card/80">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Icon className="h-4 w-4 text-primary" />
                  {title}
                </CardTitle>
                <CardDescription>{desc}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary" />
              Değerlendirme Ayarları
            </CardTitle>
            <CardDescription>
              Tam tarama seçili adımları sırayla başlatır; tek tek butonlar yalnızca ilgili testi çalıştırır.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              ref={formRef}
              onSubmit={(e) => runAssessment(e, "full")}
              className="space-y-5"
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="target_url">Hedef URL (web / ASM)</Label>
                  <Input
                    id="target_url"
                    name="target_url"
                    type="url"
                    placeholder="https://ornek.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="scan_profile">Web tarama profili</Label>
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
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="org">Organizasyon (mobil-only)</Label>
                  <select
                    id="org"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={selectedOrgId}
                    onChange={(e) => setSelectedOrgId(e.target.value)}
                  >
                    <option value="">Otomatik (web taramasından)</option>
                    {orgs.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="project">Proje (mobil-only)</Label>
                  <select
                    id="project"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={selectedProjectId}
                    onChange={(e) => setSelectedProjectId(e.target.value)}
                    disabled={!selectedOrgId}
                  >
                    <option value="">Seçin…</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="apk">APK dosyası (isteğe bağlı)</Label>
                <Input
                  id="apk"
                  name="apk"
                  type="file"
                  accept=".apk,application/vnd.android.package-archive"
                />
              </div>

              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={runWeb}
                    onChange={(e) => setRunWeb(e.target.checked)}
                  />
                  Web tarama
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={runAsm}
                    onChange={(e) => setRunAsm(e.target.checked)}
                  />
                  Saldırı yüzeyi
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={runMobile}
                    onChange={(e) => setRunMobile(e.target.checked)}
                  />
                  Mobil APK
                </label>
              </div>

              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" name="authorization" className="mt-1" defaultChecked />
                <span>Bu varlıkları test etme yetkisine sahip olduğumu onaylıyorum.</span>
              </label>

              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={loading}>
                  {loading ? "Başlatılıyor…" : "Tam Değerlendirme Başlat"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={() => {
                    if (formRef.current) {
                      void runAssessment(
                        { preventDefault: () => {}, currentTarget: formRef.current } as FormEvent<HTMLFormElement>,
                        "web"
                      );
                    }
                  }}
                >
                  Yalnızca Web
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={() => {
                    if (formRef.current) {
                      void runAssessment(
                        { preventDefault: () => {}, currentTarget: formRef.current } as FormEvent<HTMLFormElement>,
                        "asm"
                      );
                    }
                  }}
                >
                  Yalnızca ASM
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={() => {
                    if (formRef.current) {
                      void runAssessment(
                        { preventDefault: () => {}, currentTarget: formRef.current } as FormEvent<HTMLFormElement>,
                        "mobile"
                      );
                    }
                  }}
                >
                  Yalnızca Mobil
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {results.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Sonuçlar</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {results.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium">{item.label}</p>
                    {item.message && (
                      <p className="text-xs text-muted-foreground">{item.message}</p>
                    )}
                  </div>
                  {item.href && (
                    <Link href={item.href} className="text-primary underline">
                      Görüntüle
                    </Link>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </main>
    </>
  );
}

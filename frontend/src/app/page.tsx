import Link from "next/link";
import { Shield, ArrowRight } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { RedirectIfAuthed } from "@/components/redirect-if-authed";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchHealth, fetchReadiness } from "@/lib/api";

async function getSystemStatus() {
  try {
    const [health, readiness] = await Promise.all([fetchHealth(), fetchReadiness()]);
    return { health, readiness, error: null };
  } catch {
    return { health: null, readiness: null, error: "API bağlantısı kurulamadı" };
  }
}

export default async function HomePage() {
  const { health, readiness, error } = await getSystemStatus();

  return (
    <>
      <RedirectIfAuthed />
      <Navbar />
      <main className="min-h-screen">
        <div className="container mx-auto px-4 py-12">
          <div className="mb-12 text-center">
            <h1 className="mb-4 text-4xl font-bold tracking-tight">
              Web Uygulama Güvenlik Analizi
            </h1>
            <p className="mx-auto mb-8 max-w-2xl text-lg text-muted-foreground">
              Yetkilendirilmiş domainleriniz için otomatik güvenlik taraması, bulgu yönetimi ve
              yapay zekâ destekli raporlama platformu.
            </p>
            <div className="flex justify-center gap-3">
              <Link href="/register">
                <Button size="lg">
                  Başla <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/login">
                <Button size="lg" variant="outline">
                  Giriş Yap
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  API Durumu
                </CardTitle>
                <CardDescription>Backend servis sağlık kontrolü</CardDescription>
              </CardHeader>
              <CardContent>
                {error ? (
                  <p className="text-destructive">{error}</p>
                ) : health?.data ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Durum</span>
                      <span className="font-medium text-green-400">{health.data.status}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Ortam</span>
                      <span>{health.data.environment}</span>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Altyapı</CardTitle>
                <CardDescription>Veritabanı ve Redis</CardDescription>
              </CardHeader>
              <CardContent>
                {readiness?.data ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Genel</span>
                      <span className="text-green-400">{readiness.data.status}</span>
                    </div>
                    {Object.entries(readiness.data.checks).map(([name, status]) => (
                      <div key={name} className="flex justify-between capitalize">
                        <span className="text-muted-foreground">{name}</span>
                        <span className={status === "ok" ? "text-green-400" : "text-destructive"}>
                          {status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">Kontrol edilemiyor</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Platform Fazları</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="text-green-400">✓ Faz 1-2: Altyapı + Auth</li>
                  <li className="text-green-400">✓ Faz 3: Domain doğrulama</li>
                  <li className="text-green-400">✓ Faz 6: AI özet, bulgu yönetimi, test modu</li>
                  <li className="text-yellow-400">○ Faz 7+: Raporlar, ZAP worker</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </>
  );
}
